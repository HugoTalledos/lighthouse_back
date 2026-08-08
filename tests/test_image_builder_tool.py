import io
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pydantic import ValidationError
from PIL import Image

from src.agent.tools.image_builder.domain.models import (
    ImageBrief, GeneratedImage, ComposedCreative, ImageBuildResult,
)
from src.agent.tools.image_builder.image_builder_tool import image_builder_tool


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
    brief = ImageBrief.model_validate(_valid_brief_dict())
    stub_result = _stub_result(brief)

    with patch(
        "src.agent.tools.image_builder.image_builder_tool._build_service"
    ) as mock_factory, patch(
        "src.agent.tools.image_builder.image_builder_tool.get_project_repository"
    ) as mock_get_repo:
        mock_service = MagicMock()
        mock_service.build = AsyncMock(return_value=stub_result)
        mock_factory.return_value = mock_service
        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo

        from src.agent.tools.image_builder.image_builder_tool import image_builder_tool
        brief_without_project_id = {k: v for k, v in _valid_brief_dict().items() if k != "project_id"}
        result = await image_builder_tool.ainvoke({
            "brief_dict": brief_without_project_id,
            "state": {"project_id": "proj-1"},
        })

    assert result["status"] == "success"
    assert len(result["creatives"]) == 1
    mock_repo.update_resource.assert_called_once_with(
        "proj-1",
        "images",
        {
            "creatives": [
                {
                    "variant_index": 0,
                    "storage_url": "https://example.com/img.png",
                    "headline": "Save time",
                    "cta_text": "Try free",
                    "prompt_used": "prompt",
                    "provider": "openrouter",
                }
            ]
        },
        "pending",
    )


async def test_failed_tool_result_does_not_persist_an_image_resource():
    brief = ImageBrief.model_validate(_valid_brief_dict())
    failed_result = ImageBuildResult(
        brief=brief, creatives=[], status="failed", errors=["generation failed"]
    )

    with patch(
        "src.agent.tools.image_builder.image_builder_tool._build_service"
    ) as mock_factory, patch(
        "src.agent.tools.image_builder.image_builder_tool.get_project_repository"
    ) as mock_get_repo:
        mock_service = MagicMock()
        mock_service.build = AsyncMock(return_value=failed_result)
        mock_factory.return_value = mock_service
        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo

        result = await image_builder_tool.ainvoke(
            {
                "brief_dict": {
                    k: v for k, v in _valid_brief_dict().items() if k != "project_id"
                },
                "state": {"project_id": "proj-1"},
            }
        )

    assert result["status"] == "failed"
    mock_repo.update_resource.assert_not_called()


async def test_tool_raises_on_invalid_brief():
    from src.agent.tools.image_builder.image_builder_tool import image_builder_tool
    with pytest.raises(Exception):
        await image_builder_tool.ainvoke({
            "brief_dict": {"business_name": "Only this"},
            "state": {"project_id": "proj-1"},
        })


def _config_with_image_builder(provider: str, model: str):
    from src.shared.llm_config.domain.models import AppLLMConfig

    return AppLLMConfig.model_validate(
        {
            "defaults": {"provider": provider, "model": model, "temperature": 0.5},
            "agent": {},
            "tools": {"image_builder": {}},
        }
    )


def test_build_service_selects_openrouter_when_configured(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("FIREBASE_STORAGE_BUCKET", "test.appspot.com")
    monkeypatch.setattr(
        "src.agent.tools.image_builder.image_builder_tool.load_llm_config",
        lambda: _config_with_image_builder("openrouter", "google/gemini-2.5-flash-image-preview"),
    )

    with patch("src.agent.tools.image_builder.infrastructure.storage.firebase_storage.firebase_admin") as m:
        m._apps = {"[DEFAULT]": True}
        from src.agent.tools.image_builder.image_builder_tool import _build_service
        from src.shared.image_gen.infrastructure.openrouter_generator import (
            OpenRouterImageGenerator,
        )
        service = _build_service()
        assert isinstance(service._generator, OpenRouterImageGenerator)
        assert service._generator._model == "google/gemini-2.5-flash-image-preview"


def test_build_service_selects_ollama_when_configured(monkeypatch):
    monkeypatch.setenv("FIREBASE_STORAGE_BUCKET", "test.appspot.com")
    monkeypatch.setattr(
        "src.agent.tools.image_builder.image_builder_tool.load_llm_config",
        lambda: _config_with_image_builder("ollama", "x/flux2-klein:4b"),
    )

    with patch("src.agent.tools.image_builder.infrastructure.storage.firebase_storage.firebase_admin") as m:
        m._apps = {"[DEFAULT]": True}
        from src.agent.tools.image_builder.image_builder_tool import _build_service
        from src.shared.image_gen.infrastructure.ollama_generator import (
            OllamaImageGenerator,
        )
        service = _build_service()
        assert isinstance(service._generator, OllamaImageGenerator)
        assert service._generator._model == "x/flux2-klein:4b"


def test_config_rejects_unknown_providers_at_validation_time():
    """La validación ahora vive en el Literal de LLMSettings, no en la factory."""
    from pydantic import ValidationError
    from src.shared.llm_config.domain.models import AppLLMConfig

    with pytest.raises(ValidationError):
        AppLLMConfig.model_validate(
            {
                "defaults": {"provider": "dalle3", "model": "x", "temperature": 0.5},
                "agent": {},
                "tools": {},
            }
        )


async def test_tool_omits_image_bytes_and_survives_real_binary(monkeypatch):
    from src.agent.tools.image_builder.domain.models import (
        ImageBrief, ComposedCreative, ImageBuildResult,
    )
    import json

    brief = ImageBrief(
        project_id="p1", business_name="Café Luna", value_proposition="Café de origen",
        target_customer="oficinistas", headline="Café de origen", cta_text="Pide el tuyo",
        style_hints=["minimalista"], n_images=1,
    )
    result = ImageBuildResult(
        brief=brief,
        creatives=[ComposedCreative(
            variant_index=0,
            image_bytes=b"\x89PNG\r\n\x1a\n\xff\xfe",  # PNG real: no es UTF-8 válido
            storage_url="https://storage.googleapis.com/bucket/p1/0.png",
            headline="Café de origen", cta_text="Pide el tuyo",
            prompt_used="prompt", provider="openrouter",
        )],
        status="success", errors=[],
    )

    service = MagicMock()
    service.build = AsyncMock(return_value=result)
    monkeypatch.setattr(
        "src.agent.tools.image_builder.image_builder_tool._build_service", lambda: service
    )
    monkeypatch.setattr(
        "src.agent.tools.image_builder.image_builder_tool.get_project_repository",
        lambda: MagicMock(),
    )

    output = await image_builder_tool.ainvoke({
        "brief_dict": brief.model_dump(exclude={"project_id"}),
        "state": {"project_id": "p1"},
    })

    assert "image_bytes" not in output["creatives"][0]
    assert output["creatives"][0]["storage_url"].endswith("/0.png")
    json.dumps(output)  # el resultado debe ser serializable a JSON
