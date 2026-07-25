from __future__ import annotations
import pytest
from src.shared.llm.factory import build_llm_client
from src.shared.llm.infrastructure.openrouter_client import OpenRouterClient
from src.shared.llm.infrastructure.ollama_local_client import OllamaLocalClient


def test_default_provider_returns_openrouter_client(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    client = build_llm_client()
    assert isinstance(client, OpenRouterClient)


def test_openrouter_provider_returns_openrouter_client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    client = build_llm_client()
    assert isinstance(client, OpenRouterClient)


def test_ollama_provider_returns_ollama_client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    client = build_llm_client()
    assert isinstance(client, OllamaLocalClient)


def test_unknown_provider_raises_value_error(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        build_llm_client()


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_removed_providers_are_no_longer_valid(monkeypatch, provider):
    monkeypatch.setenv("LLM_PROVIDER", provider)
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        build_llm_client()
