from __future__ import annotations
import json
import pytest
from pytest_httpx import HTTPXMock
from src.shared.llm.infrastructure.ollama_local_client import OllamaLocalClient

_SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
    "additionalProperties": False,
}


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
