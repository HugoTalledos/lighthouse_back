from __future__ import annotations
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from ...application.chat_service import stream_chat
from .sse import format_event


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    thread_id: str | None = None

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be blank")
        return v


def build_chat_router(graph) -> APIRouter:
    """Construye el router con el endpoint `POST /chat` que transmite la
    conversación como Server-Sent Events."""
    router = APIRouter()

    @router.post("/chat")
    async def chat(request: ChatRequest) -> StreamingResponse:
        thread_id = request.thread_id or str(uuid.uuid4())

        async def wire():
            async for event in stream_chat(graph, request.message, thread_id):
                yield format_event(event)

        return StreamingResponse(
            wire(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router
