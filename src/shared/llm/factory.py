from __future__ import annotations
import os

from .domain.ports import LLMClientPort
from .infrastructure.openai_client import OpenAIClient
from .infrastructure.anthropic_client import AnthropicClient

_CLIENTS = {
    "openai": OpenAIClient,
    "anthropic": AnthropicClient,
}


def build_llm_client() -> LLMClientPort:
    provider = os.getenv("LLM_PROVIDER", "openai")
    client_class = _CLIENTS.get(provider)
    if client_class is None:
        valid = ", ".join(_CLIENTS)
        raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}. Valid values: {valid}")
    return client_class()
