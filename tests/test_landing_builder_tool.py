from __future__ import annotations
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.agent.tools.landing_builder.domain.models import LandingBrief, LandingBuildResult


def _valid_brief_dict():
    return dict(
        project_id="proj-1",
        business_name="Acme",
        value_proposition="Saves time",
        target_customer="Professionals",
        product_or_service="Landing pages",
    )


def _stub_result(brief):
    composition = {
        "theme": {
            "primary_color": "#111", "secondary_color": "#eee", "font_family": "Inter",
            "logo_url": None, "logo_text": "Acme", "logo_icon": None,
        },
        "sections": [
            {"type": "hero", "headline": "Welcome", "subheadline": "Sub", "cta_text": "Start"},
            {"type": "footer", "business_name": "Acme", "links": [], "social_links": []},
        ],
    }
    return LandingBuildResult(
        brief=brief, composition=composition, preview_url="https://preview.example.com",
        status="success", errors=[],
    )


async def test_tool_returns_dict_with_status():
    brief = LandingBrief.model_validate(_valid_brief_dict())
    stub_result = _stub_result(brief)

    with patch(
        "src.agent.tools.landing_builder.landing_builder_tool._build_service"
    ) as mock_factory, patch(
        "src.agent.tools.landing_builder.landing_builder_tool.FirestoreProjectRepository"
    ) as mock_repo_cls:
        mock_service = MagicMock()
        mock_service.build = AsyncMock(return_value=stub_result)
        mock_factory.return_value = mock_service

        from src.agent.tools.landing_builder.landing_builder_tool import landing_builder_tool
        result = await landing_builder_tool.ainvoke({
            "brief_dict": {k: v for k, v in _valid_brief_dict().items() if k != "project_id"},
            "state": {"project_id": "proj-1"},
        })

    assert result["status"] == "success"
    assert result["preview_url"] == "https://preview.example.com"


async def test_tool_raises_on_invalid_brief():
    from src.agent.tools.landing_builder.landing_builder_tool import landing_builder_tool
    with pytest.raises(Exception):
        await landing_builder_tool.ainvoke({
            "brief_dict": {"business_name": "Only this"},
            "state": {"project_id": "proj-1"},
        })


def test_build_service_raises_without_template_repo(monkeypatch):
    monkeypatch.delenv("LANDING_TEMPLATE_REPO", raising=False)
    from src.agent.tools.landing_builder.landing_builder_tool import _build_service
    with pytest.raises(ValueError, match="LANDING_TEMPLATE_REPO"):
        _build_service()


def test_build_service_wires_dependencies(monkeypatch):
    monkeypatch.setenv("LANDING_TEMPLATE_REPO", "acme/landing-template")
    monkeypatch.setenv("LANDING_TEMPLATE_REF", "v2")
    monkeypatch.setenv("FIREBASE_HOSTING_SITE_ID", "my-site")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")

    from src.agent.tools.landing_builder.landing_builder_tool import _build_service
    from src.agent.tools.landing_builder.infrastructure.github_template_fetcher import (
        GithubTemplateFetcher,
    )

    service = _build_service()
    assert isinstance(service._template_source, GithubTemplateFetcher)
    assert service._template_repo == "acme/landing-template"
    assert service._template_ref == "v2"
