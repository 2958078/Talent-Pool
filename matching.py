import json
DEFAULT_WEIGHTS={'required':45,'desired':10,'experience':15,'seniority':8,'availability':10,'location':5,'dedication':3,'domain':2,'languages':1,'certifications':1}
RANK={'Sin definir':0,'Junior':1,'Mid':2,'Senior':3,'Lead':4}
def score(candidate,criteria,weights=None,bands=None):
    w=weights or DEFAULT_WEIGHTS; skills=set(json.loads(candidate['skills'])); req=set(criteria.get('required',[])); des=set(criteria.get('desired',[]))
    parts={}
    parts['required']=w['required']*(len(skills&req)/len(req) if req else 1)
    parts['desired']=w['desired']*(len(skills&des)/len(des) if des else 1)
    years=int(candidate['years']); minimum=int(criteria.get('years',0)); parts['experience']=w['experience']*min(1,years/max(1,minimum))
    parts['seniority']=w['seniority'] if RANK.get(candidate['seniority'],0)>=RANK.get(criteria.get('seniority','Sin definir'),0) else 0
    parts['availability']=w['availability']*min(1,int(candidate['availability'])/max(1,int(criteria.get('dedication',100))))
    parts['location']=w['location'] if criteria.get('location','').lower() in ('','remoto',candidate['location'].lower()) else w['location']*.4
    parts['dedication']=w['dedication']*min(1,int(candidate['availability'])/max(1,int(criteria.get('dedication',100))))
    parts['domain']=w['domain']*min(1,int(candidate['domain_years'])/max(1,int(criteria.get('domain_years',0) or 1)))
    langs=set(json.loads(candidate['languages'])); need=set(criteria.get('languages',[])); parts['languages']=w['languages']*(len(langs&need)/len(need) if need else 1)
    certs=set(json.loads(candidate['certifications'])); needc=set(criteria.get('certifications',[])); parts['certifications']=w['certifications']*(len(certs&needc)/len(needc) if needc else 1)
    total=round(sum(parts.values()),1); bands=bands or {'top1':90,'top2':75}; tier='Top 1' if total>=bands['top1'] else ('Top 2' if total>=bands['top2'] else 'Top 3')
    missing=sorted(req-skills); covered=sorted((req|des)&skills)
    return {'score':total,'tier':tier,'dimensions':{k:round(v,1) for k,v in parts.items()},'covered':covered,'missing':missing,'filters':[] if not missing else ['Capacidades obligatorias incompletas'],'model_version':'rules-v1.0','evidence':[f'Habilidad declarada: {x}' for x in covered],'human_review_required':True}
