#!/usr/bin/env python3
"""Generate a small synthetic pitch-deck PDF for testing DueDil.Agent.

No network access and no API keys required. By default it writes
``data/sample_deck.pdf``.

Usage::

    python scripts/make_sample_deck.py [OUTPUT_PATH]
"""

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

DEFAULT_OUTPUT = "data/sample_deck.pdf"

# (kind, text) — kind is one of: title, subtitle, h (heading), p (paragraph)
DECK: list[tuple[str, str]] = [
    ("title", "NimbusAI - Seed Pitch Deck"),
    ("subtitle", "Sector: B2B SaaS (AI customer-support automation)"),
    ("h", "Problem"),
    ("p", "Enterprise support teams drown in tickets; about 40% are repetitive."),
    ("h", "Solution"),
    ("p", "NimbusAI is an AI copilot that resolves tier-1 support tickets automatically."),
    ("h", "Market"),
    ("p", "TAM: $14B - SAM: $3.2B."),
    ("h", "Traction"),
    ("p", "ARR: $1.2M"),
    ("p", "MRR: $100K"),
    ("p", "Customers: 180 B2B accounts (net revenue retention 128%, 18% MoM growth)."),
    ("h", "Team"),
    ("p", "Team size: 14 employees."),
    ("p", "Founders: Jane Doe (CEO, ex-Zendesk) and Ivan Petrov (CTO, ex-Google)."),
    ("p", "Hiring plan: +10 engineers within 12 months."),
    ("h", "Business model"),
    ("p", "Subscription SaaS, annual contracts, average ACV $6,700."),
    ("h", "Claims"),
    ("p", "We are the market leader in AI support automation."),
    ("p", "Website: https://nimbusai.example"),
]

_STYLES = {
    "title": ("Helvetica-Bold", 20, 26, 0),
    "subtitle": ("Helvetica-Oblique", 12, 6, 0),
    "h": ("Helvetica-Bold", 14, 22, 0),
    "p": ("Helvetica", 11, 4, 0),
}


def build(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output), pagesize=A4)
    _, height = A4
    y = height - 3 * cm

    for kind, text in DECK:
        font, size, before, _ = _STYLES[kind]
        pdf.setFont(font, size)
        y -= before
        pdf.drawString(2.5 * cm, y, text)
        y -= 18
        if y < 2 * cm:  # start a new page when running out of room
            pdf.showPage()
            y = height - 3 * cm

    pdf.showPage()
    pdf.save()


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT)
    build(out)
    print(f"Wrote sample deck: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
