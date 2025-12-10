import sys
from pathlib import Path
import types
import importlib
import pkgutil

# Ensure backend package is on path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agent_manager import AgentManager
from app.agents.base import BaseAgent


def test_agent_manager_loads_agents(monkeypatch):
    class DummyAgent(BaseAgent):
        def run(self, *args, **kwargs):
            return "done"

        def name(self) -> str:
            return "dummy"

        def description(self) -> str:
            return "dummy agent"

    def fake_iter_modules(path):
        yield None, "dummy_module", None

    original_import_module = importlib.import_module

    def fake_import_module(name):
        if name.endswith("dummy_module"):
            module = types.ModuleType(name)
            module.DummyAgent = DummyAgent
            return module
        return original_import_module(name)

    monkeypatch.setattr(pkgutil, "iter_modules", fake_iter_modules)
    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    manager = AgentManager()

    assert "dummy" in manager.available_agents
    assert isinstance(manager.available_agents["dummy"], DummyAgent)
