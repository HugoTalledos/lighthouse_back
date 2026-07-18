from __future__ import annotations
import json
import pytest
from src.agent.tools.landing_builder.application.agent_docs import (
    read_page_json_doc, read_page_schema,
)


def test_read_page_json_doc_returns_file_contents(tmp_path):
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()
    (agent_dir / "PAGE_JSON.md").write_text("# page.json reference\nSome docs.")
    assert read_page_json_doc(str(tmp_path)) == "# page.json reference\nSome docs."


def test_read_page_json_doc_raises_when_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_page_json_doc(str(tmp_path))


def test_read_page_schema_returns_parsed_json(tmp_path):
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()
    schema = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
    (agent_dir / "page.schema.json").write_text(json.dumps(schema))
    assert read_page_schema(str(tmp_path)) == schema


def test_read_page_schema_raises_when_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_page_schema(str(tmp_path))
