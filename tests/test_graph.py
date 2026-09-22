import json

from langchain_core.language_models.fake_chat_models import FakeListChatModel

import app.graph as graph_mod

EXTRACT = json.dumps(
    {
        "company_name": "Acme AI",
        "sector": "B2B SaaS",
        "arr": "$1.2M",
        "team_size": "10",
        "tam": "$10B",
        "claimed_leadership": "",
        "key_claims": [],
        "founders": ["Jane Doe"],
    }
)

CLEAN = json.dumps({"red_flags": [], "critic_feedback": ""})
FLAGGED = json.dumps(
    {
        "red_flags": ["Claimed leadership but traffic is near zero."],
        "critic_feedback": "Check LinkedIn headcount for Acme AI",
    }
)
MEMO = "# Investment Memo — Acme AI\n\n## 1. Executive Summary\nAcme looks solid."


def _install(monkeypatch, responses):
    fake = FakeListChatModel(responses=list(responses))
    monkeypatch.setattr(graph_mod, "get_llm", lambda *a, **k: fake)
    monkeypatch.setattr(graph_mod, "get_search_tool", lambda *a, **k: None)
    return fake


def test_graph_clean_path(monkeypatch):
    _install(monkeypatch, [EXTRACT, CLEAN, MEMO])
    app = graph_mod.build_graph()

    result = app.invoke({"pitch_deck_raw": "Acme AI pitch deck", "website_url": "https://acme.ai"})

    assert result["extracted_metrics"]["company_name"] == "Acme AI"
    assert result["critic_loops_count"] == 1
    assert result["red_flags"] == []
    assert result["financial_benchmarks"]["status"] == "above"
    assert result["final_memo"].startswith("# Investment Memo")
    # all five nodes reported into the shared progress log (no loop triggered)
    log = " ".join(result["progress_log"])
    for marker in ("[extractor]", "[scraper]", "[financial]", "[critic]", "[supervisor]"):
        assert marker in log
    assert "[critic] pass 1" in log  # critic ran exactly once


def test_graph_loop_is_capped(monkeypatch):
    _install(monkeypatch, [EXTRACT, FLAGGED, FLAGGED, MEMO])
    app = graph_mod.build_graph()

    result = app.invoke({"pitch_deck_raw": "Acme AI pitch deck"})

    assert result["critic_loops_count"] == graph_mod.MAX_CRITIC_LOOPS
    assert any("Claimed leadership" in flag for flag in result["red_flags"])
    assert result["final_memo"].startswith("# Investment Memo")


def test_route_function_used_by_graph():
    assert (
        graph_mod.route_after_critic({"red_flags": [], "critic_loops_count": 0})
        == "agent_supervisor"
    )


def test_safe_json_variants():
    assert graph_mod._safe_json({"a": 1}) == {"a": 1}
    assert graph_mod._safe_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert graph_mod._safe_json('prefix {"a": 1} suffix') == {"a": 1}
    assert graph_mod._safe_json("not json") == {}
    assert graph_mod._safe_json("[1, 2]") == {}


def test_graph_survives_llm_failure(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise RuntimeError("no api key")

    monkeypatch.setattr(graph_mod, "get_llm", _boom)
    monkeypatch.setattr(graph_mod, "get_search_tool", lambda *a, **k: None)

    app = graph_mod.build_graph()
    result = app.invoke({"pitch_deck_raw": "deck", "website_url": ""})

    # Missing ARR becomes a red flag, the loop runs, and a fallback memo is produced.
    assert result["final_memo"].startswith("# Investment Memo")
    assert result["critic_loops_count"] >= 1
    assert result["financial_benchmarks"]["status"] == "unknown"
