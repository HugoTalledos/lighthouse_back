from __future__ import annotations
import os
from langchain_core.tools import tool

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
async def promote_landing_tool(project_id: str, composition_dict: dict) -> dict:
    """
    Persists the approved landing's source as a versioned snapshot in
    permanent storage. Call this only after the user approves the preview
    from landing_builder_tool.
    Input: project_id and the composition dict the user approved.
    Output: serialized LandingPromoteResult dict (version, storage_path, status, errors).
    """
    result = await _build_promotion_service().promote(project_id, composition_dict)
    return result.model_dump(mode="json")
