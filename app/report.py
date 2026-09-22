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
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

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
    text = re.sub(r"`([^`]+)`", r"<font face='Courier'>\1</font>", text)
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
    data = [
        [Paragraph(_inline(cell), styles["body"]) for cell in row]
        + [Paragraph("", styles["body"])] * (width - len(row))
        for row in parsed
    ]
    table = Table(data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef7")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b8c4d9")),
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
            fontSize=20,
            leading=24,
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor("#12355b"),
        ),
        "h2": ParagraphStyle(
            "DDh2",
            parent=base["Heading2"],
            fontSize=15,
            leading=19,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor("#1a4d8f"),
        ),
        "h3": ParagraphStyle(
            "DDh3",
            parent=base["Heading3"],
            fontSize=12.5,
            leading=16,
            spaceBefore=10,
            spaceAfter=4,
            textColor=colors.HexColor("#333333"),
        ),
        "body": ParagraphStyle(
            "DDbody",
            parent=base["BodyText"],
            fontSize=10.5,
            leading=15,
            spaceAfter=6,
        ),
        "quote": ParagraphStyle(
            "DDquote",
            parent=base["BodyText"],
            fontSize=10.5,
            leading=15,
            leftIndent=14,
            textColor=colors.HexColor("#555555"),
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
# Public API
# ---------------------------------------------------------------------------
def markdown_to_pdf_bytes(markdown_text: str, title: str = "DueDil.Agent — Deal Memo") -> bytes:
    """Render a Markdown memo to PDF and return the raw bytes."""

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=title,
        author="DueDil.Agent",
    )
    styles = _styles()
    story = _flowables(markdown_text, styles)
    story.append(Spacer(1, 14))
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"<i>Generated by DueDil.Agent on {stamp}</i>", styles["quote"]))
    document.build(story)
    return buffer.getvalue()


def markdown_to_pdf(
    markdown_text: str, output_path: str, title: str = "DueDil.Agent — Deal Memo"
) -> str:
    """Render a Markdown memo to a PDF file at ``output_path``."""

    data = markdown_to_pdf_bytes(markdown_text, title=title)
    with open(output_path, "wb") as handle:
        handle.write(data)
    return output_path


__all__ = ["markdown_to_pdf", "markdown_to_pdf_bytes"]
