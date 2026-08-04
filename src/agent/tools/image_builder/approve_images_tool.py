from __future__ import annotations
from typing import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.projects.infrastructure.firestore_repository import FirestoreProjectRepository


@tool
async def approve_images_tool(
    variant_indices: list[int], creatives: list[dict], state: Annotated[dict, InjectedState]
) -> dict:
    """
    Marks the given image creative variants as approved for this project.
    Call this only after the user approves specific variants produced by
    image_builder_tool.
    Input: variant_indices the user approved, and the full creatives list
    (serialized ComposedCreative dicts) from image_builder_tool's output.
    Output: {"project_id": str, "status": "approved"|"failed", "errors": list[str]}.
    """
    project_id = state["project_id"]
    approved = [c for c in creatives if c.get("variant_index") in variant_indices]
    if not approved:
        return {"project_id": project_id, "status": "failed", "errors": ["no matching creatives for variant_indices"]}

    try:
        FirestoreProjectRepository().update_resource(
            project_id, "images",
            {"creatives": [
                {
                    "variant_index": c["variant_index"],
                    "storage_url": c["storage_url"],
                    "headline": c["headline"],
                    "cta_text": c["cta_text"],
                }
                for c in approved
            ]},
            "approved",
        )
        return {"project_id": project_id, "status": "approved", "errors": []}
    except Exception as e:
        return {"project_id": project_id, "status": "failed", "errors": [str(e)]}
