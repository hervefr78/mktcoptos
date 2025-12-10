import os
import sys
import types
from pathlib import Path


# Ensure backend package is on path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Use lightweight in-memory database to avoid optional drivers during import
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# Stub heavy optional dependencies to keep tests lightweight
sys.modules.setdefault(
    "sentence_transformers",
    types.SimpleNamespace(
        SentenceTransformer=lambda *args, **kwargs: types.SimpleNamespace(
            encode=lambda items: [[0.0] for _ in items]
        )
    ),
)


from app.agents.content_pipeline.content_agents import ContentPipelineAgent


class DummyContentAgent(ContentPipelineAgent):
    def run(self, *args, **kwargs):  # pragma: no cover - not used in tests
        return {}

    def name(self) -> str:  # pragma: no cover - trivial accessor
        return "dummy"

    def description(self) -> str:  # pragma: no cover - trivial accessor
        return "dummy agent for testing"


def test_parse_json_response_repairs_unescaped_newlines():
    agent = DummyContentAgent()

    response = """Here is the structured output:
```json
{
  "headline": "Line one
Line two",
  "items": ["alpha", "beta"]
}
```
"""

    parsed = agent._parse_json_response(response)

    assert parsed["headline"] == "Line one\nLine two"
    assert parsed["items"] == ["alpha", "beta"]
