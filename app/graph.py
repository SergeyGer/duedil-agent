"""The DueDil.Agent LangGraph pipeline.

Graph topology::

    START -> agent_extractor -> agent_scraper -> agent_financial -> agent_critic
                                       ^                                   |
                                       |                          route_after_critic
                                       |  (flags & loops < 2)              |
                                       +-----------------------------------+
                                                                           |
                                            (clean or loops >= 2)          v
                                                          agent_supervisor -> END

The critic->scraper loop is hard-capped at ``MAX_CRITIC_LOOPS`` (2) so the graph
can never run away.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from .config import get_llm
from .prompts import CRITIC_SYSTEM, EXTRACTOR_SYSTEM, SUPERVISOR_SYSTEM
from .state import VentureState, initial_state
from .tools import get_search_tool, stringify_search_results
from .utils import (
    DEFAULT_ARR_PER_EMPLOYEE_BENCHMARK,
    compute_financials,
    find_team_mentions,
    find_traffic_mentions,
    is_missing,
    parse_count,
)

# Hard cap on the "critic -> scraper" loop (spec: maximum 2 passes).
MAX_CRITIC_LOOPS = 2

# Business-triggering keywords that indicate an explicit leadership claim.
_LEADERSHIP_KEYWORDS = (
    "leader",
    "market leader",
    "#1",
    "no.1",
    "number one",
    "the only",
    "dominant",
    "best-in-class",
    "unrivalled",
    "unrivaled",
)


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------
def _safe_json(payload: Any) -> dict:
    """Best-effort JSON parsing of an LLM response (tolerates code fences)."""

    if isinstance(payload, dict):
        return payload
    text = getattr(payload, "content", payload)
    text = str(text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _message_text(message: Any) -> str:
    return str(getattr(message, "content", message) or "")


# ---------------------------------------------------------------------------
# Node: extractor
# ---------------------------------------------------------------------------
def agent_extractor(state: VentureState) -> dict:
    """Extract structured metrics from ``pitch_deck_raw`` (never invents data)."""

    deck = state.get("pitch_deck_raw") or ""

    try:
        llm = get_llm()
        message = llm.invoke(
            [
                SystemMessage(content=EXTRACTOR_SYSTEM),
                HumanMessage(content=f"PITCH DECK TEXT:\n\n{deck[:24000]}"),
            ]
        )
        metrics = _safe_json(_message_text(message))
    except Exception as exc:  # pragma: no cover - network/LLM failure path
        metrics = {}
        log = f"[extractor] FAILED: {exc}"
    else:
        log = f"[extractor] metrics extracted for '{metrics.get('company_name', '?')}'"

    if not metrics:
        metrics = {}
    metrics.setdefault("website", state.get("website_url", ""))

    return {"extracted_metrics": metrics, "progress_log": [log]}


# ---------------------------------------------------------------------------
# Node: scraper (Tavily)
# ---------------------------------------------------------------------------
def agent_scraper(state: VentureState) -> dict:
    """Search the web for competitors, traffic and founder footprint.

    On a repeat pass (after the critic) the queries are driven by
    ``critic_feedback`` instead of the default template.
    """

    metrics = state.get("extracted_metrics") or {}
    company = metrics.get("company_name") or state.get("website_url") or "the startup"
    sector = metrics.get("sector") or "technology"
    feedback = (state.get("critic_feedback") or "").strip()
    loops = state.get("critic_loops_count", 0)

    if feedback:
        queries = [
            f"{company} {feedback}",
            f"{company} employees LinkedIn {sector}",
        ]
    else:
        queries = [
            f"{company} top 3 competitors {sector}",
            f"{company} website monthly traffic visits",
            f"{company} founders LinkedIn team size",
        ]

    tool = get_search_tool()
    blocks: list[str] = []

    if tool is None:
        blocks.append("[market_data unavailable: TAVILY_API_KEY is not configured]")
    else:
        for query in queries:
            try:
                raw = tool.invoke(query)
            except Exception as exc:  # pragma: no cover - network failure path
                blocks.append(f"### Query: {query}\n[search error: {exc}]")
                continue
            blocks.append(f"### Query: {query}\n{stringify_search_results(raw)}")

    return {
        "market_data": blocks,
        "progress_log": [f"[scraper] ran {len(queries)} query(ies) (loop {loops})"],
    }


# ---------------------------------------------------------------------------
# Node: financial
# ---------------------------------------------------------------------------
def agent_financial(state: VentureState) -> dict:
    """Compute ARR / team_size and benchmark it against B2B SaaS norms."""

    metrics = state.get("extracted_metrics") or {}
    benchmarks = compute_financials(metrics, DEFAULT_ARR_PER_EMPLOYEE_BENCHMARK)
    return {
        "financial_benchmarks": benchmarks,
        "progress_log": [f"[financial] {benchmarks['verdict']}"],
    }


# ---------------------------------------------------------------------------
# Node: critic
# ---------------------------------------------------------------------------
def _deterministic_flags(state: VentureState) -> list[str]:
    """Rule-based cross-checks that run regardless of the LLM's output."""

    metrics = state.get("extracted_metrics") or {}
    market_text = "\n".join(state.get("market_data") or [])
    flags: list[str] = []

    # 1) Team-size contradiction (deck vs external sources such as LinkedIn).
    claimed = parse_count(metrics.get("team_size"))
    team_mentions = [c for c in find_team_mentions(market_text) if c > 0]
    if claimed and team_mentions:
        external = max(team_mentions)
        if external * 5 <= claimed:
            flags.append(
                f"Team-size mismatch: the deck claims {claimed} employees but external "
                f"sources indicate only about {external}."
            )
        elif claimed * 5 <= external:
            flags.append(
                f"Team-size mismatch: the deck states {claimed} employees while external "
                f"sources suggest about {external}."
            )

    # 2) Leadership claim vs near-zero website traffic.
    claim_blob = " ".join(
        [str(metrics.get("claimed_leadership", ""))]
        + [str(c) for c in (metrics.get("key_claims") or [])]
    ).lower()
    claims_leadership = any(keyword in claim_blob for keyword in _LEADERSHIP_KEYWORDS)
    traffic = find_traffic_mentions(market_text)
    if claims_leadership and traffic:
        peak = max(traffic)
        if peak < 5000:
            flags.append(
                "Implausible leadership: the deck claims market leadership but external "
                f"traffic data indicates only ~{peak:,} visits."
            )

    # 3) Missing critical financial metric.
    if is_missing(metrics.get("arr")):
        flags.append("Missing ARR: no revenue figure was stated in the deck ([NOT_FOUND]).")

    return flags


def agent_critic(state: VentureState) -> dict:
    """Cross-check deck claims vs market data and accumulate Red Flags."""

    metrics = state.get("extracted_metrics") or {}
    market_text = "\n\n".join(state.get("market_data") or [])

    try:
        llm = get_llm()
        message = llm.invoke(
            [
                SystemMessage(content=CRITIC_SYSTEM),
                HumanMessage(
                    content=(
                        "CITED STARTUP METRICS (JSON):\n"
                        + json.dumps(metrics, ensure_ascii=False)
                        + "\n\nEXTERNAL MARKET DATA:\n"
                        + market_text[:20000]
                    )
                ),
            ]
        )
        parsed = _safe_json(_message_text(message))
    except Exception as exc:  # pragma: no cover - network/LLM failure path
        parsed = {"red_flags": [], "critic_feedback": f"critic failed: {exc}"}

    llm_flags = [
        flag.strip()
        for flag in (parsed.get("red_flags") or [])
        if isinstance(flag, str) and flag.strip()
    ]
    new_flags = llm_flags + _deterministic_flags(state)

    existing = list(state.get("red_flags") or [])
    combined = existing + [flag for flag in new_flags if flag not in existing]

    feedback = parsed.get("critic_feedback") or ""
    if not feedback:
        feedback = "Verify the following concerns: " + "; ".join(combined)

    loops = state.get("critic_loops_count", 0) + 1
    return {
        "red_flags": combined,
        "critic_loops_count": loops,
        "critic_feedback": feedback,
        "progress_log": [f"[critic] pass {loops} -> {len(combined)} red flag(s) total"],
    }


# ---------------------------------------------------------------------------
# Router (conditional edge)
# ---------------------------------------------------------------------------
def route_after_critic(state: VentureState) -> str:
    """Return the next node name after the critic.

    ``"agent_scraper"`` when there are unresolved flags and we still have loop
    budget, otherwise ``"agent_supervisor"``.
    """

    flags = state.get("red_flags") or []
    loops = state.get("critic_loops_count", 0)
    if flags and loops < MAX_CRITIC_LOOPS:
        return "agent_scraper"
    return "agent_supervisor"


# ---------------------------------------------------------------------------
# Node: supervisor
# ---------------------------------------------------------------------------
def _recommendation(state: VentureState) -> str:
    """Deterministic fallback recommendation used for the context/fallback."""

    flags = state.get("red_flags") or []
    status = (state.get("financial_benchmarks") or {}).get("status")
    if not flags and status == "above":
        return "INVEST"
    if len(flags) >= 3 or status == "below":
        return "REJECT"
    return "DEEP AUDIT"


def _build_context(state: VentureState) -> str:
    metrics = state.get("extracted_metrics") or {}
    benchmarks = state.get("financial_benchmarks") or {}
    flags = state.get("red_flags") or []
    market = "\n\n".join(state.get("market_data") or []) or "(no market data)"

    return (
        "EXTRACTED METRICS (JSON):\n"
        + json.dumps(metrics, ensure_ascii=False, indent=2)
        + "\n\nFINANCIAL BENCHMARKS (JSON):\n"
        + json.dumps(benchmarks, ensure_ascii=False, indent=2)
        + "\n\nEXTERNAL MARKET DATA:\n"
        + market
        + "\n\nRED FLAGS:\n"
        + ("\n".join(f"- {flag}" for flag in flags) or "- none")
        + "\n\nWrite the deal memo now."
    )


def _fallback_memo(state: VentureState, reason: Any = "") -> str:
    """Deterministic memo used if the LLM call fails."""

    metrics = state.get("extracted_metrics") or {}
    benchmarks = state.get("financial_benchmarks") or {}
    flags = state.get("red_flags") or []
    company = metrics.get("company_name") or "Unknown Startup"
    recommendation = _recommendation(state)

    metric_lines = (
        "\n".join(f"- **{key}**: {value}" for key, value in metrics.items() if key != "key_claims")
        or "- no metrics extracted"
    )
    flag_lines = "\n".join(f"- {flag}" for flag in flags) or "- none"
    market = "\n".join(state.get("market_data") or []) or "- no market data"

    return (
        f"# Investment Memo — {company}\n\n"
        "## 1. Executive Summary\n"
        f"Automated first-pass due diligence for **{company}**.\n\n"
        "## 2. Startup Metrics\n"
        f"{metric_lines}\n\n"
        "## 3. Market Analysis\n"
        f"{market}\n\n"
        "## 4. Financial Audit\n"
        f"{benchmarks.get('verdict', 'No financial verdict available.')}\n\n"
        "## 5. Hidden Risks (Red Flags)\n"
        f"{flag_lines}\n\n"
        "## 6. Final Recommendation\n"
        f"**{recommendation}**\n\n"
        f"_(Generated without LLM: {reason})_\n"
    )


def agent_supervisor(state: VentureState) -> dict:
    """Assemble the final Markdown deal memo."""

    try:
        llm = get_llm()
        message = llm.invoke(
            [
                SystemMessage(content=SUPERVISOR_SYSTEM),
                HumanMessage(content=_build_context(state)),
            ]
        )
        memo = _message_text(message).strip()
    except Exception as exc:  # pragma: no cover - network/LLM failure path
        memo = ""
        reason = exc
    else:
        reason = "empty LLM response"

    if not memo:
        memo = _fallback_memo(state, reason)

    return {"final_memo": memo, "progress_log": ["[supervisor] deal memo generated"]}


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------
def build_graph():
    """Build and compile the DueDil.Agent state graph."""

    graph = StateGraph(VentureState)

    graph.add_node("agent_extractor", agent_extractor)
    graph.add_node("agent_scraper", agent_scraper)
    graph.add_node("agent_financial", agent_financial)
    graph.add_node("agent_critic", agent_critic)
    graph.add_node("agent_supervisor", agent_supervisor)

    graph.add_edge(START, "agent_extractor")
    graph.add_edge("agent_extractor", "agent_scraper")
    graph.add_edge("agent_scraper", "agent_financial")
    graph.add_edge("agent_financial", "agent_critic")

    graph.add_conditional_edges(
        "agent_critic",
        route_after_critic,
        {
            "agent_scraper": "agent_scraper",
            "agent_supervisor": "agent_supervisor",
        },
    )
    graph.add_edge("agent_supervisor", END)

    return graph.compile()


@lru_cache(maxsize=1)
def get_app():
    """Return a cached, compiled graph."""

    return build_graph()


def run_due_diligence(
    pitch_deck_raw: str,
    website_url: str = "",
    *,
    app=None,
) -> VentureState:
    """Convenience entry point: run the full pipeline once and return the state."""

    graph = app or get_app()
    return graph.invoke(initial_state(pitch_deck_raw, website_url))


__all__ = [
    "MAX_CRITIC_LOOPS",
    "agent_extractor",
    "agent_scraper",
    "agent_financial",
    "agent_critic",
    "agent_supervisor",
    "route_after_critic",
    "build_graph",
    "get_app",
    "run_due_diligence",
]
