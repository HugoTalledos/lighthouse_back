from __future__ import annotations
import uuid
from datetime import datetime, timezone
from pathlib import Path

import firebase_admin
from firebase_admin import firestore

from ...domain.models import Project, ResourceKind, ApprovalStatus
from ...domain.ports import ProjectRepositoryPort
from .outbox import LocalOutbox


class FirestoreProjectRepository(ProjectRepositoryPort):
    def __init__(self, outbox: LocalOutbox | None = None, outbox_root: str = ".projects_outbox") -> None:
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        self._db = firestore.client()
        self._collection = self._db.collection("projects")
        self._outbox = outbox or LocalOutbox(root=outbox_root)
        self._pending_by_thread: dict[str, Project] = {}

    def create_for_thread(self, thread_id: str) -> Project:
        if thread_id in self._pending_by_thread:
            return self._pending_by_thread[thread_id]

        try:
            existing = list(
                self._collection.where("thread_ids", "array_contains", thread_id)
                .limit(1)
                .stream()
            )
            if existing:
                return Project.model_validate(existing[0].to_dict())

            project_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            new_project = Project(
                project_id=project_id, thread_ids=[thread_id], created_at=now, updated_at=now,
            )

            @firestore.transactional
            def _get_or_create(transaction) -> Project:
                # Re-check for a concurrent write inside the transaction: another
                # caller may have created a project for this thread between our
                # outer read above and this transaction starting.
                existing_in_txn = list(
                    self._collection.where("thread_ids", "array_contains", thread_id)
                    .limit(1)
                    .stream(transaction=transaction)
                )
                if existing_in_txn:
                    return Project.model_validate(existing_in_txn[0].to_dict())

                doc_ref = self._collection.document(project_id)
                # Use native datetime objects for created_at/updated_at here (unlike
                # the outbox-fallback path below, which needs ISO strings because
                # LocalOutbox serializes with plain json.dumps) so Firestore stores
                # this field as a Timestamp consistently with _write_summary/
                # _write_resource, which also write native datetimes.
                doc = new_project.model_dump(mode="json")
                doc["created_at"] = new_project.created_at
                doc["updated_at"] = new_project.updated_at
                transaction.set(doc_ref, doc)
                return new_project

            return _get_or_create(self._db.transaction())
        except Exception:
            if thread_id in self._pending_by_thread:
                return self._pending_by_thread[thread_id]
            project_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            project = Project(
                project_id=project_id, thread_ids=[thread_id], created_at=now, updated_at=now,
            )
            self._outbox.enqueue(project_id, "create_project", project.model_dump(mode="json"))
            self._pending_by_thread[thread_id] = project
            return project

    def get_or_create_by_thread(self, thread_id: str) -> Project:
        return self.create_for_thread(thread_id)

    def get(self, project_id: str) -> Project | None:
        doc = self._collection.document(project_id).get()
        if not doc.exists:
            return None
        return Project.model_validate(doc.to_dict())

    def list(self) -> list[Project]:
        return [Project.model_validate(doc.to_dict()) for doc in self._collection.stream()]

    def upsert_summary(
        self, project_id: str, business_name: str, value_proposition: str
    ) -> None:
        self._flush_outbox(project_id)
        args = {"business_name": business_name, "value_proposition": value_proposition}
        try:
            self._write_summary(project_id, args)
        except Exception:
            self._outbox.enqueue(project_id, "upsert_summary", args)

    def update_resource(
        self,
        project_id: str,
        resource: ResourceKind,
        payload: dict,
        status: ApprovalStatus = "approved",
    ) -> None:
        self._flush_outbox(project_id)
        args = {"resource": resource, "payload": payload, "status": status}
        try:
            self._write_resource(project_id, args)
        except Exception:
            self._outbox.enqueue(project_id, "update_resource", args)

    def _write_summary(self, project_id: str, args: dict) -> None:
        self._collection.document(project_id).update({
            "business_name": args["business_name"],
            "value_proposition": args["value_proposition"],
            "updated_at": datetime.now(timezone.utc),
        })

    def _write_resource(self, project_id: str, args: dict) -> None:
        resource = args["resource"]
        self._collection.document(project_id).update({
            f"resources.{resource}.status": args["status"],
            f"resources.{resource}.payload": args["payload"],
            "updated_at": datetime.now(timezone.utc),
        })

    def _flush_outbox(self, project_id: str) -> None:
        for path, entry in self._outbox.pending(project_id):
            try:
                op = entry["op"]
                if op == "create_project":
                    self._collection.document(entry["args"]["project_id"]).set(entry["args"])
                elif op == "upsert_summary":
                    self._write_summary(project_id, entry["args"])
                elif op == "update_resource":
                    self._write_resource(project_id, entry["args"])
                self._outbox.discard(path)
            except Exception:
                break
