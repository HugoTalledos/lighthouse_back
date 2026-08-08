from __future__ import annotations
from unittest.mock import patch
from langchain_core.messages import AIMessage
from src.agent.graph import build_graph


def test_chatbot_uses_required_project_id_from_state():
    with patch("src.agent.graph.model") as mock_model:
        mock_model.invoke.return_value = AIMessage(content="hi again")

        graph = build_graph()
        result = graph.invoke(
            {
                "messages": [{"role": "user", "content": "hello again"}],
                "thread_id": "t1",
                "project_id": "already-known",
            },
            config={"configurable": {"thread_id": "t1"}},
        )

    assert result["project_id"] == "already-known"
