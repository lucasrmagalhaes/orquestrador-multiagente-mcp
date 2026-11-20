import pytest


@pytest.fixture(autouse=True)
def _ambiente_de_teste(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("ORQUESTRADOR_MCP", "processo")
    monkeypatch.delenv("ORQUESTRADOR_FALHA_NO", raising=False)
    monkeypatch.delenv("ORQUESTRADOR_DATA", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
