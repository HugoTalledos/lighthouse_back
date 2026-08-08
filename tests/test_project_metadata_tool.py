from unittest.mock import MagicMock, patch

import pytest


async def test_metadata_tool_persists_summary_for_the_project():
    with patch(
        "src.agent.tools.project_metadata_tool.get_project_repository"
    ) as factory:
        repo = MagicMock()
        factory.return_value = repo

        from src.agent.tools.project_metadata_tool import update_project_metadata_tool

        result = await update_project_metadata_tool.ainvoke(
            {
                "business_name": "Acme",
                "value_proposition": "Ahorra tiempo",
                "state": {"project_id": "p-1"},
            }
        )

    assert result == {"status": "success", "project_id": "p-1"}
    repo.upsert_summary.assert_called_once_with("p-1", "Acme", "Ahorra tiempo")


@pytest.mark.parametrize(
    ("business_name", "value_proposition"),
    [("   ", "Ahorra tiempo"), ("Acme", "\t")],
)
async def test_metadata_tool_rejects_blank_persisted_fields(
    business_name, value_proposition
):
    with patch(
        "src.agent.tools.project_metadata_tool.get_project_repository"
    ) as factory:
        from src.agent.tools.project_metadata_tool import update_project_metadata_tool

        with pytest.raises(ValueError, match="must not be blank"):
            await update_project_metadata_tool.ainvoke(
                {
                    "business_name": business_name,
                    "value_proposition": value_proposition,
                    "state": {"project_id": "p-1"},
                }
            )

    factory.return_value.upsert_summary.assert_not_called()
