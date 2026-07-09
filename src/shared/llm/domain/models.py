from __future__ import annotations
from enum import Enum
from pydantic import BaseModel


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(BaseModel):
    role: Role
    content: str


class LLMResponse(BaseModel):
    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
