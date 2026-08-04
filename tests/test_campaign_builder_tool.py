from __future__ import annotations
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.agent.tools.campaign_builder.domain.models import (
    CampaignBrief, Campaign, CampaignObjective, CampaignConfigResult,
    AdSet, BillingEvent, OptimizationGoal, Targeting, Placements, Ad,
    AdCreativeCopy, CallToAction,
)


def _valid_brief_dict():
    return dict(
        business_name="Acme",
        value_proposition="Saves time",
        target_customer="Professionals",
        product_or_service="SaaS tool",
    )


def _canned_campaign():
    return Campaign(
        name="Acme Campaign",
        objective=CampaignObjective.OUTCOME_AWARENESS,
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
                            primary_text="body",
                            headline="Short",
                            call_to_action=CallToAction.LEARN_MORE,
                        ),
                    )
                ],
            )
        ],
    )


async def test_tool_returns_dict_with_status(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")

    mock_client = MagicMock()
    mock_client.generate_structured = AsyncMock(return_value=_canned_campaign())

    with patch(
        "src.agent.tools.campaign_builder.campaign_builder_tool.build_llm_client",
        return_value=mock_client,
    ), patch(
        "src.agent.tools.campaign_builder.campaign_builder_tool.get_project_repository"
    ):
        from src.agent.tools.campaign_builder.campaign_builder_tool import campaign_builder_tool
        result = await campaign_builder_tool.ainvoke({
            "brief_dict": _valid_brief_dict(), "state": {"project_id": "proj-1"},
        })

    assert result["status"] == "success"
    assert result["campaign"]["name"] == "Acme Campaign"


async def test_tool_result_is_serializable(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")

    mock_client = MagicMock()
    mock_client.generate_structured = AsyncMock(return_value=_canned_campaign())

    with patch(
        "src.agent.tools.campaign_builder.campaign_builder_tool.build_llm_client",
        return_value=mock_client,
    ), patch(
        "src.agent.tools.campaign_builder.campaign_builder_tool.get_project_repository"
    ):
        from src.agent.tools.campaign_builder.campaign_builder_tool import campaign_builder_tool
        result = await campaign_builder_tool.ainvoke({
            "brief_dict": _valid_brief_dict(), "state": {"project_id": "proj-1"},
        })

    import json
    json.dumps(result)  # must not raise


async def test_tool_raises_on_invalid_brief():
    from src.agent.tools.campaign_builder.campaign_builder_tool import campaign_builder_tool
    with pytest.raises(Exception):
        await campaign_builder_tool.ainvoke({
            "brief_dict": {"business_name": "Only this"}, "state": {"project_id": "proj-1"},
        })


async def test_tool_captures_llm_error_in_result(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")

    mock_client = MagicMock()
    mock_client.generate_structured = AsyncMock(side_effect=RuntimeError("LLM timeout"))

    with patch(
        "src.agent.tools.campaign_builder.campaign_builder_tool.build_llm_client",
        return_value=mock_client,
    ), patch(
        "src.agent.tools.campaign_builder.campaign_builder_tool.get_project_repository"
    ):
        from src.agent.tools.campaign_builder.campaign_builder_tool import campaign_builder_tool
        result = await campaign_builder_tool.ainvoke({
            "brief_dict": _valid_brief_dict(), "state": {"project_id": "proj-1"},
        })

    assert result["status"] == "failed"
    assert "LLM timeout" in result["errors"][0]
    assert result["campaign"] is None
