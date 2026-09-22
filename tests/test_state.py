from app.state import initial_state


def test_initial_state_defaults():
    state = initial_state("deck text", "https://acme.ai")
    assert state["pitch_deck_raw"] == "deck text"
    assert state["website_url"] == "https://acme.ai"
    assert state["extracted_metrics"] == {}
    assert state["market_data"] == []
    assert state["financial_benchmarks"] == {}
    assert state["red_flags"] == []
    assert state["critic_loops_count"] == 0
    assert state["final_memo"] == ""
    assert state["progress_log"] == ["[init] run started"]


def test_initial_state_without_url():
    state = initial_state("deck")
    assert state["website_url"] == ""
