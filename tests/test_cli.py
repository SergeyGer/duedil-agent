import pytest

import app.cli as cli_mod


class _FakeGraph:
    """Minimal stand-in for a compiled LangGraph app."""

    def __init__(self, updates):
        self._updates = updates

    def stream(self, state, stream_mode=None):  # noqa: ARG002 - signature parity
        yield from self._updates


def _fake_parser(*_args, **_kwargs):
    return "deck text"


def test_version_exits_with_zero():
    with pytest.raises(SystemExit) as exc:
        cli_mod.main(["--version"])
    assert exc.value.code == 0


def test_missing_deck_returns_2():
    assert cli_mod.main([]) == 2


def test_nonexistent_file_returns_2(tmp_path):
    assert cli_mod.main([str(tmp_path / "nope.pdf")]) == 2


def test_full_run_writes_all_outputs(tmp_path, monkeypatch):
    deck = tmp_path / "deck.pdf"
    deck.write_bytes(b"%PDF-1.4 fake")

    updates = [
        {"agent_extractor": {"extracted_metrics": {"company_name": "Acme AI"}}},
        {"agent_scraper": {"market_data": ["..."]}},
        {"agent_financial": {"financial_benchmarks": {"verdict": "Healthy"}}},
        {"agent_critic": {"red_flags": [], "critic_loops_count": 1}},
        {"agent_supervisor": {"final_memo": "# Memo\n\nHello world"}},
    ]

    monkeypatch.setattr(cli_mod, "parse_pdf_to_markdown", _fake_parser)
    monkeypatch.setattr(cli_mod, "build_graph", lambda: _FakeGraph(updates))

    out_pdf = tmp_path / "out" / "memo.pdf"
    out_md = tmp_path / "out" / "memo.md"
    out_json = tmp_path / "out" / "state.json"

    rc = cli_mod.main(
        [
            str(deck),
            "https://acme.ai",
            "--out",
            str(out_pdf),
            "--md",
            str(out_md),
            "--json",
            str(out_json),
        ]
    )

    assert rc == 0
    assert out_pdf.exists() and out_pdf.read_bytes().startswith(b"%PDF")
    assert "Hello world" in out_md.read_text(encoding="utf-8")
    assert "Acme AI" in out_json.read_text(encoding="utf-8")


def test_quiet_mode_prints_only_memo(tmp_path, monkeypatch, capsys):
    deck = tmp_path / "deck.pdf"
    deck.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(cli_mod, "parse_pdf_to_markdown", _fake_parser)
    monkeypatch.setattr(
        cli_mod, "build_graph", lambda: _FakeGraph([{"agent_supervisor": {"final_memo": "# Memo"}}])
    )

    rc = cli_mod.main([str(deck), "--quiet", "--out", str(tmp_path / "m.pdf")])

    assert rc == 0
    out = capsys.readouterr().out
    assert "# Memo" in out
    assert "DueDil.Agent" not in out
