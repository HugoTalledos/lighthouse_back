from __future__ import annotations
from unittest.mock import MagicMock, patch


def _campaign_config():
    return {
        "name": "Acme Launch", "objective": "OUTCOME_TRAFFIC", "status": "PAUSED",
        "special_ad_categories": [], "ad_sets": [],
    }


async def test_approve_campaign_tool_marks_resource_approved():
    with patch(
        "src.agent.tools.campaign_builder.approve_campaign_tool.FirestoreProjectRepository"
    ) as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        from src.agent.tools.campaign_builder.approve_campaign_tool import approve_campaign_tool
        result = await approve_campaign_tool.ainvoke({
            "campaign_config": _campaign_config(),
            "state": {"project_id": "proj-1"},
        })

    assert result["status"] == "approved"
    assert result["project_id"] == "proj-1"
    mock_repo.update_resource.assert_called_once_with(
        "proj-1", "campaign", {"config": _campaign_config()}, "approved",
    )


async def test_approve_campaign_tool_rejects_empty_config():
    from src.agent.tools.campaign_builder.approve_campaign_tool import approve_campaign_tool
    result = await approve_campaign_tool.ainvoke({
        "campaign_config": {},
        "state": {"project_id": "proj-1"},
    })

    assert result["status"] == "failed"
    assert result["errors"]


async def test_approve_campaign_tool_reports_repository_failure():
    with patch(
        "src.agent.tools.campaign_builder.approve_campaign_tool.FirestoreProjectRepository"
    ) as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo.update_resource.side_effect = RuntimeError("firestore down")
        mock_repo_cls.return_value = mock_repo

        from src.agent.tools.campaign_builder.approve_campaign_tool import approve_campaign_tool
        result = await approve_campaign_tool.ainvoke({
            "campaign_config": _campaign_config(),
            "state": {"project_id": "proj-1"},
        })

    assert result["status"] == "failed"
    assert "firestore down" in result["errors"][0]
