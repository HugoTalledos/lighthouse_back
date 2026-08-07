from __future__ import annotations
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from src.main import create_app


class FakeGraph:
    def astream(self, state, config=None, stream_mode=None):
        async def gen():
            yield {"chatbot": {"messages": [AIMessage(content="hola")], "project_id": "p1"}}

        return gen()


def _client(monkeypatch, api_key=None) -> TestClient:
    if api_key is None:
        monkeypatch.delenv("API_KEY", raising=False)
    else:
        monkeypatch.setenv("API_KEY", api_key)
    repo = MagicMock()
    repo.list.return_value = []
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

    assert client.post("/chat", json={"message": "hola"}).status_code == 401

    response = client.post(
        "/chat", json={"message": "hola"}, headers={"x-api-key": "s3cret"}
    )
    assert response.status_code == 200
    assert "event: start" in response.text


def test_cors_headers_are_exposed(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com")
    repo = MagicMock()
    repo.list.return_value = []
    client = TestClient(create_app(repo=repo, graph=FakeGraph()))

    response = client.get("/projects", headers={"Origin": "https://app.example.com"})

    assert response.headers["access-control-allow-origin"] == "https://app.example.com"
