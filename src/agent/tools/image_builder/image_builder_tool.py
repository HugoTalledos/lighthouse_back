from __future__ import annotations
from langchain_core.tools import tool

from src.shared.image_gen.factory import build_image_generator
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
async def image_builder_tool(brief_dict: dict) -> dict:
    """
    Generates ad creative images for a business validation campaign.
    Input: serialized ImageBrief dict.
    Output: serialized ImageBuildResult dict.
    """
    brief = ImageBrief.model_validate(brief_dict)
    service = _build_service()
    result = await service.build(brief)
    return result.model_dump(mode="json")
