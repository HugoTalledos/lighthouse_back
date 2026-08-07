from __future__ import annotations
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from src.agent.infrastructure.rest.chat_routes import build_chat_router


class FakeGraph:
    def __init__(self):
        self.config = None

    def astream(self, state, config=None, stream_mode=None):
        self.config = config

        async def gen():
            yield {"chatbot": {"messages": [AIMessage(content="hola")], "project_id": "p1"}}

        return gen()


def _client(graph):
    app = FastAPI()
    app.include_router(build_chat_router(graph))
    return TestClient(app)


def test_chat_streams_sse_events():
    client = _client(FakeGraph())

    response = client.post("/chat", json={"message": "hola", "thread_id": "t-1"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert 'event: start\ndata: {"thread_id": "t-1"}' in body
    assert 'event: message\ndata: {"content": "hola"}' in body
    assert '"project_id": "p1"' in body
    assert body.strip().endswith("}")


def test_chat_uses_client_thread_id():
    graph = FakeGraph()

    _client(graph).post("/chat", json={"message": "hola", "thread_id": "mine"})

    assert graph.config == {"configurable": {"thread_id": "mine"}}


def test_chat_generates_thread_id_when_missing():
    graph = FakeGraph()

    response = _client(graph).post("/chat", json={"message": "hola"})

    generated = graph.config["configurable"]["thread_id"]
    assert len(generated) == 36  # uuid4
    assert f'"thread_id": "{generated}"' in response.text


def test_chat_rejects_empty_message():
    response = _client(FakeGraph()).post("/chat", json={"message": "  "})

    assert response.status_code == 422
