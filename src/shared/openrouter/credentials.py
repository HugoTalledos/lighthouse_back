from __future__ import annotations
import os


def require_api_key() -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set")
    return api_key


class OpenRouterCredentials:
    """Snapshot of the OpenRouter environment, read once at construction.

    Both the LLM client and the image generator build one of these in their
    __init__, which keeps the missing-key failure eager (callers rely on
    construction raising) and avoids re-reading os.environ on every request.
    """

    def __init__(self) -> None:
        self._api_key = require_api_key()
        self._referer = os.getenv("OPENROUTER_HTTP_REFERER")
        self._title = os.getenv("OPENROUTER_X_TITLE")

    @property
    def api_key(self) -> str:
        return self._api_key

    def headers(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._referer:
            headers["HTTP-Referer"] = self._referer
        if self._title:
            headers["X-Title"] = self._title
        return headers
