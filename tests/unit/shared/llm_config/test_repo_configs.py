"""Un config/llm.*.json roto debe fallar en CI, no en el deploy."""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from src.shared.llm_config.domain.models import AppLLMConfig

_CONFIG_DIR = Path(__file__).resolve().parents[4] / "config"
_CONFIG_FILES = sorted(_CONFIG_DIR.glob("llm.*.json"))
_EXPECTED_TOOLS = {"campaign_builder", "landing_builder", "image_builder"}


def test_config_dir_is_not_empty():
    assert _CONFIG_FILES, f"No hay archivos llm.*.json en {_CONFIG_DIR}"


@pytest.mark.parametrize("path", _CONFIG_FILES, ids=lambda p: p.name)
def test_repo_config_is_valid(path: Path):
    config = AppLLMConfig.model_validate(json.loads(path.read_text()))

    assert set(config.tools.keys()) <= _EXPECTED_TOOLS, (
        f"{path.name}: claves de 'tools' inválidas: "
        f"{set(config.tools.keys()) - _EXPECTED_TOOLS}"
    )

    for tool in _EXPECTED_TOOLS:
        settings = config.for_tool(tool)
        assert settings.model, f"{path.name}: {tool} sin modelo"

    assert config.for_agent().provider == "ollama", (
        f"{path.name}: el orquestador se construye con ChatOllama, "
        f"así que 'agent' debe declarar provider 'ollama'"
    )
