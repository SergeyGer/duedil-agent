"""The PDF must never contain a glyph the font cannot draw."""

from __future__ import annotations

import pytest

from app.textsafe import REPLACEMENTS, sanitize_for_pdf, unsupported_characters


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ARR → $1.2M", "ARR -> $1.2M"),
        ("≈ 40% growth", "~ 40% growth"),
        ("≥ 14 employees", ">= 14 employees"),
        ("≤ 3 days", "<= 3 days"),
        ("TAM · SAM", "TAM - SAM"),
        ("“quoted” — dash", '"quoted" - dash'),
        ("wait…", "wait..."),
        ("done ✅", "done yes"),
        ("broken ✗", "broken no"),
        ("⚠ risk", "! risk"),
    ],
)
def test_typographic_characters_have_plain_equivalents(raw: str, expected: str):
    assert sanitize_for_pdf(raw, unicode_font=True) == expected


def test_emoji_are_removed_even_with_a_unicode_font():
    text = "Great deck 🚀📈 — really 🇩🇪"
    cleaned = sanitize_for_pdf(text, unicode_font=True)

    assert "🚀" not in cleaned and "📈" not in cleaned
    assert "🇩🇪" not in cleaned
    assert "Great deck" in cleaned


def test_cyrillic_survives_with_a_unicode_font():
    assert sanitize_for_pdf("Привет, мир", unicode_font=True) == "Привет, мир"


def test_cyrillic_is_dropped_when_only_builtin_fonts_exist():
    """Helvetica encodes cp1252 only; leaving the letters in would draw black boxes."""

    assert sanitize_for_pdf("Привет, мир", unicode_font=False) == ", "


def test_control_characters_become_spaces():
    assert sanitize_for_pdf("a\x00b\x07c", unicode_font=True) == "a b c"


def test_sanitising_is_idempotent():
    text = "ARR → $1.2M ✅ Привет 🚀"
    once = sanitize_for_pdf(text, unicode_font=True)
    assert sanitize_for_pdf(once, unicode_font=True) == once


def test_unsupported_characters_reports_what_would_be_lost():
    assert unsupported_characters("ok → cyrillic", unicode_font=True) == set()
    assert "П" in unsupported_characters("Привет", unicode_font=False)
    assert unsupported_characters("Привет", unicode_font=True) == set()


def test_every_replacement_target_is_ascii():
    """A replacement that itself needed a font would be pointless."""

    for replacement in REPLACEMENTS.values():
        replacement.encode("ascii")
