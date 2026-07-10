from __future__ import annotations
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.agent.tools.landing_builder.domain.models import (
    Theme, HeroSection, FooterSection, PageComposition, LandingPromoteResult,
)


def _composition_dict():
    composition = PageComposition(
        theme=Theme(primary_color="#111", secondary_color="#eee", font_family="Inter"),
        sections=[
            HeroSection(headline="Welcome", subheadline="Sub", cta_text="Start"),
            FooterSection(business_name="Acme", links=[], social_links=[]),
        ],
    )
    return composition.model_dump(mode="json")


async def test_tool_returns_dict_with_status():
    stub_result = LandingPromoteResult(
        project_id="proj-1", version="20260710T000000Z",
        storage_path="landings/proj-1/20260710T000000Z/source.tar.gz",
        status="success", errors=[],
    )

    with patch(
        "src.agent.tools.landing_builder.promote_landing_tool._build_promotion_service"
    ) as mock_factory:
        mock_service = MagicMock()
        mock_service.promote = AsyncMock(return_value=stub_result)
        mock_factory.return_value = mock_service

        from src.agent.tools.landing_builder.promote_landing_tool import promote_landing_tool
        result = await promote_landing_tool.ainvoke(
            {"project_id": "proj-1", "composition_dict": _composition_dict()}
        )

    assert result["status"] == "success"
    assert result["storage_path"] == "landings/proj-1/20260710T000000Z/source.tar.gz"


async def test_tool_raises_on_invalid_composition():
    from src.agent.tools.landing_builder.promote_landing_tool import promote_landing_tool
    with pytest.raises(Exception):
        await promote_landing_tool.ainvoke(
            {"project_id": "proj-1", "composition_dict": {"theme": {}, "sections": []}}
        )


def test_build_promotion_service_raises_without_template_repo(monkeypatch):
    monkeypatch.delenv("LANDING_TEMPLATE_REPO", raising=False)
    from src.agent.tools.landing_builder.promote_landing_tool import _build_promotion_service
    with pytest.raises(ValueError, match="LANDING_TEMPLATE_REPO"):
        _build_promotion_service()


def test_build_promotion_service_wires_dependencies(monkeypatch):
    monkeypatch.setenv("LANDING_TEMPLATE_REPO", "acme/landing-template")
    monkeypatch.setenv("FIREBASE_STORAGE_BUCKET", "test.appspot.com")

    with patch(
        "src.agent.tools.landing_builder.infrastructure.landing_storage.firebase_admin"
    ) as m:
        m._apps = {"[DEFAULT]": True}
        from src.agent.tools.landing_builder.promote_landing_tool import _build_promotion_service
        from src.agent.tools.landing_builder.infrastructure.github_template_fetcher import (
            GithubTemplateFetcher,
        )

        service = _build_promotion_service()
        assert isinstance(service._template_source, GithubTemplateFetcher)
        assert service._template_repo == "acme/landing-template"
