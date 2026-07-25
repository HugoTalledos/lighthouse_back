from __future__ import annotations
from pydantic import BaseModel


class GeneratedImage(BaseModel):
    provider: str
    image_bytes: bytes
    prompt_used: str
    width: int
    height: int
