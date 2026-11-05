"""Isolated browser acceptance, optional saved real-demo result, no app DB changes."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import socket
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
from tests.test_ivr_review import OpeningLibrary, death
from tests.test_buy_mismatch import FakeLibrary as BuyLibrary
from tests.test_missed_trade_candidates import FakeLibrary as TradeLibrary
from detectors.entry_death import detect_entry_deaths
from detectors.buy_mismatch import detect_buy_mismatch
from detectors.missed_trade import get_possible_missed_trades
from review_findings import build_review_findings, prioritize_reviews
import pandas as pd


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--real-result', type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
root = Path(__file__).resolve().parents[2]
schema = 'watchdemo_test_' + uuid4().hex
repo = Repository(os.environ['WATCHDEMO_TEST_DATABASE_URL'], schema)
repo.migrate()
processes = []
try:
    user_id, match_id = uuid4(), uuid4()
    with repo.connect() as conn:
        conn.execute('INSERT INTO users VALUES (%s,%s,%s,%s,now())',
                     (user_id, 'ivr-browser@example.com', 'IVR Browser', HASHER.hash('IVR-browser-password-123')))
    repo.create_match(match_id, 'synthetic-browser.dem', [], user_id)
    result = deepcopy(RESULT)
    entries = detect_entry_deaths(OpeningLibrary(), '123', pd.DataFrame([death()]))
    trades = get_possible_missed_trades('123', pd.DataFrame([death(victim='456')]), TradeLibrary())
    trades[0].update(round=2, tick=1150)
    buys = detect_buy_mismatch(BuyLibrary(), '123')
    buys[0].update(round=3, tick=2064)
    findings = build_review_findings(entries, trades, buys)
    result['report'].update(review_findings=findings, top_problems=prioritize_reviews(findings), map='de_nuke')
    result['timeline_rounds'] = [dict(round=i+1, freeze_start_tick=i*1000,
                                      live_start_tick=i*1000+64, end_tick=(i+1)*1000,
                                      ct_score=i, t_score=0) for i in range(3)]
    ticks = [64,144,160,1000,1144,1160,2000,2064,2080]
    result['radar'] = {'map':'de_nuke', 'players':{'123':{'name':'Test Player','team':'CT',
        'positions':[dict(tick=t,x=0,y=0,z=-600 if t < 1000 else 0,is_alive=True,team='CT',yaw=0) for t in ticks]}},
        'bomb':{'states':[dict(tick=t,state='unknown') for t in ticks]}, 'kills':[], 'grenades':[]}
    with repo.analysis(match_id, '123', 'Test Player') as report_id:
        repo.complete_report(report_id, result)
    real_id = ''
    if args.real_result:
        with repo.analysis(match_id, '123', 'Real Demo') as real_id:
            repo.complete_report(real_id, json.loads(args.real_result.read_text(encoding='utf-8')))
    api_port, site_port = free_port(), free_port()
    api, site = f'http://127.0.0.1:{api_port}', f'http://127.0.0.1:{site_port}'
    env = {**os.environ, 'WATCHDEMO_COOKIE_SECURE':'false', 'WATCHDEMO_ALLOWED_ORIGINS':site,
           'VITE_API_URL':api, 'WATCHDEMO_QA_SITE_URL':site, 'WATCHDEMO_QA_REPORT_ID':str(report_id),
           'WATCHDEMO_QA_REAL_REPORT_ID':str(real_id), 'WATCHDEMO_QA_OUTPUT':str(args.output)}
    code = ("import uvicorn; from app import create_app; from storage.repository import Repository; "
            f"uvicorn.run(create_app(repository=Repository({repo.database_url!r},{schema!r}),"
            f"upload_dir={str(args.output/'uploads')!r}),host='127.0.0.1',port={api_port},log_level='warning')")
    with (args.output/'servers.log').open('w') as log:
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        processes.append(subprocess.Popen([sys.executable,'-u','-c',code],cwd=root/'backend',env=env,stdout=log,stderr=log,creationflags=flags))
        node = os.environ.get('WATCHDEMO_NODE', 'node')
        processes.append(subprocess.Popen([node,str(root/'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',str(site_port),'--strictPort'],cwd=root/'frontend',env=env,stdout=log,stderr=log,creationflags=flags))
        with httpx.Client(trust_env=False,timeout=1) as client:
            for _ in range(150):
                try:
                    if client.get(api+'/health').status_code == 200 and client.get(site).status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(.2)
            else:
                raise RuntimeError('QA servers did not start')
        subprocess.run([node,str(root/'tools/qa_ivr/browser.cjs')],check=True,env=env)
finally:
    for process in processes:
        process.terminate()
        process.wait(timeout=15)
    assert schema.startswith('watchdemo_test_')
    with repo.connect() as conn:
        conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
