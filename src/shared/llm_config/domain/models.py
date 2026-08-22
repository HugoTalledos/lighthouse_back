from __future__ import annotations
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Provider = Literal["openrouter", "ollama"]


class LLMSettings(BaseModel):
    """Configuración ya resuelta de un consumidor de LLM."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: Provider
    model: str
    temperature: float
    max_tokens: int | None = None
    top_p: float | None = None
    timeout: float = 60.0


class AppLLMConfig(BaseModel):
    """Contenido de config/llm.{APP_ENV}.json.

    `agent` y las entradas de `tools` son overrides parciales: se mergean
    campo por campo sobre `defaults` al resolverse. Se guardan como dicts
    crudos y solo se validan como LLMSettings tras el merge, que es cuando
    se sabe que están completos.
    """

    model_config = ConfigDict(extra="forbid")

    defaults: LLMSettings
    agent: dict = Field(default_factory=dict)
    tools: dict[str, dict] = Field(default_factory=dict)

    def _merge(self, override: dict) -> LLMSettings:
        return LLMSettings.model_validate({**self.defaults.model_dump(), **override})

    def for_tool(self, name: str) -> LLMSettings:
        return self._merge(self.tools.get(name, {}))

    def for_agent(self) -> LLMSettings:
        return self._merge(self.agent)
