"""Register a Unicode font for the PDF renderer.

ReportLab ships only Type-1 fonts (Helvetica and friends), which encode cp1252 and draw every
other character as a black box. A memo that quotes a founder's name in Cyrillic, or any of the
typographic characters a model likes to use, therefore needs a real Unicode font.

The font is taken from the system — DejaVu Sans is present on Debian/Ubuntu (the container
installs ``fonts-dejavu-core``), on GitHub's runners and on most desktops — with
``DUEDIL_PDF_FONT`` as an explicit override. When nothing is found the renderer falls back to
Helvetica and :mod:`app.textsafe` drops what the font cannot draw, so the output is never tofu.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

#: Where a DejaVu-style font usually lives. The first match wins.
CANDIDATES: tuple[tuple[str, str], ...] = (
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    (
        "/usr/local/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ),
    ("/Library/Fonts/Arial Unicode.ttf", "/Library/Fonts/Arial Unicode.ttf"),
    (
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ),
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
)

#: Monospace candidates, used for inline code spans.
MONO_CANDIDATES: tuple[str, ...] = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    "/usr/local/share/fonts/dejavu/DejaVuSansMono.ttf",
    "/Library/Fonts/Courier New.ttf",
    "C:/Windows/Fonts/consola.ttf",
)

BODY_FONT = "DuedilSans"
BOLD_FONT = "DuedilSans-Bold"
MONO_FONT = "DuedilMono"


def _from_font_dir(directory: str) -> tuple[str, str] | None:
    """Return ``(regular, bold)`` from ``DUEDIL_PDF_FONT``: either a file or a directory."""

    path = Path(directory).expanduser()
    if path.is_file():
        sibling = path.with_name(path.stem.replace("-Regular", "") + "-Bold" + path.suffix)
        return str(path), str(sibling) if sibling.is_file() else str(path)
    if path.is_dir():
        for name in ("DejaVuSans.ttf", "NotoSans-Regular.ttf", "Arial.ttf"):
            regular = path / name
            if regular.is_file():
                bold = regular.with_name(regular.stem + "-Bold" + regular.suffix)
                if not bold.is_file():
                    bold = regular.with_name(regular.stem + "bd" + regular.suffix)
                return str(regular), str(bold if bold.is_file() else regular)
    return None


def _font_pair() -> tuple[str, str] | None:
    override = (os.getenv("DUEDIL_PDF_FONT") or "").strip()
    if override:
        pair = _from_font_dir(override)
        if pair:
            return pair
    for regular, bold in CANDIDATES:
        if Path(regular).is_file():
            return regular, bold if Path(bold).is_file() else regular
    return None


@lru_cache(maxsize=1)
def register_pdf_fonts() -> tuple[str, str, str, bool]:
    """Register the fonts once and return ``(body, bold, mono, unicode_ok)``.

    ``unicode_ok`` is ``False`` when only the built-in fonts are available; the caller then has
    to strip what they cannot encode.
    """

    pair = _font_pair()
    if pair is None:
        return "Helvetica", "Helvetica-Bold", "Courier", False

    regular, bold = pair
    try:
        pdfmetrics.registerFont(TTFont(BODY_FONT, regular))
        pdfmetrics.registerFont(TTFont(BOLD_FONT, bold))
        mono = "Courier"
        for candidate in MONO_CANDIDATES:
            if Path(candidate).is_file():
                pdfmetrics.registerFont(TTFont(MONO_FONT, candidate))
                mono = MONO_FONT
                break
    except Exception:  # pragma: no cover - a broken font file must not break exports
        return "Helvetica", "Helvetica-Bold", "Courier", False

    return BODY_FONT, BOLD_FONT, mono, True


__all__ = ["CANDIDATES", "MONO_CANDIDATES", "register_pdf_fonts"]
