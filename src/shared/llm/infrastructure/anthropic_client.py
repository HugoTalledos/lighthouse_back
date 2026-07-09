from __future__ import annotations
from typing import TypeVar
from pydantic import BaseModel

from ..domain.ports import LLMClientPort

T = TypeVar("T", bound=BaseModel)


class AnthropicClient(LLMClientPort):
    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        raise NotImplementedError("TODO: Anthropic integration")

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        *,
        system: str | None = None,
        temperature: float = 0.4,
    ) -> T:
        raise NotImplementedError("TODO: Anthropic integration")
