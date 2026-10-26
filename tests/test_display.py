"""Tests for the presentation layer (``app.display``).

The helpers are pure, so the UI's readability can be asserted without a browser.
"""

from app.display import (
    benchmark_rows,
    format_metric_value,
    format_money,
    format_ratio,
    metric_rows,
    state_summary,
    verdict_of,
)

METRICS = {
    "company_name": "NimbusAI",
    "sector": "B2B SaaS",
    "arr": "$1.2M",
    "team_size": "14",
    "founded_year": "[NOT_FOUND]",
    "founders": ["Jane Doe", "Ivan Petrov"],
    "key_claims": ["market leader"],
}

BENCHMARKS = {
    "arr": 1_200_000.0,
    "team_size": 14,
    "arr_per_employee": 85714.28571428571,
    "benchmark_arr_per_employee": 100_000,
    "ratio_to_benchmark": 0.8571428571428571,
    "status": "below",
    "verdict": "Weak: ARR/employee of $85,714 sits below the B2B SaaS benchmark of $100,000.",
}


def test_format_money_rounds_and_groups():
    assert format_money(1_200_000.0) == "$1,200,000"
    assert format_money(85_714.2857) == "$85,714"
    assert format_money(None) == "—"


def test_format_ratio_reads_as_a_comparison():
    assert format_ratio(0.8571428571) == "0.86× the benchmark"
    assert format_ratio(27.4) == "27.40× the benchmark"
    assert format_ratio(None) == "—"


def test_missing_metrics_are_labelled_not_blank():
    # A reader must be able to tell "the deck did not say" from "we did not parse it".
    assert format_metric_value("[NOT_FOUND]") == "— (not in the deck)"
    assert format_metric_value("n/a") == "— (not in the deck)"
    assert format_metric_value("") == "— (not in the deck)"
    assert format_metric_value(None) == "—"


def test_metric_value_formats_lists():
    assert format_metric_value(["Jane Doe", "Ivan Petrov"]) == "Jane Doe, Ivan Petrov"
    assert format_metric_value([]) == "—"


def test_metric_rows_follow_the_reading_order():
    labels = [row["metric"] for row in metric_rows(METRICS)]
    # The figures a reader looks for first come before the incidental ones.
    assert labels.index("Company") < labels.index("Sector") < labels.index("ARR")
    assert labels.index("ARR") < labels.index("Founders")
    # `key_claims` is rendered as prose elsewhere, so it is not a table row.
    assert "Key claims" not in labels


def test_metric_rows_put_the_website_last():
    rows = metric_rows({"website": "https://acme.example", "company_name": "Acme"})
    assert [row["metric"] for row in rows] == ["Company", "Website"]


def test_metric_rows_keep_unknown_keys():
    rows = metric_rows({"company_name": "Acme", "burn_rate": "$50K/mo"})
    assert {row["metric"] for row in rows} == {"Company", "Burn rate"}


def test_metric_rows_tolerate_empty_input():
    assert metric_rows(None) == []
    assert metric_rows({}) == []


def test_benchmark_rows_do_not_contain_the_verdict():
    # The verdict is a conclusion, not another input figure — it gets its own callout.
    labels = {row["metric"] for row in benchmark_rows(BENCHMARKS)}
    assert "Verdict" not in labels
    assert labels == {
        "ARR",
        "Team size",
        "ARR per employee",
        "Benchmark (B2B SaaS)",
        "Against the benchmark",
    }


def test_benchmark_rows_are_readable():
    rows = {row["metric"]: row["value"] for row in benchmark_rows(BENCHMARKS)}
    assert rows["ARR per employee"] == "$85,714"
    assert rows["Against the benchmark"] == "0.86× the benchmark"


def test_verdict_marker_follows_the_status():
    marker, verdict = verdict_of(BENCHMARKS)
    assert marker == "⚠️"
    assert verdict.startswith("Weak: ARR/employee")

    assert verdict_of({"status": "above", "verdict": "Healthy"})[0] == "✅"
    assert verdict_of({"status": "unknown", "verdict": "x"})[0] == "❔"


def test_verdict_explains_its_absence():
    _, verdict = verdict_of({})
    assert "did not contain enough data" in verdict


def test_state_summary_reports_the_model_and_the_work_done():
    rows = {
        row["metric"]: row["value"]
        for row in state_summary(
            {
                "extracted_metrics": {"company_name": "Acme"},
                "red_flags": ["a", "b", "c"],
                "critic_loops_count": 2,
                "used_model": "gpt-4o (OpenAI)",
            }
        )
    }
    assert rows["Red Flags found"] == "3"
    assert rows["Critic passes"] == "2 of 2"
    assert rows["Model used"] == "gpt-4o (OpenAI)"


def test_state_summary_says_unknown_rather_than_showing_nothing():
    rows = {row["metric"]: row["value"] for row in state_summary({})}
    assert rows["Model used"] == "unknown"
    assert rows["Critic passes"] == "0 (nothing to re-check)"


def test_metric_values_lose_deck_formatting():
    """Regression: a dashboard showed `## **Business model** Per-seat …` verbatim."""

    from app.display import format_metric_value

    assert format_metric_value("## **Business model** Per-seat") == "Business model Per-seat"
    assert format_metric_value("# **Cursor (Anysphere)** — reconstructed") == (
        "Cursor (Anysphere) — reconstructed"
    )
    assert format_metric_value(["**A**", "## B"]) == "A, B"
    assert format_metric_value("$100M") == "$100M"
