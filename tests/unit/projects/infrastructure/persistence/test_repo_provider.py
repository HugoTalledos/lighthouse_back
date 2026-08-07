from __future__ import annotations
from unittest.mock import patch
from src.projects.infrastructure.persistence.repo_provider import _LazyProjectRepository


def test_get_returns_none_when_construction_raises():
    provider = _LazyProjectRepository()
    with patch(
        "src.projects.infrastructure.persistence.repo_provider.FirestoreProjectRepository",
        side_effect=RuntimeError("no credentials"),
    ):
        assert provider._get() is None


def test_get_or_create_by_thread_falls_back_to_ephemeral_project_when_construction_fails():
    provider = _LazyProjectRepository()
    with patch(
        "src.projects.infrastructure.persistence.repo_provider.FirestoreProjectRepository",
        side_effect=RuntimeError("no credentials"),
    ):
        project = provider.get_or_create_by_thread("t1")

    assert project.thread_ids == ["t1"]
    assert project.project_id


def test_upsert_summary_is_noop_when_construction_fails():
    provider = _LazyProjectRepository()
    with patch(
        "src.projects.infrastructure.persistence.repo_provider.FirestoreProjectRepository",
        side_effect=RuntimeError("no credentials"),
    ):
        provider.upsert_summary("p1", "Acme", "Saves time")  # must not raise


def test_update_resource_is_noop_when_construction_fails():
    provider = _LazyProjectRepository()
    with patch(
        "src.projects.infrastructure.persistence.repo_provider.FirestoreProjectRepository",
        side_effect=RuntimeError("no credentials"),
    ):
        provider.update_resource("p1", "campaign", {"config": {}}, "approved")  # must not raise
