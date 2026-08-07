"""Cubre el guard de arranque en src/agent/config.py: el modelo orquestador
solo soporta ChatOllama, así que un `agent.provider` distinto de "ollama"
debe reventar el import con un mensaje accionable.
"""
from __future__ import annotations
import importlib

import pytest

import src.agent.config as config_module
from src.shared.llm_config.domain.models import AppLLMConfig


def _config_with_agent(**agent_overrides):
    return AppLLMConfig.model_validate(
        {
            "defaults": {"provider": "ollama", "model": "llama3.1", "temperature": 0.5},
            "agent": agent_overrides,
            "tools": {},
        }
    )


@pytest.fixture
def reload_config_module(monkeypatch):
    """Recarga src.agent.config con un load_llm_config parcheado y siempre
    deja el módulo en su estado real (config/llm.dev.json) al terminar, para
    no contaminar al resto de la suite (p. ej. tests/unit/agent/test_graph.py,
    que importa el grafo construido sobre este módulo)."""

    def _reload_with(fake_config):
        monkeypatch.setattr(
            "src.shared.llm_config.loader.load_llm_config", lambda: fake_config
        )
        return importlib.reload(config_module)

    yield _reload_with

    # El fixture `monkeypatch` es dependencia nuestra, así que su teardown
    # corre DESPUÉS del nuestro — hay que deshacer el parche explícitamente
    # antes de recargar, o el módulo quedaría releído con la config falsa.
    monkeypatch.undo()
    importlib.reload(config_module)


def test_guard_raises_when_agent_provider_is_not_ollama(reload_config_module):
    fake_config = _config_with_agent(provider="openrouter", model="openai/gpt-4o")

    with pytest.raises(ValueError, match="openrouter"):
        reload_config_module(fake_config)


def test_guard_passes_and_model_uses_resolved_agent_settings(reload_config_module):
    fake_config = _config_with_agent(
        provider="ollama", model="qwen2.5-coder:7b", temperature=0.2,
        max_tokens=500, top_p=0.8,
    )

    reloaded = reload_config_module(fake_config)
    bound_model = reloaded.model.bound

    assert bound_model.model == "qwen2.5-coder:7b"
    assert bound_model.temperature == 0.2
    assert bound_model.top_p == 0.8
