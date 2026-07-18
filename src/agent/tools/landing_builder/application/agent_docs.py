from __future__ import annotations
import json
import os


def read_page_json_doc(project_dir: str) -> str:
    path = os.path.join(project_dir, ".agent", "PAGE_JSON.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_page_schema(project_dir: str) -> dict:
    path = os.path.join(project_dir, ".agent", "page.schema.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
