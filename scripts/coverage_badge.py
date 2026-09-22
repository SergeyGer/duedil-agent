#!/usr/bin/env python3
"""Generate a shields.io-style coverage badge from the ``.coverage`` data file.

Self-contained: no external services, no extra dependencies beyond ``coverage``
(installed with pytest-cov). Used by the CI workflow to keep a coverage badge
committed to the repository.

Usage::

    python scripts/coverage_badge.py [OUTPUT_PATH]
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

from coverage import Coverage

DEFAULT_OUTPUT = ".github/badges/coverage.svg"
LABEL = "coverage"


def _color(pct: float) -> str:
    if pct >= 90:
        return "#4c1"  # brightgreen
    if pct >= 80:
        return "#97ca00"  # green
    if pct >= 70:
        return "#dfb317"  # yellow
    if pct >= 60:
        return "#fe7d37"  # orange
    return "#e05d44"  # red


def _text_width(text: str) -> int:
    return 6 * len(text) + 10


def build_svg(pct: float) -> str:
    value = f"{pct:.0f}%"
    color = _color(pct)
    label_w = _text_width(LABEL)
    value_w = _text_width(value)
    total = label_w + value_w
    label_cx = label_w / 2
    value_cx = label_w + value_w / 2

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="20" '
        f'role="img" aria-label="{LABEL}: {value}">\n'
        f"  <title>{LABEL}: {value}</title>\n"
        '  <linearGradient id="s" x2="0" y2="100%">\n'
        '    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>\n'
        '    <stop offset="1" stop-opacity=".1"/>\n'
        "  </linearGradient>\n"
        f'  <clipPath id="r"><rect width="{total}" height="20" rx="3" fill="#fff"/></clipPath>\n'
        '  <g clip-path="url(#r)">\n'
        f'    <rect width="{label_w}" height="20" fill="#555"/>\n'
        f'    <rect x="{label_w}" width="{value_w}" height="20" fill="{color}"/>\n'
        f'    <rect width="{total}" height="20" fill="url(#s)"/>\n'
        "  </g>\n"
        '  <g fill="#fff" text-anchor="middle" '
        'font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">\n'
        f'    <text x="{label_cx:.0f}" y="15" fill="#010101" fill-opacity=".3">{LABEL}</text>\n'
        f'    <text x="{label_cx:.0f}" y="14">{LABEL}</text>\n'
        f'    <text x="{value_cx:.0f}" y="15" fill="#010101" fill-opacity=".3">{value}</text>\n'
        f'    <text x="{value_cx:.0f}" y="14">{value}</text>\n'
        "  </g>\n"
        "</svg>\n"
    )


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT)

    coverage = Coverage()
    coverage.load()
    sink = io.StringIO()
    total = coverage.report(file=sink, show_missing=False)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_svg(total), encoding="utf-8")
    print(f"Wrote {output} — coverage {total:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
