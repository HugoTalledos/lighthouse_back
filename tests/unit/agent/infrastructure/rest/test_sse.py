import json
from src.agent.domain.events import start_event, tool_result_event, message_event
from src.agent.infrastructure.rest.sse import format_event


def test_format_event_writes_event_and_data_lines():
    assert format_event(start_event("t-1")) == 'event: start\ndata: {"thread_id": "t-1"}\n\n'


def test_format_event_ends_with_blank_line_separator():
    assert format_event(message_event("hola")).endswith("\n\n")


def test_format_event_keeps_accents_readable():
    assert "café" in format_event(message_event("café"))


def test_format_event_serializes_nested_result():
    wire = format_event(tool_result_event("t", "success", {"creatives": [{"url": "u"}]}))
    payload = json.loads(wire.split("data: ", 1)[1])
    assert payload["result"]["creatives"][0]["url"] == "u"


def test_format_event_escapes_newlines_in_content():
    wire = format_event(message_event("línea 1\nlínea 2"))
    assert len(wire.strip().splitlines()) == 2
