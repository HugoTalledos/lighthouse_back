from __future__ import annotations
import os
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.agent.graph import build_graph
from src.agent.infrastructure.rest.chat_routes import build_chat_router
from src.projects.infrastructure.persistence.repo_provider import get_project_repository
from src.projects.infrastructure.rest.routes import build_router


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Si API_KEY no está seteada el API queda abierto: es el modo local."""
    expected = os.getenv("API_KEY")
    if not expected:
        return
    # compare_digest evita filtrar por timing cuántos caracteres coinciden;
    # falla si algún argumento es None, así que primero descartamos ese caso.
    if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="invalid api key")


def _allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "*")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app(repo=None, graph=None) -> FastAPI:
    app = FastAPI(title="Lighthouse API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    protected = [Depends(require_api_key)]
    project_repo = repo or get_project_repository()
    app.include_router(
        build_chat_router(graph or build_graph(), project_repo), dependencies=protected
    )
    app.include_router(
        build_router(project_repo), dependencies=protected
    )
    return app


app = create_app()
