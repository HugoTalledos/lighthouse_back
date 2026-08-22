from __future__ import annotations
import os
import json
from typing import TypeVar
import httpx
from pydantic import BaseModel

from ..domain.ports import LLMClientPort

T = TypeVar("T", bound=BaseModel)


class OllamaLocalClient(LLMClientPort):
    def __init__(self, model: str, temperature: float = 0.7, timeout: float = 60.0) -> None:
        self._base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._model = model
        self._temperature = temperature
        self._timeout = timeout

    def _resolve_temperature(self, temperature: float | None) -> float:
        return self._temperature if temperature is None else temperature

    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": self._resolve_temperature(temperature)},
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
        temperature: float | None = None,
    ) -> T:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": False,
                    "format": response_model.model_json_schema(),
                    "options": {"temperature": self._resolve_temperature(temperature)},
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

    async def generate_structured_from_schema(
        self,
        prompt: str,
        schema: dict,
        *,
        system: str | None = None,
        temperature: float | None = None,
    ) -> dict:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": False,
                    "format": schema,
                    "options": {"temperature": self._resolve_temperature(temperature)},
                },
            )
            response.raise_for_status()

        content = response.json()["message"]["content"]
        try:
            return json.loads(content)
        except Exception as e:
            raise ValueError(f"Failed to parse structured response from schema: {e}") from e
