import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure backend path is on sys.path
backend_path = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_path))

import app.auth as auth

app = FastAPI()
app.include_router(auth.router)


def test_admin_login_on_auth_import():
    client = TestClient(app)
    resp = client.post("/api/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    assert "token" in resp.json()
