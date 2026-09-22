"""Streamlit UI for DueDil.Agent.

Run with::

    streamlit run app/ui.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make sure the project root is importable when launched via `streamlit run`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from app.graph import build_graph  # noqa: E402
from app.parser import ParserError, parse_pdf_to_markdown  # noqa: E402
from app.report import markdown_to_pdf_bytes  # noqa: E402
from app.state import initial_state  # noqa: E402

NODE_LABELS = {
    "agent_extractor": "Extractor — извлечение метрик из Pitch Deck",
    "agent_scraper": "Scraper — сбор рыночных данных (Tavily)",
    "agent_financial": "Financial — расчет бенчмарков (ARR / сотрудник)",
    "agent_critic": "Critic — перекрестная проверка и Red Flags",
    "agent_supervisor": "Supervisor — сборка инвестиционного меморандума",
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


def main() -> None:
    st.set_page_config(page_title="DueDil.Agent", page_icon="🔍", layout="wide")
    st.title("🔍 DueDil.Agent")
    st.caption(
        "Автономный многоагентный скоринг и проверка благонадежности "
        "технологических стартапов (LangGraph)."
    )

    with st.sidebar:
        st.header("Входные данные")
        uploaded = st.file_uploader("Pitch Deck (PDF)", type=["pdf"])
        website_url = st.text_input("Сайт стартапа", placeholder="https://example.com")
        run = st.button("Запустить проверку", type="primary", use_container_width=True)
        st.divider()
        st.caption(
            "Для полноценной работы нужны ключи: `OPENAI_API_KEY` / "
            "`ANTHROPIC_API_KEY`, `LLAMA_CLOUD_API_KEY`, `TAVILY_API_KEY`."
        )

    st.subheader("Ход проверки")
    step_slots = {node: st.empty() for node in NODE_LABELS}
    for node, slot in step_slots.items():
        slot.info(f"⏳ {NODE_LABELS[node]}")

    if not run:
        st.info("Загрузите PDF и нажмите «Запустить проверку».")
        return

    if not uploaded:
        st.error("Сначала загрузите PDF-презентацию стартапа.")
        return

    pdf_bytes = uploaded.read()
    with st.spinner("Парсинг PDF в Markdown (LlamaParse)..."):
        try:
            deck_text = parse_pdf_to_markdown(pdf_bytes)
        except ParserError as exc:
            st.error(f"Не удалось распарсить PDF: {exc}")
            return
    st.success(f"Из PDF извлечено {len(deck_text):,} символов.")

    graph = build_graph()
    state = initial_state(deck_text, website_url)

    with st.status("Пайплайн агентов выполняется...", expanded=True) as status:
        for chunk in graph.stream(state, stream_mode="updates"):
            for node, payload in (chunk or {}).items():
                if node in step_slots:
                    step_slots[node].success(f"✅ {NODE_LABELS[node]}")
                _merge_update(state, node, payload)
        status.update(label="Пайплайн завершен.", state="complete", expanded=False)

    memo = state.get("final_memo") or ""
    if not memo:
        st.error("Меморандум не был сгенерирован.")
        return

    # --- Diagnostics -------------------------------------------------------
    metrics = state.get("extracted_metrics") or {}
    benchmarks = state.get("financial_benchmarks") or {}
    flags = state.get("red_flags") or []

    left, right = st.columns(2)
    with left:
        st.subheader("Метрики стартапа")
        if metrics:
            st.json(metrics)
        else:
            st.write("Метрики не извлечены.")
    with right:
        st.subheader("Финансовые бенчмарки")
        if benchmarks:
            st.json(benchmarks)
        else:
            st.write("Бенчмарки не рассчитаны.")

    if flags:
        st.subheader("🚩 Red Flags")
        for flag in flags:
            st.warning(flag)
    else:
        st.success("Red Flags не обнаружены.")

    st.subheader("Инвестиционный меморандум")
    st.markdown(memo)

    pdf_report = markdown_to_pdf_bytes(memo)
    st.download_button(
        "⬇️ Скачать PDF",
        data=pdf_report,
        file_name="duediligence_memo.pdf",
        mime="application/pdf",
        type="primary",
    )

    with st.expander("Журнал выполнения"):
        for line in state.get("progress_log", []):
            st.write(line)


if __name__ == "__main__":
    main()
