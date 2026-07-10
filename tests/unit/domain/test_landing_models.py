from __future__ import annotations
import pytest
from pydantic import ValidationError
from src.agent.tools.landing_builder.domain.models import (
    LandingBrief, Theme, HeroSection, FeaturesSection, FeatureItem,
    TestimonialsSection, Testimonial, PricingSection, PricingPlan,
    FAQSection, FAQItem, CTASection, FooterSection, FooterLink, SocialLink,
    PageComposition, LandingBuildResult, LandingPromoteResult,
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


def _theme():
    return Theme(primary_color="#111111", secondary_color="#eeeeee", font_family="Inter")


def _hero():
    return HeroSection(headline="Welcome", subheadline="Sub", cta_text="Start")


def _footer():
    return FooterSection(business_name="Acme", links=[], social_links=[])


# --- LandingBrief ---

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


# --- Section discriminated union ---

def test_hero_section_default_type():
    assert _hero().type == "hero"


def test_page_composition_dispatches_by_type():
    composition = PageComposition(
        theme=_theme(),
        sections=[
            {"type": "hero", "headline": "H", "subheadline": "S", "cta_text": "Go"},
            {"type": "footer", "business_name": "Acme", "links": [], "social_links": []},
        ],
    )
    assert isinstance(composition.sections[0], HeroSection)
    assert isinstance(composition.sections[1], FooterSection)


def test_page_composition_rejects_unknown_section_type():
    with pytest.raises(ValidationError):
        PageComposition(theme=_theme(), sections=[{"type": "banner", "headline": "H"}])


def test_page_composition_requires_at_least_one_section():
    with pytest.raises(ValidationError):
        PageComposition(theme=_theme(), sections=[])


def test_page_composition_preserves_section_order():
    composition = PageComposition(theme=_theme(), sections=[_hero(), _footer()])
    assert composition.sections[0].type == "hero"
    assert composition.sections[1].type == "footer"


# --- FeaturesSection bounds (3-6 items) ---

def _feature_item(i):
    return FeatureItem(icon="star", title=f"Feature {i}", description="desc")


def test_features_section_rejects_fewer_than_3_items():
    with pytest.raises(ValidationError):
        FeaturesSection(items=[_feature_item(1), _feature_item(2)])


def test_features_section_rejects_more_than_6_items():
    with pytest.raises(ValidationError):
        FeaturesSection(items=[_feature_item(i) for i in range(7)])


def test_features_section_accepts_3_to_6_items():
    section = FeaturesSection(items=[_feature_item(i) for i in range(4)])
    assert len(section.items) == 4


# --- Other section variants construct cleanly ---

def test_testimonials_section():
    section = TestimonialsSection(
        items=[Testimonial(quote="Great!", author_name="Jane", author_role="CEO")]
    )
    assert section.type == "testimonials"


def test_pricing_section():
    section = PricingSection(
        plans=[PricingPlan(name="Pro", price="$10", features=["A", "B"], cta_text="Buy")]
    )
    assert section.type == "pricing"


def test_faq_section():
    section = FAQSection(items=[FAQItem(question="Q?", answer="A.")])
    assert section.type == "faq"


def test_cta_section():
    section = CTASection(headline="Ready?", button_text="Go")
    assert section.type == "cta"


def test_footer_section_with_links():
    section = FooterSection(
        business_name="Acme",
        links=[FooterLink(label="Privacy", url="https://acme.com/privacy")],
        social_links=[SocialLink(platform="twitter", url="https://twitter.com/acme")],
    )
    assert section.type == "footer"


# --- LandingBuildResult / LandingPromoteResult ---

def test_build_result_allows_composition_without_preview_url():
    composition = PageComposition(theme=_theme(), sections=[_hero(), _footer()])
    result = LandingBuildResult(
        brief=_brief(), composition=composition, preview_url=None,
        status="failed", errors=["build failed"],
    )
    assert result.preview_url is None
    assert result.composition is not None


def test_promote_result_failed_has_no_version():
    result = LandingPromoteResult(
        project_id="proj-1", version=None, storage_path=None,
        status="failed", errors=["upload failed"],
    )
    assert result.version is None
