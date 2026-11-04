import os
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4
import httpx
from psycopg import sql
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from auth import HASHER
from storage.repository import Repository
from tests.test_storage import RESULT

root=Path(__file__).resolve().parents[2]
schema='watchdemo_test_'+uuid4().hex
repo=Repository(os.environ['WATCHDEMO_TEST_DATABASE_URL'],schema)
repo.migrate()
user_id,match_id=uuid4(),uuid4()
with repo.connect() as conn:
    conn.execute('INSERT INTO users VALUES (%s,%s,%s,%s,now())',(user_id,'browser@example.com','Browser User',HASHER.hash('Browser-Password-123')))
repo.create_match(match_id,'browser.dem',[],user_id)
with repo.analysis(match_id,'123','Тестовый игрок') as report_id:
    result=deepcopy(RESULT)
    result["report"]["summary"]["adr"]=42.5
    repo.complete_report(report_id,result)
api_port=int(os.getenv('WATCHDEMO_QA_API_PORT','8000'))
site_port=int(os.getenv('WATCHDEMO_QA_SITE_PORT','5173'))
site=f'http://127.0.0.1:{site_port}'
api=f'http://127.0.0.1:{api_port}'
env={**os.environ,'WATCHDEMO_COOKIE_SECURE':'false','WATCHDEMO_ALLOWED_ORIGINS':site,'VITE_API_URL':api,'WATCHDEMO_QA_SITE_URL':site}
code=f"import uvicorn; from app import create_app; from storage.repository import Repository; uvicorn.run(create_app(repository=Repository({repo.database_url!r},{schema!r}),upload_dir={str(root/'.test-tools/browser-uploads')!r}),host='127.0.0.1',port={api_port})"
processes=[]
try:
    with (root/'review-accounts/browser-servers.log').open('w') as log:
        processes.append(subprocess.Popen([sys.executable,'-c',code],cwd=root/'backend',env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW))
        processes.append(subprocess.Popen(['node',str(root/'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',str(site_port),'--strictPort'],cwd=root/'frontend',env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW))
        with httpx.Client(trust_env=False,timeout=1) as client:
            for attempt in range(100):
                try:
                    if client.get(api+'/health').status_code==200 and client.get(site).status_code==200: break
                except httpx.TransportError: pass
                time.sleep(.2)
            else: raise RuntimeError('Test servers did not start')
        subprocess.run(['node',str(root/'tools/qa_accounts/browser.cjs')],check=True,env=env)
finally:
    for process in processes:
        process.terminate();process.wait(timeout=15)
    with repo.connect() as conn:
        conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
