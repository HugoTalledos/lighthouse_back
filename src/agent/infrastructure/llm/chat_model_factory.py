from __future__ import annotations

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from src.shared.llm_config.domain.models import LLMSettings
from src.shared.openrouter.credentials import OpenRouterCredentials

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _build_ollama(settings: LLMSettings) -> BaseChatModel:
    # ChatOllama ignora `max_tokens`: el parámetro equivalente es `num_predict`.
    return ChatOllama(
        model=settings.model,
        temperature=settings.temperature,
        num_predict=settings.max_tokens,
        top_p=settings.top_p,
    )


def _build_openrouter(settings: LLMSettings) -> BaseChatModel:
    # OpenRouter habla el protocolo de OpenAI, así que basta con apuntar el
    # cliente de OpenAI a su base_url. Construir las credenciales aquí mantiene
    # el fallo eager: config.py se importa al arranque, así que levantar el
    # server con provider remoto y sin OPENROUTER_API_KEY revienta enseguida.
    credentials = OpenRouterCredentials()
    return init_chat_model(
        settings.model,
        model_provider="openai",
        base_url=_OPENROUTER_BASE_URL,
        api_key=credentials.api_key,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        top_p=settings.top_p,
    )


_BUILDERS = {
    "ollama": _build_ollama,
    "openrouter": _build_openrouter,
}


def build_chat_model(settings: LLMSettings) -> BaseChatModel:
    """Construye el chat model del orquestador según `settings.provider`.

    Devuelve un BaseChatModel (no un LLMClientPort) porque el agente le llama
    `.bind_tools()` y lo consume el ToolNode del grafo.
    """
    try:
        builder = _BUILDERS[settings.provider]
    except KeyError:
        raise ValueError(
            f"El modelo orquestador no soporta provider {settings.provider!r}. "
            f"Válidos: {sorted(_BUILDERS)}"
        ) from None
    return builder(settings)
