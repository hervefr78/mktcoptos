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
from app.agents.base import BaseAgent

app = main.app
agent_manager = main.agent_manager


class DummyAgent(BaseAgent):
    def run(self, *args, **kwargs):
        return "success"

    def name(self) -> str:
        return "dummy"

    def description(self) -> str:
        return "Dummy agent"


def setup_dummy_agent():
    agent_manager.available_agents = {"dummy": DummyAgent()}


def test_llm_endpoint(monkeypatch):
    class DummyTask:
        id = "123"

    monkeypatch.setattr(main.run_llm, "delay", lambda prompt: DummyTask())

    client = TestClient(app)
    response = client.post("/llm", json={"prompt": "hi"})
    assert response.status_code == 200
    assert response.json() == {"task_id": "123"}


def test_ingest_endpoint(monkeypatch):
    class DummyTask:
        id = "abc"

    monkeypatch.setattr(main.ingest_data, "delay", lambda items: DummyTask())

    client = TestClient(app)
    response = client.post("/ingest", json={"items": ["a", "b"]})
    assert response.status_code == 200
    assert response.json() == {"task_id": "abc"}


def test_list_agents():
    setup_dummy_agent()
    client = TestClient(app)
    response = client.get("/agents")
    assert response.status_code == 200
    assert response.json() == [{"name": "dummy", "description": "Dummy agent"}]


def test_run_agent():
    setup_dummy_agent()
    client = TestClient(app)
    response = client.post("/agents/dummy", json={"params": {}})
    assert response.status_code == 200
    assert response.json() == {"result": "success"}


def test_run_agent_not_found():
    agent_manager.available_agents = {}
    client = TestClient(app)
    response = client.post("/agents/unknown", json={"params": {}})
    assert response.status_code == 404


def test_stream_agent(monkeypatch):
    setup_dummy_agent()
    monkeypatch.setattr(main, "get_cached_response", lambda agent, prompt: None)
    monkeypatch.setattr(main, "set_cached_response", lambda agent, prompt, response: None)

    client = TestClient(app)
    response = client.post("/agents/dummy/stream", json={"params": {"prompt": "x"}})
    assert response.status_code == 200
    assert response.text == "data: success\n\n"
