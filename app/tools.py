"""External search tool wiring (Tavily)."""

from __future__ import annotations

import os
from typing import Any

DEFAULT_MAX_RESULTS = 5


def get_search_tool(max_results: int = DEFAULT_MAX_RESULTS) -> Any | None:
    """Return a configured Tavily search tool, or ``None`` if unavailable.

    Returns ``None`` (instead of raising) when ``TAVILY_API_KEY`` is not set or
    the ``langchain-community`` Tavily integration cannot be imported, so the
    graph degrades gracefully and stays testable offline.
    """

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return None

    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
    except Exception:  # pragma: no cover - depends on optional install
        return None

    try:
        return TavilySearchResults(max_results=max_results, tavily_api_key=api_key)
    except Exception:  # pragma: no cover - defensive
        return None


def stringify_search_results(results: Any) -> str:
    """Convert raw Tavily results into a compact, LLM-friendly text block."""

    if results is None:
        return ""
    if isinstance(results, str):
        return results
    if isinstance(results, dict):
        results = [results]
    if isinstance(results, list):
        lines: list[str] = []
        for item in results:
            if isinstance(item, dict):
                title = item.get("title") or ""
                url = item.get("url") or ""
                content = item.get("content") or item.get("snippet") or ""
                lines.append(f"- {title} ({url}): {content}".strip())
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)
    return str(results)


__all__ = ["get_search_tool", "stringify_search_results", "DEFAULT_MAX_RESULTS"]
