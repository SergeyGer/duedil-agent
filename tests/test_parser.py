import io
import sys
import types

from reportlab.pdfgen import canvas

from app.parser import parse_pdf_to_markdown


def _make_pdf(text: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, text)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def test_parser_falls_back_to_pypdf_without_llamaparse(monkeypatch):
    monkeypatch.delenv("LLAMA_CLOUD_API_KEY", raising=False)
    pdf_bytes = _make_pdf("Acme AI raised ARR of 1.2M")
    text = parse_pdf_to_markdown(pdf_bytes)
    assert "Acme AI" in text


def test_parser_uses_llamaparse_when_configured(monkeypatch, tmp_path):
    deck = tmp_path / "deck.pdf"
    deck.write_bytes(b"%PDF-1.4")

    class _Doc:
        def __init__(self, text):
            self.text = text

    class _FakeLlamaParse:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def load_data(self, _path):
            return [_Doc("# Deck title"), _Doc("body")]

    fake = types.ModuleType("llama_parse")
    fake.LlamaParse = _FakeLlamaParse
    monkeypatch.setitem(sys.modules, "llama_parse", fake)
    monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "llx-test")

    text = parse_pdf_to_markdown(str(deck))
    assert "# Deck title" in text
    assert "body" in text


def test_parser_falls_back_when_llamaparse_errors(monkeypatch):
    class _BrokenLlamaParse:
        def __init__(self, **kwargs):
            pass

        def load_data(self, _path):
            raise RuntimeError("api down")

    fake = types.ModuleType("llama_parse")
    fake.LlamaParse = _BrokenLlamaParse
    monkeypatch.setitem(sys.modules, "llama_parse", fake)
    monkeypatch.setenv("LLAMA_CLOUD_API_KEY", "llx-test")

    text = parse_pdf_to_markdown(_make_pdf("Acme AI deck"))
    assert "Acme" in text
