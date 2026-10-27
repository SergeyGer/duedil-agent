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
from app.comment import build_comment, recommendation_of
from app.config import model_label
from app.display import report_facts
from app.graph import build_graph
from app.parser import ParserError, parse_pdf_to_markdown
from app.redact import redact_secrets, redact_state
from app.report import markdown_to_pdf
from app.state import initial_state

NODE_LABELS = {
    "agent_extractor": "Extractor   — extracting pitch-deck metrics",
    "agent_scraper": "Scraper     — gathering market data (Tavily)",
    "agent_financial": "Financial   — computing ARR / employee benchmarks",
    "agent_critic": "Critic      — cross-checking claims & Red Flags",
    "agent_supervisor": "Supervisor  — assembling the deal memo",
}


def _install_offline() -> None:
    """Swap in the rule-based agents used by the hosted demo: no keys, no network.

    The stubs live in ``scripts/demo_offline.py`` because the Streamlit app imports them the
    same way; reusing them keeps one definition of "offline" instead of two behaviours that
    drift apart.
    """

    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from demo_offline import install_stubs

    # No canned market notes: the deck may be any company, and quoting another one is
    # worse than admitting there is no external evidence at all.
    install_stubs(mode="deck_aware", market_blocks=[], llm_red_flags=[])


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
    parser.add_argument(
        "--comment-file",
        dest="comment_out",
        help="write a short Markdown summary (recommendation, top Red Flags) here",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="run the rule-based offline agents instead of an LLM (no API keys, no network)",
    )
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

    if args.offline:
        _install_offline()
    elif args.model:
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
    log(f"  model : {'offline rules, deck_aware (no model)' if args.offline else model_label()}")
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
    state = initial_state(deck_text, args.url, deck_path.name)
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
        log(f"Critic loops: {state.get('critic_loops_count', 0)}")
        if benchmarks.get("verdict"):
            log(f"Financials : {benchmarks['verdict']}")
        log(f"Model used : {state.get('used_model') or model_label()}")

    # --- write outputs -----------------------------------------------------
    company = (state.get("extracted_metrics") or {}).get("company_name") or "startup"
    out_path = Path(args.out) if args.out else Path("data") / f"{_slugify(company)}_memo.pdf"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    company = (state.get("extracted_metrics") or {}).get("company_name") or ""
    markdown_to_pdf(
        memo,
        str(out_path),
        model=state.get("used_model") or model_label(),
        company=str(company),
        recommendation=recommendation_of(state),
        facts=report_facts(state),
    )

    # `newline="\n"` keeps the generated artefacts LF-only on Windows, matching
    # `.gitattributes` (`eol=lf`) and the pre-commit `mixed-line-ending` hook.
    if args.md_out:
        Path(args.md_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md_out).write_text(redact_secrets(memo), encoding="utf-8", newline="\n")

    if args.comment_out:
        comment_path = Path(args.comment_out)
        comment_path.parent.mkdir(parents=True, exist_ok=True)
        comment_path.write_text(
            # The summary is a fixed template over deck-derived values: the model label is
            # validated and credential shapes are redacted. A taint tracker still follows the
            # label from `DUE_DIL_MODEL` into this file, which is why the write is suppressed —
            # `tests/test_redact.py` and `tests/test_comment.py` assert what can reach it.
            redact_secrets(build_comment(state)),  # codeql[py/clear-text-storage-sensitive-data]
            encoding="utf-8",
            newline="\n",
        )

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(
            json.dumps(redact_state(state), ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
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
        if args.comment_out:
            print(f"PR comment: {args.comment_out}")
        if args.json_out:
            print(f"State JSON: {args.json_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
