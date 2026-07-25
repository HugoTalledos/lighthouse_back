from __future__ import annotations
import os
import json
from typing import TypeVar
import httpx
from pydantic import BaseModel

from ..domain.ports import LLMClientPort
from src.shared.openrouter.credentials import OpenRouterCredentials

T = TypeVar("T", bound=BaseModel)

_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
_TIMEOUT = 60.0


class OpenRouterClient(LLMClientPort):
    def __init__(self) -> None:
        self._credentials = OpenRouterCredentials()
        self._model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

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
                _CHAT_URL,
                headers=self._credentials.headers(),
                json={
                    "model": self._model,
                    "messages": messages,
                    "temperature": temperature,
                },
            )
            response.raise_for_status()

        return response.json()["choices"][0]["message"]["content"]

    async def generate_structured(
        self,
        prompt: str,
        response_type: type[T],
        *,
        system: str | None = None,
        temperature: float = 0.4,
    ) -> T:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        schema = response_type.model_json_schema()
        response_name = response_type.__name__

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                _CHAT_URL,
                headers=self._credentials.headers(),
                json={
                    "model": self._model,
                    "messages": messages,
                    "temperature": temperature,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": response_name,
                            "schema": schema,
                            "strict": True,
                        },
                    },
                },
            )
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        try:
            return response_type.model_validate_json(content)
        except Exception as e:
            raise ValueError(f"Failed to parse {response_name} from LLM response: {e}") from e

    async def generate_structured_from_schema(
        self,
        prompt: str,
        schema: dict,
        *,
        system: str | None = None,
        temperature: float = 0.4,
    ) -> dict:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                _CHAT_URL,
                headers=self._credentials.headers(),
                json={
                    "model": self._model,
                    "messages": messages,
                    "temperature": temperature,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "StructuredResponse",
                            "schema": schema,
                            "strict": True,
                        },
                    },
                },
            )
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except Exception as e:
            raise ValueError(f"Failed to parse structured response from schema: {e}") from e
