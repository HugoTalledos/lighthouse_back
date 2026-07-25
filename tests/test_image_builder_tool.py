import io
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pydantic import ValidationError
from PIL import Image

from src.agent.tools.image_builder.domain.models import (
    ImageBrief, GeneratedImage, ComposedCreative, ImageBuildResult,
)


def _valid_brief_dict():
    return dict(
        project_id="proj-1",
        business_name="Acme",
        value_proposition="Saves time",
        target_customer="Professionals",
        headline="Save time",
        cta_text="Try free",
        style_hints=["clean"],
        n_images=1,
    )


def _stub_result(brief):
    creative = ComposedCreative(
        variant_index=0,
        image_bytes=b"png",
        storage_url="https://example.com/img.png",
        headline=brief.headline,
        cta_text=brief.cta_text,
        prompt_used="prompt",
        provider="openrouter",
    )
    return ImageBuildResult(brief=brief, creatives=[creative], status="success", errors=[])


async def test_tool_returns_dict_with_status(monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "openrouter")

    brief = ImageBrief.model_validate(_valid_brief_dict())
    stub_result = _stub_result(brief)

    with patch(
        "src.agent.tools.image_builder.image_builder_tool._build_service"
    ) as mock_factory:
        mock_service = MagicMock()
        mock_service.build = AsyncMock(return_value=stub_result)
        mock_factory.return_value = mock_service

        from src.agent.tools.image_builder.image_builder_tool import image_builder_tool
        result = await image_builder_tool.ainvoke({"brief_dict": _valid_brief_dict()})

    assert result["status"] == "success"
    assert len(result["creatives"]) == 1


async def test_tool_raises_on_invalid_brief():
    from src.agent.tools.image_builder.image_builder_tool import image_builder_tool
    with pytest.raises(Exception):
        await image_builder_tool.ainvoke({"brief_dict": {"business_name": "Only this"}})


def test_build_service_selects_openrouter_by_default(monkeypatch):
    monkeypatch.delenv("IMAGE_PROVIDER", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("FIREBASE_STORAGE_BUCKET", "test.appspot.com")

    with patch("src.agent.tools.image_builder.infrastructure.storage.firebase_storage.firebase_admin") as m:
        m._apps = {"[DEFAULT]": True}
        from src.agent.tools.image_builder.image_builder_tool import _build_service
        from src.shared.image_gen.infrastructure.openrouter_generator import (
            OpenRouterImageGenerator,
        )
        service = _build_service()
        assert isinstance(service._generator, OpenRouterImageGenerator)


def test_build_service_selects_ollama(monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "ollama")
    monkeypatch.setenv("FIREBASE_STORAGE_BUCKET", "test.appspot.com")

    with patch("src.agent.tools.image_builder.infrastructure.storage.firebase_storage.firebase_admin") as m:
        m._apps = {"[DEFAULT]": True}
        from src.agent.tools.image_builder.image_builder_tool import _build_service
        from src.shared.image_gen.infrastructure.ollama_generator import (
            OllamaImageGenerator,
        )
        service = _build_service()
        assert isinstance(service._generator, OllamaImageGenerator)


@pytest.mark.parametrize("provider", ["dalle3", "vertex"])
def test_build_service_rejects_removed_providers(monkeypatch, provider):
    monkeypatch.setenv("IMAGE_PROVIDER", provider)
    monkeypatch.setenv("FIREBASE_STORAGE_BUCKET", "test.appspot.com")

    from src.agent.tools.image_builder.image_builder_tool import _build_service
    with pytest.raises(ValueError, match="Unknown IMAGE_PROVIDER"):
        _build_service()
