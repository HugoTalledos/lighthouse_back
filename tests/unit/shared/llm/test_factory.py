from __future__ import annotations
import pytest

from src.shared.llm.factory import build_llm_client
from src.shared.llm.infrastructure.openrouter_client import OpenRouterClient
from src.shared.llm.infrastructure.ollama_local_client import OllamaLocalClient
from src.shared.llm_config.domain.models import LLMSettings


def test_openrouter_settings_return_openrouter_client(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    settings = LLMSettings(provider="openrouter", model="openai/gpt-4o", temperature=0.3)

    client = build_llm_client(settings)

    assert isinstance(client, OpenRouterClient)


def test_ollama_settings_return_ollama_client():
    settings = LLMSettings(provider="ollama", model="llama3.1", temperature=0.3)

    client = build_llm_client(settings)

    assert isinstance(client, OllamaLocalClient)


def test_model_and_temperature_reach_the_client():
    settings = LLMSettings(provider="ollama", model="llama3.1", temperature=0.9)

    client = build_llm_client(settings)

    assert client._model == "llama3.1"
    assert client._temperature == 0.9


def test_two_settings_produce_independently_configured_clients():
    a = build_llm_client(LLMSettings(provider="ollama", model="llama3.1", temperature=0.1))
    b = build_llm_client(LLMSettings(provider="ollama", model="mistral", temperature=0.9))

    assert (a._model, a._temperature) == ("llama3.1", 0.1)
    assert (b._model, b._temperature) == ("mistral", 0.9)
