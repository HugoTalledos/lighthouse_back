from __future__ import annotations
import os
from langchain_core.tools import tool

from src.shared.llm.factory import build_llm_client
from .domain.models import LandingBrief
from .application.landing_builder_service import LandingBuilderService
from .infrastructure.github_template_fetcher import GithubTemplateFetcher
from .infrastructure.astro_builder import AstroNodeBuilder
from .infrastructure.firebase_hosting_deployer import FirebaseHostingDeployer


def _build_service() -> LandingBuilderService:
    template_repo = os.getenv("LANDING_TEMPLATE_REPO")
    if not template_repo:
        raise ValueError("LANDING_TEMPLATE_REPO environment variable is not set")
    template_ref = os.getenv("LANDING_TEMPLATE_REF", "main")

    llm = build_llm_client()
    return LandingBuilderService(
        llm, GithubTemplateFetcher(), AstroNodeBuilder(), FirebaseHostingDeployer(),
        template_repo=template_repo, template_ref=template_ref,
    )


@tool
async def landing_builder_tool(brief_dict: dict) -> dict:
    """
    Generates a landing page from a business brief and deploys it to a
    Firebase Hosting preview channel for review. Nothing is persisted;
    call promote_landing_tool once the user approves this version.
    Input: serialized LandingBrief dict.
    Output: serialized LandingBuildResult dict (composition, preview_url, status, errors).
    """
    brief = LandingBrief.model_validate(brief_dict)
    result = await _build_service().build(brief)
    return result.model_dump(mode="json")
