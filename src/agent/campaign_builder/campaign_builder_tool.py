from __future__ import annotations
from langchain_core.tools import tool

from .domain.models import CampaignBrief
from .application.campaign_builder_service import CampaignBuilderService
from src.shared.llm.factory import build_llm_client


@tool
async def campaign_builder_tool(brief_dict: dict) -> dict:
    """
    Generates a base Facebook Marketing API campaign configuration
    (Campaign -> AdSet -> Ad) from a business brief. Does not publish.
    Input: serialized CampaignBrief dict.
    Output: serialized CampaignConfigResult dict.
    """
    brief = CampaignBrief.model_validate(brief_dict)
    llm = build_llm_client()
    service = CampaignBuilderService(llm)
    result = await service.build(brief)
    return result.model_dump(mode="json")
