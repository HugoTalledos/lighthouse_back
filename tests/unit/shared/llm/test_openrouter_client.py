from __future__ import annotations

import json

import pytest
from pytest_httpx import HTTPXMock
from pydantic import BaseModel

from src.shared.llm.infrastructure.openrouter_client import OpenRouterClient


class _Color(BaseModel):
    name: str


async def test_complete_returns_content_and_sends_auth_header(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")

    httpx_mock.add_response(
        method="POST",
        url="https://openrouter.ai/api/v1/chat/completions",
        json={"choices": [{"message": {"content": "hello"}}]},
    )

    client = OpenRouterClient(model="openai/gpt-4o")
    result = await client.complete("Say hello")

    assert result == "hello"

    request = httpx_mock.get_request()
    assert request.headers["Authorization"] == "Bearer sk-test"


async def test_missing_api_key_raises_at_construction(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY environment variable is not set"):
        OpenRouterClient(model="openai/gpt-4o")


async def test_complete_falls_back_to_constructor_temperature(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    httpx_mock.add_response(
        method="POST",
        url="https://openrouter.ai/api/v1/chat/completions",
        json={"choices": [{"message": {"content": "hello"}}]},
    )

    client = OpenRouterClient(model="openai/gpt-4o", temperature=0.2)
    await client.complete("Say hello")

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["temperature"] == 0.2


async def test_complete_explicit_temperature_overrides_constructor(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    httpx_mock.add_response(
        method="POST",
        url="https://openrouter.ai/api/v1/chat/completions",
        json={"choices": [{"message": {"content": "hello"}}]},
    )

    client = OpenRouterClient(model="openai/gpt-4o", temperature=0.2)
    await client.complete("Say hello", temperature=0.9)

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["temperature"] == 0.9


async def test_generate_structured_falls_back_to_constructor_temperature(
    monkeypatch, httpx_mock: HTTPXMock
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    httpx_mock.add_response(
        method="POST",
        url="https://openrouter.ai/api/v1/chat/completions",
        json={"choices": [{"message": {"content": '{"name": "red"}'}}]},
    )

    client = OpenRouterClient(model="openai/gpt-4o", temperature=0.2)
    await client.generate_structured("pick a color", _Color)

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["temperature"] == 0.2


async def test_generate_structured_explicit_temperature_overrides_constructor(
    monkeypatch, httpx_mock: HTTPXMock
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    httpx_mock.add_response(
        method="POST",
        url="https://openrouter.ai/api/v1/chat/completions",
        json={"choices": [{"message": {"content": '{"name": "red"}'}}]},
    )

    client = OpenRouterClient(model="openai/gpt-4o", temperature=0.2)
    await client.generate_structured("pick a color", _Color, temperature=0.9)

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["temperature"] == 0.9


async def test_generate_structured_from_schema_falls_back_to_constructor_temperature(
    monkeypatch, httpx_mock: HTTPXMock
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    httpx_mock.add_response(
        method="POST",
        url="https://openrouter.ai/api/v1/chat/completions",
        json={"choices": [{"message": {"content": '{"name": "red"}'}}]},
    )

    client = OpenRouterClient(model="openai/gpt-4o", temperature=0.2)
    await client.generate_structured_from_schema(
        "pick a color",
        {"type": "object", "properties": {"name": {"type": "string"}}},
    )

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["temperature"] == 0.2
