"""Remove credential-shaped strings before anything is written to disk.

The memo, the JSON state and the pull-request summary all end up in files, and those files are
often attached to a build or a pull request. A model id or an error message can carry a key by
accident (``sk-…`` in an API response, for instance), so every artefact passes through
:func:`redact_secrets` on the way out.

This is a narrow, shape-based filter on purpose: it removes things that look like credentials and
changes nothing else, so the memo stays readable.
"""

from __future__ import annotations

import re
from typing import Any

#: Credential shapes the project can encounter: OpenAI, Anthropic, LangSmith, Tavily, LlamaParse,
#: GitHub. Long enough that a normal word cannot match.
_SECRET_RE = re.compile(
    r"\b(?:sk-ant-[A-Za-z0-9_-]{16,}"
    r"|sk-[A-Za-z0-9_-]{16,}"
    r"|lsv2_[A-Za-z0-9_-]{16,}"
    r"|tvly-[A-Za-z0-9_-]{16,}"
    r"|llx-[A-Za-z0-9_-]{16,}"
    r"|ghp_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,})\b"
)

PLACEHOLDER = "[REDACTED]"


def redact_secrets(text: str) -> str:
    """Replace credential-shaped substrings with ``[REDACTED]``."""

    return _SECRET_RE.sub(PLACEHOLDER, text or "")


def redact_state(state: dict[str, Any]) -> dict[str, Any]:
    """Deep-copy the state with every string redacted (keys are kept as they are)."""

    if not isinstance(state, dict):  # pragma: no cover - defensive
        return state
    cleaned: dict[str, Any] = {}
    for key, value in state.items():
        cleaned[key] = _redact_value(value)
    return cleaned


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, dict):
        return {key: _redact_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_value(item) for item in value]
    return value


__all__ = ["PLACEHOLDER", "redact_secrets", "redact_state"]
