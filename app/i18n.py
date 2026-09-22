"""Translations for the Streamlit UI (English, German, French, Russian).

The UI defaults to English. Keep every language table in sync with ``en`` --
``tests/test_i18n.py`` enforces that all languages share the same keys and the
same format placeholders.
"""

from __future__ import annotations

DEFAULT_LANGUAGE = "en"

# Language code -> endonym (the name shown in the selector).
LANGUAGES: dict[str, str] = {
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
    "ru": "Русский",
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "language_label": "🌐 Language / Sprache / Langue / Язык",
        "tagline": "Autonomous multi-agent due diligence for technology startups (LangGraph).",
        "sidebar_header": "Inputs",
        "uploader_label": "Pitch Deck (PDF)",
        "url_label": "Startup website",
        "url_placeholder": "https://example.com",
        "run_button": "Run due diligence",
        "keys_caption": "Full functionality requires the API keys: `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`, `LLAMA_CLOUD_API_KEY`, `TAVILY_API_KEY`.",
        "progress_header": "Progress",
        "idle_hint": "Upload a PDF and click “Run due diligence”.",
        "err_no_pdf": "Please upload the startup's pitch deck PDF first.",
        "spinner_parsing": "Parsing PDF to Markdown (LlamaParse)…",
        "err_parse": "Could not parse the PDF: {error}",
        "ok_parsed": "Extracted {count:,} characters from the PDF.",
        "status_running": "Running the agent pipeline…",
        "status_done": "Pipeline complete.",
        "err_no_memo": "No memo was generated.",
        "metrics_header": "Startup metrics",
        "no_metrics": "No metrics extracted.",
        "benchmarks_header": "Financial benchmarks",
        "no_benchmarks": "No benchmarks computed.",
        "redflags_header": "Red Flags",
        "no_redflags": "No Red Flags detected.",
        "memo_header": "Investment memo",
        "download_pdf": "⬇️ Download PDF",
        "log_expander": "Execution log",
        "step_extractor": "Extractor — extracting metrics from the pitch deck",
        "step_scraper": "Scraper — gathering market data (Tavily)",
        "step_financial": "Financial — computing ARR / employee benchmarks",
        "step_critic": "Critic — cross-checking claims & Red Flags",
        "step_supervisor": "Supervisor — assembling the investment memo",
    },
    "de": {
        "language_label": "🌐 Language / Sprache / Langue / Язык",
        "tagline": "Autonome Multi-Agenten-Due-Diligence für Technologie-Startups (LangGraph).",
        "sidebar_header": "Eingaben",
        "uploader_label": "Pitch Deck (PDF)",
        "url_label": "Website des Startups",
        "url_placeholder": "https://example.com",
        "run_button": "Prüfung starten",
        "keys_caption": "Für den vollen Funktionsumfang sind die API-Schlüssel nötig: `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`, `LLAMA_CLOUD_API_KEY`, `TAVILY_API_KEY`.",
        "progress_header": "Fortschritt",
        "idle_hint": "Laden Sie ein PDF hoch und klicken Sie auf „Prüfung starten“.",
        "err_no_pdf": "Bitte laden Sie zuerst das Pitch Deck (PDF) des Startups hoch.",
        "spinner_parsing": "PDF wird in Markdown umgewandelt (LlamaParse) …",
        "err_parse": "PDF konnte nicht verarbeitet werden: {error}",
        "ok_parsed": "{count:,} Zeichen aus dem PDF extrahiert.",
        "status_running": "Agenten-Pipeline läuft …",
        "status_done": "Pipeline abgeschlossen.",
        "err_no_memo": "Es wurde kein Memo erstellt.",
        "metrics_header": "Startup-Kennzahlen",
        "no_metrics": "Keine Kennzahlen extrahiert.",
        "benchmarks_header": "Finanzielle Benchmarks",
        "no_benchmarks": "Keine Benchmarks berechnet.",
        "redflags_header": "Warnsignale (Red Flags)",
        "no_redflags": "Keine Red Flags gefunden.",
        "memo_header": "Investment-Memo",
        "download_pdf": "⬇️ PDF herunterladen",
        "log_expander": "Ausführungsprotokoll",
        "step_extractor": "Extraktor — Metriken aus dem Pitch Deck extrahieren",
        "step_scraper": "Scraper — Marktdaten sammeln (Tavily)",
        "step_financial": "Finanzen — ARR-/Mitarbeiter-Benchmarks berechnen",
        "step_critic": "Kritiker — Aussagen und Red Flags gegenprüfen",
        "step_supervisor": "Supervisor — Investment-Memo zusammenstellen",
    },
    "fr": {
        "language_label": "🌐 Language / Sprache / Langue / Язык",
        "tagline": "Due diligence multi-agents autonome pour les startups technologiques (LangGraph).",
        "sidebar_header": "Entrées",
        "uploader_label": "Pitch deck (PDF)",
        "url_label": "Site de la startup",
        "url_placeholder": "https://example.com",
        "run_button": "Lancer l'analyse",
        "keys_caption": "Le fonctionnement complet nécessite les clés API : `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`, `LLAMA_CLOUD_API_KEY`, `TAVILY_API_KEY`.",
        "progress_header": "Progression",
        "idle_hint": "Téléversez un PDF et cliquez sur « Lancer l'analyse ».",
        "err_no_pdf": "Veuillez d'abord téléverser le pitch deck (PDF) de la startup.",
        "spinner_parsing": "Conversion du PDF en Markdown (LlamaParse)…",
        "err_parse": "Impossible d'analyser le PDF : {error}",
        "ok_parsed": "{count:,} caractères extraits du PDF.",
        "status_running": "Exécution du pipeline d'agents…",
        "status_done": "Pipeline terminé.",
        "err_no_memo": "Aucun mémo n'a été généré.",
        "metrics_header": "Métriques de la startup",
        "no_metrics": "Aucune métrique extraite.",
        "benchmarks_header": "Benchmarks financiers",
        "no_benchmarks": "Aucun benchmark calculé.",
        "redflags_header": "Signaux d'alerte (Red Flags)",
        "no_redflags": "Aucun signal d'alerte détecté.",
        "memo_header": "Mémo d'investissement",
        "download_pdf": "⬇️ Télécharger le PDF",
        "log_expander": "Journal d'exécution",
        "step_extractor": "Extracteur — extraction des métriques du pitch deck",
        "step_scraper": "Scraper — collecte des données de marché (Tavily)",
        "step_financial": "Finance — calcul des benchmarks ARR / employé",
        "step_critic": "Critique — vérification croisée et Red Flags",
        "step_supervisor": "Superviseur — rédaction du mémo d'investissement",
    },
    "ru": {
        "language_label": "🌐 Language / Sprache / Langue / Язык",
        "tagline": "Автономный многоагентный due-diligence для технологических стартапов (LangGraph).",
        "sidebar_header": "Входные данные",
        "uploader_label": "Pitch Deck (PDF)",
        "url_label": "Сайт стартапа",
        "url_placeholder": "https://example.com",
        "run_button": "Запустить проверку",
        "keys_caption": "Для полноценной работы нужны ключи: `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`, `LLAMA_CLOUD_API_KEY`, `TAVILY_API_KEY`.",
        "progress_header": "Ход проверки",
        "idle_hint": "Загрузите PDF и нажмите «Запустить проверку».",
        "err_no_pdf": "Сначала загрузите PDF-презентацию стартапа.",
        "spinner_parsing": "Парсинг PDF в Markdown (LlamaParse)…",
        "err_parse": "Не удалось распарсить PDF: {error}",
        "ok_parsed": "Из PDF извлечено {count:,} символов.",
        "status_running": "Пайплайн агентов выполняется…",
        "status_done": "Пайплайн завершён.",
        "err_no_memo": "Меморандум не был сгенерирован.",
        "metrics_header": "Метрики стартапа",
        "no_metrics": "Метрики не извлечены.",
        "benchmarks_header": "Финансовые бенчмарки",
        "no_benchmarks": "Бенчмарки не рассчитаны.",
        "redflags_header": "Красные флаги (Red Flags)",
        "no_redflags": "Red Flags не обнаружены.",
        "memo_header": "Инвестиционный меморандум",
        "download_pdf": "⬇️ Скачать PDF",
        "log_expander": "Журнал выполнения",
        "step_extractor": "Extractor — извлечение метрик из Pitch Deck",
        "step_scraper": "Scraper — сбор рыночных данных (Tavily)",
        "step_financial": "Financial — расчёт бенчмарков (ARR / сотрудник)",
        "step_critic": "Critic — перекрёстная проверка и Red Flags",
        "step_supervisor": "Supervisor — сборка инвестиционного меморандума",
    },
}


def translate(language: str, key: str, **kwargs) -> str:
    """Return the translation of ``key`` for ``language`` (English fallback)."""

    table = TRANSLATIONS.get(language) or TRANSLATIONS[DEFAULT_LANGUAGE]
    text = table.get(key) or TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


__all__ = ["DEFAULT_LANGUAGE", "LANGUAGES", "TRANSLATIONS", "translate"]
