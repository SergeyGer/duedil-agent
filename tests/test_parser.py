import io
import sys
import types
from pathlib import Path

from reportlab.pdfgen import canvas

from app.parser import parse_pdf_to_markdown
from app.utils import find_team_mentions


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


# --- the bundled example decks ------------------------------------------------
# These guard the files in examples/: they are generated artefacts, so a change to
# the generator (or a stray binary rewrite) must not silently produce a deck the
# pipeline cannot read.
EXAMPLE_DECKS = [
    "airbnb_deck.pdf",
    "uber_deck.pdf",
    "cursor_deck.pdf",
    "lovable_deck.pdf",
    "cognition_deck.pdf",
]


def test_example_decks_exist_and_parse():
    examples = Path(__file__).resolve().parents[1] / "examples"
    for name in EXAMPLE_DECKS:
        path = examples / name
        assert path.exists(), f"{name} is missing from examples/"
        text = parse_pdf_to_markdown(path)
        assert len(text) > 1200, f"{name} extracted only {len(text)} characters"
        # Deliberately not asserting on Markdown syntax: with LlamaParse configured the
        # parser returns `#` headings, while the pypdf fallback (what CI uses, since LLAMA
        # keys are absent there) returns plain text. Both are correct, so the check is that
        # the deck's sections survived the round trip.
        for section in ("Problem", "Solution", "Traction", "Team", "Business model", "Sources"):
            assert section in text, f"{name} lost its '{section}' section"


def test_example_decks_carry_their_own_provenance():
    examples = Path(__file__).resolve().parents[1] / "examples"
    for name in EXAMPLE_DECKS:
        text = parse_pdf_to_markdown(examples / name).lower()
        # Each deck states that it is a reconstruction and lists where the facts came from.
        assert "reconstructed" in text, f"{name} does not say it is reconstructed"
        assert "sources" in text, f"{name} has no sources section"


def test_example_decks_feed_the_number_parser():
    """The decks are written to give the pipeline real, parseable input."""

    examples = Path(__file__).resolve().parents[1] / "examples"
    airbnb = parse_pdf_to_markdown(examples / "airbnb_deck.pdf")
    # `About 40 people` in the deck must survive into a number the heuristics can use.
    assert 40 in find_team_mentions(airbnb)
    # And the deliberate gap must be visible as an unresolved metric.
    assert "[NOT_FOUND]" in parse_pdf_to_markdown(examples / "cognition_deck.pdf")
