import sys
from pathlib import Path
from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_path))

import app.main as main

app = main.app


def test_export_wordpress():
    client = TestClient(app)
    resp = client.post('/export/wordpress', json={'content': 'hello'})
    assert resp.status_code == 200
    assert resp.json() == {'status': 'success'}


def test_share_linkedin():
    client = TestClient(app)
    resp = client.post('/share/linkedin', json={'content': 'hi'})
    assert resp.status_code == 200
    assert resp.json() == {'status': 'shared'}


def test_share_x():
    client = TestClient(app)
    resp = client.post('/share/x', json={'content': 'hi'})
    assert resp.status_code == 200
    assert resp.json() == {'status': 'shared'}
