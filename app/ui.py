"""Streamlit UI for DueDil.Agent.

Run with::

    streamlit run app/ui.py

The interface ships in English (default), German, French and Russian.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make sure the project root is importable when launched via `streamlit run`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from app.graph import build_graph  # noqa: E402
from app.i18n import DEFAULT_LANGUAGE, LANGUAGES, translate  # noqa: E402
from app.parser import ParserError, parse_pdf_to_markdown  # noqa: E402
from app.report import markdown_to_pdf_bytes  # noqa: E402
from app.state import initial_state  # noqa: E402

# Maps a graph node to its i18n key.
NODE_LABEL_KEYS = {
    "agent_extractor": "step_extractor",
    "agent_scraper": "step_scraper",
    "agent_financial": "step_financial",
    "agent_critic": "step_critic",
    "agent_supervisor": "step_supervisor",
}


def _merge_update(state: dict, node: str, payload: dict | None) -> None:
    """Merge a node's partial update into the accumulated state."""

    payload = payload or {}
    for key, value in payload.items():
        if key == "progress_log":
            state.setdefault("progress_log", [])
            state["progress_log"].extend(value or [])
        else:
            state[key] = value


def _language_selector() -> str:
    """Render the language picker in the sidebar and return the chosen code."""

    codes = list(LANGUAGES)
    current = st.session_state.get("lang", DEFAULT_LANGUAGE)
    if current not in codes:
        current = DEFAULT_LANGUAGE
    choice = st.selectbox(
        translate(DEFAULT_LANGUAGE, "language_label"),
        options=codes,
        index=codes.index(current),
        format_func=lambda code: LANGUAGES[code],
    )
    st.session_state["lang"] = choice
    return choice


def main() -> None:
    st.set_page_config(page_title="DueDil.Agent", page_icon="🔍", layout="wide")
    if "lang" not in st.session_state:
        st.session_state["lang"] = DEFAULT_LANGUAGE

    with st.sidebar:
        lang = _language_selector()

    def t(key: str, **kwargs) -> str:
        return translate(lang, key, **kwargs)

    st.title("🔍 DueDil.Agent")
    st.caption(t("tagline"))

    with st.sidebar:
        st.header(t("sidebar_header"))
        uploaded = st.file_uploader(t("uploader_label"), type=["pdf"])
        website_url = st.text_input(t("url_label"), placeholder=t("url_placeholder"))
        run = st.button(t("run_button"), type="primary", use_container_width=True)
        st.divider()
        st.caption(t("keys_caption"))

    st.subheader(t("progress_header"))
    step_slots = {node: st.empty() for node in NODE_LABEL_KEYS}
    for node, slot in step_slots.items():
        slot.info(f"⏳ {t(NODE_LABEL_KEYS[node])}")

    if not run:
        st.info(t("idle_hint"))
        return

    if not uploaded:
        st.error(t("err_no_pdf"))
        return

    pdf_bytes = uploaded.read()
    with st.spinner(t("spinner_parsing")):
        try:
            deck_text = parse_pdf_to_markdown(pdf_bytes)
        except ParserError as exc:
            st.error(t("err_parse", error=exc))
            return
    st.success(t("ok_parsed", count=len(deck_text)))

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

    metrics = state.get("extracted_metrics") or {}
    benchmarks = state.get("financial_benchmarks") or {}
    flags = state.get("red_flags") or []

    left, right = st.columns(2)
    with left:
        st.subheader(t("metrics_header"))
        if metrics:
            st.json(metrics)
        else:
            st.write(t("no_metrics"))
    with right:
        st.subheader(t("benchmarks_header"))
        if benchmarks:
            st.json(benchmarks)
        else:
            st.write(t("no_benchmarks"))

    if flags:
        st.subheader(f"🚩 {t('redflags_header')}")
        for flag in flags:
            st.warning(flag)
    else:
        st.success(t("no_redflags"))

    st.subheader(t("memo_header"))
    st.markdown(memo)

    st.download_button(
        t("download_pdf"),
        data=markdown_to_pdf_bytes(memo),
        file_name="duediligence_memo.pdf",
        mime="application/pdf",
        type="primary",
    )

    with st.expander(t("log_expander")):
        for line in state.get("progress_log", []):
            st.write(line)


if __name__ == "__main__":
    main()
