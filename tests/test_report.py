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
