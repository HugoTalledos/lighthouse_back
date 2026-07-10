from __future__ import annotations
import os
from ..domain.models import PageComposition


def render(composition: PageComposition, project_dir: str) -> None:
    path = os.path.join(project_dir, "src", "data", "page.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(composition.model_dump_json())
