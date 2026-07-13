import base64

import httpx
import pytest
from pytest_httpx import HTTPXMock

from src.agent.tools.image_builder.infrastructure.ollama_generator import (
    OllamaImageGenerator,
)

FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # minimal fake PNG bytes
FAKE_PNG_B64 = base64.b64encode(FAKE_PNG).decode()


async def test_generate_returns_generated_image(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_IMAGE_MODEL", raising=False)

    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/generate",
        match_json={
            "model": "x/flux2-klein:4b",
            "prompt": "A background image",
            "options": {"width": 1200, "height": 628},
            "stream": False,
        },
        json={"model": "x/flux2-klein:4b", "response": "", "done": True, "image": FAKE_PNG_B64},
    )

    generator = OllamaImageGenerator()
    result = await generator.generate("A background image", 1200, 628)

    assert result.provider == "ollama"
    assert result.image_bytes == FAKE_PNG
    assert result.prompt_used == "A background image"
    assert result.width == 1200
    assert result.height == 628


async def test_generate_uses_env_var_overrides(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.internal:9999")
    monkeypatch.setenv("OLLAMA_IMAGE_MODEL", "x/other-model:1b")

    httpx_mock.add_response(
        method="POST",
        url="http://ollama.internal:9999/api/generate",
        match_json={
            "model": "x/other-model:1b",
            "prompt": "A prompt",
            "options": {"width": 512, "height": 512},
            "stream": False,
        },
        json={"image": FAKE_PNG_B64},
    )

    generator = OllamaImageGenerator()
    result = await generator.generate("A prompt", 512, 512)

    assert result.image_bytes == FAKE_PNG


async def test_api_error_raises(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_IMAGE_MODEL", raising=False)

    httpx_mock.add_response(
        method="POST",
        url="http://localhost:11434/api/generate",
        status_code=500,
        json={"error": "model not found"},
    )

    generator = OllamaImageGenerator()
    with pytest.raises(httpx.HTTPStatusError):
        await generator.generate("A prompt", 1200, 628)
