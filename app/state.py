"""Typed state for the DueDil.Agent LangGraph pipeline.

The graph carries a single :class:`VentureState` dictionary between nodes. All
core fields required by the spec are declared here; a few bookkeeping fields
(``website_url``, ``critic_feedback``, ``progress_log``, ``error``) are added so
the UI and the critic->scraper loop have somewhere to store their data.
"""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict


class ExtractedMetrics(TypedDict, total=False):
    """Structured facts pulled out of the pitch deck (all strings by design)."""

    company_name: str
    sector: str
    arr: str
    mrr: str
    team_size: str
    tam: str
    founded_year: str
    business_model: str
    claimed_leadership: str
    founders: list[str]
    website: str
    key_claims: list[str]


class VentureState(TypedDict, total=False):
    """Shared state flowing through the agent graph."""

    # --- Inputs -------------------------------------------------------------
    website_url: str
    pitch_deck_raw: str

    # --- Extractor ----------------------------------------------------------
    extracted_metrics: dict

    # --- Scraper ------------------------------------------------------------
    market_data: list[str]

    # --- Financial ----------------------------------------------------------
    financial_benchmarks: dict

    # --- Critic -------------------------------------------------------------
    red_flags: list[str]
    critic_loops_count: int
    critic_feedback: str

    # --- Supervisor ---------------------------------------------------------
    final_memo: str

    # --- Bookkeeping / observability ---------------------------------------
    # ``progress_log`` uses the ``add`` reducer so every node can append its own
    # status lines without clobbering the others' entries.
    progress_log: Annotated[list[str], add]
    error: str


def initial_state(pitch_deck_raw: str, website_url: str = "") -> VentureState:
    """Build a fresh, fully-initialised state for a single run."""

    return VentureState(
        website_url=website_url or "",
        pitch_deck_raw=pitch_deck_raw or "",
        extracted_metrics={},
        market_data=[],
        financial_benchmarks={},
        red_flags=[],
        critic_loops_count=0,
        critic_feedback="",
        final_memo="",
        progress_log=["[init] run started"],
        error="",
    )


__all__ = ["VentureState", "ExtractedMetrics", "initial_state"]
