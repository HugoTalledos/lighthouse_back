from __future__ import annotations
import json
import os


def render(composition: dict, project_dir: str) -> None:
    path = os.path.join(project_dir, "src", "data", "page.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(composition, f)
