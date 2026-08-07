from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any


class LocalOutbox:
    def __init__(self, root: str = ".projects_outbox") -> None:
        self._root = Path(root)

    def enqueue(self, project_id: str, op: str, args: dict[str, Any]) -> None:
        project_dir = self._root / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{time.time_ns()}-{op}.json"
        (project_dir / filename).write_text(json.dumps({"op": op, "args": args}))

    def pending(self, project_id: str) -> list[tuple[Path, dict[str, Any]]]:
        project_dir = self._root / project_id
        if not project_dir.exists():
            return []
        entries = []
        for path in sorted(project_dir.iterdir()):
            if path.suffix == ".json":
                entries.append((path, json.loads(path.read_text())))
        return entries

    def discard(self, path: Path) -> None:
        path.unlink(missing_ok=True)
