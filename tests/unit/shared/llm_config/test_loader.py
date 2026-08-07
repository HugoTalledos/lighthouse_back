from __future__ import annotations
import json
import pytest

from src.shared.llm_config import loader
from src.shared.llm_config.loader import load_llm_config

_VALID = {
    "defaults": {"provider": "ollama", "model": "qwen2.5-coder:7b", "temperature": 0.5},
    "agent": {"max_tokens": 1000},
    "tools": {"campaign_builder": {"provider": "openrouter", "model": "openai/gpt-4o"}},
}


@pytest.fixture(autouse=True)
def _clear_cache():
    load_llm_config.cache_clear()
    yield
    load_llm_config.cache_clear()


def _write(tmp_path, name: str, payload) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    path = config_dir / name
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload))


def test_loads_the_file_matching_app_env(tmp_path, monkeypatch):
    _write(tmp_path, "llm.prod.json", _VALID)
    monkeypatch.setattr(loader, "_PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("APP_ENV", "prod")

    config = load_llm_config()

    assert config.for_tool("campaign_builder").model == "openai/gpt-4o"


def test_defaults_to_dev_when_app_env_is_unset(tmp_path, monkeypatch):
    _write(tmp_path, "llm.dev.json", _VALID)
    monkeypatch.setattr(loader, "_PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("APP_ENV", raising=False)

    assert load_llm_config().defaults.model == "qwen2.5-coder:7b"


def test_result_is_cached_across_calls(tmp_path, monkeypatch):
    _write(tmp_path, "llm.dev.json", _VALID)
    monkeypatch.setattr(loader, "_PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("APP_ENV", raising=False)

    assert load_llm_config() is load_llm_config()


def test_missing_file_raises_with_path_and_app_env(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "_PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(FileNotFoundError, match="llm.staging.json"):
        load_llm_config()


def test_malformed_json_raises_value_error(tmp_path, monkeypatch):
    _write(tmp_path, "llm.dev.json", "{not json")
    monkeypatch.setattr(loader, "_PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("APP_ENV", raising=False)

    with pytest.raises(ValueError, match="not valid JSON"):
        load_llm_config()


def test_invalid_schema_raises_value_error_with_path_and_app_env(tmp_path, monkeypatch):
    _write(tmp_path, "llm.staging.json", {
        "defaults": {"provider": "ollama", "model": "x"},  # missing temperature
        "agent": {},
        "tools": {},
    })
    monkeypatch.setattr(loader, "_PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(ValueError, match=r"llm\.staging\.json.*invalid LLM config.*APP_ENV='staging'"):
        load_llm_config()
