from __future__ import annotations
from unittest.mock import MagicMock, patch


def _creatives():
    return [
        {"variant_index": 0, "storage_url": "https://x/0.png", "headline": "Save time", "cta_text": "Try free"},
        {"variant_index": 1, "storage_url": "https://x/1.png", "headline": "Save time", "cta_text": "Try free"},
    ]


async def test_approve_images_tool_marks_selected_variants_approved():
    with patch(
        "src.agent.tools.image_builder.approve_images_tool.get_project_repository"
    ) as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        from src.agent.tools.image_builder.approve_images_tool import approve_images_tool
        result = await approve_images_tool.ainvoke({
            "variant_indices": [0],
            "creatives": _creatives(),
            "state": {"project_id": "proj-1"},
        })

    assert result["status"] == "approved"
    mock_repo.update_resource.assert_called_once_with(
        "proj-1", "images",
        {"creatives": [
            {"variant_index": 0, "storage_url": "https://x/0.png", "headline": "Save time", "cta_text": "Try free"},
        ]},
        "approved",
    )


async def test_approve_images_tool_rejects_no_matching_variants():
    from src.agent.tools.image_builder.approve_images_tool import approve_images_tool
    result = await approve_images_tool.ainvoke({
        "variant_indices": [9],
        "creatives": _creatives(),
        "state": {"project_id": "proj-1"},
    })

    assert result["status"] == "failed"
    assert result["errors"]


async def test_approve_images_tool_reports_repository_failure():
    with patch(
        "src.agent.tools.image_builder.approve_images_tool.get_project_repository"
    ) as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo.update_resource.side_effect = RuntimeError("firestore down")
        mock_repo_cls.return_value = mock_repo

        from src.agent.tools.image_builder.approve_images_tool import approve_images_tool
        result = await approve_images_tool.ainvoke({
            "variant_indices": [0],
            "creatives": _creatives(),
            "state": {"project_id": "proj-1"},
        })

    assert result["status"] == "failed"
    assert "firestore down" in result["errors"][0]
