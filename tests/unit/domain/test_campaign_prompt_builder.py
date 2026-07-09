from __future__ import annotations
from src.agent.campaign_builder.domain.models import CampaignBrief
from src.agent.campaign_builder.domain.prompt_builder import build_campaign_prompt


def _brief(**overrides):
    defaults = dict(
        project_id="proj-1",
        business_name="Acme Corp",
        value_proposition="Saves time",
        target_customer="Busy professionals",
        product_or_service="SaaS productivity tool",
    )
    return CampaignBrief(**{**defaults, **overrides})


def test_returns_two_strings():
    result = build_campaign_prompt(_brief())
    assert isinstance(result, tuple)
    assert len(result) == 2
    system, user = result
    assert isinstance(system, str) and len(system) > 0
    assert isinstance(user, str) and len(user) > 0


def test_system_mentions_meta_ads_strategist():
    system, _ = build_campaign_prompt(_brief())
    assert "Meta Ads" in system


def test_system_includes_all_campaign_objective_values():
    system, _ = build_campaign_prompt(_brief())
    for value in ["OUTCOME_AWARENESS", "OUTCOME_TRAFFIC", "OUTCOME_ENGAGEMENT",
                  "OUTCOME_LEADS", "OUTCOME_APP_PROMOTION", "OUTCOME_SALES"]:
        assert value in system, f"Missing {value} in system prompt"


def test_system_includes_all_call_to_action_values():
    system, _ = build_campaign_prompt(_brief())
    for value in ["LEARN_MORE", "SHOP_NOW", "SIGN_UP", "SUBSCRIBE",
                  "CONTACT_US", "DOWNLOAD", "GET_OFFER", "GET_QUOTE"]:
        assert value in system, f"Missing {value} in system prompt"


def test_system_requires_paused_status():
    system, _ = build_campaign_prompt(_brief())
    assert "PAUSED" in system


def test_system_mentions_adset_and_ad_count_constraints():
    system, _ = build_campaign_prompt(_brief())
    assert "one AdSet" in system or "1 AdSet" in system or "exactly one" in system.lower()


def test_user_includes_business_name():
    _, user = build_campaign_prompt(_brief())
    assert "Acme Corp" in user


def test_user_includes_value_proposition():
    _, user = build_campaign_prompt(_brief())
    assert "Saves time" in user


def test_user_includes_target_customer():
    _, user = build_campaign_prompt(_brief())
    assert "Busy professionals" in user


def test_user_includes_product_or_service():
    _, user = build_campaign_prompt(_brief())
    assert "SaaS productivity tool" in user


def test_user_includes_budget_when_provided():
    brief = _brief(approx_daily_budget_usd=10.0)
    _, user = build_campaign_prompt(brief)
    assert "10.0" in user


def test_user_omits_budget_when_none():
    _, user = build_campaign_prompt(_brief())
    assert "budget" not in user.lower()


def test_user_includes_country_when_provided():
    brief = _brief(country="MX")
    _, user = build_campaign_prompt(brief)
    assert "MX" in user


def test_user_omits_country_when_none():
    _, user = build_campaign_prompt(_brief())
    assert "country" not in user.lower()


def test_user_includes_goal_hint_when_provided():
    brief = _brief(goal_hint="Drive webinar sign-ups")
    _, user = build_campaign_prompt(brief)
    assert "Drive webinar sign-ups" in user


def test_user_omits_goal_hint_when_none():
    _, user = build_campaign_prompt(_brief())
    assert "goal" not in user.lower()
