from __future__ import annotations
import os

from .domain.ports import LLMClientPort
from .infrastructure.ollama_local_client import OllamaLocalClient
from .infrastructure.openrouter_client import OpenRouterClient

_CLIENTS = {
    "openrouter": OpenRouterClient,
    "ollama": OllamaLocalClient,
}


def build_llm_client() -> LLMClientPort:
    provider = os.getenv("LLM_PROVIDER", "openrouter")
    client_class = _CLIENTS.get(provider)
    if client_class is None:
        valid = ", ".join(_CLIENTS)
        raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}. Valid values: {valid}")
    return client_class()
