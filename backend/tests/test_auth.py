import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend path is on sys.path
backend_path = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_path))

# Import agent_manager so main can reference it as a top-level module
import app.agent_manager as agent_manager_module
sys.modules["agent_manager"] = agent_manager_module

import app.main as main

app = main.app


def test_default_admin_login():
    client = TestClient(app)
    response = client.post("/api/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    assert "token" in response.json()
