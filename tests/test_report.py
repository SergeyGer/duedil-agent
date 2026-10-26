from app.report import markdown_to_pdf, markdown_to_pdf_bytes

SAMPLE = """# Investment Memo — Acme AI

## 1. Executive Summary
Acme is a **strong** candidate with `ARR` growth.

## 2. Startup Metrics
- ARR: $1.2M
- Team: 10
1. First
2. Second

## 3. Table
| Metric | Value |
|--------|-------|
| ARR | $1.2M |
| ARR/employee | $120k |

> This is a quote.

---
"""


def test_markdown_to_pdf_bytes():
    data = markdown_to_pdf_bytes(SAMPLE)
    assert data.startswith(b"%PDF")
    assert len(data) > 1000


def test_markdown_to_pdf_file(tmp_path):
    out = tmp_path / "memo.pdf"
    markdown_to_pdf(SAMPLE, str(out))
    assert out.exists()
    assert out.read_bytes().startswith(b"%PDF")


def test_pdf_contains_no_unrenderable_glyphs(tmp_path):
    """Regression: a memo with arrows, emoji and Cyrillic used to produce black boxes."""

    from app.fonts import register_pdf_fonts
    from app.parser import parse_pdf_to_markdown
    from app.textsafe import sanitize_for_pdf, unsupported_characters

    memo = (
        "# Investment Memo — Пример\n\n"
        "## 1. Executive Summary\n\n"
        "Growth 300% → 400% ✅ with ARR ≈ $1.2M 🚀 and team ≥ 14.\n"
        "Привет — это проверка кириллицы.\n\n"
        "| Metric | Value |\n|---|---|\n| ARR | $1.2M → $4M |\n"
    )
    unicode_fonts = register_pdf_fonts()[3]

    path = tmp_path / "memo.pdf"
    markdown_to_pdf(memo, str(path), model="gpt-4o (OpenAI)")
    extracted = parse_pdf_to_markdown(path)

    assert "->" in extracted, "the arrow must be replaced by its plain equivalent"
    assert "🚀" not in extracted, "emoji must not reach the PDF"
    assert unsupported_characters(extracted, unicode_font=unicode_fonts) == set(), (
        "every character left in the PDF must be renderable by the font in use"
    )
    assert sanitize_for_pdf(extracted, unicode_font=unicode_fonts) == extracted

    if unicode_fonts:
        assert "Привет" in extracted, "a Unicode font must keep Cyrillic readable"


def test_the_report_opens_with_a_cover_page(tmp_path):
    """A memo is a document for a partner: it opens with its own cover, not with section 1."""

    from app.parser import parse_pdf_to_markdown

    path = tmp_path / "report.pdf"
    markdown_to_pdf(
        SAMPLE,
        str(path),
        model="gpt-4o (OpenAI)",
        company="Acme AI",
        recommendation="DEEP AUDIT",
        facts=[("ARR", "$1.2M"), ("Team size", "10")],
    )
    text = parse_pdf_to_markdown(path)

    assert "INVESTMENT DUE DILIGENCE REPORT" in text
    assert "Acme AI" in text
    assert "DEEP AUDIT" in text
    assert "CONTENTS" in text
    assert "1. Executive Summary" in text
    assert "Prepared by DueDil" in text
    # The memo's own H1 is not repeated on the content page: the cover carries the title.
    assert text.count("Investment Memo") <= 1


def test_page_numbers_and_running_header_are_present(tmp_path):
    from app.parser import parse_pdf_to_markdown

    path = tmp_path / "report.pdf"
    markdown_to_pdf(SAMPLE, str(path), company="Acme AI")
    text = parse_pdf_to_markdown(path)

    assert "Due diligence - Acme AI" in text
    assert "Page 1" in text
    assert "confidential" in text
