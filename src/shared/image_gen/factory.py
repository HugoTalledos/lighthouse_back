from __future__ import annotations

from .domain.ports import ImageGeneratorPort
from .infrastructure.ollama_generator import OllamaImageGenerator
from .infrastructure.openrouter_generator import OpenRouterImageGenerator
from src.shared.llm_config.domain.models import LLMSettings

_GENERATORS = {
    "openrouter": OpenRouterImageGenerator,
    "ollama": OllamaImageGenerator,
}


def build_image_generator(settings: LLMSettings) -> ImageGeneratorPort:
    """Los generadores usan solo `model`; ignoran temperature/max_tokens/top_p."""
    generator_class = _GENERATORS[settings.provider]
    return generator_class(model=settings.model)
