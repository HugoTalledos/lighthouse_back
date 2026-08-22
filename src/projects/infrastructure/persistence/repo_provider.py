from __future__ import annotations
from .firestore_repository import FirestoreProjectRepository
from ...domain.ports import ProjectRepositoryPort


class _LazyProjectRepository:
    def __init__(self) -> None:
        self._instance: ProjectRepositoryPort | None = None
        self._ephemeral_by_thread = {}

    def _get(self) -> ProjectRepositoryPort | None:
        if self._instance is None:
            try:
                self._instance = FirestoreProjectRepository()
            except Exception:
                return None
        return self._instance

    def create_for_thread(self, thread_id: str):
        repo = self._get()
        if thread_id in self._ephemeral_by_thread:
            return self._ephemeral_by_thread[thread_id]
        if repo is None:
            from datetime import datetime, timezone
            import uuid
            from ...domain.models import Project
            now = datetime.now(timezone.utc)
            project = Project(
                project_id=str(uuid.uuid4()), thread_ids=[thread_id],
                created_at=now, updated_at=now,
            )
            self._ephemeral_by_thread[thread_id] = project
            return project
        return repo.create_for_thread(thread_id)

    def get_or_create_by_thread(self, thread_id: str):
        return self.create_for_thread(thread_id)

    def get(self, project_id: str):
        ephemeral = next(
            (
                project
                for project in self._ephemeral_by_thread.values()
                if project.project_id == project_id
            ),
            None,
        )
        if ephemeral is not None:
            return ephemeral
        repo = self._get()
        return None if repo is None else repo.get(project_id)

    def list(self):
        repo = self._get()
        persisted = repo.list() if repo is not None else []
        persisted_ids = {project.project_id for project in persisted}
        ephemeral = [
            project
            for project in self._ephemeral_by_thread.values()
            if project.project_id not in persisted_ids
        ]
        return persisted + ephemeral

    def upsert_summary(self, project_id: str, business_name: str, value_proposition: str) -> None:
        repo = self._get()
        if repo is None:
            return
        try:
            repo.upsert_summary(project_id, business_name, value_proposition)
        except Exception:
            pass

    def update_resource(self, project_id: str, resource, payload: dict, status: str = "approved") -> None:
        repo = self._get()
        if repo is None:
            return
        try:
            repo.update_resource(project_id, resource, payload, status)
        except Exception:
            pass


_project_repository = _LazyProjectRepository()


def get_project_repository() -> _LazyProjectRepository:
    return _project_repository
