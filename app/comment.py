"""A short Markdown summary of a run, sized for a pull-request comment.

The memo is six sections long; a reader scrolling a pull request needs the verdict, the numbers
behind it and the worst findings — in a comment they can take in at a glance.

Everything here is a pure function of the final state, so the format can be tested without
GitHub, and the same text feeds the PR comment, the CLI and the action's job summary.
"""

from __future__ import annotations

import re
from typing import Any

from app import utils
from app.display import format_metric_value, format_money

#: How many Red Flags fit in a comment before it stops being skimmable.
MAX_FLAGS = 3

#: The verdicts the memo may state.
RECOMMENDATIONS = ("INVEST", "DEEP AUDIT", "REJECT")

_RECOMMENDATION_RE = re.compile(r"\b(INVEST|DEEP AUDIT|REJECT)\b", re.IGNORECASE)

#: A model label comes from the environment (`DUE_DIL_MODEL`) and ends up in a file, so it is
#: validated before it enters an artefact: an unexpected value must not be written as-is.
_MODEL_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,_()/+-]{0,63}$")

#: Prefixes of credentials that must never be echoed into a memo, a comment or a JSON dump.
_SECRET_PREFIXES = ("sk-", "sk_", "lsv2_", "tvly-", "llx-", "ghp_", "github_pat_")


def safe_model_label(value: Any) -> str:
    """Return the model label when it looks like one, otherwise ``"unknown"``.

    ``DUE_DIL_MODEL`` is free-form, so someone can point it at a key by mistake. Anything that
    looks like a credential, or that is not a plausible model id, is replaced instead of written.
    """

    text = " ".join(str(value or "").split())
    if not text or len(text) > 64:
        return "unknown"
    if text.lower().startswith(_SECRET_PREFIXES):
        return "unknown"
    return text if _MODEL_LABEL_RE.match(text) else "unknown"


_STATUS_TEXT = {
    "above": "above the benchmark",
    "below": "below the benchmark",
    "unknown": "not computable",
}


def extract_recommendation(memo: str) -> str:
    """Return the verdict the memo states, or ``"UNKNOWN"`` when it states none.

    The memo's final section is ``**REJECT**`` (or ``INVEST``/``DEEP AUDIT``), so the first
    standalone occurrence is the answer. ``INVEST`` deliberately does not match ``INVESTMENT``:
    the word boundary after the ``T`` requires a non-word character.
    """

    match = _RECOMMENDATION_RE.search(memo or "")
    return match.group(1).upper() if match else "UNKNOWN"


def recommendation_of(state: dict[str, Any]) -> str:
    """The memo's verdict, with the deterministic rules as the fallback.

    A model may omit the verdict or write something unexpected; the deterministic
    recommendation then keeps the comment honest instead of printing ``UNKNOWN``.
    """

    stated = extract_recommendation(str(state.get("final_memo") or ""))
    if stated != "UNKNOWN":
        return stated
    return utils.deterministic_recommendation(state)


def _cell(value: Any) -> str:
    """Markdown-safe table cell: no newlines, no unescaped pipes.

    A field the extractor never returned is reported the same way as an explicit
    ``[NOT_FOUND]``: the reader should not have to distinguish two flavours of "absent".
    """

    text = format_metric_value(value) if value is not None else "— (not in the deck)"
    return text.replace("|", "\\|").replace("\n", " ")


def _score_row(state: dict[str, Any]) -> str:
    benchmarks = state.get("financial_benchmarks") or {}
    per_employee = benchmarks.get("arr_per_employee")
    if per_employee is None:
        return "| ARR / employee | — (not computable) |"
    benchmark = benchmarks.get("benchmark_arr_per_employee")
    status = _STATUS_TEXT.get(str(benchmarks.get("status") or "unknown"), "not computable")
    benchmark_cell = f"${benchmark:,}" if isinstance(benchmark, (int, float)) else "—"
    return f"| ARR / employee | {format_money(per_employee)} ({status} of {benchmark_cell}) |"


def build_comment(state: dict[str, Any]) -> str:
    """Render the final state as a compact Markdown comment."""

    metrics = state.get("extracted_metrics") or {}
    benchmarks = state.get("financial_benchmarks") or {}
    flags = [str(flag).strip() for flag in (state.get("red_flags") or []) if str(flag).strip()]
    loops = state.get("critic_loops_count", 0)

    company = _cell(metrics.get("company_name"))
    recommendation = recommendation_of(state)
    model = safe_model_label(state.get("used_model"))

    lines = [
        f"### Due diligence — {company}",
        "",
        f"**{recommendation}** · {len(flags)} Red Flag{'s' if len(flags) != 1 else ''} · {model}",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| ARR (as stated) | {_cell(metrics.get('arr'))} |",
        f"| Team size | {_cell(metrics.get('team_size'))} |",
        _score_row(state),
        f"| Critic passes | {loops} of 2 |",
        "",
    ]

    if flags:
        shown = flags[:MAX_FLAGS]
        lines.append("**Top Red Flags**")
        lines.append("")
        lines.extend(f"{index}. {flag}" for index, flag in enumerate(shown, start=1))
        if len(flags) > len(shown):
            lines.append("")
            lines.append(f"_{len(flags) - len(shown)} more in the full memo._")
    else:
        lines.append("**No Red Flags were raised.**")

    verdict = str(benchmarks.get("verdict") or "").strip()
    if verdict:
        lines.extend(["", f"> {verdict}"])

    lines.extend(
        [
            "",
            "<sub>Generated by [DueDil.Agent](https://github.com/SergeyGer/duedil-agent)"
            + " · the full memo is attached to this run as an artifact.</sub>",
            "",
        ]
    )
    return "\n".join(lines)
