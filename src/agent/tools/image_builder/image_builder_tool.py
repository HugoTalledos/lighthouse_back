from __future__ import annotations
from typing import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.shared.image_gen.factory import build_image_generator
from src.shared.llm_config.loader import load_llm_config
from src.projects.infrastructure.persistence.repo_provider import get_project_repository
from .domain.models import ImageBrief
from .application.image_builder_service import ImageBuilderService
from .infrastructure.composer.pillow_composer import PillowImageComposer
from .infrastructure.storage.firebase_storage import FirebaseStorageAdapter


def _build_service() -> ImageBuilderService:
    return ImageBuilderService(
        build_image_generator(load_llm_config().for_tool("image_builder")),
        PillowImageComposer(),
        FirebaseStorageAdapter(),
    )


@tool
async def image_builder_tool(brief_dict: dict, state: Annotated[dict, InjectedState]) -> dict:
    """
    Generates ad creative images for a business validation campaign.
    Input: serialized ImageBrief dict (without project_id — it is resolved
    automatically from the current conversation).
    Output: serialized ImageBuildResult dict.
    """
    brief = ImageBrief.model_validate({**brief_dict, "project_id": state["project_id"]})
    service = _build_service()
    result = await service.build(brief)
    serialized_result = result.model_dump(
        mode="json", exclude={"creatives": {"__all__": {"image_bytes"}}}
    )
    repository = get_project_repository()
    repository.upsert_summary(
        brief.project_id, brief.business_name, brief.value_proposition
    )
    if result.status != "failed" and serialized_result["creatives"]:
        repository.update_resource(
            brief.project_id,
            "images",
            {"creatives": serialized_result["creatives"]},
            "pending",
        )
    return serialized_result
