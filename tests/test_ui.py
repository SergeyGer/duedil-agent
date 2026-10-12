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
    assert at.title[0].value == "🔍 DueDil.Agent"
    assert at.selectbox[0].value == "en"
    assert at.button(key="run_button").label == "Run due diligence"


def test_ui_switches_to_german():
    at = AppTest.from_file(UI).run()
    at.selectbox[0].set_value("de").run()
    assert not at.exception
    assert at.button(key="run_button").label == "Prüfung starten"


def test_ui_switches_to_french():
    at = AppTest.from_file(UI).run()
    at.selectbox[0].set_value("fr").run()
    assert not at.exception
    assert at.button(key="run_button").label == "Lancer l'analyse"


def test_ui_switches_to_russian():
    at = AppTest.from_file(UI).run()
    at.selectbox[0].set_value("ru").run()
    assert not at.exception
    assert at.button(key="run_button").label == "Запустить проверку"


# --- bundled example decks ----------------------------------------------------
# The hosted demo is the first thing most visitors see. The sidebar keeps a single
# uploader; the bundled decks live behind one button that opens a listing, because a
# browser cannot let the uploader's own "Browse files" dialog reach the server.


def test_sidebar_offers_one_button_for_the_bundled_decks_and_no_list():
    at = AppTest.from_file(UI).run()
    assert not at.exception
    labels = [button.label for button in at.button]
    assert "📂 Browse examples/" in labels
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
    assert at.button(key="clear_example").label == "Clear selection"

    at.button(key="clear_example").click().run()
    assert at.session_state["chosen_example"] is None
    assert at.text_input[0].value == ""


def test_ui_asks_for_a_deck_when_none_is_provided():
    at = AppTest.from_file(UI).run()
    at.button(key="run_button").click().run()
    assert not at.exception
    assert any("Upload a pitch deck or pick" in err.value for err in at.error)
