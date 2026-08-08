from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ...domain.ports import ProjectRepositoryPort


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str = Field(min_length=1, max_length=200)

    @field_validator("thread_id")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("thread_id must not be blank")
        return value


def build_router(repo: ProjectRepositoryPort) -> APIRouter:
    router = APIRouter()

    @router.post("/projects", status_code=201)
    def create_project(request: CreateProjectRequest) -> dict:
        project = repo.create_for_thread(request.thread_id)
        return project.model_dump(mode="json")

    @router.get("/projects")
    def list_projects() -> list[dict]:
        return [project.model_dump(mode="json") for project in repo.list()]

    @router.get("/projects/{project_id}")
    def get_project(project_id: str) -> dict:
        project = repo.get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        return project.model_dump(mode="json")

    return router
