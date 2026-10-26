"""Make text safe for the PDF renderer.

ReportLab's built-in fonts use ``WinAnsi`` (≈ cp1252) and draw anything outside it as a black
box — the "tofu" squares that make a memo look broken. Emoji and pictographs have the same
problem even with a broad Unicode font: no text font ships them.

So every string that reaches ReportLab goes through :func:`sanitize_for_pdf`, which

* maps typographic characters to their plain equivalents (``→`` → ``->``, ``≈`` → ``~`` …);
* removes emoji, pictographs and joiners, which no PDF text font can draw;
* when no Unicode font is available, drops anything cp1252 cannot encode.

The result is deterministic and testable: whatever the model writes, the PDF contains only
glyphs the chosen font can actually render.
"""

from __future__ import annotations

#: Typographic characters -> the plain equivalent a reader still understands.
REPLACEMENTS: dict[str, str] = {
    "\u2192": "->",
    "\u2190": "<-",
    "\u2194": "<->",
    "\u21d2": "=>",
    "\u21d0": "<=",
    "\u2248": "~",
    "\u2264": "<=",
    "\u2265": ">=",
    "\u2260": "!=",
    "\u00d7": "x",
    "\u2212": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": ",",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u2026": "...",
    "\u2022": "-",
    "\u00b7": "-",
    "\u25cf": "-",
    "\u25aa": "-",
    "\u00a0": " ",
    "\u202f": " ",
    "\u2009": " ",
    "\u200b": "",
    "\ufeff": "",
    "\u2713": "yes",
    "\u2714": "yes",
    "\u2705": "yes",
    "\u2717": "no",
    "\u2718": "no",
    "\u274c": "no",
    "\u26a0": "!",
    "\ufe0f": "",
}

#: Emoji and pictograph blocks. Not a complete Unicode table — the ranges that actually show up
#: in model output, plus the plumbing code points (joiners, variation selectors, keycaps).
_EMOJI_RANGES = (
    (0x1F000, 0x1FAFF),
    (0x1F1E6, 0x1F1FF),
    (0x2600, 0x26FF),
    (0x2700, 0x27BF),
    (0x2B00, 0x2BFF),
    (0x2190, 0x21FF),  # arrows are mapped above; any survivor is dropped
    (0xFE00, 0xFE0F),
    (0x20D0, 0x20FF),
    (0x200D, 0x200D),
)


def _is_emoji(code_point: int) -> bool:
    return any(low <= code_point <= high for low, high in _EMOJI_RANGES)


def _in_cp1252(char: str) -> bool:
    try:
        char.encode("cp1252")
    except UnicodeEncodeError:
        return False
    return True


def sanitize_for_pdf(text: str, *, unicode_font: bool) -> str:
    """Return ``text`` with only glyphs the PDF font can render.

    ``unicode_font`` says whether a font with Latin/Cyrillic/Greek coverage was registered; when
    it is false the renderer falls back to ReportLab's built-in fonts, which only encode cp1252.
    """

    out: list[str] = []
    for char in text or "":
        if char in REPLACEMENTS:
            out.append(REPLACEMENTS[char])
            continue
        if char in "\n\t":
            out.append(char)
            continue
        code_point = ord(char)
        if code_point < 32 or code_point == 0x7F:
            out.append(" ")
            continue
        if _is_emoji(code_point):
            continue
        if not unicode_font and not _in_cp1252(char):
            continue
        out.append(char)
    return "".join(out)


def unsupported_characters(text: str, *, unicode_font: bool) -> set[str]:
    """Return the characters that :func:`sanitize_for_pdf` would remove or replace.

    Used by the tests to prove that a document has no tofu left: after sanitising, this set must
    be empty for the sanitised text.
    """

    found: set[str] = set()
    for char in text or "":
        if char in "\n\t":
            continue
        if char in REPLACEMENTS or ord(char) < 32:
            continue
        if _is_emoji(ord(char)) or (not unicode_font and not _in_cp1252(char)):
            found.add(char)
    return found


__all__ = ["REPLACEMENTS", "sanitize_for_pdf", "unsupported_characters"]
