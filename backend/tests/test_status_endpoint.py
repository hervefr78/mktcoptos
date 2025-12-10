import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend path is on sys.path
backend_path = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_path))

import app.main as main

app = main.app


def test_status_endpoint():
  client = TestClient(app)
  response = client.get('/status')
  assert response.status_code == 200
  data = response.json()
  assert 'activities' in data
  assert isinstance(data['activities'], list)
