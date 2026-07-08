from __future__ import annotations
import os
import httpx

from ..domain.models import GeneratedImage
from ..domain.ports import ImageGeneratorPort

_DALLE_URL = "https://api.openai.com/v1/images/generations"
_TIMEOUT = 60.0


class DalleImageGenerator(ImageGeneratorPort):
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self._api_key = api_key

    async def generate(self, prompt: str, width: int, height: int) -> GeneratedImage:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                _DALLE_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": f"{width}x{height}",
                    "response_format": "url",
                },
            )
            response.raise_for_status()
            image_url = response.json()["data"][0]["url"]

            image_response = await client.get(image_url)
            image_response.raise_for_status()

        return GeneratedImage(
            provider="dalle3",
            image_bytes=image_response.content,
            prompt_used=prompt,
            width=width,
            height=height,
        )
