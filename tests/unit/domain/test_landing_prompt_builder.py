from __future__ import annotations
from src.agent.tools.landing_builder.domain.models import LandingBrief
from src.agent.tools.landing_builder.domain.prompt_builder import build_landing_prompt

_PAGE_JSON_DOC = (
    "# page.json Reference\n\n"
    "Sections: hero, features, capture, pricing, testimonials, faq, cta, footer."
)


def _brief(**overrides):
    defaults = dict(
        project_id="proj-1",
        business_name="Acme Corp",
        value_proposition="Saves you time",
        target_customer="Busy professionals",
        product_or_service="Landing page builder",
    )
    return LandingBrief(**{**defaults, **overrides})


def test_returns_two_strings():
    system, user = build_landing_prompt(_brief(), _PAGE_JSON_DOC)
    assert isinstance(system, str) and len(system) > 0
    assert isinstance(user, str) and len(user) > 0


def test_system_includes_page_json_doc_verbatim():
    system, _ = build_landing_prompt(_brief(), _PAGE_JSON_DOC)
    assert _PAGE_JSON_DOC in system


def test_system_mentions_cro_strategist():
    system, _ = build_landing_prompt(_brief(), _PAGE_JSON_DOC)
    assert "CRO" in system or "conversion" in system.lower()


def test_system_states_fixed_section_library_constraint():
    system, _ = build_landing_prompt(_brief(), _PAGE_JSON_DOC)
    assert "never write" in system.lower()


def test_user_includes_business_name():
    _, user = build_landing_prompt(_brief(), _PAGE_JSON_DOC)
    assert "Acme Corp" in user


def test_user_includes_value_proposition():
    _, user = build_landing_prompt(_brief(), _PAGE_JSON_DOC)
    assert "Saves you time" in user


def test_user_includes_target_customer():
    _, user = build_landing_prompt(_brief(), _PAGE_JSON_DOC)
    assert "Busy professionals" in user


def test_user_includes_product_or_service():
    _, user = build_landing_prompt(_brief(), _PAGE_JSON_DOC)
    assert "Landing page builder" in user


def test_user_includes_tone_hint_when_provided():
    _, user = build_landing_prompt(_brief(tone_hint="playful"), _PAGE_JSON_DOC)
    assert "playful" in user


def test_user_omits_tone_when_none():
    _, user = build_landing_prompt(_brief(), _PAGE_JSON_DOC)
    assert "Tone:" not in user


def test_user_includes_primary_cta_goal_when_provided():
    _, user = build_landing_prompt(_brief(primary_cta_goal="collect emails"), _PAGE_JSON_DOC)
    assert "collect emails" in user


def test_user_omits_primary_cta_goal_when_none():
    _, user = build_landing_prompt(_brief(), _PAGE_JSON_DOC)
    assert "Primary CTA goal:" not in user


def test_user_includes_brand_color_hint_when_provided():
    _, user = build_landing_prompt(_brief(brand_color_hint="#FF5733"), _PAGE_JSON_DOC)
    assert "#FF5733" in user


def test_user_omits_brand_color_hint_when_none():
    _, user = build_landing_prompt(_brief(), _PAGE_JSON_DOC)
    assert "Brand color hint:" not in user
