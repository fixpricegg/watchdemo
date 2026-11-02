from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from tests.test_storage import PostgreSQLStorageTests, authenticate
from app import create_app
import hashlib
import json

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('demo', type=Path)
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
    (case.directory / uploaded['filename']).unlink()
    with TestClient(create_app(repository=case.repo, upload_dir=case.directory)) as fresh:
        authenticate(fresh)
        reopened = fresh.get('/reports/' + analyzed['report_id'])
        assert reopened.status_code == 200, reopened.text
        assert reopened.json()['result'] == analyzed['result']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    print('REAL_DEMO_OK', source.name, source.stat().st_size, player['name'], len(analyzed['result']['timeline_rounds']), flush=True)
    print('INPUT_SHA256', before)
    print('RESULT_SHA256', hashlib.sha256(json.dumps(analyzed['result'], sort_keys=True, ensure_ascii=False).encode()).hexdigest())
finally:
    case.tearDown()
