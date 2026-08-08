from datetime import datetime, timezone

from src.projects.domain.models import Project, ResourceState
from src.projects.domain.status import derive_project_status


def test_new_project_starts_in_progress():
    project = Project(
        project_id="p-1", thread_ids=["t-1"],
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )

    assert project.status == "in_progress"


def test_generated_pending_resource_puts_project_in_review():
    resources = {
        "landing": ResourceState(status="pending", payload={"preview_url": "https://preview"}),
        "campaign": ResourceState(),
        "images": ResourceState(),
    }

    assert derive_project_status(resources) == "review"


def test_all_required_resources_approved_puts_project_in_approved():
    resources = {
        kind: ResourceState(status="approved", payload={"ready": True})
        for kind in ("landing", "campaign", "images")
    }

    assert derive_project_status(resources) == "approved"
