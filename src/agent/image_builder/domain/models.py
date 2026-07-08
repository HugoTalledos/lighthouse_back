from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, field_validator


class ImageBrief(BaseModel):
    project_id: str
    business_name: str
    value_proposition: str
    target_customer: str
    headline: str
    cta_text: str
    style_hints: list[str]
    n_images: int = 3

    @field_validator("headline")
    @classmethod
    def headline_max_40(cls, v: str) -> str:
        if len(v) > 40:
            raise ValueError("headline must be ≤ 40 characters")
        return v

    @field_validator("cta_text")
    @classmethod
    def cta_max_20(cls, v: str) -> str:
        if len(v) > 20:
            raise ValueError("cta_text must be ≤ 20 characters")
        return v


class GeneratedImage(BaseModel):
    provider: str
    image_bytes: bytes
    prompt_used: str
    width: int
    height: int


class ComposedCreative(BaseModel):
    variant_index: int
    image_bytes: bytes
    storage_url: Optional[str]
    headline: str
    cta_text: str
    prompt_used: str
    provider: str


class ImageBuildResult(BaseModel):
    brief: ImageBrief
    creatives: list[ComposedCreative]
    status: Literal["success", "partial", "failed"]
    errors: list[str]
