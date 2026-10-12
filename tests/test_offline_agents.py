"""Tests for the rule-based offline agents used by the hosted demo.

The demo must not answer the same thing for every deck (that was the bug), and it must
not invent figures either — anything the deck does not state has to come back as
``[NOT_FOUND]``.
"""

from pathlib import Path

from app.offline_agents import NOT_FOUND, extract_company_name, extract_metrics, format_amount
from app.parser import parse_pdf_to_markdown

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
DECKS = [
    "airbnb_deck.pdf",
    "uber_deck.pdf",
    "cursor_deck.pdf",
    "lovable_deck.pdf",
    "cognition_deck.pdf",
]


def _metrics(name: str) -> dict:
    return extract_metrics(parse_pdf_to_markdown(EXAMPLES / name), "https://example.com")


def test_format_amount_reads_like_a_deck():
    assert format_amount(500_000_000) == "$500M"
    assert format_amount(1_200_000) == "$1.2M"
    assert format_amount(400_000) == "$400K"
    assert format_amount(250) == "$250"


def test_company_name_comes_from_the_deck_title():
    # With LlamaParse the title is a Markdown heading; the pypdf fallback (what a
    # deployment without LLAMA_CLOUD_API_KEY gets) returns it as plain text. Both must
    # work — supporting only the heading was the bug that made every hosted run say
    # "Unknown Startup".
    assert extract_company_name("# **Airbnb — Series B (2011), reconstructed**") == "Airbnb"
    assert extract_company_name("# **Cognition AI — reconstructed case study**") == "Cognition AI"
    assert extract_company_name("Lovable — reconstructed case study\nbody text") == "Lovable"
    assert extract_company_name("\n\nUber — Series B era (2011)\n") == "Uber"


def test_company_name_falls_back_only_when_there_is_nothing_to_read():
    assert extract_company_name("") == "Unknown Startup"
    assert extract_company_name("   \n  \n") == "Unknown Startup"


def test_every_example_deck_yields_its_own_company():
    names = [_metrics(name)["company_name"] for name in DECKS]
    assert names == ["Airbnb", "Uber", "Cursor", "Lovable", "Cognition AI"]


def test_the_decks_no_longer_produce_identical_metrics():
    """The regression this module exists for: five decks, five different readings.

    Compared on the fields the decks actually vary in. ``mrr``/``tam`` and the website are
    excluded on purpose: no deck states them, so they are expected to be identical.
    """

    def fingerprint(name: str) -> tuple:
        metrics = _metrics(name)
        return tuple(
            str(metrics.get(key))
            for key in ("company_name", "arr", "team_size", "founded_year", "sector", "founders")
        )

    prints = [fingerprint(name) for name in DECKS]
    assert len(set(prints)) == len(DECKS), f"decks produced identical readings: {prints}"


def test_headcount_is_read_where_the_deck_states_it():
    assert _metrics("cursor_deck.pdf")["team_size"] == "300"
    assert _metrics("lovable_deck.pdf")["team_size"] == "146"
    assert _metrics("cognition_deck.pdf")["team_size"] == "15"
    assert _metrics("airbnb_deck.pdf")["team_size"] == "40"


def test_figures_the_deck_does_not_state_are_reported_as_missing():
    # The Cognition deck publishes no ARR and says so; the two 2011 decks predate ARR.
    for name in ("cognition_deck.pdf", "airbnb_deck.pdf", "uber_deck.pdf"):
        metrics = _metrics(name)
        assert metrics["arr"] == NOT_FOUND, f"{name} invented an ARR"
        assert metrics["mrr"] == NOT_FOUND, f"{name} invented an MRR"


def test_arr_is_read_next_to_its_label():
    # "Reported ARR passed $100M" — the figure nearest the label wins.
    assert _metrics("cursor_deck.pdf")["arr"] == "$100M"


def test_founders_are_names_not_sentences():
    assert _metrics("lovable_deck.pdf")["founders"] == ["Anton Osika"]
    assert _metrics("cognition_deck.pdf")["founders"] == ["Scott Wu"]
    assert "Brian Chesky" in _metrics("airbnb_deck.pdf")["founders"]


def test_the_website_argument_fills_the_gap():
    assert _metrics("cursor_deck.pdf")["website"] == "https://example.com"


def test_founders_are_read_in_both_parser_modes():
    """The label and its value may share a line or be split across lines.

    LlamaParse emits `**Team** Brian Chesky (CEO), …`; the pypdf fallback used by a
    deployment without `LLAMA_CLOUD_API_KEY` emits `**Team**` as its own paragraph, so the
    value starts on the next line. Both were seen in CI and in the container.
    """

    same_line = "## **Team**\nBrian Chesky (CEO), Joe Gebbia (CPO)\n\n## **Funding**\n"
    next_line = "## **Team**\n\nBrian Chesky (CEO), Joe Gebbia (CPO)\n\n## **Funding**\n"
    separated = "## **Team**\n\nBrian Chesky — CEO, Joe Gebbia — CPO\n\n"
    for text in (same_line, next_line, separated):
        assert extract_metrics(text)["founders"][:2] == ["Brian Chesky", "Joe Gebbia"], text


def test_role_notes_are_not_part_of_the_name():
    metrics = extract_metrics("## **Team**\n\nTravis Kalanick (CEO), Garrett Camp (chairman)\n")
    assert metrics["founders"] == ["Travis Kalanick", "Garrett Camp"]
