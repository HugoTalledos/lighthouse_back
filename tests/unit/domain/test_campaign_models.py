from __future__ import annotations
import pytest
from pydantic import ValidationError
from src.agent.campaign_builder.domain.models import (
    Targeting, Gender, AdCreativeCopy, CallToAction, AdSet, BillingEvent,
    OptimizationGoal, Placements, Ad, CampaignBrief, Campaign, CampaignObjective,
    CampaignConfigResult,
)


def _targeting(**overrides):
    defaults = dict(countries=["MX"], age_min=25, age_max=40)
    return Targeting(**{**defaults, **overrides})


def _creative(**overrides):
    defaults = dict(
        primary_text="Body copy here.",
        headline="Short headline",
        call_to_action=CallToAction.LEARN_MORE,
    )
    return AdCreativeCopy(**{**defaults, **overrides})


def _ad():
    return Ad(name="Ad 1", creative=_creative())


def _adset(**overrides):
    defaults = dict(
        name="Ad Set 1",
        daily_budget_usd=5.0,
        billing_event=BillingEvent.IMPRESSIONS,
        optimization_goal=OptimizationGoal.REACH,
        targeting=_targeting(),
        placements=Placements(publisher_platforms=["facebook"]),
        duration_days=7,
        ads=[_ad()],
    )
    return AdSet(**{**defaults, **overrides})


def _brief():
    return CampaignBrief(
        project_id="proj-1",
        business_name="Acme",
        value_proposition="Saves time",
        target_customer="Professionals",
        product_or_service="SaaS tool",
    )


# --- Targeting validators ---

def test_age_max_less_than_age_min_raises():
    with pytest.raises(ValidationError, match="age_max"):
        _targeting(age_min=40, age_max=25)


def test_age_max_equal_age_min_is_valid():
    t = _targeting(age_min=30, age_max=30)
    assert t.age_max == 30


def test_targeting_requires_at_least_one_country():
    with pytest.raises(ValidationError):
        Targeting(countries=[], age_min=18, age_max=65)


def test_default_gender_is_all():
    t = _targeting()
    assert t.genders == [Gender.ALL]


def test_enum_coercion_gender_from_string():
    t = Targeting(countries=["US"], age_min=18, age_max=65, genders=["MALE"])
    assert t.genders == [Gender.MALE]


# --- AdCreativeCopy validators ---

def test_headline_over_40_chars_raises():
    with pytest.raises(ValidationError, match="headline"):
        _creative(headline="A" * 41)


def test_headline_exactly_40_chars_is_valid():
    copy = _creative(headline="A" * 40)
    assert len(copy.headline) == 40


# --- AdSet validators ---

def test_daily_budget_zero_raises():
    with pytest.raises(ValidationError):
        _adset(daily_budget_usd=0)


def test_daily_budget_negative_raises():
    with pytest.raises(ValidationError):
        _adset(daily_budget_usd=-1.0)


def test_duration_days_zero_raises():
    with pytest.raises(ValidationError):
        _adset(duration_days=0)


def test_adset_requires_at_least_one_ad():
    with pytest.raises(ValidationError):
        _adset(ads=[])


# --- Campaign validators ---

def test_campaign_requires_at_least_one_adset():
    with pytest.raises(ValidationError):
        Campaign(
            name="Camp",
            objective=CampaignObjective.OUTCOME_AWARENESS,
            ad_sets=[],
        )


def test_campaign_default_status_is_paused():
    camp = Campaign(
        name="Camp",
        objective=CampaignObjective.OUTCOME_TRAFFIC,
        ad_sets=[_adset()],
    )
    assert camp.status == "PAUSED"


# --- CampaignConfigResult ---

def test_campaign_config_result_success():
    camp = Campaign(
        name="Camp", objective=CampaignObjective.OUTCOME_LEADS, ad_sets=[_adset()]
    )
    result = CampaignConfigResult(brief=_brief(), campaign=camp, status="success", errors=[])
    assert result.status == "success"
    assert result.campaign is not None


def test_campaign_config_result_failed_has_no_campaign():
    result = CampaignConfigResult(
        brief=_brief(), campaign=None, status="failed", errors=["LLM timeout"]
    )
    assert result.campaign is None
    assert result.errors == ["LLM timeout"]
