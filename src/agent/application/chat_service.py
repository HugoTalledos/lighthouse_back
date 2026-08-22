from __future__ import annotations
import json
import logging
import time
from typing import Any, AsyncIterator

from ..domain.events import (
    ChatEvent, start_event, message_event, tool_call_event,
    tool_result_event, done_event, error_event,
)

logger = logging.getLogger(__name__)


def _log_event(event: ChatEvent, *, thread_id: str, project_id: str, tool_timers: dict) -> None:
    name = event.event
    data = event.data
    extra: dict = {"thread_id": thread_id, "project_id": project_id, "event": name}

    if name == "tool_call":
        tool = data.get("name", "")
        extra["tool"] = tool
        tool_timers[tool] = time.perf_counter()
        logger.info("tool_call", extra=extra)

    elif name == "tool_result":
        tool = data.get("name", "")
        extra["tool"] = tool
        extra["status"] = data.get("status", "unknown")
        start = tool_timers.pop(tool, None)
        if start is not None:
            extra["duration_ms"] = round((time.perf_counter() - start) * 1000)
        level = logging.WARNING if extra["status"] in {"failed", "partial"} else logging.INFO
        logger.log(level, "tool_result", extra=extra)

    elif name == "error":
        extra["error"] = data.get("message", "")
        logger.error("agent_error", extra=extra)

    elif name == "done":
        logger.info("turn_done", extra=extra)


def _parse_tool_content(content: Any) -> dict:
    """El ToolMessage trae un string JSON. Si no lo es, el ToolNode capturó una
    excepción de la tool y dejó el texto crudo del error."""
    if isinstance(content, dict):
        return content
    try:
        parsed = json.loads(content)
    except (TypeError, ValueError):
        return {"error": str(content)}
    return parsed if isinstance(parsed, dict) else {"result": parsed}


def _chatbot_events(payload: dict) -> list[ChatEvent]:
    events: list[ChatEvent] = []
    for message in payload.get("messages", []):
        for call in getattr(message, "tool_calls", None) or []:
            events.append(tool_call_event(call["name"], call.get("args") or {}))
        content = getattr(message, "content", "")
        if isinstance(content, str) and content.strip():
            events.append(message_event(content))
    return events


def _tool_events(payload: dict) -> list[ChatEvent]:
    events: list[ChatEvent] = []
    for message in payload.get("messages", []):
        result = _parse_tool_content(getattr(message, "content", ""))
        status = result.get("status", "failed")
        events.append(tool_result_event(getattr(message, "name", "") or "", status, result))
    return events


async def stream_chat(
    graph, message: str, project_id: str, thread_id: str
) -> AsyncIterator[ChatEvent]:
    """Corre un turno del agente y emite los eventos del chat en orden.

    Siempre empieza con `start` y termina con `done`, incluso si el turno falla:
    los headers de la respuesta ya salieron y el cliente no puede recibir otro
    status code, así que el fallo viaja como evento `error`.
    """
    yield start_event(thread_id)
    stream = None
    tool_timers: dict = {}
    logger.info(
        "turn_start",
        extra={"thread_id": thread_id, "project_id": project_id, "event": "start"},
    )

    try:
        stream = graph.astream(
            {
                "messages": [{"role": "user", "content": message}],
                "thread_id": thread_id,
                "project_id": project_id,
            },
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates",
        )
        async for update in stream:
            for node, payload in update.items():
                if not isinstance(payload, dict):
                    continue
                events = _tool_events(payload) if node == "tools" else _chatbot_events(payload)
                for event in events:
                    _log_event(event, thread_id=thread_id, project_id=project_id, tool_timers=tool_timers)
                    yield event
    except Exception:  # noqa: BLE001 - el turno entero se cayó
        logger.exception(
            "turn_failed",
            extra={"thread_id": thread_id, "project_id": project_id, "event": "error"},
        )
        yield error_event("El turno falló por un error interno. Intenta de nuevo.")
    finally:
        aclose = getattr(stream, "aclose", None)
        if aclose is not None:
            await aclose()

    done = done_event(thread_id, project_id)
    _log_event(done, thread_id=thread_id, project_id=project_id, tool_timers=tool_timers)
    yield done
