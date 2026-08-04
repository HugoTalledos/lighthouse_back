from __future__ import annotations
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage
from src.projects.domain.models import Project


def _fake_project(thread_id: str) -> Project:
    now = datetime.now(timezone.utc)
    return Project(project_id="resolved-project-id", thread_ids=[thread_id], created_at=now, updated_at=now)


def test_chatbot_resolves_project_id_when_missing():
    with patch("src.agent.graph.get_project_repository") as mock_get_repo, \
         patch("src.agent.graph.model") as mock_model:
        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo
        mock_repo.get_or_create_by_thread.return_value = _fake_project("t1")
        mock_model.invoke.return_value = AIMessage(content="hi")

        from src.agent.graph import build_graph
        graph = build_graph()
        result = graph.invoke(
            {"messages": [{"role": "user", "content": "hello"}], "thread_id": "t1"},
            config={"configurable": {"thread_id": "t1"}},
        )

    mock_repo.get_or_create_by_thread.assert_called_once_with("t1")
    assert result["project_id"] == "resolved-project-id"


def test_chatbot_skips_lookup_when_project_id_already_present():
    with patch("src.agent.graph.get_project_repository") as mock_get_repo, \
         patch("src.agent.graph.model") as mock_model:
        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo
        mock_model.invoke.return_value = AIMessage(content="hi again")

        from src.agent.graph import build_graph
        graph = build_graph()
        result = graph.invoke(
            {
                "messages": [{"role": "user", "content": "hello again"}],
                "thread_id": "t1",
                "project_id": "already-known",
            },
            config={"configurable": {"thread_id": "t1"}},
        )

    mock_repo.get_or_create_by_thread.assert_not_called()
    assert result["project_id"] == "already-known"
