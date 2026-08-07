from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from src.shared.llm.infrastructure.openrouter_client import OpenRouterClient


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
