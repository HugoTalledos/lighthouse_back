from __future__ import annotations
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.agent.tools.landing_builder.domain.models import LandingPromoteResult


def _composition_dict():
    return {
        "theme": {
            "primary_color": "#111", "secondary_color": "#eee", "font_family": "Inter",
            "logo_url": None, "logo_text": None, "logo_icon": None,
        },
        "sections": [
            {"type": "hero", "headline": "Welcome", "subheadline": "Sub", "cta_text": "Start"},
            {"type": "footer", "business_name": "Acme", "links": [], "social_links": []},
        ],
    }


async def test_tool_returns_dict_with_status():
    stub_result = LandingPromoteResult(
        project_id="proj-1", version="20260710T000000Z",
        storage_path="landings/proj-1/20260710T000000Z/source.tar.gz",
        status="success", errors=[],
    )

    with patch(
        "src.agent.tools.landing_builder.promote_landing_tool._build_promotion_service"
    ) as mock_factory, patch(
        "src.agent.tools.landing_builder.promote_landing_tool.FirestoreProjectRepository"
    ) as mock_repo_cls:
        mock_service = MagicMock()
        mock_service.promote = AsyncMock(return_value=stub_result)
        mock_factory.return_value = mock_service

        from src.agent.tools.landing_builder.promote_landing_tool import promote_landing_tool
        result = await promote_landing_tool.ainvoke({
            "composition_dict": _composition_dict(),
            "state": {"project_id": "proj-1"},
        })

    assert result["status"] == "success"
    assert result["storage_path"] == "landings/proj-1/20260710T000000Z/source.tar.gz"


async def test_tool_passes_composition_dict_through_to_service():
    with patch(
        "src.agent.tools.landing_builder.promote_landing_tool._build_promotion_service"
    ) as mock_factory, patch(
        "src.agent.tools.landing_builder.promote_landing_tool.FirestoreProjectRepository"
    ) as mock_repo_cls:
        mock_service = MagicMock()
        mock_service.promote = AsyncMock(return_value=LandingPromoteResult(
            project_id="proj-1", version="v1", storage_path="path", status="success", errors=[],
        ))
        mock_factory.return_value = mock_service

        from src.agent.tools.landing_builder.promote_landing_tool import promote_landing_tool
        composition = _composition_dict()
        await promote_landing_tool.ainvoke({
            "composition_dict": composition,
            "state": {"project_id": "proj-1"},
        })

        mock_service.promote.assert_awaited_once_with("proj-1", composition)


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
