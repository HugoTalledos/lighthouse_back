from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClientPort(ABC):
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
    ) -> str: ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        *,
        system: str | None = None,
        temperature: float | None = None,
    ) -> T: ...

    @abstractmethod
    async def generate_structured_from_schema(
        self,
        prompt: str,
        schema: dict,
        *,
        system: str | None = None,
        temperature: float | None = None,
    ) -> dict: ...
