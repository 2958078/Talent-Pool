from fastapi import FastAPI,UploadFile,File,Form,Header,HTTPException,Request
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from typing import Optional
import json,uuid,hashlib,zipfile,io,re
from .db import init,conn,audit
from .matching import score,DEFAULT_WEIGHTS
app=FastAPI(title='Talent Pool API',version='1.0.0'); init()
ROLES={'reclutador','hiring_manager','administrador','auditor','integrador'}
def auth(role,user,allowed=None):
    if role not in ROLES: raise HTTPException(401,'Rol no valido')
    if allowed and role not in allowed: raise HTTPException(403,'Permisos insuficientes')
    return user
@app.get('/')
def home():return FileResponse('app/static/index.html')
@app.get('/health')
def health():return {'status':'ok','version':'1.0.0'}
ALLOWED={'application/pdf':'.pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document':'.docx','text/plain':'.txt','text/markdown':'.md'}
@app.post('/api/v1/documents/extract')
async def extract(file:UploadFile=File(...),x_role:str=Header('reclutador'),x_user:str=Header('demo.user')):
    auth(x_role,x_user,{'reclutador','administrador'}); data=await file.read()
    if len(data)>20*1024*1024: raise HTTPException(413,'Archivo superior a 20 MB')
    ext='.'+file.filename.rsplit('.',1)[-1].lower() if '.' in file.filename else ''
    expected=ALLOWED.get(file.content_type)
    if not expected or (ext not in (expected,'.markdown') and not(expected=='.md' and ext=='.markdown')): raise HTTPException(415,'Tipo MIME o extension no permitidos')
    try:
        if ext in ('.txt','.md','.markdown'): text=data.decode('utf-8')
        elif ext=='.docx':
            with zipfile.ZipFile(io.BytesIO(data)) as z: text=re.sub(r'<[^>]+>',' ',z.read('word/document.xml').decode('utf-8'))
        else:
            from pypdf import PdfReader
            r=PdfReader(io.BytesIO(data)); text='
'.join((p.extract_text() or '') for p in r.pages)
            if not text.strip(): return {'status':'ocr_required','message':'PDF sin texto detectable. En piloto empresarial debe enviarse al servicio OCR aprobado.','confidence':0,'text':''}
    except Exception: raise HTTPException(422,'Archivo corrupto, cifrado o no procesable')
    skills=[s for s in ['Java','JavaScript','AWS','Microservicios','Arquitectura','Angular','Spring','PostgreSQL','Kubernetes','Monitoreo','SQL','Python','Azure'] if s.lower() in text.lower()]
    result={'status':'extracted','title':next((x.strip() for x in text.splitlines() if len(x.strip())>8),'Vacante sin titulo confirmado')[:100],'summary':text.strip()[:700],'required':skills[:5],'desired':skills[5:10],'confidence':round(min(.98,.45+len(skills)*.07),2),'evidence':skills,'hash':hashlib.sha256(data).hexdigest()}
    audit(x_user,x_role,'DOCUMENT_EXTRACTED','document',result['hash'],f'filename={file.filename}; size={len(data)}')
    return result
class MatchRequest(BaseModel):
    required:list[str]=[];desired:list[str]=[];years:int=0;seniority:str='Sin definir';dedication:int=100;location:str='Remoto';domain_years:int=0;languages:list[str]=[];certifications:list[str]=[];weights:Optional[dict]=None;bands:Optional[dict]=None
@app.post('/api/v1/matches')
def matches(q:MatchRequest,x_role:str=Header('reclutador'),x_user:str=Header('demo.user'),x_correlation_id:str=Header(default_factory=lambda:str(uuid.uuid4()))):
    auth(x_role,x_user); criteria=q.model_dump();
    with conn() as c: rows=c.execute('SELECT * FROM candidates').fetchall()
    results=[]
    for r in rows:
        m=score(r,criteria,q.weights,q.bands); results.append({'id':r['id'],'role':r['role'],'years':r['years'],'availability':r['availability'],'location':r['location'],'seniority':r['seniority'],**m})
    results.sort(key=lambda x:(-x['score'],x['id'])); audit(x_user,x_role,'MATCH_EXECUTED','match',x_correlation_id,json.dumps({'criteria':criteria,'count':len(results)}),x_correlation_id)
    return {'correlation_id':x_correlation_id,'results':results,'weights':q.weights or DEFAULT_WEIGHTS,'disclaimer':'El ranking apoya la revision humana y no constituye una decision automatizada final.'}
class Vacancy(BaseModel):
    title:str=Field(min_length=3);summary:str=Field(min_length=10);area:str='Tecnologia';hiring_manager:str;recruiter:str;required:list[str]=[];desired:list[str]=[];seniority:str='Sin definir';years:int=0;modality:str='Remoto';location:str='';dedication:int=100;contract_type:str='Tiempo completo';positions:int=1;start_date:Optional[str]=None;end_date:Optional[str]=None;status:str='Borrador';candidate_ids:list[str]=[];source:str='Texto';created_by:str='demo.user'
@app.post('/api/v1/vacancies')
def create_vacancy(v:Vacancy,idempotency_key:str=Header(...,alias='Idempotency-Key'),x_role:str=Header('reclutador'),x_user:str=Header('demo.user')):
    auth(x_role,x_user,{'reclutador','administrador','integrador'})
    with conn() as c:
        old=c.execute('SELECT response FROM idempotency WHERE key=?',(idempotency_key,)).fetchone()
        if old:return json.loads(old['response'])
        vid='VAC-'+uuid.uuid4().hex[:8].upper(); payload=v.model_dump(); response={'id':vid,'status':'Borrador','integration_status':'PENDING_CONFIGURATION','message':'Guardada localmente. La integracion ATS real no esta configurada; no se afirma creacion externa.'}
        c.execute('INSERT INTO vacancies(id,title,summary,status,payload,created_by) VALUES(?,?,?,?,?,?)',(vid,v.title,v.summary,'Borrador',json.dumps(payload),x_user))
        for cid in v.candidate_ids:c.execute('INSERT OR IGNORE INTO selections(vacancy_id,candidate_id,reason,status,created_by) VALUES(?,?,?,?,?)',(vid,cid,'Seleccion inicial','Seleccionado',x_user))
        c.execute('INSERT INTO idempotency(key,response) VALUES(?,?)',(idempotency_key,json.dumps(response)))
    audit(x_user,x_role,'VACANCY_CREATED_LOCAL','vacancy',vid,'ATS pending')
    return response
@app.get('/api/v1/vacancies')
def list_vacancies(x_role:str=Header('reclutador'),x_user:str=Header('demo.user')):
    auth(x_role,x_user)
    with conn() as c:return [dict(r) for r in c.execute('SELECT id,title,status,ats_id,created_by,created_at FROM vacancies ORDER BY created_at DESC').fetchall()]
@app.get('/api/v1/audit')
def audit_log(x_role:str=Header('auditor'),x_user:str=Header('demo.auditor')):
    auth(x_role,x_user,{'auditor','administrador'})
    with conn() as c:return [dict(r) for r in c.execute('SELECT * FROM audit ORDER BY created_at DESC LIMIT 200').fetchall()]
