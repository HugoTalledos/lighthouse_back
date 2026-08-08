from .models import ProjectStatus, ResourceKind, ResourceState


REQUIRED_RESOURCES = ("landing", "campaign", "images")


def derive_project_status(resources: dict[ResourceKind, ResourceState]) -> ProjectStatus:
    if all(resources[kind].status == "approved" for kind in REQUIRED_RESOURCES):
        return "approved"
    if any(state.payload and state.status == "pending" for state in resources.values()):
        return "review"
    return "in_progress"
