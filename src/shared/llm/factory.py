from __future__ import annotations

from .domain.ports import LLMClientPort
from .infrastructure.ollama_local_client import OllamaLocalClient
from .infrastructure.openrouter_client import OpenRouterClient
from src.shared.llm_config.domain.models import LLMSettings

_CLIENTS = {
    "openrouter": OpenRouterClient,
    "ollama": OllamaLocalClient,
}


def build_llm_client(settings: LLMSettings) -> LLMClientPort:
    client_class = _CLIENTS[settings.provider]
    return client_class(model=settings.model, temperature=settings.temperature)
