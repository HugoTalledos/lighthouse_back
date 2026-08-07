from __future__ import annotations

import base64

import pytest
from pytest_httpx import HTTPXMock

from src.shared.image_gen.infrastructure.openrouter_generator import OpenRouterImageGenerator

FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # minimal fake PNG bytes
FAKE_PNG_B64 = base64.b64encode(FAKE_PNG).decode()


async def test_generate_returns_generated_image_and_sends_auth_header(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.delenv("OPENROUTER_HTTP_REFERER", raising=False)
    monkeypatch.delenv("OPENROUTER_X_TITLE", raising=False)

    httpx_mock.add_response(
        method="POST",
        url="https://openrouter.ai/api/v1/chat/completions",
        json={
            "choices": [
                {
                    "message": {
                        "images": [
                            {"image_url": {"url": f"data:image/png;base64,{FAKE_PNG_B64}"}}
                        ]
                    }
                }
            ]
        },
    )

    generator = OpenRouterImageGenerator(model="google/gemini-2.5-flash-image-preview")
    result = await generator.generate("A prompt", 1200, 628)

    assert result.provider == "openrouter"
    assert result.image_bytes == FAKE_PNG
    assert result.prompt_used == "A prompt"
    assert result.width == 1200
    assert result.height == 628

    request = httpx_mock.get_request()
    assert request.headers["Authorization"] == "Bearer sk-test"


async def test_missing_api_key_raises_at_construction(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY environment variable is not set"):
        OpenRouterImageGenerator(model="google/gemini-2.5-flash-image-preview")
