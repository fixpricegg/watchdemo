from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from tests.test_storage import PostgreSQLStorageTests, authenticate
from app import create_app
import hashlib
import json
import os
import socket
import subprocess
import time
import httpx

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('demo', type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
case = PostgreSQLStorageTests()
case.setUp()
try:
    source = args.demo.resolve()
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    with source.open('rb') as stream:
        response = case.client.post('/demo/upload', files={'file': (source.name, stream)})
    assert response.status_code == 200, response.text
    uploaded = response.json()
    player = next((p for p in uploaded['players'] if p['name'] == 'wesiqe'), uploaded['players'][0])
    response = case.client.post('/demo/analyze', json={'match_id': uploaded['match_id'], 'steamid': player['steamid']})
    assert response.status_code == 200, response.text
    analyzed = response.json()
    result = analyzed['result']
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'real-result.json').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    findings = result['report']['review_findings']
    assert all(f['status'] == 'review_required' and f['verdict'] == 'not_evaluated' for f in findings)
    for finding in findings:
        round_data = next(r for r in result['timeline_rounds'] if r['round'] == finding['round'])
        assert round_data['live_start_tick'] <= finding['tick'] < round_data['end_tick']
        assert any(e['type'] == finding['type'] and e['tick'] == finding['tick'] and e['category'] == 'neutral' for e in result['events'])
    from collections import Counter
    print('DETECTOR_COUNTS', dict(Counter(f['detector'] for f in findings)), flush=True)
    print('ROUNDS', len(result['timeline_rounds']), flush=True)
    print('ADR_EVIDENCE', json.dumps(analyzed['result']['report']['adr_details'], ensure_ascii=False), flush=True)
    (case.directory / uploaded['filename']).unlink()
    with TestClient(create_app(repository=case.repo, upload_dir=case.directory)) as fresh:
        authenticate(fresh)
        reopened = fresh.get('/reports/' + analyzed['report_id'])
        assert reopened.status_code == 200, reopened.text
        assert reopened.json()['result'] == analyzed['result']
    # Also exercise an actual backend process, stop it, and reopen in another.
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    code = (
        'import uvicorn; from app import create_app; from storage.repository import Repository; '
        f'uvicorn.run(create_app(repository=Repository({case.repo.database_url!r},{case.repo.schema!r}),'
        f'upload_dir={str(case.directory)!r}),host="127.0.0.1",port={port},log_level="warning",access_log=False)'
    )
    for run in range(2):
        process = subprocess.Popen([sys.executable, '-c', code], cwd=Path(__file__).resolve().parents[1],
                                   env=os.environ.copy(), creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', trust_env=False, timeout=30) as http:
                for attempt in range(100):
                    if process.poll() is not None:
                        raise RuntimeError('Real-demo QA backend exited before startup')
                    try:
                        if http.get('/health').status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.1)
                else:
                    raise RuntimeError('Real-demo QA backend startup timed out')
                authenticate(http)
                reopened = http.get('/reports/' + analyzed['report_id'])
                assert reopened.status_code == 200, reopened.text
                assert reopened.json()['result'] == analyzed['result']
                exported = http.get('/reports/' + analyzed['report_id'] + '/export')
                assert exported.status_code == 200, exported.text
                assert exported.json()['report']['summary'] == analyzed['result']['report']['summary']
                print('REAL_PROCESS_REOPEN_EXPORT_OK', run + 1, flush=True)
        finally:
            process.terminate()
            process.wait(timeout=15)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    print('REAL_DEMO_OK', source.name, source.stat().st_size, player['name'], len(analyzed['result']['timeline_rounds']), flush=True)
    print('INPUT_SHA256', before)
    print('RESULT_SHA256', hashlib.sha256(json.dumps(analyzed['result'], sort_keys=True, ensure_ascii=False).encode()).hexdigest())
finally:
    case.tearDown()
