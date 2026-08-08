from __future__ import annotations

from src.agent.application.chat_service import stream_chat


class CapturingGraph:
    def __init__(self):
        self.state = None

    def astream(self, state, config=None, stream_mode=None):
        self.state = state

        async def gen():
            return
            yield

        return gen()


async def test_stream_chat_passes_project_and_thread_to_graph_state():
    graph = CapturingGraph()

    _ = [event async for event in stream_chat(graph, "hola", "p-1", "t-1")]

    assert graph.state == {
        "messages": [{"role": "user", "content": "hola"}],
        "thread_id": "t-1",
        "project_id": "p-1",
    }
