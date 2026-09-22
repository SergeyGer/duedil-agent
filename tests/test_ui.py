"""Smoke tests for the Streamlit UI (rendered headlessly via AppTest)."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

UI = str(Path(__file__).resolve().parent.parent / "app" / "ui.py")


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
