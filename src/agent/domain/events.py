from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel

EventName = Literal["start", "message", "tool_call", "tool_result", "done", "error"]


class ChatEvent(BaseModel):
    """Un evento del turno de chat, listo para serializar a SSE."""
    event: EventName
    data: dict[str, Any]


def start_event(thread_id: str) -> ChatEvent:
    return ChatEvent(event="start", data={"thread_id": thread_id})


def message_event(content: str) -> ChatEvent:
    return ChatEvent(event="message", data={"content": content})


def tool_call_event(name: str, args: dict) -> ChatEvent:
    return ChatEvent(event="tool_call", data={"name": name, "args": args})


def tool_result_event(name: str, status: str, result: dict) -> ChatEvent:
    return ChatEvent(
        event="tool_result", data={"name": name, "status": status, "result": result}
    )


def done_event(thread_id: str, project_id: str | None) -> ChatEvent:
    return ChatEvent(
        event="done", data={"thread_id": thread_id, "project_id": project_id}
    )


def error_event(message: str) -> ChatEvent:
    return ChatEvent(event="error", data={"message": message})
