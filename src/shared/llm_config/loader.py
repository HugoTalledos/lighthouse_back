from __future__ import annotations
import json
import os
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from .domain.models import AppLLMConfig

# src/shared/llm_config/loader.py -> raíz del repo
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_DIR_NAME = "config"


@lru_cache(maxsize=1)
def load_llm_config() -> AppLLMConfig:
    """Lee y valida config/llm.{APP_ENV}.json. El resultado se cachea.

    Se invoca al arranque desde el composition root para que un archivo
    inválido falle al levantar el proceso y no a mitad de un turno de /chat.
    """
    app_env = os.getenv("APP_ENV", "dev")
    path = _PROJECT_ROOT / _CONFIG_DIR_NAME / f"llm.{app_env}.json"

    if not path.exists():
        raise FileNotFoundError(
            f"LLM config not found at {path} (APP_ENV={app_env!r}). "
            f"Create it or set APP_ENV to an environment that has one."
        )

    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"{path} is not valid JSON: {e}") from e

    try:
        return AppLLMConfig.model_validate(payload)
    except ValidationError as e:
        raise ValueError(
            f"{path} has invalid LLM config (APP_ENV={app_env!r}): {e}"
        ) from e
