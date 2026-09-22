import pytest

from app.utils import (
    compute_financials,
    find_team_mentions,
    find_traffic_mentions,
    is_missing,
    parse_count,
    parse_money,
    parse_number,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("$1.2M", 1_200_000),
        ("1,200,000", 1_200_000),
        ("$10 million", 10_000_000),
        ("$2.5B", 2_500_000_000),
        ("500k", 500_000),
        ("50 employees", 50),
        (42, 42.0),
        ("[NOT_FOUND]", None),
        ("N/A", None),
        ("", None),
        (None, None),
        ("no numbers here", None),
    ],
)
def test_parse_number(raw, expected):
    assert parse_number(raw) == expected


def test_parse_money_and_count():
    assert parse_money("$1.5M") == 1_500_000
    assert parse_count("42") == 42
    assert parse_count("[NOT_FOUND]") is None


def test_is_missing():
    assert is_missing("[NOT_FOUND]") is True
    assert is_missing("") is True
    assert is_missing("Acme") is False


def test_financials_above_benchmark():
    result = compute_financials({"arr": "$1.2M", "team_size": "10"})
    assert result["status"] == "above"
    assert result["arr_per_employee"] == pytest.approx(120_000)


def test_financials_below_benchmark():
    result = compute_financials({"arr": "$500k", "team_size": "10"})
    assert result["status"] == "below"
    assert result["arr_per_employee"] == pytest.approx(50_000)


def test_financials_missing_arr():
    result = compute_financials({"arr": "[NOT_FOUND]", "team_size": "10"})
    assert result["status"] == "unknown"
    assert "ARR" in result["verdict"]


def test_financials_missing_team():
    result = compute_financials({"arr": "$1M", "team_size": "[NOT_FOUND]"})
    assert result["status"] == "unknown"
    assert "team size" in result["verdict"].lower()


def test_find_team_mentions():
    assert find_team_mentions("LinkedIn shows 2 employees") == [2]
    assert 1000 in find_team_mentions("scale-up with 1k employees")
    assert find_team_mentions("no headcount here") == []


def test_find_traffic_mentions():
    assert find_traffic_mentions("about 1,500 monthly visits") == [1500]
    assert find_traffic_mentions("12k visits per month") == [12000]
    assert find_traffic_mentions("traffic unknown") == []
