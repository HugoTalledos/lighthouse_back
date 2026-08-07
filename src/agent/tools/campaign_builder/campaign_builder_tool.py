from __future__ import annotations
from typing import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from .domain.models import CampaignBrief
from .application.campaign_builder_service import CampaignBuilderService
from src.shared.llm.factory import build_llm_client
from src.shared.llm_config.loader import load_llm_config
from src.projects.infrastructure.persistence.repo_provider import get_project_repository


@tool
async def campaign_builder_tool(brief_dict: dict, state: Annotated[dict, InjectedState]) -> dict:
    """
    Generates a base Facebook Marketing API campaign configuration
    (Campaign -> AdSet -> Ad) from a business brief. Does not publish.
    Input: serialized CampaignBrief dict (without project_id — it is resolved
    automatically from the current conversation).
    Output: serialized CampaignConfigResult dict.
    """
    brief = CampaignBrief.model_validate({**brief_dict, "project_id": state["project_id"]})
    llm = build_llm_client(load_llm_config().for_tool("campaign_builder"))
    service = CampaignBuilderService(llm)
    result = await service.build(brief)
    get_project_repository().upsert_summary(
        brief.project_id, brief.business_name, brief.value_proposition
    )
    return result.model_dump(mode="json")
