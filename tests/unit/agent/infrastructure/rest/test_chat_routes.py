from __future__ import annotations
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from src.agent.infrastructure.rest.chat_routes import build_chat_router
from src.projects.domain.models import Project
from src.projects.infrastructure.persistence.firestore_repository import FirestoreProjectRepository
from src.main import create_app


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


def test_chat_streams_for_project_pending_after_firestore_write_failure(monkeypatch, tmp_path):
    monkeypatch.delenv("API_KEY", raising=False)
    with patch(
        "src.projects.infrastructure.persistence.firestore_repository.firebase_admin"
    ) as firebase, patch(
        "src.projects.infrastructure.persistence.firestore_repository.firestore"
    ) as firestore:
        firebase._apps = {"[DEFAULT]": True}
        db = MagicMock()
        firestore.client.return_value = db
        repo = FirestoreProjectRepository(outbox_root=str(tmp_path))
        repo._collection = db.collection.return_value
        repo._collection.where.side_effect = RuntimeError("firestore unavailable")
        repo._collection.document.return_value.get.return_value.exists = False
        project = repo.create_for_thread("t-1")

        response = TestClient(create_app(repo=repo, graph=FakeGraph())).post(
            "/chat",
            json={"project_id": project.project_id, "thread_id": "t-1", "message": "hola"},
        )

    assert response.status_code == 200
    assert 'event: start\ndata: {"thread_id": "t-1"}' in response.text
