"""Cada consumidor pide su propia entrada del JSON, no una compartida."""
from __future__ import annotations
import pytest

from src.shared.llm.infrastructure.ollama_local_client import OllamaLocalClient
from src.shared.llm.infrastructure.openrouter_client import OpenRouterClient
from src.shared.llm_config.domain.models import AppLLMConfig

_CONFIG = AppLLMConfig.model_validate(
    {
        "defaults": {"provider": "ollama", "model": "llama3.1", "temperature": 0.5},
        "agent": {},
        "tools": {
            "campaign_builder": {"provider": "openrouter", "model": "openai/gpt-4o"},
            "landing_builder": {"model": "mistral", "temperature": 0.9},
        },
    }
)


def test_campaign_builder_builds_its_own_client(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setattr(
        "src.agent.tools.campaign_builder.campaign_builder_tool.load_llm_config",
        lambda: _CONFIG,
    )
    from src.agent.tools.campaign_builder import campaign_builder_tool as module

    client = module.build_llm_client(module.load_llm_config().for_tool("campaign_builder"))

    assert isinstance(client, OpenRouterClient)
    assert client._model == "openai/gpt-4o"


def test_landing_builder_gets_a_different_model_than_campaign_builder():
    campaign = _CONFIG.for_tool("campaign_builder")
    landing = _CONFIG.for_tool("landing_builder")

    assert campaign.model != landing.model
    assert campaign.provider != landing.provider
    assert landing.temperature == 0.9


def test_a_tool_without_overrides_uses_defaults():
    settings = _CONFIG.for_tool("image_builder")

    assert (settings.provider, settings.model) == ("ollama", "llama3.1")


def test_ollama_client_built_from_landing_settings_carries_its_temperature():
    settings = _CONFIG.for_tool("landing_builder")

    client = OllamaLocalClient(model=settings.model, temperature=settings.temperature)

    assert client._temperature == 0.9
