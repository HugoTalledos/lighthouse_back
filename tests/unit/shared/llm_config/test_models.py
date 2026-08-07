from __future__ import annotations
import pytest
from pydantic import ValidationError

from src.shared.llm_config.domain.models import AppLLMConfig, LLMSettings


def _config() -> AppLLMConfig:
    return AppLLMConfig.model_validate(
        {
            "defaults": {"provider": "ollama", "model": "qwen2.5-coder:7b", "temperature": 0.5},
            "agent": {"model": "llama3.1", "max_tokens": 1000},
            "tools": {
                "campaign_builder": {"provider": "openrouter", "model": "openai/gpt-4o"},
                "landing_builder": {"temperature": 0.9},
            },
        }
    )


def test_tool_overrides_are_merged_field_by_field_over_defaults():
    settings = _config().for_tool("campaign_builder")
    assert settings == LLMSettings(
        provider="openrouter", model="openai/gpt-4o", temperature=0.5
    )


def test_tool_inherits_fields_it_does_not_declare():
    settings = _config().for_tool("landing_builder")
    assert settings.provider == "ollama"
    assert settings.model == "qwen2.5-coder:7b"
    assert settings.temperature == 0.9


def test_missing_tool_falls_back_to_defaults():
    settings = _config().for_tool("image_builder")
    assert settings == LLMSettings(
        provider="ollama", model="qwen2.5-coder:7b", temperature=0.5
    )


def test_agent_settings_are_merged_over_defaults():
    settings = _config().for_agent()
    assert settings.provider == "ollama"
    assert settings.model == "llama3.1"
    assert settings.temperature == 0.5
    assert settings.max_tokens == 1000


def test_invalid_provider_is_rejected():
    with pytest.raises(ValidationError):
        AppLLMConfig.model_validate(
            {
                "defaults": {"provider": "gemini", "model": "x", "temperature": 0.5},
                "agent": {},
                "tools": {},
            }
        )


def test_invalid_provider_in_a_tool_override_is_rejected():
    config = AppLLMConfig.model_validate(
        {
            "defaults": {"provider": "ollama", "model": "x", "temperature": 0.5},
            "agent": {},
            "tools": {"campaign_builder": {"provider": "midjourney"}},
        }
    )
    with pytest.raises(ValidationError):
        config.for_tool("campaign_builder")


def test_defaults_must_declare_provider_model_and_temperature():
    with pytest.raises(ValidationError):
        AppLLMConfig.model_validate(
            {"defaults": {"provider": "ollama"}, "agent": {}, "tools": {}}
        )


def test_unknown_field_in_an_override_is_rejected():
    config = AppLLMConfig.model_validate(
        {
            "defaults": {"provider": "ollama", "model": "x", "temperature": 0.5},
            "agent": {},
            "tools": {"campaign_builder": {"modell": "typo"}},
        }
    )
    with pytest.raises(ValidationError):
        config.for_tool("campaign_builder")
