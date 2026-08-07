from __future__ import annotations
from fastapi import FastAPI

from ...domain.ports import ProjectRepositoryPort
from ..persistence.firestore_repository import FirestoreProjectRepository
from .routes import build_router


def create_app(repo: ProjectRepositoryPort | None = None) -> FastAPI:
    app = FastAPI(title="Lighthouse Projects API")
    app.include_router(build_router(repo or FirestoreProjectRepository()))
    return app
