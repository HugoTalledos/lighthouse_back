from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from ...application.chat_service import stream_chat
from .sse import format_event


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    project_id: str = Field(max_length=200)
    thread_id: str = Field(max_length=200)

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be blank")
        return v


def build_chat_router(graph, repo) -> APIRouter:
    """Construye el router con el endpoint `POST /chat` que transmite la
    conversación como Server-Sent Events."""
    router = APIRouter()

    @router.post("/chat")
    async def chat(request: ChatRequest) -> StreamingResponse:
        project = repo.get(request.project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        if request.thread_id not in project.thread_ids:
            raise HTTPException(status_code=409, detail="thread does not belong to project")

        async def wire():
            async for event in stream_chat(
                graph, request.message, request.project_id, request.thread_id
            ):
                yield format_event(event)

        return StreamingResponse(
            wire(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router
