from __future__ import annotations

from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.projects.infrastructure.persistence.repo_provider import (
    get_project_repository,
)


@tool
async def update_project_metadata_tool(
    business_name: str,
    value_proposition: str,
    state: Annotated[dict, InjectedState],
) -> dict:
    """Persist the reliable business summary for the current project."""
    if not business_name.strip() or not value_proposition.strip():
        raise ValueError("business_name and value_proposition must not be blank")

    project_id = state["project_id"]
    get_project_repository().upsert_summary(
        project_id, business_name, value_proposition
    )
    return {"status": "success", "project_id": project_id}
