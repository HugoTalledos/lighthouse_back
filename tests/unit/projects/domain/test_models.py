from __future__ import annotations
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from src.projects.domain.models import Project, ResourceState


def _now():
    return datetime.now(timezone.utc)


def test_project_defaults_all_resources_pending():
    project = Project(
        project_id="p1", thread_ids=["t1"], created_at=_now(), updated_at=_now(),
    )
    assert set(project.resources.keys()) == {"landing", "campaign", "images"}
    for state in project.resources.values():
        assert state.status == "pending"
        assert state.payload == {}


def test_project_rejects_unknown_resource_kind():
    with pytest.raises(ValidationError):
        Project(
            project_id="p1", thread_ids=["t1"], created_at=_now(), updated_at=_now(),
            resources={"unknown": ResourceState()},
        )


def test_project_round_trips_through_json():
    project = Project(
        project_id="p1", thread_ids=["t1"], business_name="Acme",
        created_at=_now(), updated_at=_now(),
    )
    dumped = project.model_dump(mode="json")
    restored = Project.model_validate(dumped)
    assert restored.project_id == "p1"
    assert restored.business_name == "Acme"
