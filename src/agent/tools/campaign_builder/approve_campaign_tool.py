from __future__ import annotations
from typing import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.projects.infrastructure.repo_provider import get_project_repository


@tool
async def approve_campaign_tool(campaign_config: dict, state: Annotated[dict, InjectedState]) -> dict:
    """
    Marks the given Facebook Marketing API campaign configuration as approved
    for this project. Call this only after the user approves the config
    produced by campaign_builder_tool.
    Input: the Campaign dict the user approved.
    Output: {"project_id": str, "status": "approved"|"failed", "errors": list[str]}.
    """
    project_id = state["project_id"]
    if not campaign_config:
        return {"project_id": project_id, "status": "failed", "errors": ["campaign_config is empty"]}

    try:
        get_project_repository().update_resource(
            project_id, "campaign", {"config": campaign_config}, "approved",
        )
        return {"project_id": project_id, "status": "approved", "errors": []}
    except Exception as e:
        return {"project_id": project_id, "status": "failed", "errors": [str(e)]}
