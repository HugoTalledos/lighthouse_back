from __future__ import annotations
import os
from typing import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.projects.infrastructure.firestore_repository import FirestoreProjectRepository
from .application.landing_promotion_service import LandingPromotionService
from .infrastructure.github_template_fetcher import GithubTemplateFetcher
from .infrastructure.landing_storage import FirebaseLandingStorage


def _build_promotion_service() -> LandingPromotionService:
    template_repo = os.getenv("LANDING_TEMPLATE_REPO")
    if not template_repo:
        raise ValueError("LANDING_TEMPLATE_REPO environment variable is not set")
    template_ref = os.getenv("LANDING_TEMPLATE_REF", "main")

    return LandingPromotionService(
        GithubTemplateFetcher(), FirebaseLandingStorage(),
        template_repo=template_repo, template_ref=template_ref,
    )


@tool
async def promote_landing_tool(composition_dict: dict, state: Annotated[dict, InjectedState]) -> dict:
    """
    Persists the approved landing's source as a versioned snapshot in
    permanent storage, and marks the landing resource as approved for this
    project. Call this only after the user approves the preview from
    landing_builder_tool.
    Input: the composition dict the user approved (project_id is resolved
    automatically from the current conversation).
    Output: serialized LandingPromoteResult dict (version, storage_path, status, errors).
    """
    project_id = state["project_id"]
    result = await _build_promotion_service().promote(project_id, composition_dict)
    if result.status == "success":
        FirestoreProjectRepository().update_resource(
            project_id, "landing",
            {"storage_path": result.storage_path, "version": result.version},
            "approved",
        )
    return result.model_dump(mode="json")
