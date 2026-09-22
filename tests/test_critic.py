from app.graph import MAX_CRITIC_LOOPS, _deterministic_flags, route_after_critic


def test_route_clean_goes_to_supervisor():
    assert route_after_critic({"red_flags": [], "critic_loops_count": 1}) == "agent_supervisor"


def test_route_with_flags_loops_back():
    assert route_after_critic({"red_flags": ["x"], "critic_loops_count": 1}) == "agent_scraper"


def test_route_stops_at_max_loops():
    state = {"red_flags": ["x"], "critic_loops_count": MAX_CRITIC_LOOPS}
    assert route_after_critic(state) == "agent_supervisor"


def test_deterministic_team_mismatch():
    state = {
        "extracted_metrics": {"team_size": "50", "arr": "$1M"},
        "market_data": ["LinkedIn shows only 2 employees at the company"],
    }
    flags = _deterministic_flags(state)
    assert any("Team-size mismatch" in flag for flag in flags)


def test_deterministic_leadership_vs_traffic():
    state = {
        "extracted_metrics": {"claimed_leadership": "We are the market leader", "arr": "$1M"},
        "market_data": ["Estimated monthly visits: 300"],
    }
    flags = _deterministic_flags(state)
    assert any("leadership" in flag.lower() for flag in flags)


def test_deterministic_missing_arr():
    flags = _deterministic_flags({"extracted_metrics": {"arr": "[NOT_FOUND]"}, "market_data": []})
    assert any("Missing ARR" in flag for flag in flags)


def test_deterministic_clean_state_has_no_flags():
    state = {
        "extracted_metrics": {"arr": "$1.2M", "team_size": "10", "claimed_leadership": ""},
        "market_data": ["company HQ in Berlin"],
    }
    assert _deterministic_flags(state) == []
