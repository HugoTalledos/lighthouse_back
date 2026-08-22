from __future__ import annotations
import pytest
from src.shared.llm.domain.ports import LLMClientPort
from src.agent.tools.campaign_builder.domain.models import (
    CampaignBrief, Campaign, CampaignObjective, CampaignConfigResult,
    AdSet, BillingEvent, OptimizationGoal, Targeting, Placements, Ad,
    AdCreativeCopy, CallToAction,
)
from src.agent.tools.campaign_builder.application.campaign_builder_service import CampaignBuilderService


def _brief():
    return CampaignBrief(
        project_id="proj-1",
        business_name="Acme",
        value_proposition="Saves time",
        target_customer="Professionals",
        product_or_service="SaaS tool",
    )


def _canned_campaign():
    return Campaign(
        name="Acme Awareness Campaign",
        objective=CampaignObjective.OUTCOME_AWARENESS,
        status="PAUSED",
        ad_sets=[
            AdSet(
                name="Ad Set 1",
                daily_budget_usd=5.0,
                billing_event=BillingEvent.IMPRESSIONS,
                optimization_goal=OptimizationGoal.REACH,
                targeting=Targeting(countries=["MX"], age_min=25, age_max=45),
                placements=Placements(publisher_platforms=["facebook"]),
                duration_days=7,
                ads=[
                    Ad(
                        name="Ad 1",
                        creative=AdCreativeCopy(
                            primary_text="Try Acme today.",
                            headline="Save Time Now",
                            call_to_action=CallToAction.LEARN_MORE,
                        ),
                    )
                ],
            )
        ],
    )


class FakeLLMClient(LLMClientPort):
    def __init__(self, return_value=None, raise_exc=None):
        self._return = return_value
        self._raise = raise_exc

    async def complete(self, prompt, *, system=None, temperature=0.7):
        raise NotImplementedError

    async def generate_structured(self, prompt, response_model, *, system=None, temperature=0.4):
        if self._raise:
            raise self._raise
        return self._return

    async def generate_structured_from_schema(self, prompt, schema, *, system=None, temperature=0.4):
        raise NotImplementedError


async def test_success_path_returns_success_status():
    service = CampaignBuilderService(FakeLLMClient(return_value=_canned_campaign()))
    result = await service.build(_brief())
    assert result.status == "success"
    assert result.campaign is not None
    assert result.errors == []


async def test_success_path_campaign_matches_llm_output():
    campaign = _canned_campaign()
    service = CampaignBuilderService(FakeLLMClient(return_value=campaign))
    result = await service.build(_brief())
    assert result.campaign.name == campaign.name
    assert result.campaign.objective == CampaignObjective.OUTCOME_AWARENESS


async def test_success_path_brief_is_echoed():
    brief = _brief()
    service = CampaignBuilderService(FakeLLMClient(return_value=_canned_campaign()))
    result = await service.build(brief)
    assert result.brief.project_id == brief.project_id


async def test_llm_runtime_error_returns_failed():
    service = CampaignBuilderService(FakeLLMClient(raise_exc=RuntimeError("API down")))
    result = await service.build(_brief())
    assert result.status == "failed"
    assert result.campaign is None
    assert "API down" in result.errors[0]


async def test_llm_value_error_returns_failed():
    service = CampaignBuilderService(FakeLLMClient(raise_exc=ValueError("bad schema")))
    result = await service.build(_brief())
    assert result.status == "failed"
    assert "bad schema" in result.errors[0]


async def test_service_never_raises():
    service = CampaignBuilderService(FakeLLMClient(raise_exc=Exception("unexpected")))
    result = await service.build(_brief())
    assert isinstance(result, CampaignConfigResult)


async def test_exception_with_empty_str_falls_back_to_exception_type_name():
    service = CampaignBuilderService(FakeLLMClient(raise_exc=TimeoutError()))
    result = await service.build(_brief())
    assert result.status == "failed"
    assert result.errors == ["TimeoutError"]
