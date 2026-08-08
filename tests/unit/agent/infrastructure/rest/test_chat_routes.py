from __future__ import annotations
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from src.agent.infrastructure.rest.chat_routes import build_chat_router
from src.projects.domain.models import Project


class FakeGraph:
    def __init__(self):
        self.config = None

    def astream(self, state, config=None, stream_mode=None):
        self.config = config

        async def gen():
            yield {"chatbot": {"messages": [AIMessage(content="hola")], "project_id": "p1"}}

        return gen()


class FakeRepository:
    def get(self, project_id):
        now = datetime.now(timezone.utc)
        return Project(
            project_id=project_id,
            thread_ids=["t-1", "mine"],
            created_at=now,
            updated_at=now,
        )


def _client(graph):
    app = FastAPI()
    app.include_router(build_chat_router(graph, FakeRepository()))
    return TestClient(app)


def test_chat_streams_sse_events():
    client = _client(FakeGraph())

    response = client.post(
        "/chat", json={"message": "hola", "project_id": "p1", "thread_id": "t-1"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert 'event: start\ndata: {"thread_id": "t-1"}' in body
    assert 'event: message\ndata: {"content": "hola"}' in body
    assert '"project_id": "p1"' in body
    assert body.strip().endswith("}")


def test_chat_uses_client_thread_id():
    graph = FakeGraph()

    _client(graph).post(
        "/chat", json={"message": "hola", "project_id": "p1", "thread_id": "mine"}
    )

    assert graph.config == {"configurable": {"thread_id": "mine"}}


def test_chat_requires_thread_id():
    graph = FakeGraph()

    response = _client(graph).post("/chat", json={"message": "hola", "project_id": "p1"})

    assert response.status_code == 422


def test_chat_rejects_empty_message():
    response = _client(FakeGraph()).post(
        "/chat", json={"message": "  ", "project_id": "p1", "thread_id": "t-1"}
    )

    assert response.status_code == 422


def test_chat_rejects_message_over_max_length():
    response = _client(FakeGraph()).post(
        "/chat", json={"message": "a" * 8001, "project_id": "p1", "thread_id": "t-1"}
    )

    assert response.status_code == 422


def test_chat_rejects_thread_id_over_max_length():
    response = _client(FakeGraph()).post(
        "/chat", json={"message": "hola", "project_id": "p1", "thread_id": "a" * 201}
    )

    assert response.status_code == 422
