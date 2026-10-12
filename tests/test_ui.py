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
    assert at.button[0].label == "Run due diligence"


def test_ui_switches_to_german():
    at = AppTest.from_file(UI).run()
    at.selectbox[0].set_value("de").run()
    assert not at.exception
    assert at.button[0].label == "Prüfung starten"


def test_ui_switches_to_french():
    at = AppTest.from_file(UI).run()
    at.selectbox[0].set_value("fr").run()
    assert not at.exception
    assert at.button[0].label == "Lancer l'analyse"


def test_ui_switches_to_russian():
    at = AppTest.from_file(UI).run()
    at.selectbox[0].set_value("ru").run()
    assert not at.exception
    assert at.button[0].label == "Запустить проверку"


# --- bundled example decks ----------------------------------------------------
# The hosted demo is the first thing most visitors see, so the picker has to keep
# working: it is the difference between "upload a PDF" and "click and watch".


def test_ui_offers_the_bundled_example_decks():
    at = AppTest.from_file(UI).run()
    assert not at.exception
    assert len(at.radio) == 1, "the example picker should render exactly once"
    options = at.radio[0].options
    # The first entry is the "none, upload my own" choice.
    assert len(options) == len(EXAMPLE_DECKS) + 1
    for _, label in EXAMPLE_DECKS:
        assert label in options


def test_every_offered_example_exists_on_disk_and_has_a_url():
    examples = REPO_ROOT / "examples"
    for name, _ in EXAMPLE_DECKS:
        assert (examples / name).is_file(), f"{name} is offered but missing"
        assert EXAMPLE_URLS[name].startswith("https://")


def test_ui_prefills_the_website_for_a_chosen_example():
    at = AppTest.from_file(UI).run()
    _, label = EXAMPLE_DECKS[2]  # cursor_deck.pdf
    at.radio[0].set_value(label).run()
    assert not at.exception
    assert at.text_input[0].value == EXAMPLE_URLS["cursor_deck.pdf"]


def test_ui_asks_for_a_deck_when_none_is_provided():
    at = AppTest.from_file(UI).run()
    at.button[0].click().run()
    assert not at.exception
    # No upload, no example chosen -> the user is told what is missing, in English.
    assert any("Upload a pitch deck or pick" in err.value for err in at.error)
