from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class LandingBrief(BaseModel):
    project_id: str
    business_name: str
    value_proposition: str
    target_customer: str
    product_or_service: str
    tone_hint: str | None = None
    primary_cta_goal: str | None = None
    brand_color_hint: str | None = None


class LandingBuildResult(BaseModel):
    brief: LandingBrief
    composition: dict | None
    preview_url: str | None
    status: Literal["success", "failed"]
    errors: list[str]


class LandingPromoteResult(BaseModel):
    project_id: str
    version: str | None
    storage_path: str | None
    status: Literal["success", "failed"]
    errors: list[str]
