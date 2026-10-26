"""Markdown -> PDF rendering of the final deal memo (ReportLab).

A small, dependency-light Markdown parser that understands headings, bullet and
numbered lists, tables, blockquotes, horizontal rules and inline
bold/italic/code/links -- enough to render an investment memo cleanly.
"""

from __future__ import annotations

import io
import re
from datetime import UTC, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.fonts import register_pdf_fonts
from app.textsafe import sanitize_for_pdf

_BODY_FONT, _BOLD_FONT, _MONO_FONT, _UNICODE_FONTS = register_pdf_fonts()

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
_ORDERED_RE = re.compile(r"^\s*\d+[.)]\s+(.*)$")


# ---------------------------------------------------------------------------
# Inline formatting
# ---------------------------------------------------------------------------
def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text: str) -> str:
    """Convert inline Markdown into ReportLab's mini-HTML."""

    text = _escape(text)
    # Code spans first so their content is not re-processed.
    text = re.sub(r"`([^`]+)`", rf"<font face='{_MONO_FONT}'>\1</font>", text)
    # Links.
    text = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        r'<link href="\2"><font color="#1a73e8">\1</font></link>',
        text,
    )
    # Bold then italic (order matters).
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__([^_]+)__", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    return text


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------
def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def _is_separator(line: str) -> bool:
    body = line.replace("|", " ").replace(":", " ").strip()
    return bool(body) and set(body) <= {"-", " "} and "-" in line


def _build_table(rows: list[str], styles: dict) -> Table:
    parsed = [_split_row(row) for row in rows if not _is_separator(row)]
    if not parsed:
        return Spacer(1, 0)
    width = max(len(row) for row in parsed)
    data = []
    for index, row in enumerate(parsed):
        cells = [
            Paragraph(_inline(cell), styles["table_head" if index == 0 else "body"]) for cell in row
        ]
        data.append(cells + [Paragraph("", styles["body"])] * (width - len(row)))
    table = Table(data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#12355b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fb")]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d8e0ea")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


# ---------------------------------------------------------------------------
# Styles + flowables
# ---------------------------------------------------------------------------
def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle(
            "DDh1",
            parent=base["Heading1"],
            fontName=_BOLD_FONT,
            fontSize=20,
            leading=24,
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor("#12355b"),
        ),
        "h2": ParagraphStyle(
            "DDh2",
            parent=base["Heading2"],
            fontName=_BOLD_FONT,
            fontSize=15,
            leading=19,
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True,
            textColor=colors.HexColor("#1a4d8f"),
        ),
        "h3": ParagraphStyle(
            "DDh3",
            parent=base["Heading3"],
            fontName=_BOLD_FONT,
            fontSize=12.5,
            leading=16,
            spaceBefore=10,
            spaceAfter=4,
            textColor=colors.HexColor("#333333"),
        ),
        "body": ParagraphStyle(
            "DDbody",
            parent=base["BodyText"],
            fontName=_BODY_FONT,
            fontSize=10.5,
            leading=15,
            spaceAfter=6,
        ),
        "quote": ParagraphStyle(
            "DDquote",
            parent=base["BodyText"],
            fontName=_BODY_FONT,
            fontSize=10.5,
            leading=15,
            leftIndent=12,
            borderColor=colors.HexColor("#1a4d8f"),
            borderWidth=0.9,
            borderPadding=7,
            backColor=colors.HexColor("#f2f5fa"),
            textColor=colors.HexColor("#33404f"),
        ),
        "table_head": ParagraphStyle(
            "DDthead",
            parent=base["BodyText"],
            fontName=_BOLD_FONT,
            fontSize=9.5,
            leading=13,
            textColor=colors.white,
        ),
    }


def _is_block_start(line: str) -> bool:
    return bool(
        _HEADING_RE.match(line)
        or _BULLET_RE.match(line)
        or _ORDERED_RE.match(line)
        or line.startswith("|")
        or line.startswith(">")
        or line in {"---", "***", "___"}
    )


def _flowables(markdown_text: str, styles: dict) -> list:
    lines = (markdown_text or "").splitlines()
    story: list = []
    i, n = 0, len(lines)

    while i < n:
        stripped = lines[i].strip()

        if not stripped:
            i += 1
            continue

        if stripped in {"---", "***", "___"}:
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
            i += 1
            continue

        heading = _HEADING_RE.match(stripped)
        if heading:
            level = len(heading.group(1))
            style = styles["h1"] if level == 1 else styles["h2"] if level == 2 else styles["h3"]
            story.append(Paragraph(_inline(heading.group(2).strip()), style))
            i += 1
            continue

        if stripped.startswith(">"):
            story.append(Paragraph(_inline(stripped.lstrip(">").strip()), styles["quote"]))
            i += 1
            continue

        if stripped.startswith("|"):
            table_lines = []
            while i < n and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            story.append(_build_table(table_lines, styles))
            story.append(Spacer(1, 6))
            continue

        bullet = _BULLET_RE.match(stripped)
        if bullet:
            items = []
            while i < n:
                match = _BULLET_RE.match(lines[i])
                if not match:
                    break
                items.append(ListItem(Paragraph(_inline(match.group(1)), styles["body"])))
                i += 1
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=16))
            story.append(Spacer(1, 6))
            continue

        ordered = _ORDERED_RE.match(stripped)
        if ordered:
            items = []
            while i < n:
                match = _ORDERED_RE.match(lines[i])
                if not match:
                    break
                items.append(ListItem(Paragraph(_inline(match.group(1)), styles["body"])))
                i += 1
            story.append(ListFlowable(items, bulletType="1", leftIndent=16))
            story.append(Spacer(1, 6))
            continue

        # Paragraph: consume consecutive plain lines.
        para = [stripped]
        i += 1
        while i < n and lines[i].strip() and not _is_block_start(lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        story.append(Paragraph(_inline(" ".join(para)), styles["body"]))

    return story


# ---------------------------------------------------------------------------
# Cover page + running header/footer
# ---------------------------------------------------------------------------
_DATE_FORMAT = "%d %B %Y"

_BADGE_COLORS = {
    "invest": colors.HexColor("#1f7a44"),
    "deep audit": colors.HexColor("#a86412"),
    "reject": colors.HexColor("#a3231c"),
}


def company_from_markdown(markdown_text: str) -> str:
    """Pull the company out of the memo's first heading (``# Investment Memo — X``)."""

    for line in (markdown_text or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("# "):
            continue
        text = stripped[2:].strip()
        for separator in ("—", "–", "-", ":"):
            if separator in text:
                candidate = text.split(separator, 1)[1].strip()
                if candidate:
                    return candidate
        return text
    return ""


def _strip_leading_heading(markdown_text: str) -> str:
    """Drop the first H1: the cover already carries the report's title."""

    lines = (markdown_text or "").splitlines()
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        if line.strip().startswith("# "):
            return "\n".join(lines[:index] + lines[index + 1 :]).lstrip("\n")
        break
    return markdown_text or ""


def sections_from_markdown(markdown_text: str) -> list[str]:
    """Return the level-2 headings, in order — the report's table of contents."""

    return [
        match.group(2).strip()
        for match in (
            _HEADING_RE.match(line.strip()) for line in (markdown_text or "").splitlines()
        )
        if match and len(match.group(1)) == 2
    ]


class _ReportContext:
    """Everything the cover and the running header need."""

    def __init__(
        self,
        *,
        title: str,
        company: str,
        recommendation: str,
        facts: list[tuple[str, str]],
        sections: list[str],
        model: str,
        stamp: str,
    ) -> None:
        self.title = title
        self.company = company or "Investment memo"
        self.recommendation = recommendation.strip()
        self.facts = facts[:4]
        self.sections = sections[:9]
        self.model = model
        self.stamp = stamp


def _draw_cover(canvas: pdf_canvas.Canvas, doc, context: _ReportContext) -> None:
    page_width, page_height = A4
    canvas.saveState()

    # Top band, with the report type and the company.
    band_height = page_height * 0.42
    canvas.setFillColor(colors.HexColor("#0b2545"))
    canvas.rect(0, page_height - band_height, page_width, band_height, stroke=0, fill=1)
    canvas.setFillColor(colors.HexColor("#2e6be6"))
    canvas.rect(0, page_height - band_height, page_width, 6, stroke=0, fill=1)

    canvas.setFillColor(colors.HexColor("#9db4d6"))
    canvas.setFont(_BOLD_FONT, 10)
    canvas.drawString(2 * cm, page_height - 2.6 * cm, "INVESTMENT DUE DILIGENCE REPORT")

    canvas.setFillColor(colors.white)
    size = 26 if len(context.company) <= 28 else 20
    canvas.setFont(_BOLD_FONT, size)
    canvas.drawString(2 * cm, page_height - 3.9 * cm, context.company[:60])

    canvas.setFillColor(colors.HexColor("#c9d8ee"))
    canvas.setFont(_BODY_FONT, 11)
    canvas.drawString(2 * cm, page_height - 4.7 * cm, context.stamp + "  |  Prepared by DueDil")

    # Recommendation badge.
    if context.recommendation:
        badge = context.recommendation.upper()
        colour = _BADGE_COLORS.get(context.recommendation.lower(), colors.HexColor("#44536b"))
        canvas.setFillColor(colour)
        width = max(canvas.stringWidth(badge, _BOLD_FONT, 12) + 28, 96)
        canvas.roundRect(
            2 * cm, page_height - band_height + 1.5 * cm, width, 0.95 * cm, 6, stroke=0, fill=1
        )
        canvas.setFillColor(colors.white)
        canvas.setFont(_BOLD_FONT, 12)
        canvas.drawCentredString(2 * cm + width / 2, page_height - band_height + 1.75 * cm, badge)

    # Key figures strip under the band.
    y = page_height - band_height - 2.2 * cm
    if context.facts:
        column_width = (page_width - 4 * cm) / len(context.facts)
        for index, (label, value) in enumerate(context.facts):
            x = 2 * cm + index * column_width
            canvas.setFillColor(colors.HexColor("#6b7a90"))
            canvas.setFont(_BODY_FONT, 9)
            canvas.drawString(x, y, label.upper()[:26])
            canvas.setFillColor(colors.HexColor("#18212e"))
            canvas.setFont(_BOLD_FONT, 15)
            canvas.drawString(x, y - 0.75 * cm, str(value)[:24])

    # Table of contents: a report announces what it contains.
    if context.sections:
        top = page_height - band_height - 5.6 * cm
        canvas.setFillColor(colors.HexColor("#6b7a90"))
        canvas.setFont(_BOLD_FONT, 9)
        canvas.drawString(2 * cm, top, "CONTENTS")
        canvas.setFillColor(colors.HexColor("#18212e"))
        canvas.setFont(_BODY_FONT, 10.5)
        y = top - 0.9 * cm
        for section in context.sections:
            canvas.drawString(2 * cm, y, section[:78])
            y -= 0.62 * cm

    # Footer of the cover.
    canvas.setStrokeColor(colors.HexColor("#d8e0ea"))
    canvas.setLineWidth(0.6)
    canvas.line(2 * cm, 3.0 * cm, page_width - 2 * cm, 3.0 * cm)
    canvas.setFillColor(colors.HexColor("#6b7a90"))
    canvas.setFont(_BODY_FONT, 8.5)
    canvas.drawString(
        2 * cm,
        2.4 * cm,
        f"Prepared {context.stamp}"
        + (f"  |  analysis produced with {context.model}" if context.model else ""),
    )
    canvas.drawString(
        2 * cm,
        1.9 * cm,
        "Automated first-pass screen. Verify every figure independently before an investment decision.",
    )
    canvas.restoreState()


def _draw_running_header_footer(canvas: pdf_canvas.Canvas, doc, context: _ReportContext) -> None:
    page_width, page_height = A4
    canvas.saveState()

    canvas.setFont(_BODY_FONT, 8.5)
    canvas.setFillColor(colors.HexColor("#6b7a90"))
    canvas.drawString(2 * cm, page_height - 1.5 * cm, f"Due diligence - {context.company}"[:90])
    canvas.drawRightString(page_width - 2 * cm, page_height - 1.5 * cm, context.stamp)
    canvas.setStrokeColor(colors.HexColor("#d8e0ea"))
    canvas.setLineWidth(0.6)
    canvas.line(2 * cm, page_height - 1.8 * cm, page_width - 2 * cm, page_height - 1.8 * cm)

    canvas.line(2 * cm, 1.9 * cm, page_width - 2 * cm, 1.9 * cm)
    canvas.drawString(2 * cm, 1.45 * cm, "DueDil - confidential")
    canvas.drawRightString(page_width - 2 * cm, 1.45 * cm, f"Page {doc.page - 1}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def markdown_to_pdf_bytes(
    markdown_text: str,
    title: str = "Investment Due Diligence Report",
    model: str = "",
    *,
    company: str = "",
    recommendation: str = "",
    facts: list[tuple[str, str]] | None = None,
    stamp: str | None = None,
) -> bytes:
    """Render a Markdown memo to a PDF report and return the raw bytes.

    The first page is a cover: report type, company, date, the recommendation and up to four
    key figures — the shape a reader expects from an investment memo. Every following page
    carries a running header and a page number.

    ``model`` is stamped into the footer: a report produced by an LLM has to say which model
    produced it, otherwise the reader cannot judge or reproduce the analysis.
    """

    clean = sanitize_for_pdf(markdown_text, unicode_font=_UNICODE_FONTS) if markdown_text else ""
    stamp_text = stamp or datetime.now(UTC).strftime(_DATE_FORMAT)

    context = _ReportContext(
        title=sanitize_for_pdf(title, unicode_font=_UNICODE_FONTS),
        company=sanitize_for_pdf(
            company or company_from_markdown(markdown_text), unicode_font=_UNICODE_FONTS
        ),
        recommendation=sanitize_for_pdf(recommendation, unicode_font=_UNICODE_FONTS),
        facts=[
            (
                sanitize_for_pdf(str(label), unicode_font=_UNICODE_FONTS),
                sanitize_for_pdf(str(value), unicode_font=_UNICODE_FONTS),
            )
            for label, value in (facts or [])
        ],
        sections=[
            sanitize_for_pdf(section, unicode_font=_UNICODE_FONTS)
            for section in sections_from_markdown(markdown_text)
        ],
        model=sanitize_for_pdf(model, unicode_font=_UNICODE_FONTS),
        stamp=sanitize_for_pdf(stamp_text, unicode_font=_UNICODE_FONTS),
    )

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.4 * cm,
        bottomMargin=2.2 * cm,
        title=context.title,
        author="DueDil.Agent",
    )

    styles = _styles()
    story = [PageBreak()] + _flowables(_strip_leading_heading(clean), styles)
    document.build(
        story,
        onFirstPage=lambda canv, doc: _draw_cover(canv, doc, context),
        onLaterPages=lambda canv, doc: _draw_running_header_footer(canv, doc, context),
    )
    return buffer.getvalue()


def markdown_to_pdf(
    markdown_text: str,
    output_path: str,
    title: str = "Investment Due Diligence Report",
    model: str = "",
    *,
    company: str = "",
    recommendation: str = "",
    facts: list[tuple[str, str]] | None = None,
    stamp: str | None = None,
) -> str:
    """Render a Markdown memo to a PDF report file at ``output_path``."""

    data = markdown_to_pdf_bytes(
        markdown_text,
        title=title,
        model=model,
        company=company,
        recommendation=recommendation,
        facts=facts,
        stamp=stamp,
    )
    with open(output_path, "wb") as handle:
        handle.write(data)
    return output_path


__all__ = [
    "company_from_markdown",
    "sections_from_markdown",
    "markdown_to_pdf",
    "markdown_to_pdf_bytes",
]
