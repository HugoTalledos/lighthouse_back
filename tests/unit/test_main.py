from __future__ import annotations
from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from src.main import create_app
from src.projects.domain.models import Project


class FakeGraph:
    def astream(self, state, config=None, stream_mode=None):
        async def gen():
            yield {"chatbot": {"messages": [AIMessage(content="hola")], "project_id": "p1"}}

        return gen()


class InMemoryProjectRepository:
    def __init__(self, projects: list[Project] | None = None):
        self.projects = {project.project_id: project for project in projects or []}

    @classmethod
    def with_project(cls, project_id: str, thread_ids: list[str]):
        now = datetime.now(timezone.utc)
        return cls([
            Project(
                project_id=project_id,
                thread_ids=thread_ids,
                created_at=now,
                updated_at=now,
            )
        ])

    def get(self, project_id: str):
        return self.projects.get(project_id)

    def list(self):
        return list(self.projects.values())


def _client(monkeypatch, api_key=None) -> TestClient:
    if api_key is None:
        monkeypatch.delenv("API_KEY", raising=False)
    else:
        monkeypatch.setenv("API_KEY", api_key)
    repo = InMemoryProjectRepository.with_project("p1", ["t-1"])
    return TestClient(create_app(repo=repo, graph=FakeGraph()))


def test_open_when_api_key_env_is_unset(monkeypatch):
    assert _client(monkeypatch).get("/projects").status_code == 200


def test_rejects_missing_api_key(monkeypatch):
    assert _client(monkeypatch, api_key="s3cret").get("/projects").status_code == 401


def test_rejects_wrong_api_key(monkeypatch):
    client = _client(monkeypatch, api_key="s3cret")
    assert client.get("/projects", headers={"x-api-key": "nope"}).status_code == 401


def test_accepts_correct_api_key(monkeypatch):
    client = _client(monkeypatch, api_key="s3cret")
    assert client.get("/projects", headers={"x-api-key": "s3cret"}).status_code == 200


def test_chat_route_is_mounted_and_protected(monkeypatch):
    client = _client(monkeypatch, api_key="s3cret")
    payload = {"project_id": "p1", "thread_id": "t-1", "message": "hola"}

    assert client.post("/chat", json=payload).status_code == 401

    response = client.post(
        "/chat", json=payload, headers={"x-api-key": "s3cret"}
    )
    assert response.status_code == 200
    assert "event: start" in response.text


def test_chat_requires_project_id(monkeypatch):
    client = _client(monkeypatch)

    response = client.post("/chat", json={"thread_id": "t-1", "message": "hola"})

    assert response.status_code == 422


def test_chat_rejects_unknown_project(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    client = TestClient(create_app(repo=InMemoryProjectRepository(), graph=FakeGraph()))

    response = client.post("/chat", json={
        "project_id": "p-1", "thread_id": "t-1", "message": "hola",
    })

    assert response.status_code == 404


def test_chat_rejects_thread_not_belonging_to_project(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    repo = InMemoryProjectRepository.with_project("p-1", ["other-thread"])
    client = TestClient(create_app(repo=repo, graph=FakeGraph()))

    response = client.post("/chat", json={
        "project_id": "p-1", "thread_id": "t-1", "message": "hola",
    })

    assert response.status_code == 409


def test_cors_headers_are_exposed(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com")
    repo = MagicMock()
    repo.list.return_value = []
    client = TestClient(create_app(repo=repo, graph=FakeGraph()))

    response = client.get("/projects", headers={"Origin": "https://app.example.com"})

    assert response.headers["access-control-allow-origin"] == "https://app.example.com"
