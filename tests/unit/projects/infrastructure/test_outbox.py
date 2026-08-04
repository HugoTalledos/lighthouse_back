from __future__ import annotations
from src.projects.infrastructure.outbox import LocalOutbox


def test_enqueue_then_pending_returns_entry(tmp_path):
    outbox = LocalOutbox(root=str(tmp_path))
    outbox.enqueue("proj-1", "upsert_summary", {"business_name": "Acme"})

    pending = outbox.pending("proj-1")

    assert len(pending) == 1
    path, entry = pending[0]
    assert entry["op"] == "upsert_summary"
    assert entry["args"] == {"business_name": "Acme"}


def test_pending_empty_for_unknown_project(tmp_path):
    outbox = LocalOutbox(root=str(tmp_path))
    assert outbox.pending("nope") == []


def test_pending_is_ordered_oldest_first(tmp_path):
    outbox = LocalOutbox(root=str(tmp_path))
    outbox.enqueue("proj-1", "op_a", {"n": 1})
    outbox.enqueue("proj-1", "op_b", {"n": 2})

    pending = outbox.pending("proj-1")

    assert [entry["op"] for _, entry in pending] == ["op_a", "op_b"]


def test_discard_removes_entry(tmp_path):
    outbox = LocalOutbox(root=str(tmp_path))
    outbox.enqueue("proj-1", "op_a", {"n": 1})
    path, _ = outbox.pending("proj-1")[0]

    outbox.discard(path)

    assert outbox.pending("proj-1") == []
