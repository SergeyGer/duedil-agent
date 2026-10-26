"""Credentials must never be written into an artefact by accident."""

from __future__ import annotations

import pytest

from app.redact import PLACEHOLDER, redact_secrets, redact_state


@pytest.mark.parametrize(
    "secret",
    [
        "sk-abcdefghijklmnopqrstuvwxyz012345",
        "sk-ant-api03-abcdefghijklmnopqrstuvwxyz",
        "lsv2_pt_abcdefghijklmnopqrstuvwxyz",
        "tvly-abcdefghijklmnopqrstuvwxyz",
        "llx-abcdefghijklmnopqrstuvwxyz",
        "ghp_abcdefghijklmnopqrstuvwxyz012345",
        "github_pat_abcdefghijklmnopqrstuvwxyz",
    ],
)
def test_credential_shapes_are_redacted(secret: str):
    text = f"the provider said: {secret} is invalid"
    assert secret not in redact_secrets(text)
    assert PLACEHOLDER in redact_secrets(text)


def test_normal_text_is_untouched():
    text = "ARR of $1.2M, 14 employees, gpt-4o (OpenAI), model id claude-3-5-sonnet"
    assert redact_secrets(text) == text


def test_redact_state_walks_nested_structures():
    state = {
        "final_memo": "error: sk-abcdefghijklmnopqrstuvwxyz012345",
        "extracted_metrics": {"founders": ["sk-ant-api03-abcdefghijklmnopqrstuvwxyz"]},
        "count": 3,
        "progress_log": ["ok", "token lsv2_pt_abcdefghijklmnopqrstuvwxyz"],
    }
    cleaned = redact_state(state)

    assert "sk-" not in cleaned["final_memo"]
    assert "sk-ant" not in cleaned["extracted_metrics"]["founders"][0]
    assert "lsv2_" not in cleaned["progress_log"][1]
    assert cleaned["count"] == 3
    # The original state is untouched, so callers keep the real values in memory.
    assert "sk-" in state["final_memo"]


def test_short_lookalikes_are_not_redacted():
    """A short `sk-` prefix is not a credential and must not mangle ordinary text."""

    assert redact_secrets("sk-learn and sk-123") == "sk-learn and sk-123"
