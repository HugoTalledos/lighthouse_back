from __future__ import annotations
import pytest

from src.shared.image_gen.factory import build_image_generator
from src.shared.image_gen.infrastructure.openrouter_generator import OpenRouterImageGenerator
from src.shared.image_gen.infrastructure.ollama_generator import OllamaImageGenerator


def test_default_provider_returns_openrouter_generator(monkeypatch):
    monkeypatch.delenv("IMAGE_PROVIDER", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    generator = build_image_generator()
    assert isinstance(generator, OpenRouterImageGenerator)


def test_openrouter_provider_returns_openrouter_generator(monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    generator = build_image_generator()
    assert isinstance(generator, OpenRouterImageGenerator)


def test_ollama_provider_returns_ollama_generator(monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "ollama")
    generator = build_image_generator()
    assert isinstance(generator, OllamaImageGenerator)


def test_unknown_provider_raises_value_error(monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDER", "midjourney")
    with pytest.raises(ValueError, match="Unknown IMAGE_PROVIDER"):
        build_image_generator()


@pytest.mark.parametrize("provider", ["dalle3", "vertex"])
def test_removed_providers_are_no_longer_valid(monkeypatch, provider):
    monkeypatch.setenv("IMAGE_PROVIDER", provider)
    with pytest.raises(ValueError, match="Unknown IMAGE_PROVIDER"):
        build_image_generator()
