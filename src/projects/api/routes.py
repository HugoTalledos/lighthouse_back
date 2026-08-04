from __future__ import annotations
from fastapi import APIRouter, HTTPException

from ..domain.ports import ProjectRepositoryPort


def build_router(repo: ProjectRepositoryPort) -> APIRouter:
    router = APIRouter()

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
