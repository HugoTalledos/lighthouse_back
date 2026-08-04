from __future__ import annotations
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from src.projects.domain.models import Project
from src.projects.infrastructure.firestore_repository import FirestoreProjectRepository


@pytest.fixture
def repo(tmp_path):
    with patch("src.projects.infrastructure.firestore_repository.firebase_admin") as fb, \
         patch("src.projects.infrastructure.firestore_repository.firestore") as fs:
        fb._apps = {"[DEFAULT]": True}
        mock_db = MagicMock()
        fs.client.return_value = mock_db
        instance = FirestoreProjectRepository(outbox_root=str(tmp_path))
        instance._db = mock_db
        instance._collection = mock_db.collection.return_value
        yield instance


def test_get_or_create_by_thread_returns_existing_project(repo):
    now = datetime.now(timezone.utc)
    existing_doc = MagicMock()
    existing_doc.to_dict.return_value = Project(
        project_id="p1", thread_ids=["t1"], created_at=now, updated_at=now,
    ).model_dump(mode="json")
    repo._collection.where.return_value.limit.return_value.stream.return_value = [existing_doc]

    project = repo.get_or_create_by_thread("t1")

    assert project.project_id == "p1"
    repo._collection.document.assert_not_called()


def test_get_or_create_by_thread_creates_new_project_when_none_exists(repo):
    repo._collection.where.return_value.limit.return_value.stream.return_value = []
    repo._db.transaction.return_value = MagicMock()

    with patch(
        "src.projects.infrastructure.firestore_repository.firestore.transactional",
        lambda fn: fn,
    ):
        project = repo.get_or_create_by_thread("t1")

    assert project.thread_ids == ["t1"]
    assert project.project_id


def test_get_or_create_by_thread_writes_native_datetimes_on_creation(repo):
    repo._collection.where.return_value.limit.return_value.stream.return_value = []
    mock_transaction = MagicMock()
    repo._db.transaction.return_value = mock_transaction

    with patch(
        "src.projects.infrastructure.firestore_repository.firestore.transactional",
        lambda fn: fn,
    ):
        project = repo.get_or_create_by_thread("t1")

    mock_transaction.set.assert_called_once()
    _, written_doc = mock_transaction.set.call_args[0]
    assert isinstance(written_doc["created_at"], datetime)
    assert isinstance(written_doc["updated_at"], datetime)
    assert written_doc["created_at"] == project.created_at
    assert written_doc["updated_at"] == project.updated_at


def test_get_or_create_by_thread_returns_existing_when_transaction_sees_concurrent_write(repo):
    now = datetime.now(timezone.utc)
    existing_project = Project(
        project_id="existing-p", thread_ids=["t1"], created_at=now, updated_at=now,
    )
    existing_doc = MagicMock()
    existing_doc.to_dict.return_value = existing_project.model_dump(mode="json")

    stream_mock = repo._collection.where.return_value.limit.return_value.stream
    # Outer (pre-transaction) read: nothing found yet.
    # Read inside the transaction: another caller already created the project.
    stream_mock.side_effect = [[], [existing_doc]]
    repo._db.transaction.return_value = MagicMock()

    with patch(
        "src.projects.infrastructure.firestore_repository.firestore.transactional",
        lambda fn: fn,
    ):
        project = repo.get_or_create_by_thread("t1")

    assert project.project_id == "existing-p"
    repo._db.transaction.return_value.set.assert_not_called()


def test_get_or_create_by_thread_dedupes_same_thread_during_outage(repo):
    repo._collection.where.side_effect = RuntimeError("firestore down")

    project1 = repo.get_or_create_by_thread("t1")
    project2 = repo.get_or_create_by_thread("t1")

    assert project1.project_id == project2.project_id
    pending = repo._outbox.pending(project1.project_id)
    assert len(pending) == 1


def test_get_or_create_by_thread_falls_back_to_outbox_on_failure(repo):
    repo._collection.where.side_effect = RuntimeError("firestore down")

    project = repo.get_or_create_by_thread("t1")

    assert project.thread_ids == ["t1"]
    pending = repo._outbox.pending(project.project_id)
    assert len(pending) == 1
    assert pending[0][1]["op"] == "create_project"


def test_upsert_summary_flushes_outbox_first_then_writes(repo):
    repo._outbox.enqueue("p1", "update_resource", {
        "resource": "landing", "payload": {"a": 1}, "status": "approved",
    })

    repo.upsert_summary("p1", "Acme", "Saves time")

    assert repo._collection.document.return_value.update.call_count == 2
    assert repo._outbox.pending("p1") == []


def test_upsert_summary_falls_back_to_outbox_on_write_failure(repo):
    repo._collection.document.return_value.update.side_effect = RuntimeError("down")

    repo.upsert_summary("p1", "Acme", "Saves time")

    pending = repo._outbox.pending("p1")
    assert len(pending) == 1
    assert pending[0][1]["op"] == "upsert_summary"
    assert pending[0][1]["args"] == {"business_name": "Acme", "value_proposition": "Saves time"}


def test_update_resource_writes_status_and_payload(repo):
    repo.update_resource("p1", "campaign", {"config": {"name": "c1"}}, "approved")

    repo._collection.document.assert_called_with("p1")
    call_kwargs = repo._collection.document.return_value.update.call_args[0][0]
    assert call_kwargs["resources.campaign.status"] == "approved"
    assert call_kwargs["resources.campaign.payload"] == {"config": {"name": "c1"}}


def test_update_resource_falls_back_to_outbox_on_write_failure(repo):
    repo._collection.document.return_value.update.side_effect = RuntimeError("down")

    repo.update_resource("p1", "images", {"creatives": []}, "approved")

    pending = repo._outbox.pending("p1")
    assert len(pending) == 1
    assert pending[0][1]["op"] == "update_resource"
    assert pending[0][1]["args"]["resource"] == "images"
