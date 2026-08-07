from __future__ import annotations
import json
import pytest
from pytest_httpx import HTTPXMock
from pydantic import BaseModel
from src.shared.llm.infrastructure.ollama_local_client import OllamaLocalClient

_SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
    "additionalProperties": False,
}


class _Color(BaseModel):
    name: str


async def test_generate_structured_from_schema_returns_dict(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/chat",
        json={"message": {"content": '{"name": "red"}'}},
    )
    client = OllamaLocalClient(model="llama3.1")
    result = await client.generate_structured_from_schema("What color?", _SCHEMA)
    assert result == {"name": "red"}


async def test_generate_structured_from_schema_sends_schema_as_format(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/chat",
        json={"message": {"content": '{"name": "blue"}'}},
    )
    client = OllamaLocalClient(model="llama3.1")
    await client.generate_structured_from_schema("pick a color", _SCHEMA)
    request = httpx_mock.get_requests()[0]
    body = json.loads(request.content)
    assert body["format"] == _SCHEMA


async def test_generate_structured_from_schema_raises_on_invalid_response(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/chat",
        json={"message": {"content": "not valid json"}},
    )
    client = OllamaLocalClient(model="llama3.1")
    with pytest.raises(ValueError, match="Failed to parse"):
        await client.generate_structured_from_schema("prompt", _SCHEMA)


async def test_complete_falls_back_to_constructor_temperature(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/chat",
        json={"message": {"content": "hello"}},
    )
    client = OllamaLocalClient(model="llama3.1", temperature=0.2)
    await client.complete("Say hello")

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["options"]["temperature"] == 0.2


async def test_complete_explicit_temperature_overrides_constructor(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/chat",
        json={"message": {"content": "hello"}},
    )
    client = OllamaLocalClient(model="llama3.1", temperature=0.2)
    await client.complete("Say hello", temperature=0.9)

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["options"]["temperature"] == 0.9


async def test_generate_structured_falls_back_to_constructor_temperature(
    monkeypatch, httpx_mock: HTTPXMock
):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/chat",
        json={"message": {"content": '{"name": "red"}'}},
    )
    client = OllamaLocalClient(model="llama3.1", temperature=0.2)
    await client.generate_structured("pick a color", _Color)

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["options"]["temperature"] == 0.2


async def test_generate_structured_explicit_temperature_overrides_constructor(
    monkeypatch, httpx_mock: HTTPXMock
):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/chat",
        json={"message": {"content": '{"name": "red"}'}},
    )
    client = OllamaLocalClient(model="llama3.1", temperature=0.2)
    await client.generate_structured("pick a color", _Color, temperature=0.9)

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["options"]["temperature"] == 0.9


async def test_generate_structured_from_schema_falls_back_to_constructor_temperature(
    monkeypatch, httpx_mock: HTTPXMock
):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/chat",
        json={"message": {"content": '{"name": "red"}'}},
    )
    client = OllamaLocalClient(model="llama3.1", temperature=0.2)
    await client.generate_structured_from_schema("pick a color", _SCHEMA)

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["options"]["temperature"] == 0.2
