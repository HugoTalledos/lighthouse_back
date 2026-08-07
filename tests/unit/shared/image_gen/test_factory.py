from __future__ import annotations
import pytest

from src.shared.image_gen.factory import build_image_generator
from src.shared.image_gen.infrastructure.openrouter_generator import OpenRouterImageGenerator
from src.shared.image_gen.infrastructure.ollama_generator import OllamaImageGenerator
from src.shared.llm_config.domain.models import LLMSettings


def test_openrouter_settings_return_openrouter_generator(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    settings = LLMSettings(
        provider="openrouter",
        model="google/gemini-2.5-flash-image-preview",
        temperature=0.5,
    )

    generator = build_image_generator(settings)

    assert isinstance(generator, OpenRouterImageGenerator)
    assert generator._model == "google/gemini-2.5-flash-image-preview"


def test_ollama_settings_return_ollama_generator():
    settings = LLMSettings(provider="ollama", model="x/flux2-klein:4b", temperature=0.5)

    generator = build_image_generator(settings)

    assert isinstance(generator, OllamaImageGenerator)
    assert generator._model == "x/flux2-klein:4b"


def test_image_generator_is_independent_of_the_text_llm_provider(monkeypatch):
    """El eje de imagen se configura por su cuenta: nada de LLM_PROVIDER."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    text = LLMSettings(provider="ollama", model="llama3.1", temperature=0.5)
    image = LLMSettings(provider="openrouter", model="google/gemini-2.5-flash-image-preview", temperature=0.5)

    assert isinstance(build_image_generator(image), OpenRouterImageGenerator)
    assert text.provider == "ollama"
