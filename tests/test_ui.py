"""Smoke tests for the Streamlit UI (rendered headlessly via AppTest)."""

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parent.parent
UI = str(REPO_ROOT / "app" / "ui.py")

sys.path.insert(0, str(REPO_ROOT))

from app.ui import EXAMPLE_DECKS, EXAMPLE_URLS  # noqa: E402


def test_ui_renders_in_english_by_default():
    at = AppTest.from_file(UI).run()
    assert not at.exception
    assert at.title[0].value == "Investment due diligence in minutes"
    assert at.selectbox[0].value == "en"
    assert at.button(key="run_button").label == "Analyse the deck"


def test_ui_switches_to_german():
    at = AppTest.from_file(UI).run()
    at.selectbox[0].set_value("de").run()
    assert not at.exception
    assert at.button(key="run_button").label == "Deck analysieren"


def test_ui_switches_to_french():
    at = AppTest.from_file(UI).run()
    at.selectbox[0].set_value("fr").run()
    assert not at.exception
    assert at.button(key="run_button").label == "Analyser le deck"


def test_ui_switches_to_russian():
    at = AppTest.from_file(UI).run()
    at.selectbox[0].set_value("ru").run()
    assert not at.exception
    assert at.button(key="run_button").label == "Проанализировать дек"


# --- bundled example decks ----------------------------------------------------
# The hosted demo is the first thing most visitors see. The sidebar keeps a single
# uploader; the bundled decks live behind one button that opens a listing, because a
# browser cannot let the uploader's own "Browse files" dialog reach the server.


def test_sidebar_offers_one_button_for_the_bundled_decks_and_no_list():
    at = AppTest.from_file(UI).run()
    assert not at.exception
    labels = [button.label for button in at.button]
    assert "or open a sample deck" in labels
    # No selectbox or radio list of decks: the sidebar shows an uploader, not a menu.
    assert len(at.radio) == 0
    assert [box.value for box in at.selectbox] == ["en"]  # only the language selector


def test_every_bundled_deck_is_offered_and_exists():
    examples = REPO_ROOT / "examples"
    for name, _ in EXAMPLE_DECKS:
        assert (examples / name).is_file(), f"{name} is offered but missing"
        assert EXAMPLE_URLS[name].startswith("https://")


def test_browse_dialog_lists_every_deck():
    at = AppTest.from_file(UI).run()
    at.button(key="browse_examples").click().run()
    assert not at.exception
    # The dialog is a fragment, so its buttons appear in the same AppTest tree.
    for name, label in EXAMPLE_DECKS:
        assert at.button(key=f"example_{name}").label.startswith(f"📄 {label}")


def test_a_chosen_example_becomes_the_deck_and_can_be_cleared():
    """The dialog writes `chosen_example`; this is what the app then does with it.

    AppTest does not re-run a fragment when a button inside `st.dialog` is clicked, so the
    selection is exercised through the session state it writes rather than through the click.
    """

    at = AppTest.from_file(UI).run()
    at.session_state["chosen_example"] = "cursor_deck.pdf"
    at.run()
    assert not at.exception
    # The choice is visible, and the website field is prefilled from it.
    assert any("cursor_deck.pdf" in c.value for c in at.caption)
    assert at.text_input[0].value == EXAMPLE_URLS["cursor_deck.pdf"]
    assert at.button(key="clear_example").label == "Remove sample"

    at.button(key="clear_example").click().run()
    assert at.session_state["chosen_example"] is None
    assert at.text_input[0].value == ""


def test_the_run_button_is_disabled_until_a_deck_is_chosen():
    """Nothing to analyse, nothing to click — the button says so instead of failing later."""

    at = AppTest.from_file(UI).run()
    button = at.button(key="run_button")
    assert button.disabled is True
    assert button.help and "Attach a deck" in button.help

    at.session_state["chosen_example"] = "cursor_deck.pdf"
    at.run()
    assert at.button(key="run_button").disabled is False


def test_first_screen_speaks_to_an_investor_not_to_an_engineer():
    """The landing screen must state the purpose and the outcome, without implementation talk."""

    at = AppTest.from_file(UI).run()
    assert not at.exception

    visible = " ".join(
        [at.title[0].value]
        + [m.value for m in at.markdown]
        + [c.value for c in at.caption]
        + [b.label for b in at.button]
    )
    for technical in ("LangGraph", "Tavily", "LlamaParse", "Streamlit", "Extractor", "Critic"):
        assert technical not in visible, f"the first screen leaks {technical!r}"

    assert "due diligence" in visible.lower()
    assert "memo" in visible.lower()


def test_the_fallback_copy_matches_the_english_table():
    """The in-module fallback exists for a stale translation table, and must not drift."""

    from app.i18n import TRANSLATIONS
    from app.ui import EN_FALLBACK

    for key, value in EN_FALLBACK.items():
        assert key in TRANSLATIONS["en"], f"{key} is not a real translation key"
        assert TRANSLATIONS["en"][key] == value, f"{key} drifted from the English table"


def test_the_memo_is_split_at_its_sections():
    """The long market-analysis prose is rendered behind a disclosure, so the split must work."""

    from app.ui import _memo_sections

    memo = (
        "# Investment Memo — Acme\n\n"
        "## 1. Executive Summary\nAcme is growing.\n\n"
        "## 3. Market Analysis\nThe market is large.\nSecond line.\n\n"
        "## 6. Final Recommendation\n**INVEST**"
    )
    sections = _memo_sections(memo)

    headings = [heading for heading, _ in sections]
    assert "1. Executive Summary" in headings
    assert "3. Market Analysis" in headings
    market = dict(sections)["3. Market Analysis"]
    assert "The market is large." in market and "Second line." in market
