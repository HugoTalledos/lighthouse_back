from __future__ import annotations
import base64
import os
import httpx

from ...domain.models import GeneratedImage
from ...domain.ports import ImageGeneratorPort

_TIMEOUT = 180.0


class OllamaImageGenerator(ImageGeneratorPort):
    def __init__(self) -> None:
        self._base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._model = os.getenv("OLLAMA_IMAGE_MODEL", "x/flux2-klein:4b")

    async def generate(self, prompt: str, width: int, height: int) -> GeneratedImage:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "options": {"width": width, "height": height},
                    "stream": False,
                },
            )
            response.raise_for_status()
            image_b64 = response.json()["image"]

        return GeneratedImage(
            provider="ollama",
            image_bytes=base64.b64decode(image_b64),
            prompt_used=prompt,
            width=width,
            height=height,
        )
