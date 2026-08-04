from __future__ import annotations
from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from src.projects.domain.models import Project, ResourceState
from src.projects.api.app import create_app


def _project(project_id="p1"):
    now = datetime.now(timezone.utc)
    return Project(
        project_id=project_id, thread_ids=["t1"], business_name="Acme",
        value_proposition="Saves time", created_at=now, updated_at=now,
        resources={
            "landing": ResourceState(status="approved", payload={"storage_path": "landings/p1/v1/source.tar.gz"}),
            "campaign": ResourceState(),
            "images": ResourceState(),
        },
    )


def _client_with_repo(repo: MagicMock) -> TestClient:
    app = create_app(repo)
    return TestClient(app)


def test_list_projects_returns_summaries():
    repo = MagicMock()
    repo.list.return_value = [_project("p1"), _project("p2")]
    client = _client_with_repo(repo)

    response = client.get("/projects")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["project_id"] == "p1"
    assert body[0]["resources"]["landing"]["status"] == "approved"


def test_get_project_returns_detail():
    repo = MagicMock()
    repo.get.return_value = _project("p1")
    client = _client_with_repo(repo)

    response = client.get("/projects/p1")

    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == "p1"
    assert body["resources"]["landing"]["payload"]["storage_path"] == "landings/p1/v1/source.tar.gz"


def test_get_project_returns_404_when_missing():
    repo = MagicMock()
    repo.get.return_value = None
    client = _client_with_repo(repo)

    response = client.get("/projects/does-not-exist")

    assert response.status_code == 404
