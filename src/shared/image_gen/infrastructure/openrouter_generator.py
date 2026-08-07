from __future__ import annotations
import base64
import httpx

from src.shared.openrouter.credentials import OpenRouterCredentials
from ..domain.models import GeneratedImage
from ..domain.ports import ImageGeneratorPort

_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
_TIMEOUT = 180.0


class OpenRouterImageGenerator(ImageGeneratorPort):
    """Image generation via OpenRouter's chat-completions endpoint.

    OpenRouter has no dedicated /images/generations endpoint - image-capable
    models (e.g. google/gemini-2.5-flash-image-preview) are called through
    /chat/completions with modalities: ["image", "text"], and return the
    image as a data: URL in message.images[0].image_url.url. There is no
    request-side width/height control, so the target size is only passed as
    a hint inside the prompt text; the composer center-crops the actual
    returned image to the target creative size regardless.
    """

    def __init__(self, model: str) -> None:
        self._credentials = OpenRouterCredentials()
        self._model = model

    async def generate(self, prompt: str, width: int, height: int) -> GeneratedImage:
        sized_prompt = f"{prompt}\n\nTarget image dimensions: {width}x{height} pixels."

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                _CHAT_URL,
                headers=self._credentials.headers(),
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": sized_prompt}],
                    "modalities": ["image", "text"],
                },
            )
            response.raise_for_status()
            body = response.json()

        try:
            images = body["choices"][0]["message"]["images"]
            data_url = images[0]["image_url"]["url"]
            _, _, b64_data = data_url.partition("base64,")
            if not b64_data:
                raise ValueError("image_url is not a base64 data URL")
            image_bytes = base64.b64decode(b64_data)
        except (KeyError, IndexError, ValueError) as e:
            raise ValueError(f"No image returned by OpenRouter model {self._model!r}: {e}") from e

        return GeneratedImage(
            provider="openrouter",
            image_bytes=image_bytes,
            prompt_used=prompt,
            width=width,
            height=height,
        )
