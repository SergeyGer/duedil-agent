"""Runtime configuration and the LLM factory.

The LLM is created lazily so the module can be imported (and the graph built)
without any API keys present. This keeps unit tests and the "structure" steps
runnable offline.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gpt-4o"


def get_model_name() -> str:
    """Return the configured model id (``gpt-4o`` by default)."""

    return os.getenv("DUE_DIL_MODEL", DEFAULT_MODEL)


def model_label(model: str | None = None) -> str:
    """Return a human-readable label for the model, owner included.

    Every artefact has to state which model produced the analysis — "which model ran
    this?" is the first question anyone asks about an LLM result, and a bare id
    (``claude-3-5-sonnet``) does not say whose endpoint answered.
    """

    name = model or get_model_name()
    lowered = name.lower()
    if lowered.startswith("claude"):
        return f"{name} (Anthropic)"
    if lowered.startswith(("gpt", "o1", "o3", "o4", "chatgpt")):
        return f"{name} (OpenAI)"
    return name


@lru_cache(maxsize=4)
def _cached_llm(model: str, temperature: float):
    if model.lower().startswith("claude"):
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, temperature=temperature, timeout=120, max_retries=2)

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=model, temperature=temperature, timeout=120, max_retries=2)


def get_llm(temperature: float = 0.0, model: str | None = None):
    """Build (or fetch a cached) chat model instance.

    ``gpt-*`` ids go through ``langchain-openai``; ``claude-*`` ids go through
    ``langchain-anthropic``.
    """

    name = model or get_model_name()
    return _cached_llm(name, float(temperature))


__all__ = ["get_llm", "get_model_name", "model_label", "DEFAULT_MODEL"]
