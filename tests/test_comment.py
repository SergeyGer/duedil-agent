"""Tests for the short Markdown summary used in pull-request comments."""

from __future__ import annotations

from app.comment import (
    MAX_FLAGS,
    build_comment,
    extract_recommendation,
    recommendation_of,
)

MEMO = """# Investment Memo — NimbusAI

## 1. Executive Summary
NimbusAI claims to be a market leader.

## 6. Final Recommendation
**REJECT**
"""

STATE = {
    "extracted_metrics": {"company_name": "NimbusAI", "arr": "$1.2M", "team_size": "14"},
    "financial_benchmarks": {
        "arr_per_employee": 85714.0,
        "benchmark_arr_per_employee": 100_000,
        "status": "below",
        "verdict": "Weak: ARR/employee of $85,714 sits below the B2B SaaS benchmark of $100,000.",
    },
    "red_flags": ["Team-size mismatch", "Missing founding year", "Inflated TAM", "No funding data"],
    "critic_loops_count": 2,
    "used_model": "gpt-4o (OpenAI)",
    "final_memo": MEMO,
}


def test_extract_recommendation_reads_the_bold_verdict():
    assert extract_recommendation("## 6. Final Recommendation\n**DEEP AUDIT**") == "DEEP AUDIT"
    assert extract_recommendation("... **INVEST** ...") == "INVEST"
    assert extract_recommendation("**REJECT**") == "REJECT"


def test_extract_recommendation_does_not_match_investment():
    """`INVEST` must not fire inside `Investment` — the word boundary is the contract."""

    assert extract_recommendation("# Investment Memo — Acme") == "UNKNOWN"


def test_extract_recommendation_is_case_insensitive():
    assert extract_recommendation("**invest**") == "INVEST"


def test_recommendation_falls_back_to_the_deterministic_rules():
    """A model that forgets the verdict must not leave the comment saying UNKNOWN."""

    state = {**STATE, "final_memo": "no verdict here", "red_flags": ["a", "b", "c"]}
    assert recommendation_of(state) == "REJECT"


def test_build_comment_contains_the_essentials():
    text = build_comment(STATE)

    assert "### Due diligence — NimbusAI" in text
    assert "**REJECT**" in text
    assert "$1.2M" in text
    assert "14" in text
    assert "$85,714" in text
    assert "below the benchmark" in text
    assert "gpt-4o (OpenAI)" in text
    assert "the full memo is attached" in text


def test_build_comment_truncates_flags_but_says_how_many_remain():
    text = build_comment(STATE)

    assert f"1. {STATE['red_flags'][0]}" in text
    assert STATE["red_flags"][MAX_FLAGS] not in text
    assert f"_{len(STATE['red_flags']) - MAX_FLAGS} more in the full memo._" in text


def test_build_comment_keeps_the_table_intact():
    """Regression: an empty row once split the table and broke the rendering in GitHub."""

    lines = build_comment(STATE).splitlines()
    start = lines.index("| Metric | Value |")
    table = []
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        table.append(line)

    assert table[1] == "|---|---|"
    assert all(line.count("|") >= 3 for line in table)
    assert not any(line.strip() == "" for line in table)


def test_build_comment_handles_missing_financials():
    state = {
        **STATE,
        "financial_benchmarks": {"status": "unknown", "verdict": ""},
        "extracted_metrics": {"company_name": "Acme"},
    }
    text = build_comment(state)

    assert "— (not computable)" in text
    assert "not in the deck" in text  # the ARR/team cells report the missing values


def test_build_comment_handles_no_flags():
    text = build_comment({**STATE, "red_flags": []})
    assert "**No Red Flags were raised.**" in text


def test_build_comment_marks_offline_runs():
    text = build_comment({**STATE, "used_model": "offline rules, deck_aware (no model)"})
    assert "offline rules, deck_aware (no model)" in text


def test_build_comment_escapes_pipes_in_values():
    state = {**STATE, "extracted_metrics": {"company_name": "A | B"}}
    assert "A \\| B" in build_comment(state)
