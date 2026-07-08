from __future__ import annotations
import os
from langchain_core.tools import tool

from .domain.models import ImageBrief
from .application.image_builder_service import ImageBuilderService
from .infrastructure.dalle_generator import DalleImageGenerator
from .infrastructure.vertex_generator import VertexImageGenerator
from .infrastructure.pillow_composer import PillowImageComposer
from .infrastructure.firebase_storage import FirebaseStorageAdapter


def _build_service() -> ImageBuilderService:
    provider = os.getenv("IMAGE_PROVIDER", "dalle3")
    if provider == "dalle3":
        generator = DalleImageGenerator()
    elif provider == "vertex":
        generator = VertexImageGenerator()
    else:
        raise ValueError(f"Unknown IMAGE_PROVIDER: {provider!r}. Valid values: dalle3, vertex")
    composer = PillowImageComposer()
    storage = FirebaseStorageAdapter()
    return ImageBuilderService(generator, composer, storage)


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
