from __future__ import annotations
import os
from typing import TypeVar
import httpx
from pydantic import BaseModel

from ..domain.ports import LLMClientPort

T = TypeVar("T", bound=BaseModel)

_TIMEOUT = 60.0


class OllamaLocalClient(LLMClientPort):
    def __init__(self) -> None:
        self._base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._model = os.getenv("OLLAMA_MODEL", "llama3.1")

    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
            )
            response.raise_for_status()

        return response.json()["message"]["content"]

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        *,
        system: str | None = None,
        temperature: float = 0.4,
    ) -> T:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": False,
                    "format": response_model.model_json_schema(),
                    "options": {"temperature": temperature},
                },
            )
            response.raise_for_status()

        content = response.json()["message"]["content"]
        try:
            return response_model.model_validate_json(content)
        except Exception as e:
            raise ValueError(
                f"Failed to parse {response_model.__name__} from LLM response: {e}"
            ) from e
