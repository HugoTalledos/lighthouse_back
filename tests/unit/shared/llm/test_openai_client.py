from __future__ import annotations
import json
import pytest
import httpx
from pytest_httpx import HTTPXMock
from pydantic import BaseModel
from src.shared.llm.infrastructure.openai_client import OpenAIClient


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIClient()


async def test_complete_returns_text(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/chat/completions",
        json={"choices": [{"message": {"content": "Hello world"}}]},
    )
    client = OpenAIClient()
    result = await client.complete("Say hello")
    assert result == "Hello world"


async def test_complete_sends_system_message(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/chat/completions",
        json={"choices": [{"message": {"content": "ok"}}]},
    )
    client = OpenAIClient()
    await client.complete("prompt", system="You are helpful")
    request = httpx_mock.get_requests()[0]
    body = json.loads(request.content)
    assert body["messages"][0] == {"role": "system", "content": "You are helpful"}
    assert body["messages"][1] == {"role": "user", "content": "prompt"}


async def test_complete_without_system_sends_only_user(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/chat/completions",
        json={"choices": [{"message": {"content": "hi"}}]},
    )
    client = OpenAIClient()
    await client.complete("prompt")
    request = httpx_mock.get_requests()[0]
    body = json.loads(request.content)
    assert len(body["messages"]) == 1
    assert body["messages"][0]["role"] == "user"


async def test_generate_structured_returns_validated_model(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    class Color(BaseModel):
        name: str
        hex: str

    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/chat/completions",
        json={"choices": [{"message": {"content": '{"name": "red", "hex": "#ff0000"}'}}]},
    )
    client = OpenAIClient()
    result = await client.generate_structured("What color?", Color)
    assert isinstance(result, Color)
    assert result.name == "red"
    assert result.hex == "#ff0000"


async def test_generate_structured_sends_json_schema(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    class Color(BaseModel):
        name: str

    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/chat/completions",
        json={"choices": [{"message": {"content": '{"name": "blue"}'}}]},
    )
    client = OpenAIClient()
    await client.generate_structured("pick a color", Color)
    request = httpx_mock.get_requests()[0]
    body = json.loads(request.content)
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["name"] == "Color"
    assert "properties" in body["response_format"]["json_schema"]["schema"]
    assert body["response_format"]["json_schema"]["strict"] is True


async def test_generate_structured_raises_on_invalid_response(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    class Color(BaseModel):
        name: str

    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/chat/completions",
        json={"choices": [{"message": {"content": "not valid json"}}]},
    )
    client = OpenAIClient()
    with pytest.raises(ValueError, match="Failed to parse"):
        await client.generate_structured("prompt", Color)


async def test_api_error_raises(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/chat/completions",
        status_code=429,
        json={"error": {"message": "Rate limit exceeded"}},
    )
    client = OpenAIClient()
    with pytest.raises(httpx.HTTPStatusError):
        await client.complete("hello")
