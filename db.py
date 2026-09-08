import sqlite3, json, uuid
from pathlib import Path
DB=Path(__file__).resolve().parent.parent/'talent_pool.db'
def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS vacancies(id TEXT PRIMARY KEY,title TEXT NOT NULL,summary TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL,ats_id TEXT,created_by TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS candidates(id TEXT PRIMARY KEY,role TEXT,years INTEGER,availability INTEGER,location TEXT,seniority TEXT,skills TEXT,domain_years INTEGER DEFAULT 0,languages TEXT DEFAULT '[]',certifications TEXT DEFAULT '[]');
        CREATE TABLE IF NOT EXISTS selections(vacancy_id TEXT,candidate_id TEXT,reason TEXT,status TEXT,created_by TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(vacancy_id,candidate_id));
        CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY,actor TEXT,role TEXT,action TEXT,entity TEXT,entity_id TEXT,detail TEXT,correlation_id TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS idempotency(key TEXT PRIMARY KEY,response TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        """)
        if c.execute('SELECT COUNT(*) n FROM candidates').fetchone()['n']==0:
            rows=[
            ('C-001','Lider tecnico',12,40,'Remoto','Lead',['Java','Microservicios','Arquitectura','Spring','AWS'],8,['Ingles'],['AWS Architect']),
            ('C-002','Desarrollo Full Stack',8,80,'Remoto','Senior',['Java','JavaScript','Angular','Microservicios','PostgreSQL'],5,['Ingles'],[]),
            ('C-003','Arquitectura de soluciones',10,60,'Hibrido','Lead',['Arquitectura','AWS','Cloud','Java','Kubernetes'],9,['Ingles'],['TOGAF']),
            ('C-004','Ingenieria Backend',6,100,'Remoto','Senior',['Java','Spring','PostgreSQL','Microservicios'],4,[],[]),
            ('C-005','Ingenieria Frontend',5,80,'Remoto','Mid',['JavaScript','Angular','AWS'],2,[],[]),
            ('C-006','DevOps Cloud',5,100,'Hibrido','Senior',['AWS','Kubernetes','Monitoreo','Cloud'],4,['Ingles'],['AWS Associate']),
            ('C-007','Analisis de infraestructura',3,100,'Remoto','Mid',['Monitoreo','Cloud','Kubernetes'],3,[],[]),
            ('C-008','Desarrollo Junior',2,100,'Remoto','Junior',['Java','JavaScript','SQL'],1,[],[]),
            ('C-009','Analisis de datos',4,60,'Hibrido','Mid',['SQL','PostgreSQL','Cloud'],3,[],[])]
            c.executemany('INSERT INTO candidates VALUES(?,?,?,?,?,?,?,?,?,?)',[(a,b,d,e,f,g,json.dumps(h),i,json.dumps(j),json.dumps(k)) for a,b,d,e,f,g,h,i,j,k in rows])
def audit(actor,role,action,entity,entity_id,detail='',correlation_id=''):
    with conn() as c:c.execute('INSERT INTO audit(id,actor,role,action,entity,entity_id,detail,correlation_id) VALUES(?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),actor,role,action,entity,entity_id,detail[:1000],correlation_id))
