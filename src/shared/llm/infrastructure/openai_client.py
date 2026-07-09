from __future__ import annotations
import os
from typing import TypeVar
import httpx
from pydantic import BaseModel

from ..domain.ports import LLMClientPort

T = TypeVar("T", bound=BaseModel)

_CHAT_URL = "https://api.openai.com/v1/chat/completions"
_TIMEOUT = 60.0


class OpenAIClient(LLMClientPort):
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self._api_key = api_key
        self._model = os.getenv("OPENAI_MODEL", "gpt-4o")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

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
                headers=self._headers(),
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
                headers=self._headers(),
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
