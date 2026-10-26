"""Human-readable rendering of the pipeline's results for the Streamlit UI.

The raw state is a machine artefact: ``extracted_metrics`` holds strings exactly as
they appeared in the deck (``"$1.2M"``, ``"14"``, ``"[NOT_FOUND]"``) and
``financial_benchmarks`` holds floats with long tails (``85714.28571428571``). Printing
them as JSON is accurate but unreadable, and it hides the interesting part: which
figures the analysis actually produced.

This module turns that state into tables and a highlighted verdict. It is pure — it
takes dicts and returns lists of rows — so it can be unit-tested without Streamlit,
and the UI stays a thin layer over it.
"""

from __future__ import annotations

import re
from typing import Any

# Order the metric table so the numbers a reader looks for first come first. Anything
# the extractor found beyond this list is appended afterwards, so nothing is lost.
_METRIC_ORDER = [
    ("company_name", "Company"),
    ("sector", "Sector"),
    ("business_model", "Business model"),
    ("founded_year", "Founded"),
    ("arr", "ARR"),
    ("mrr", "MRR"),
    ("team_size", "Team size"),
    ("tam", "TAM"),
    ("claimed_leadership", "Claimed leadership"),
    ("founders", "Founders"),
    ("website", "Website"),
]

_METRIC_LABELS = dict(_METRIC_ORDER)

# Raw keys that belong to the state rather than to the reader, or that are rendered
# elsewhere on the page.
_METRIC_HIDDEN = {"key_claims"}

STATUS_MARKERS = {
    "above": "✅",
    "below": "⚠️",
    "unknown": "❔",
}


def format_money(value: Any) -> str:
    """``1200000.0`` -> ``"$1,200,000"``; unknown values pass through untouched."""

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"${value:,.0f}"
    return "—" if value in (None, "") else str(value)


def format_ratio(value: Any) -> str:
    """``0.8571428571428571`` -> ``"0.86× the benchmark"``."""

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:.2f}× the benchmark"
    return "—" if value in (None, "") else str(value)


def format_metric_value(value: Any) -> str:
    """Normalise one extracted metric for display.

    Lists (founders, claims) become comma-separated text; an explicit "not found"
    marker is shown as a dash so a missing figure stands out from a real one.
    """

    if value is None:
        return "—"
    if isinstance(value, list):
        return ", ".join(_plain(item) for item in value) if value else "—"
    text = _plain(value)
    if not text or text.lower() in {"[not_found]", "not_found", "n/a", "na", "none", "unknown"}:
        return "— (not in the deck)"
    return text


def _plain(value: Any) -> str:
    """Flatten deck formatting out of a value: no `##`, no `**`, one line."""

    text = re.sub(r"^[\s#>*_-]+", "", str(value or ""))
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"\s+", " ", text).strip(" -:;,")
    return text


def metric_rows(metrics: dict[str, Any] | None) -> list[dict[str, str]]:
    """Return the metrics as ``[{metric, value}]`` rows in a stable, readable order."""

    metrics = metrics or {}
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    for key, label in _METRIC_ORDER:
        if key in metrics:
            rows.append({"metric": label, "value": format_metric_value(metrics[key])})
            seen.add(key)

    for key, value in metrics.items():
        if key in seen or key in _METRIC_HIDDEN:
            continue
        label = _METRIC_LABELS.get(key, key.replace("_", " ").capitalize())
        rows.append({"metric": label, "value": format_metric_value(value)})

    return rows


def benchmark_rows(benchmarks: dict[str, Any] | None) -> list[dict[str, str]]:
    """Return the financial audit as readable rows.

    The verdict is deliberately **not** a row: it is the conclusion of the analysis and
    is rendered separately so it cannot be mistaken for another input figure.
    """

    benchmarks = benchmarks or {}
    rows = [
        {"metric": "ARR", "value": format_money(benchmarks.get("arr"))},
        {"metric": "Team size", "value": format_metric_value(benchmarks.get("team_size"))},
        {
            "metric": "ARR per employee",
            "value": format_money(benchmarks.get("arr_per_employee")),
        },
        {
            "metric": "Benchmark (B2B SaaS)",
            "value": format_money(benchmarks.get("benchmark_arr_per_employee")),
        },
        {
            "metric": "Against the benchmark",
            "value": format_ratio(benchmarks.get("ratio_to_benchmark")),
        },
    ]
    return rows


def verdict_of(benchmarks: dict[str, Any] | None) -> tuple[str, str]:
    """Return ``(marker, verdict_text, status)`` for the highlighted verdict callout."""

    benchmarks = benchmarks or {}
    status = str(benchmarks.get("status") or "unknown")
    verdict = str(benchmarks.get("verdict") or "").strip()
    if not verdict:
        verdict = "No financial verdict — the deck did not contain enough data."
    return STATUS_MARKERS.get(status, "❔"), verdict


def state_summary(state: dict[str, Any] | None) -> list[dict[str, str]]:
    """A small headline strip: what ran, how much it found, and which model did it."""

    state = state or {}
    metrics = state.get("extracted_metrics") or {}
    loops = state.get("critic_loops_count", 0)
    return [
        {"metric": "Company", "value": format_metric_value(metrics.get("company_name"))},
        {"metric": "Red Flags found", "value": str(len(state.get("red_flags") or []))},
        {
            "metric": "Critic passes",
            "value": f"{loops} of 2" if loops else "0 (nothing to re-check)",
        },
        {"metric": "Model used", "value": str(state.get("used_model") or "unknown")},
    ]


def report_facts(state: dict[str, Any] | None) -> list[tuple[str, str]]:
    """The four figures printed on the report's cover."""

    state = state or {}
    metrics = state.get("extracted_metrics") or {}
    benchmarks = state.get("financial_benchmarks") or {}
    per_employee = benchmarks.get("arr_per_employee")
    return [
        ("ARR (stated)", format_metric_value(metrics.get("arr"))),
        ("Team size", format_metric_value(metrics.get("team_size"))),
        (
            "ARR / employee",
            format_money(per_employee) if per_employee is not None else "not computable",
        ),
        ("Red flags", str(len(state.get("red_flags") or []))),
    ]


__all__ = [
    "benchmark_rows",
    "format_metric_value",
    "format_money",
    "format_ratio",
    "metric_rows",
    "report_facts",
    "state_summary",
    "verdict_of",
]
