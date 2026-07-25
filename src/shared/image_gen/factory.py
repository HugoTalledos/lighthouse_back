from __future__ import annotations
import os

from .domain.ports import ImageGeneratorPort
from .infrastructure.ollama_generator import OllamaImageGenerator
from .infrastructure.openrouter_generator import OpenRouterImageGenerator

_GENERATORS = {
    "openrouter": OpenRouterImageGenerator,
    "ollama": OllamaImageGenerator,
}


def build_image_generator() -> ImageGeneratorPort:
    provider = os.getenv("IMAGE_PROVIDER", "openrouter")
    generator_class = _GENERATORS.get(provider)
    if generator_class is None:
        valid = ", ".join(_GENERATORS)
        raise ValueError(f"Unknown IMAGE_PROVIDER: {provider!r}. Valid values: {valid}")
    return generator_class()
