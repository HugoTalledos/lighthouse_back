from __future__ import annotations
import json
from langchain_core.messages import AIMessage, ToolMessage
from src.agent.application.chat_service import stream_chat


class FakeGraph:
    """Grafo doble: emite updates predefinidos y recuerda cómo lo invocaron."""

    def __init__(self, updates, error=None):
        self._updates = updates
        self._error = error
        self.state = None
        self.config = None

    def astream(self, state, config=None, stream_mode=None):
        self.state = state
        self.config = config

        async def gen():
            for update in self._updates:
                yield update
            if self._error:
                raise self._error

        return gen()


async def _collect(graph, message="hola", thread_id="t-1"):
    return [event async for event in stream_chat(graph, message, thread_id)]


async def test_plain_answer_emits_start_message_done():
    graph = FakeGraph([
        {"chatbot": {"messages": [AIMessage(content="hola, ¿en qué te ayudo?")],
                     "project_id": "p1"}},
    ])

    events = await _collect(graph)

    assert [e.event for e in events] == ["start", "message", "done"]
    assert events[0].data == {"thread_id": "t-1"}
    assert events[1].data == {"content": "hola, ¿en qué te ayudo?"}
    assert events[2].data == {"thread_id": "t-1", "project_id": "p1"}


async def test_passes_thread_id_to_graph_config():
    graph = FakeGraph([])

    await _collect(graph, message="quiero anuncios", thread_id="abc")

    assert graph.config == {"configurable": {"thread_id": "abc"}}
    assert graph.state["thread_id"] == "abc"
    assert graph.state["messages"] == [{"role": "user", "content": "quiero anuncios"}]


async def test_tool_call_and_result_are_emitted():
    ai = AIMessage(content="", tool_calls=[{
        "name": "image_builder_tool", "args": {"brief_dict": {"b": 1}}, "id": "call_1",
    }])
    payload = {"status": "success", "errors": [],
               "creatives": [{"variant_index": 0, "storage_url": "https://x/0.png"}]}
    graph = FakeGraph([
        {"chatbot": {"messages": [ai], "project_id": "p1"}},
        {"tools": {"messages": [ToolMessage(
            content=json.dumps(payload), name="image_builder_tool", tool_call_id="call_1",
        )]}},
    ])

    events = await _collect(graph)

    assert [e.event for e in events] == ["start", "tool_call", "tool_result", "done"]
    assert events[1].data["name"] == "image_builder_tool"
    assert events[1].data["args"] == {"brief_dict": {"b": 1}}
    assert events[2].data["status"] == "success"
    assert events[2].data["result"]["creatives"][0]["storage_url"] == "https://x/0.png"


async def test_failed_tool_is_a_tool_result_not_an_error_event():
    payload = {"status": "failed", "errors": ["storage upload failed"]}
    graph = FakeGraph([
        {"tools": {"messages": [ToolMessage(
            content=json.dumps(payload), name="image_builder_tool", tool_call_id="c1",
        )]}},
    ])

    events = await _collect(graph)

    assert [e.event for e in events] == ["start", "tool_result", "done"]
    assert events[1].data["status"] == "failed"
    assert events[1].data["result"]["errors"] == ["storage upload failed"]


async def test_non_json_tool_content_is_reported_as_failed():
    graph = FakeGraph([
        {"tools": {"messages": [ToolMessage(
            content="Error: headline must be ≤ 40 characters",
            name="image_builder_tool", tool_call_id="c1",
        )]}},
    ])

    events = await _collect(graph)

    assert events[1].event == "tool_result"
    assert events[1].data["status"] == "failed"
    assert events[1].data["result"] == {"error": "Error: headline must be ≤ 40 characters"}


async def test_graph_exception_emits_error_then_done():
    graph = FakeGraph(
        [{"chatbot": {"messages": [AIMessage(content="voy a empezar")], "project_id": "p1"}}],
        error=RuntimeError("llm unreachable"),
    )

    events = await _collect(graph)

    assert [e.event for e in events] == ["start", "message", "error", "done"]
    assert events[2].data == {"message": "llm unreachable"}
    assert events[3].data["project_id"] == "p1"


async def test_empty_assistant_content_emits_no_message_event():
    ai = AIMessage(content="   ", tool_calls=[{
        "name": "approve_images_tool", "args": {}, "id": "c1",
    }])
    graph = FakeGraph([{"chatbot": {"messages": [ai], "project_id": "p1"}}])

    events = await _collect(graph)

    assert [e.event for e in events] == ["start", "tool_call", "done"]
