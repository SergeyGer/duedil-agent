#!/usr/bin/env python3
"""Run DueDil.Agent end-to-end with no API keys and no network.

The graph, its nodes, the routing, the critic->scraper loop, the PDF parser and
the ReportLab export are all exercised for real — only the two external
dependencies are replaced:

* ``app.graph.get_llm``            -> a canned LLM (metrics / red flags / memo)
* ``app.graph.get_search_tool``    -> a canned Tavily search (market data)

The canned payloads come from ``examples/sample_memo.json`` (metrics and memo) and
``examples/sample_offline_run.json`` (the Red Flags an LLM would have reported).
The deterministic Red-Flag heuristics are *not* stubbed, so the final flag list is
still produced by the real critic code.

Usage::

    python scripts/demo_offline.py                       # -> data/nimbusai_memo.pdf
    python scripts/demo_offline.py --out /tmp/memo.pdf --md /tmp/memo.md

Nothing here is imported by the application itself.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app import graph as graph_module  # noqa: E402
from app.offline_agents import OfflineExtractorLLM, OfflineSupervisorLLM  # noqa: E402
from app.parser import parse_pdf_to_markdown  # noqa: E402
from app.prompts import CRITIC_SYSTEM, EXTRACTOR_SYSTEM  # noqa: E402
from app.report import markdown_to_pdf  # noqa: E402

DEFAULT_EXAMPLE = REPO_ROOT / "examples" / "sample_memo.json"
DEFAULT_FLAGS = REPO_ROOT / "examples" / "sample_offline_run.json"
DEFAULT_DECK = REPO_ROOT / "examples" / "sample_deck.pdf"

#: Offline modes: recorded payloads, or a rule-based reading of the deck.
OFFLINE_MODES = ("canned", "deck_aware")


class _Response:
    """Minimal stand-in for a LangChain ``AIMessage`` (``_message_text`` reads ``.content``)."""

    def __init__(self, content: str) -> None:
        self.content = content


class CannedLLM:
    """Returns a fixed answer per agent, chosen by the system prompt in the request."""

    def __init__(self, metrics: dict, memo: str, red_flags: list[str], delay: float = 0.0) -> None:
        self.metrics = metrics
        self.memo = memo
        self.red_flags = red_flags
        self.delay = delay

    def invoke(self, messages, **_: object) -> _Response:  # noqa: ANN001 - mimic LangChain
        # Optional latency so a recorded demo shows the per-step progress instead
        # of a single frame (0 for normal runs).
        if self.delay:
            time.sleep(self.delay)
        # Match on the real system prompts so a prompt edit cannot silently turn
        # the demo into "every agent returns the memo".
        system = str(getattr(messages[0], "content", "")).strip()
        if system == EXTRACTOR_SYSTEM.strip():
            return _Response(json.dumps(self.metrics, ensure_ascii=False))
        if system == CRITIC_SYSTEM.strip():
            payload = {
                "red_flags": self.red_flags,
                "critic_feedback": "verify the team size and the traffic figures",
            }
            return _Response(json.dumps(payload, ensure_ascii=False))
        return _Response(self.memo)


class DeckAwareLLM:
    """Reads the deck it is given, then writes the memo from what it read.

    The Extractor is answered by :class:`app.offline_agents.OfflineExtractorLLM`
    (deterministic rules over the deck text) and the Supervisor by
    :class:`app.offline_agents.OfflineSupervisorLLM` (a memo built from the metrics and
    market notes). The Critic keeps the canned Red Flags, because the real deterministic
    heuristics add their own findings on top of whatever it reports.
    """

    def __init__(self, red_flags: list[str], delay: float = 0.0) -> None:
        self.red_flags = red_flags
        self.delay = delay

    def invoke(self, messages, **_: object) -> _Response:  # noqa: ANN001 - mimic LangChain
        if self.delay:
            time.sleep(self.delay)
        system = str(getattr(messages[0], "content", "")).strip()
        if system == EXTRACTOR_SYSTEM.strip():
            return OfflineExtractorLLM().invoke(messages)
        if system == CRITIC_SYSTEM.strip():
            payload = {
                "red_flags": self.red_flags,
                "critic_feedback": "verify the team size and the traffic figures",
            }
            return _Response(json.dumps(payload, ensure_ascii=False))
        return OfflineSupervisorLLM().invoke(messages)


class CannedSearchTool:
    """Serves slices of the canned market data instead of calling Tavily."""

    def __init__(self, blocks: list[str], delay: float = 0.0) -> None:
        self.blocks = blocks
        self.delay = delay

    def invoke(self, query: str, **_: object) -> dict:
        if self.delay:
            time.sleep(self.delay)
        lowered = (query or "").lower()
        chosen = self.blocks
        if "competitor" in lowered:
            chosen = [b for b in self.blocks if "competitor" in b.lower()] or self.blocks
        elif "traffic" in lowered or "visits" in lowered:
            chosen = [b for b in self.blocks if "traffic" in b.lower()] or self.blocks
        elif "founder" in lowered or "linkedin" in lowered:
            chosen = [
                b for b in self.blocks if "linkedin" in b.lower() or "founder" in b.lower()
            ] or self.blocks
        return {
            "results": [
                {"title": f"Offline search: {query}", "url": "", "content": "\n".join(chosen)}
            ]
        }


def offline_mode() -> str | None:
    """Return the offline mode the environment asks for, or ``None`` for a live run.

    ``DUE_DIL_OFFLINE_MODE=deck_aware`` is the explicit switch used by the hosted demo.
    The legacy ``DUEDIL_MODE`` (anything other than ``ui``) still means "offline", and
    defaults to the canned payloads so existing recordings stay reproducible.
    """

    explicit = (os.getenv("DUE_DIL_OFFLINE_MODE") or "").strip().lower()
    if explicit in OFFLINE_MODES:
        return explicit
    legacy = (os.getenv("DUEDIL_MODE") or "ui").strip().lower()
    if legacy != "ui":
        return "canned" if legacy == "demo-ui" else "deck_aware"
    return None


def _market_blocks() -> list[str]:
    """Reconstruct the ``market_data`` list from the committed example state."""

    state = json.loads(DEFAULT_EXAMPLE.read_text(encoding="utf-8"))
    blocks = state.get("market_data") or []
    return [str(block) for block in blocks]


def _canned_payload() -> tuple[dict, str, list[str]]:
    state = json.loads(DEFAULT_EXAMPLE.read_text(encoding="utf-8"))
    flags = json.loads(DEFAULT_FLAGS.read_text(encoding="utf-8")).get("llm_red_flags") or []
    return (
        state.get("extracted_metrics") or {},
        state.get("final_memo") or "",
        [str(flag) for flag in flags],
    )


def install_stubs(
    delay: float = 0.0,
    mode: str = "canned",
    market_blocks: list[str] | None = None,
    llm_red_flags: list[str] | None = None,
) -> str:
    """Swap the LLM and the search tool for offline versions.

    ``mode`` is ``"canned"`` (recorded NimbusAI payloads — the same output for any deck)
    or ``"deck_aware"`` (the Extractor and Supervisor read the deck they are given).
    ``delay`` (seconds) is added to every call so a recorded demo shows the per-agent
    progress; leave it at 0 for normal runs. Returns the mode installed, so a caller can
    report which one is in effect.
    """

    if mode not in OFFLINE_MODES:
        raise ValueError(f"unknown offline mode {mode!r}; expected one of {OFFLINE_MODES}")

    # The canned NimbusAI market notes are right for the recorded demo and wrong for any other
    # deck: a caller running an arbitrary file (the CLI's `--offline`) passes an empty list, so
    # the memo never quotes evidence about a different company.
    blocks = _market_blocks() if market_blocks is None else market_blocks
    _, memo, recorded_flags = _canned_payload()
    # Same reasoning for the recorded LLM flags: they describe the NimbusAI example deck. A
    # caller analysing its own deck passes an empty list and gets only the deterministic rules.
    flags = recorded_flags if llm_red_flags is None else llm_red_flags

    if mode == "deck_aware":
        llm: CannedLLM | DeckAwareLLM = DeckAwareLLM(flags, delay)
    else:
        metrics, _, canned_flags = _canned_payload()
        llm = CannedLLM(metrics, memo, canned_flags, delay)

    # The memo must not claim a model ran when none did: the artefacts are stamped with
    # whatever `model_label()` returns, so point it at the truth for offline runs.
    graph_module.model_label = lambda *_, **__: f"offline rules, {mode} (no model)"  # type: ignore[assignment]

    graph_module.get_llm = lambda *_, **__: llm  # type: ignore[assignment]
    graph_module.get_search_tool = lambda *_, **__: CannedSearchTool(  # type: ignore[assignment]
        blocks, delay
    )
    return mode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline DueDil.Agent demo run (no API keys).")
    parser.add_argument("deck", nargs="?", default=str(DEFAULT_DECK))
    parser.add_argument("url", nargs="?", default="https://nimbusai.example")
    parser.add_argument("--out", default="data/nimbusai_memo.pdf")
    parser.add_argument("--md")
    parser.add_argument("--json", dest="json_out")
    parser.add_argument(
        "--offline-mode",
        choices=OFFLINE_MODES,
        default="canned",
        help="canned: recorded payloads (same output for any deck); "
        "deck_aware: the agents read the deck they are given",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="seconds of latency added to every canned agent call (for recordings)",
    )
    args = parser.parse_args(argv)

    mode = install_stubs(delay=args.delay, mode=args.offline_mode)

    print(f"DueDil.Agent — OFFLINE DEMO ({mode} LLM + canned search, no API keys)\n")
    print(f"  deck  : {args.deck}")
    print(f"  url   : {args.url}")
    print(f"  model : offline-demo ({mode})\n")

    print("[1/2] Parsing PDF -> Markdown ...")
    deck_text = parse_pdf_to_markdown(args.deck)
    print(f"      extracted {len(deck_text):,} characters\n")

    print("[2/2] Running the agent graph:")
    graph = graph_module.build_graph()
    state = graph_module.initial_state(deck_text, args.url)
    for chunk in graph.stream(state, stream_mode="updates"):
        for node, payload in (chunk or {}).items():
            print(f"      done  {node}")
            for key, value in (payload or {}).items():
                if key == "progress_log":
                    state.setdefault("progress_log", []).extend(value or [])
                else:
                    state[key] = value

    memo = state.get("final_memo") or ""
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_to_pdf(memo, str(out_path))
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(memo, encoding="utf-8", newline="\n")
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
        )

    benchmarks = state.get("financial_benchmarks") or {}
    print(f"\nRed flags  : {len(state.get('red_flags') or [])}")
    print(f"Critic loops: {state.get('critic_loops_count', 0)}")
    print(f"Financials : {benchmarks.get('verdict', 'n/a')}")
    print(f"Company    : {(state.get('extracted_metrics') or {}).get('company_name', '?')}")
    print(f"\nPDF memo   : {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
