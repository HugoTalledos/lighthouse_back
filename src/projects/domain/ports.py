from __future__ import annotations
from abc import ABC, abstractmethod
from .models import Project, ResourceKind, ApprovalStatus


class ProjectRepositoryPort(ABC):
    @abstractmethod
    def get_or_create_by_thread(self, thread_id: str) -> Project:
        ...

    @abstractmethod
    def get(self, project_id: str) -> Project | None:
        ...

    @abstractmethod
    def list(self) -> list[Project]:
        ...

    @abstractmethod
    def upsert_summary(
        self, project_id: str, business_name: str, value_proposition: str
    ) -> None:
        ...

    @abstractmethod
    def update_resource(
        self,
        project_id: str,
        resource: ResourceKind,
        payload: dict,
        status: ApprovalStatus = "approved",
    ) -> None:
        ...
