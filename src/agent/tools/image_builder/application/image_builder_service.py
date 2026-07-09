from __future__ import annotations
import asyncio
import re
from datetime import datetime

from ..domain.models import ImageBrief, ComposedCreative, ImageBuildResult
from ..domain.ports import ImageGeneratorPort, ImageComposerPort, ImageStoragePort
from ..domain.prompt_builder import PromptBuilder


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class ImageBuilderService:
    def __init__(
        self,
        generator: ImageGeneratorPort,
        composer: ImageComposerPort,
        storage: ImageStoragePort,
    ) -> None:
        self._generator = generator
        self._composer = composer
        self._storage = storage

    async def build(self, brief: ImageBrief) -> ImageBuildResult:
        prompts = PromptBuilder().build_prompts(brief)
        results = await asyncio.gather(
            *[self._generator.generate(prompt, 1200, 628) for prompt in prompts],
            return_exceptions=True,
        )

        creatives: list[ComposedCreative] = []
        errors: list[str] = []
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"Variant {i}: {result}")
                continue
            composed_bytes = self._composer.compose(result, brief)
            filename = f"{_slugify(brief.business_name)}_{i}_{timestamp}.png"
            url = await self._storage.upload(composed_bytes, filename, brief.project_id)
            creatives.append(
                ComposedCreative(
                    variant_index=i,
                    image_bytes=composed_bytes,
                    storage_url=url,
                    headline=brief.headline,
                    cta_text=brief.cta_text,
                    prompt_used=result.prompt_used,
                    provider=result.provider,
                )
            )

        if len(creatives) == brief.n_images:
            status = "success"
        elif len(creatives) > 0:
            status = "partial"
        else:
            status = "failed"

        return ImageBuildResult(
            brief=brief,
            creatives=creatives,
            status=status,
            errors=errors,
        )
