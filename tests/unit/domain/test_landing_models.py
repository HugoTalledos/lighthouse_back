from __future__ import annotations
import pytest
from pydantic import ValidationError
from src.agent.tools.landing_builder.domain.models import (
    LandingBrief, LandingBuildResult, LandingPromoteResult,
)


def _brief(**overrides):
    defaults = dict(
        project_id="proj-1",
        business_name="Acme",
        value_proposition="Saves time",
        target_customer="Professionals",
        product_or_service="Landing pages",
    )
    return LandingBrief(**{**defaults, **overrides})


def _composition():
    return {
        "theme": {
            "primary_color": "#111111", "secondary_color": "#eeeeee", "font_family": "Inter",
            "logo_url": None, "logo_text": None, "logo_icon": None,
        },
        "sections": [
            {"type": "hero", "headline": "Welcome", "subheadline": "Sub", "image_url": None,
             "cta_text": "Start", "cta_url": None},
            {"type": "footer", "business_name": "Acme", "links": [], "social_links": []},
        ],
    }


def test_brief_optional_fields_default_to_none():
    brief = _brief()
    assert brief.tone_hint is None
    assert brief.primary_cta_goal is None
    assert brief.brand_color_hint is None


def test_brief_requires_business_name():
    with pytest.raises(ValidationError):
        LandingBrief(
            project_id="p1", value_proposition="v", target_customer="t", product_or_service="s"
        )


def test_build_result_allows_composition_without_preview_url():
    result = LandingBuildResult(
        brief=_brief(), composition=_composition(), preview_url=None,
        status="failed", errors=["build failed"],
    )
    assert result.preview_url is None
    assert result.composition is not None
    assert result.composition["sections"][0]["type"] == "hero"


def test_build_result_allows_composition_none():
    result = LandingBuildResult(
        brief=_brief(), composition=None, preview_url=None,
        status="failed", errors=["llm failed"],
    )
    assert result.composition is None


def test_promote_result_failed_has_no_version():
    result = LandingPromoteResult(
        project_id="proj-1", version=None, storage_path=None,
        status="failed", errors=["upload failed"],
    )
    assert result.version is None
