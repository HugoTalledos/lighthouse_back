"""Despacho de la estrategia que construye el chat model del orquestador.

El agente necesita un BaseChatModel (llama a .bind_tools), no el LLMClientPort
de src/shared/llm, así que esta factory es independiente de build_llm_client.
"""
from __future__ import annotations

import pytest
from langchain_ollama import ChatOllama

from src.agent.infrastructure.llm.chat_model_factory import (
    _OPENROUTER_BASE_URL,
    build_chat_model,
)
from src.shared.llm_config.domain.models import LLMSettings


def _settings(**overrides) -> LLMSettings:
    base = {"provider": "ollama", "model": "llama3.1", "temperature": 0.5}
    return LLMSettings.model_validate({**base, **overrides})


def test_ollama_settings_return_chat_ollama():
    model = build_chat_model(_settings(model="qwen2.5-coder:7b", temperature=0.2, top_p=0.8))

    assert isinstance(model, ChatOllama)
    assert model.model == "qwen2.5-coder:7b"
    assert model.temperature == 0.2
    assert model.top_p == 0.8


def test_ollama_maps_max_tokens_to_num_predict():
    """ChatOllama ignora `max_tokens`; el parámetro real es `num_predict`."""
    model = build_chat_model(_settings(max_tokens=500))

    assert model.num_predict == 500


def test_ollama_without_max_tokens_leaves_num_predict_unset():
    model = build_chat_model(_settings())

    assert model.num_predict is None


def test_openrouter_settings_build_an_openai_client_pointed_at_openrouter(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    captured = {}

    def fake_init_chat_model(model, **kwargs):
        captured["model"] = model
        captured.update(kwargs)
        return "chat-model-sentinel"

    monkeypatch.setattr(
        "src.agent.infrastructure.llm.chat_model_factory.init_chat_model",
        fake_init_chat_model,
    )

    result = build_chat_model(
        _settings(provider="openrouter", model="openai/gpt-4o", temperature=0.3,
                  max_tokens=1000, top_p=0.9)
    )

    assert result == "chat-model-sentinel"
    assert captured["model"] == "openai/gpt-4o"
    assert captured["model_provider"] == "openai"
    assert captured["base_url"] == _OPENROUTER_BASE_URL
    assert captured["api_key"] == "sk-test"
    assert captured["temperature"] == 0.3
    assert captured["max_tokens"] == 1000
    assert captured["top_p"] == 0.9


def test_openrouter_without_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        build_chat_model(_settings(provider="openrouter", model="openai/gpt-4o"))


def test_unsupported_provider_raises_listing_the_valid_ones():
    settings = _settings()
    unsupported = settings.model_copy(update={"provider": "anthropic"})

    with pytest.raises(ValueError, match="anthropic") as excinfo:
        build_chat_model(unsupported)

    assert "ollama" in str(excinfo.value)
    assert "openrouter" in str(excinfo.value)


def test_two_settings_produce_independently_configured_models():
    a = build_chat_model(_settings(model="llama3.1", temperature=0.1))
    b = build_chat_model(_settings(model="mistral", temperature=0.9))

    assert (a.model, a.temperature) == ("llama3.1", 0.1)
    assert (b.model, b.temperature) == ("mistral", 0.9)
