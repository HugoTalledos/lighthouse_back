from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

ResourceKind = Literal["landing", "campaign", "images"]
ApprovalStatus = Literal["pending", "approved"]


class ResourceState(BaseModel):
    status: ApprovalStatus = "pending"
    payload: dict = Field(default_factory=dict)


class Project(BaseModel):
    project_id: str
    thread_ids: list[str]
    business_name: str | None = None
    value_proposition: str | None = None
    created_at: datetime
    updated_at: datetime
    resources: dict[ResourceKind, ResourceState] = Field(
        default_factory=lambda: {
            "landing": ResourceState(),
            "campaign": ResourceState(),
            "images": ResourceState(),
        }
    )
