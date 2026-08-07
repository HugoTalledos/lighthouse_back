from __future__ import annotations
import json

from ...domain.events import ChatEvent


def format_event(event: ChatEvent) -> str:
    """Serializa un ChatEvent al formato de cable SSE.

    json.dumps escapa los saltos de línea del contenido, que si no partirían
    el evento en dos en el cable.
    """
    data = json.dumps(event.data, ensure_ascii=False)
    return f"event: {event.event}\ndata: {data}\n\n"
