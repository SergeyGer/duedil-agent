"""Command-line interface for DueDil.Agent.

Examples
--------
Run the full pipeline on a pitch deck and write a PDF memo::

    python -m app.cli deck.pdf https://startup.example

Override the model, choose an output path and dump the raw state::

    python -m app.cli pitch.pdf https://acme.ai \\
        --model claude-3-5-sonnet --out reports/acme.pdf --json reports/acme.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

from app import __version__
from app.config import DEFAULT_MODEL
from app.graph import build_graph
from app.parser import ParserError, parse_pdf_to_markdown
from app.report import markdown_to_pdf
from app.state import initial_state

NODE_LABELS = {
    "agent_extractor": "Extractor   — extracting pitch-deck metrics",
    "agent_scraper": "Scraper     — gathering market data (Tavily)",
    "agent_financial": "Financial   — computing ARR / employee benchmarks",
    "agent_critic": "Critic      — cross-checking claims & Red Flags",
    "agent_supervisor": "Supervisor  — assembling the deal memo",
}


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or "memo"


def _merge(state: dict, payload: dict | None) -> None:
    """Merge one node's partial update into the accumulated state."""

    payload = payload or {}
    for key, value in payload.items():
        if key == "progress_log":
            state.setdefault("progress_log", [])
            state["progress_log"].extend(value or [])
        else:
            state[key] = value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="duedil",
        description="Run DueDil.Agent on a pitch deck PDF and produce an investment memo.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("deck", nargs="?", help="path to the pitch deck PDF")
    parser.add_argument("url", nargs="?", default="", help="startup website URL")
    parser.add_argument("-o", "--out", help="output PDF path (default: data/<company>_memo.pdf)")
    parser.add_argument("--md", dest="md_out", help="also write the raw Markdown memo here")
    parser.add_argument(
        "--json", dest="json_out", help="dump the full final state to this JSON file"
    )
    parser.add_argument("--model", help="override the LLM id (e.g. claude-3-5-sonnet)")
    parser.add_argument("--quiet", action="store_true", help="only print the final memo")
    parser.add_argument("--version", action="version", version=f"duedil {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_dotenv()

    if not args.deck:
        build_parser().print_help(sys.stderr)
        print("\nerror: a pitch deck PDF path is required.", file=sys.stderr)
        return 2

    if args.model:
        os.environ["DUE_DIL_MODEL"] = args.model

    deck_path = Path(args.deck)
    if not deck_path.exists():
        print(f"error: file not found: {deck_path}", file=sys.stderr)
        return 2

    def log(message: str) -> None:
        if not args.quiet:
            print(message)

    log("DueDil.Agent")
    log(f"  deck  : {deck_path}")
    log(f"  url   : {args.url or '(not provided)'}")
    log(f"  model : {os.getenv('DUE_DIL_MODEL', DEFAULT_MODEL)}")
    log("")

    log("[1/2] Parsing PDF -> Markdown ...")
    try:
        deck_text = parse_pdf_to_markdown(deck_path)
    except ParserError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    log(f"      extracted {len(deck_text):,} characters\n")

    log("[2/2] Running the agent graph:")
    graph = build_graph()
    state = initial_state(deck_text, args.url)
    try:
        for chunk in graph.stream(state, stream_mode="updates"):
            for node, payload in (chunk or {}).items():
                log(f"      done  {NODE_LABELS.get(node, node)}")
                _merge(state, payload)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"error: pipeline failed: {exc}", file=sys.stderr)
        return 4

    memo = state.get("final_memo") or ""
    if not memo.strip():
        print("error: no memo was produced.", file=sys.stderr)
        return 5

    if not args.quiet:
        benchmarks = state.get("financial_benchmarks") or {}
        flags = state.get("red_flags") or []
        log("")
        log(f"Red flags  : {len(flags)}")
        if benchmarks.get("verdict"):
            log(f"Financials : {benchmarks['verdict']}")

    # --- write outputs -----------------------------------------------------
    company = (state.get("extracted_metrics") or {}).get("company_name") or "startup"
    out_path = Path(args.out) if args.out else Path("data") / f"{_slugify(company)}_memo.pdf"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_to_pdf(memo, str(out_path))

    # `newline="\n"` keeps the generated artefacts LF-only on Windows, matching
    # `.gitattributes` (`eol=lf`) and the pre-commit `mixed-line-ending` hook.
    if args.md_out:
        Path(args.md_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md_out).write_text(memo, encoding="utf-8", newline="\n")

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
        )

    if args.quiet:
        print(memo)
    else:
        print()
        print(memo)
        print()
        print(f"PDF memo  : {out_path}")
        if args.md_out:
            print(f"Markdown  : {args.md_out}")
        if args.json_out:
            print(f"State JSON: {args.json_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
