import pytest
import httpx
from pytest_httpx import HTTPXMock
from src.agent.tools.image_builder.infrastructure.generators.dalle_generator import DalleImageGenerator


FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # minimal fake PNG bytes


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        DalleImageGenerator()


async def test_generate_returns_generated_image(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    image_url = "https://oaidalleapiprodscus.blob.core.windows.net/img.png"

    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/generations",
        json={"data": [{"url": image_url}]},
    )
    httpx_mock.add_response(
        method="GET",
        url=image_url,
        content=FAKE_PNG,
    )

    generator = DalleImageGenerator()
    result = await generator.generate("A background image", 1200, 628)

    assert result.provider == "dalle3"
    assert result.image_bytes == FAKE_PNG
    assert result.prompt_used == "A background image"
    assert result.width == 1792
    assert result.height == 1024


async def test_api_error_raises(monkeypatch, httpx_mock: HTTPXMock):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    httpx_mock.add_response(
        method="POST",
        url="https://api.openai.com/v1/images/generations",
        status_code=429,
        json={"error": {"message": "Rate limit exceeded"}},
    )

    generator = DalleImageGenerator()
    with pytest.raises(httpx.HTTPStatusError):
        await generator.generate("A prompt", 1200, 628)
