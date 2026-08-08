from unittest.mock import MagicMock

from src.projects.domain.models import ResourceState
from src.projects.infrastructure.persistence.firestore_repository import (
    FirestoreProjectRepository,
)


def _repository_with_resources(resources):
    repository = FirestoreProjectRepository.__new__(FirestoreProjectRepository)
    repository._collection = MagicMock()
    repository._outbox = MagicMock()
    repository._pending_by_thread = {}
    repository._outbox.pending.return_value = []

    document = repository._collection.document.return_value
    snapshot = document.get.return_value
    snapshot.to_dict.return_value = {
        "resources": {
            kind: state.model_dump(mode="json") for kind, state in resources.items()
        }
    }
    return repository, document


def test_pending_resource_update_puts_project_in_review():
    resources = {
        "landing": ResourceState(),
        "campaign": ResourceState(),
        "images": ResourceState(),
    }
    repository, document = _repository_with_resources(resources)

    repository.update_resource(
        "p-1", "campaign", {"config": {"name": "Acme launch"}}, "pending"
    )

    written = document.update.call_args.args[0]
    assert written["resources.campaign.status"] == "pending"
    assert written["resources.campaign.payload"] == {
        "config": {"name": "Acme launch"}
    }
    assert written["status"] == "review"


def test_approving_all_three_resources_puts_project_in_approved():
    resources = {
        "landing": ResourceState(status="approved", payload={"version": "v1"}),
        "campaign": ResourceState(),
        "images": ResourceState(status="approved", payload={"creatives": [{}]}),
    }
    repository, document = _repository_with_resources(resources)

    repository.update_resource(
        "p-1", "campaign", {"config": {"name": "Acme launch"}}, "approved"
    )

    written = document.update.call_args.args[0]
    assert written["resources.campaign.status"] == "approved"
    assert written["status"] == "approved"
