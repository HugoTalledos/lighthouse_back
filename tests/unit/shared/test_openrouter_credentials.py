from __future__ import annotations
import pytest

from src.shared.openrouter.credentials import OpenRouterCredentials, require_api_key


def _clear_optional(monkeypatch):
    monkeypatch.delenv("OPENROUTER_HTTP_REFERER", raising=False)
    monkeypatch.delenv("OPENROUTER_X_TITLE", raising=False)


def test_require_api_key_returns_the_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    assert require_api_key() == "sk-test"


def test_require_api_key_raises_when_missing(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY environment variable is not set"):
        require_api_key()


def test_credentials_raise_at_construction_when_key_missing(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY environment variable is not set"):
        OpenRouterCredentials()


def test_headers_contain_auth_and_content_type(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    _clear_optional(monkeypatch)

    headers = OpenRouterCredentials().headers()

    assert headers == {
        "Authorization": "Bearer sk-test",
        "Content-Type": "application/json",
    }


def test_headers_include_optional_attribution_headers(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("OPENROUTER_HTTP_REFERER", "https://lighthouse.test")
    monkeypatch.setenv("OPENROUTER_X_TITLE", "Lighthouse")

    headers = OpenRouterCredentials().headers()

    assert headers["HTTP-Referer"] == "https://lighthouse.test"
    assert headers["X-Title"] == "Lighthouse"


def test_env_is_read_once_at_construction(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("OPENROUTER_X_TITLE", "Lighthouse")

    credentials = OpenRouterCredentials()

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-changed")
    monkeypatch.delenv("OPENROUTER_X_TITLE", raising=False)

    headers = credentials.headers()
    assert headers["Authorization"] == "Bearer sk-test"
    assert headers["X-Title"] == "Lighthouse"
    assert credentials.api_key == "sk-test"
