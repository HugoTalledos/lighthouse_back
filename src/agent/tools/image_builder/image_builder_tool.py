from __future__ import annotations
from typing import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.shared.image_gen.factory import build_image_generator
from src.projects.infrastructure.repo_provider import get_project_repository
from .domain.models import ImageBrief
from .application.image_builder_service import ImageBuilderService
from .infrastructure.composer.pillow_composer import PillowImageComposer
from .infrastructure.storage.firebase_storage import FirebaseStorageAdapter


def _build_service() -> ImageBuilderService:
    return ImageBuilderService(
        build_image_generator(),
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
    get_project_repository().upsert_summary(
        brief.project_id, brief.business_name, brief.value_proposition
    )
    return result.model_dump(mode="json")
