from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from src.main import create_app
from src.projects.domain.models import Project


class FakeGraph:
    pass


class InMemoryProjectRepository:
    def __init__(self):
        self.projects = {}

    def create_for_thread(self, thread_id):
        existing = next(
            (project for project in self.projects.values() if thread_id in project.thread_ids),
            None,
        )
        if existing:
            return existing
        now = datetime.now(timezone.utc)
        project = Project(
            project_id=f"project-{len(self.projects) + 1}",
            thread_ids=[thread_id],
            created_at=now,
            updated_at=now,
        )
        self.projects[project.project_id] = project
        return project

    def get(self, project_id):
        return self.projects.get(project_id)

    def list(self):
        return list(self.projects.values())


def test_create_project_generates_project_id_and_starts_in_progress():
    repo = InMemoryProjectRepository()
    client = TestClient(create_app(repo=repo, graph=FakeGraph()))

    response = client.post("/projects", json={"thread_id": "thread-1"})

    assert response.status_code == 201
    body = response.json()
    assert body["project_id"]
    assert body["thread_ids"] == ["thread-1"]
    assert body["business_name"] is None
    assert body["value_proposition"] is None
    assert body["status"] == "in_progress"


def test_create_project_is_idempotent_for_an_existing_thread():
    repo = InMemoryProjectRepository()
    client = TestClient(create_app(repo=repo, graph=FakeGraph()))

    first = client.post("/projects", json={"thread_id": "thread-1"}).json()
    second = client.post("/projects", json={"thread_id": "thread-1"}).json()

    assert second["project_id"] == first["project_id"]
    assert len(repo.projects) == 1


def test_create_project_rejects_a_blank_thread_id():
    client = TestClient(create_app(repo=InMemoryProjectRepository(), graph=FakeGraph()))

    response = client.post("/projects", json={"thread_id": "   "})

    assert response.status_code == 422


def test_create_project_rejects_a_thread_id_over_the_existing_limit():
    client = TestClient(create_app(repo=InMemoryProjectRepository(), graph=FakeGraph()))

    response = client.post("/projects", json={"thread_id": "a" * 201})

    assert response.status_code == 422
