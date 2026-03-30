from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_analyze_success() -> None:
    payload = b'FAKE_DEMO_BYTES' * 8
    response = client.post(
        '/api/analyze',
        files={'file': ('name.dem', payload, 'application/octet-stream')},
    )
    assert response.status_code == 200
    data = response.json()
    assert data['file'] == 'name.dem'
    assert 'summary' in data
    assert 'stats' in data
    assert isinstance(data['mistakes'], list)
    assert isinstance(data['recommendations'], list)


def test_analyze_wrong_extension() -> None:
    response = client.post(
        '/api/analyze',
        files={'file': ('bad.txt', b'abc', 'text/plain')},
    )
    assert response.status_code == 400
    assert 'dem' in response.json()['detail']
