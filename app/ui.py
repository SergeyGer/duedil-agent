"""Streamlit UI for DueDil.Agent.

Run with::

    streamlit run app/ui.py

The interface ships in English (default), German, French and Russian.

The page is deliberately thin: everything that turns state into something readable
lives in :mod:`app.display`, so it can be unit-tested without a browser.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make sure the project root is importable when Streamlit runs this file as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from app.comment import recommendation_of
from app.display import (  # noqa: E402
    benchmark_rows,
    metric_rows,
    state_summary,
    verdict_of,
)
from app.graph import build_graph  # noqa: E402
from app.i18n import DEFAULT_LANGUAGE, LANGUAGES, translate  # noqa: E402
from app.parser import ParserError, parse_pdf_to_markdown  # noqa: E402
from app.report import markdown_to_pdf_bytes  # noqa: E402
from app.state import initial_state  # noqa: E402

NODE_LABEL_KEYS = {
    "agent_extractor": "step_extractor",
    "agent_scraper": "step_scraper",
    "agent_financial": "step_financial",
    "agent_critic": "step_critic",
    "agent_supervisor": "step_supervisor",
}

# Bundled decks from examples/ — the ones documented in examples/README.md. They are
# reconstructions built from public reporting, which is why the picker says so.
EXAMPLE_DECKS: list[tuple[str, str]] = [
    ("airbnb_deck.pdf", "Airbnb (2011)"),
    ("uber_deck.pdf", "Uber (2011)"),
    ("cursor_deck.pdf", "Cursor"),
    ("lovable_deck.pdf", "Lovable"),
    ("cognition_deck.pdf", "Cognition AI"),
]

# The website field is prefilled with the matching public URL when an example is picked.
EXAMPLE_URLS = {
    "airbnb_deck.pdf": "https://www.airbnb.com",
    "uber_deck.pdf": "https://www.uber.com",
    "cursor_deck.pdf": "https://cursor.com",
    "lovable_deck.pdf": "https://lovable.dev",
    "cognition_deck.pdf": "https://cognition.ai",
}


def _language_selector() -> str:
    options = list(LANGUAGES)
    current = st.session_state.get("lang", DEFAULT_LANGUAGE)
    choice = st.selectbox(
        translate(current, "language_label"),
        options,
        index=options.index(current),
        format_func=lambda code: LANGUAGES[code],
    )
    st.session_state["lang"] = choice
    return choice


def _literal(text: str) -> str:
    """Escape dollar signs so Streamlit renders money instead of LaTeX."""

    return text.replace("$", "\\$")


def _llm_is_configured() -> bool:
    """True when the provider that the configured model needs has a key."""

    from app.config import get_model_name

    if get_model_name().lower().startswith("claude"):
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    return bool(os.getenv("OPENAI_API_KEY"))


def _offline_mode() -> str | None:
    """Decide whether this process must run offline, and in which mode.

    An explicit ``DUE_DIL_OFFLINE_MODE`` wins. Otherwise a deployment with the LLM
    keys missing would call a model it cannot reach and fall back to
    "Investment Memo — Unknown Startup" for every input — which is exactly what the
    hosted demo did. Falling back to the rule-based agents instead makes the demo
    honest and shows a different analysis per deck.
    """

    requested = (os.getenv("DUE_DIL_OFFLINE_MODE") or "").strip()
    if requested:
        return requested
    return None if _llm_is_configured() else "deck_aware"


def _examples_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "examples"


def _deck_from_example(name: str) -> bytes | None:
    """Read a bundled deck from disk, or explain why it is unavailable."""

    path = _examples_dir() / name
    try:
        return path.read_bytes()
    except OSError:
        return None


def _merge_update(state: dict, node: str, payload: dict | None) -> None:
    """Apply a node's partial update to the state under construction."""

    for key, value in (payload or {}).items():
        if key == "progress_log":
            state.setdefault("progress_log", []).extend(value or [])
        else:
            state[key] = value


@st.dialog("Pick a deck from examples/")
def _browse_examples_dialog() -> None:
    """Show the bundled decks as a file listing.

    The sidebar keeps a single uploader; this dialog is what the second button opens,
    so choosing a bundled deck stays a deliberate two-click action instead of a list
    that is always on screen. Browser security would not let the uploader's own "Browse
    files" button reach the server's filesystem, so the listing is rendered by the app.
    """

    st.caption(
        "Reconstructed from public reporting — each deck prints its sources on its last "
        "page. Or cancel and upload your own PDF."
    )
    for name, label in EXAMPLE_DECKS:
        exists = (_examples_dir() / name).is_file()
        if st.button(
            f"📄 {label} — {name}",
            key=f"example_{name}",
            use_container_width=True,
            disabled=not exists,
            help=None if exists else f"{name} is not available in this deployment",
        ):
            st.session_state["chosen_example"] = name
            st.rerun()


def _hero(t) -> None:
    """The landing block: purpose, outcome and the three things a reader gets."""

    st.title(t("hero_title"))
    st.markdown(
        "<div style='font-size:1.08rem;line-height:1.6;color:#3f4a5a;max-width:62rem;"
        f"margin:-0.4rem 0 1.4rem 0'>{t('hero_subtitle')}</div>",
        unsafe_allow_html=True,
    )

    columns = st.columns(3, gap="large")
    values = (
        ("value_1_title", "value_1_text"),
        ("value_2_title", "value_2_text"),
        ("value_3_title", "value_3_text"),
    )
    for column, (title_key, text_key) in zip(columns, values, strict=True):
        with column:
            st.markdown(f"**{t(title_key)}**")
            st.caption(t(text_key))

    st.markdown(f"#### {t('how_header')}")
    st.markdown(t("how_steps"))


def _chosen_example_name() -> str | None:
    return st.session_state.get("chosen_example")


def main() -> None:
    st.set_page_config(
        page_title="DueDil — Investment Due Diligence", page_icon="📄", layout="wide"
    )
    if "lang" not in st.session_state:
        st.session_state["lang"] = DEFAULT_LANGUAGE

    with st.sidebar:
        lang = _language_selector()

    def t(key: str, **kwargs) -> str:
        return translate(lang, key, **kwargs)

    with st.sidebar:
        st.header(t("sidebar_header"))
        uploaded = st.file_uploader(t("uploader_label"), type=["pdf"])

        can_browse = any((_examples_dir() / name).is_file() for name, _ in EXAMPLE_DECKS)
        if st.button(
            t("browse_examples"),
            key="browse_examples",
            use_container_width=True,
            disabled=not can_browse,
            help=None if can_browse else t("err_no_examples"),
        ):
            _browse_examples_dialog()

        chosen_file = _chosen_example_name()
        # Rendered through a placeholder so the selection row only appears when there is
        # something to show, without the widgets below it shifting position.
        selection_slot = st.empty()
        if chosen_file and (_examples_dir() / chosen_file).is_file():
            with selection_slot.container():
                st.caption(t("example_selected", name=chosen_file))
                if st.button(t("clear_example"), key="clear_example", use_container_width=True):
                    st.session_state["chosen_example"] = None
                    st.rerun()

        website_url = st.text_input(
            t("url_label"),
            value=EXAMPLE_URLS.get(chosen_file or "", ""),
            placeholder=t("url_placeholder"),
        )
        run = st.button(t("run_button"), key="run_button", type="primary", use_container_width=True)
        st.divider()
        st.caption(t("keys_caption"))

    # The first screen speaks to the reader's job, not to the implementation: what they get,
    # how it works, and what to do next.
    if not run:
        _hero(t)
        st.info(t("idle_hint"))
        return

    st.subheader(t("progress_header"))
    step_slots = {node: st.empty() for node in NODE_LABEL_KEYS}
    for node, slot in step_slots.items():
        slot.info(f"⏳ {t(NODE_LABEL_KEYS[node])}")

    deck_bytes: bytes | None = None
    if uploaded is not None:
        # An explicit upload wins, and the remembered example is dropped so the next run
        # cannot silently fall back to it.
        st.session_state["chosen_example"] = None
        deck_bytes = uploaded.read()
    elif chosen_file:
        deck_bytes = _deck_from_example(chosen_file)
        if deck_bytes is None:
            st.error(t("err_parse", error=f"{chosen_file} is not available in this deployment"))
            return
        st.info(f"📄 {chosen_file}")

    if not deck_bytes:
        st.error(t("err_no_deck"))
        return

    with st.spinner(t("spinner_parsing")):
        try:
            deck_text = parse_pdf_to_markdown(deck_bytes)
        except ParserError as exc:
            st.error(t("err_parse", error=exc))
            return
    st.success(t("ok_parsed", count=len(deck_text)))

    offline_mode = _offline_mode()
    if offline_mode:
        # Imported here so a live deployment never loads the demo module.
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        from demo_offline import install_stubs

        install_stubs(delay=float(os.getenv("DUE_DIL_DEMO_DELAY", "0")), mode=offline_mode)

    graph = build_graph()
    state = initial_state(deck_text, website_url)

    with st.status(t("status_running"), expanded=True) as status:
        for chunk in graph.stream(state, stream_mode="updates"):
            for node, payload in (chunk or {}).items():
                if node in step_slots:
                    step_slots[node].success(f"✅ {t(NODE_LABEL_KEYS[node])}")
                _merge_update(state, node, payload)
        status.update(label=t("status_done"), state="complete", expanded=False)

    memo = state.get("final_memo") or ""
    if not memo:
        st.error(t("err_no_memo"))
        return

    if offline_mode:
        st.warning(t("offline_notice"))

    metrics = state.get("extracted_metrics") or {}
    benchmarks = state.get("financial_benchmarks") or {}
    flags = state.get("red_flags") or []

    # The step-by-step chips did their job while the analysis ran; keeping them on screen
    # afterwards pushes the result below the fold.
    for slot in step_slots.values():
        slot.empty()

    # --- what ran, and what came out of it ---------------------------------
    st.subheader(t("summary_header"))
    summary = state_summary(state)
    summary = [row for row in summary if row["metric"] != "Model used"]
    summary.insert(0, {"metric": t("recommendation_metric"), "value": recommendation_of(state)})
    summary_cols = st.columns(len(summary))
    for column, row in zip(summary_cols, summary, strict=True):
        column.metric(row["metric"], row["value"])

    # --- readable tables instead of raw JSON -------------------------------
    left, right = st.columns(2)
    with left:
        st.subheader(t("metrics_header"))
        rows = metric_rows(metrics)
        if rows:
            st.dataframe(
                rows,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "metric": t("table_metric"),
                    "value": t("table_value"),
                },
            )
        else:
            st.write(t("no_metrics"))
    with right:
        st.subheader(t("benchmarks_header"))
        rows = benchmark_rows(benchmarks)
        if benchmarks:
            st.dataframe(
                rows,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "metric": t("table_metric"),
                    "value": t("table_value"),
                },
            )
        else:
            st.write(t("no_benchmarks"))

    # --- the conclusion gets its own, unmistakable block -------------------
    marker, verdict = verdict_of(benchmarks)
    st.subheader(t("verdict_header"))
    callout = getattr(
        st,
        {"above": "success", "below": "warning"}.get(str(benchmarks.get("status") or ""), "info"),
    )
    # `$1,200,000` inside a Streamlit markdown block is parsed as LaTeX unless the dollars
    # are escaped, which renders money as "1, 200, 000". The verdict, the flags and the
    # memo are prose about money, not formulas.
    callout(_literal(f"{marker} {verdict}"))

    if flags:
        st.subheader(t("redflags_header"))
        for flag in flags:
            st.warning(_literal(flag))
    else:
        st.success(t("no_redflags"))

    st.subheader(t("memo_header"))
    st.markdown(_literal(memo))

    st.download_button(
        t("download_pdf"),
        data=markdown_to_pdf_bytes(memo, model=state.get("used_model") or ""),
        file_name="duediligence_memo.pdf",
        mime="application/pdf",
        type="primary",
    )

    with st.expander(t("log_expander")):
        for line in state.get("progress_log", []):
            st.write(line)


if __name__ == "__main__":
    main()
