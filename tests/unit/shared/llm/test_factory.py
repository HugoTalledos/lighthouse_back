from __future__ import annotations
import pytest
from src.shared.llm.factory import build_llm_client
from src.shared.llm.infrastructure.openai_client import OpenAIClient
from src.shared.llm.infrastructure.anthropic_client import AnthropicClient


def test_default_provider_returns_openai_client(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    client = build_llm_client()
    assert isinstance(client, OpenAIClient)


def test_openai_provider_returns_openai_client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    client = build_llm_client()
    assert isinstance(client, OpenAIClient)


def test_anthropic_provider_returns_anthropic_client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    client = build_llm_client()
    assert isinstance(client, AnthropicClient)


def test_unknown_provider_raises_value_error(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        build_llm_client()


async def test_anthropic_complete_raises_not_implemented(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    client = build_llm_client()
    with pytest.raises(NotImplementedError):
        await client.complete("hello")


async def test_anthropic_generate_structured_raises_not_implemented(monkeypatch):
    from pydantic import BaseModel

    class Dummy(BaseModel):
        x: str

    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    client = build_llm_client()
    with pytest.raises(NotImplementedError):
        await client.generate_structured("prompt", Dummy)


async def test_anthropic_generate_structured_from_schema_raises_not_implemented(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    client = build_llm_client()
    with pytest.raises(NotImplementedError):
        await client.generate_structured_from_schema("prompt", {"type": "object"})
