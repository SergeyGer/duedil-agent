"""Pure helper functions: numeric parsing, financial benchmarks and heuristics.

Everything in this module is deterministic and dependency-free so it can be unit
tested without any LLM, network access or API keys.
"""

from __future__ import annotations

import re
from typing import Any

# Benchmark for B2B SaaS: healthy companies generally clear $100k ARR / employee.
DEFAULT_ARR_PER_EMPLOYEE_BENCHMARK = 100_000

_MISSING_TOKENS = {
    "",
    "-",
    "n/a",
    "na",
    "none",
    "null",
    "unknown",
    "not found",
    "[not_found]",
    "not_found",
}

_SCALES = {
    "billion": 1_000_000_000,
    "bn": 1_000_000_000,
    "b": 1_000_000_000,
    "million": 1_000_000,
    "mn": 1_000_000,
    "m": 1_000_000,
    "thousand": 1_000,
    "k": 1_000,
}

_NUM_RE = re.compile(
    r"(?P<num>\d[\d,.]*)\s*"
    r"(?:(?P<scale>billion|million|thousand|bn|mn|k|m|b)(?![A-Za-z]))?",
    re.IGNORECASE,
)


def is_missing(value: Any) -> bool:
    """Return True when ``value`` looks like an explicit "not found" marker."""

    if value is None:
        return True
    return str(value).strip().lower() in _MISSING_TOKENS


def parse_number(value: Any) -> float | None:
    """Parse the first number in ``value``, honouring ``k``/``m``/``b`` scales.

    Examples: ``"$1.2M"`` -> ``1200000.0``; ``"1,200,000"`` -> ``1200000.0``;
    ``"50 employees"`` -> ``50.0``; ``"[NOT_FOUND]"`` -> ``None``.
    """

    if value is None:
        return None
    if isinstance(value, bool):  # bool is a subclass of int -> reject explicitly
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if is_missing(value):
        return None

    match = _NUM_RE.search(str(value))
    if not match:
        return None

    raw = match.group("num").replace(",", "")
    if raw.count(".") > 1:  # e.g. "1.200.000" -> treat dots as thousands sep
        raw = raw.replace(".", "")
    try:
        number = float(raw)
    except ValueError:
        return None

    scale = (match.group("scale") or "").lower()
    return number * _SCALES.get(scale, 1)


def parse_money(value: Any) -> float | None:
    """Alias of :func:`parse_number` used for currency figures."""

    return parse_number(value)


def parse_count(value: Any) -> int | None:
    """Parse an integer count (e.g. team size)."""

    number = parse_number(value)
    if number is None:
        return None
    return int(round(number))


def compute_financials(
    metrics: dict[str, Any],
    benchmark: int = DEFAULT_ARR_PER_EMPLOYEE_BENCHMARK,
) -> dict[str, Any]:
    """Compute ARR / team_size and compare it with the SaaS benchmark."""

    metrics = metrics or {}
    arr = parse_money(metrics.get("arr"))
    team = parse_count(metrics.get("team_size"))

    result: dict[str, Any] = {
        "arr": arr,
        "team_size": team,
        "arr_per_employee": None,
        "benchmark_arr_per_employee": benchmark,
        "ratio_to_benchmark": None,
        "status": "unknown",
        "verdict": "",
    }

    if arr is None and team is None:
        result["verdict"] = "Insufficient data: neither ARR nor team size could be parsed."
        return result
    if arr is None:
        result["verdict"] = "Cannot compute efficiency: ARR is missing or reported as [NOT_FOUND]."
        return result
    if not team:
        result["verdict"] = "Cannot compute efficiency: team size is missing or zero."
        return result

    per_employee = arr / team
    result["arr_per_employee"] = per_employee
    result["ratio_to_benchmark"] = per_employee / benchmark

    if per_employee >= benchmark:
        result["status"] = "above"
        result["verdict"] = (
            f"Healthy: ARR/employee of ${per_employee:,.0f} exceeds the B2B SaaS "
            f"benchmark of ${benchmark:,.0f}."
        )
    else:
        result["status"] = "below"
        result["verdict"] = (
            f"Weak: ARR/employee of ${per_employee:,.0f} sits below the B2B SaaS "
            f"benchmark of ${benchmark:,.0f}."
        )
    return result


# Headcount mentioned in free text. `engineers` and `researchers` are included because
# technical decks and interviews routinely describe a team that way ("about 15
# engineers"), and they are as much a headcount claim as "employees".
_TEAM_RE = re.compile(
    r"(\d[\d,.]*)\s*(?:(?:billion|million|thousand|bn|mn|k|m|b)(?![A-Za-z]))?\s*"
    r"(?:full[- ]?time\s+)?"
    r"(?:employees|employee|people|staff|team\s+members|headcount|engineers|researchers)",
    re.IGNORECASE,
)

_TRAFFIC_RE = re.compile(
    r"(\d[\d,.]*)\s*(?:(?:billion|million|thousand|bn|mn|k|m|b)(?![A-Za-z]))?\s*"
    r"(?:monthly\s+|unique\s+|total\s+|estimated\s+)?"
    r"(?:visits|visitors|pageviews|page\s+views|sessions|users)",
    re.IGNORECASE,
)

# Matches the reversed form, e.g. "Monthly Visits: 300".
_TRAFFIC_RE_REVERSED = re.compile(
    r"(?:visits|visitors|pageviews|page\s+views|sessions|users)\D{0,15}?"
    r"(\d[\d,.]*)\s*(?:(?:billion|million|thousand|bn|mn|k|m|b)(?![A-Za-z]))?",
    re.IGNORECASE,
)


_STATED_TEAM_RE = re.compile(r"team\s*size\s*[:=-]?\s*(\d{1,6})", re.IGNORECASE)

#: A LinkedIn-style range ("51-200 employees") describes a band, and its upper bound is not the
#: headcount: reading 200 there made a 50-person company look four times larger.
_TEAM_RANGE_RE = re.compile(r"(\d{1,5})\s*[-–]\s*(\d{1,5})\s*employees?", re.IGNORECASE)


def find_stated_team_size(text: str) -> int | None:
    """Return an explicitly stated headcount ("Team Size: 50"), or ``None``.

    Structured fields beat prose ranges: when a data provider states the number, that is the
    number, not the top of a band.
    """

    match = _STATED_TEAM_RE.search(text or "")
    return int(match.group(1)) if match else None


def find_team_mentions(text: str) -> list[int]:
    """Extract team-size figures mentioned in free text (e.g. LinkedIn counts)."""

    if not text:
        return []
    counts: list[int] = []
    for match in _TEAM_RE.finditer(text):
        value = parse_number(match.group(0))
        # A headcount above 100 000 is a parsing accident (a traffic figure or a funding number
        # caught by the "employees" window), not a team.
        if value is not None and 0 < value <= 100_000:
            counts.append(int(value))
    return counts


def find_traffic_mentions(text: str) -> list[int]:
    """Extract website-traffic figures mentioned in free text.

    Handles both ``"1500 monthly visits"`` and ``"Monthly visits: 1500"``.
    """

    if not text:
        return []
    counts: list[int] = []
    for pattern in (_TRAFFIC_RE, _TRAFFIC_RE_REVERSED):
        for match in pattern.finditer(text):
            value = parse_number(match.group(0))
            if value is not None:
                counts.append(int(value))
    return counts


#: Words that mark a flag as a contradiction rather than a task to verify.
_MATERIAL_FLAG_WORDS = (
    "mismatch",
    "implausib",
    "contradict",
    "inconsisten",
    "overstat",
    "impossible",
)


def is_material_flag(flag: str) -> bool:
    """True when a flag contradicts evidence, false for a "we could not verify X" note."""

    lowered = (flag or "").lower()
    return any(word in lowered for word in _MATERIAL_FLAG_WORDS)


def deterministic_recommendation(state: dict[str, Any]) -> str:
    """The recommendation the evidence implies, independent of any model.

    The rule is about materiality, not about the number of observations: a real deck always
    leaves questions open, and a partner answers those with conditions, not with a rejection
    notice.

    * **REJECT** — the financials fail the benchmark, or a flag contradicts the evidence.
    * **DEEP AUDIT** — the benchmark cannot be computed from the deck.
    * **INVEST** — the numbers clear the benchmark and the remaining flags are verification tasks.
    """

    flags = state.get("red_flags") or []
    benchmarks = state.get("financial_benchmarks") or {}
    status = benchmarks.get("status")
    ratio = benchmarks.get("ratio_to_benchmark") or 0

    if status == "below":
        return "REJECT"
    if status != "above":
        return "DEEP AUDIT"

    # A contradiction matters in proportion to how thin the margin is: a company at several times
    # the benchmark can carry an open question as a condition, a marginal one cannot.
    if any(is_material_flag(flag) for flag in flags):
        if ratio < 3:
            return "REJECT"
        if ratio < 8:
            return "DEEP AUDIT"
    return "INVEST"


__all__ = [
    "is_material_flag",
    "find_stated_team_size",
    "deterministic_recommendation",
    "DEFAULT_ARR_PER_EMPLOYEE_BENCHMARK",
    "is_missing",
    "parse_number",
    "parse_money",
    "parse_count",
    "compute_financials",
    "find_team_mentions",
    "find_traffic_mentions",
]
