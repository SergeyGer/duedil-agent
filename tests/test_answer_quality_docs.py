"""The quality-and-guardrails page cites code by line number; those citations must stay true.

`docs/wiki/Answer-Quality.md` makes a claim a reader can check: "the rule is at this line".
When the code moves, the page silently starts lying. This test pins the citations in both
directions — the documented line must contain the documented symbol, and the page must
actually mention that line.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GUIDE = REPO_ROOT / "docs" / "wiki" / "Answer-Quality.md"

#: ``(file, line, expected token)`` for every citation in the page.
CITED = [
    ("app/graph.py", 45, "MAX_CRITIC_LOOPS"),
    ("app/graph.py", 92, "def agent_extractor"),
    ("app/graph.py", 262, "def agent_critic"),
    ("app/graph.py", 48, "_LEADERSHIP_KEYWORDS"),
    ("app/graph.py", 65, "def _safe_json"),
    ("app/graph.py", 217, "def _deterministic_flags"),
    ("app/graph.py", 229, "external * 5 <= claimed"),
    ("app/graph.py", 249, "peak < 5000"),
    ("app/graph.py", 256, 'is_missing(metrics.get("arr"))'),
    ("app/graph.py", 313, "def route_after_critic"),
    ("app/graph.py", 352, "def _build_context"),
    ("app/graph.py", 371, "def _fallback_memo"),
    ("app/utils.py", 13, "DEFAULT_ARR_PER_EMPLOYEE_BENCHMARK"),
    ("app/utils.py", 46, "def is_missing"),
    ("app/utils.py", 101, "def compute_financials"),
    ("app/utils.py", 126, "Cannot compute efficiency"),
    ("app/prompts.py", 9, "EXTRACTOR_SYSTEM"),
    ("app/prompts.py", 14, 'literal string "[NOT_FOUND]"'),
    ("app/prompts.py", 32, "Be conservative"),
    ("app/prompts.py", 35, "CRITIC_SYSTEM"),
    ("app/prompts.py", 67, "SUPERVISOR_SYSTEM"),
    ("app/config.py", 44, "def _cached_llm"),
    ("app/config.py", 55, "def get_llm"),
    ("app/offline_agents.py", 395, "def extract_metrics"),
    ("app/offline_agents.py", 617, "class OfflineSupervisorLLM"),
    ("pyproject.toml", 101, "fail_under"),
]


def test_the_guide_exists_and_has_its_metadata():
    assert GUIDE.is_file(), "docs/wiki/Answer-Quality.md is missing"
    text = GUIDE.read_text(encoding="utf-8")
    assert "Last reviewed:" in text
    assert "[NOT_FOUND]" in text


@pytest.mark.parametrize(("path", "line", "token"), CITED)
def test_each_citation_points_at_the_documented_symbol(path: str, line: int, token: str):
    source = (REPO_ROOT / path).read_text(encoding="utf-8").splitlines()
    assert line <= len(source), f"{path} has only {len(source)} lines, citation says {line}"
    assert token in source[line - 1], (
        f"{path}:{line} no longer contains {token!r} — it reads: {source[line - 1].strip()!r}. "
        "Update docs/wiki/Answer-Quality.md."
    )


@pytest.mark.parametrize(("path", "line", "token"), CITED)
def test_the_guide_mentions_every_citation(path: str, line: int, token: str):
    text = GUIDE.read_text(encoding="utf-8")
    assert f"{path}:{line}" in text, f"the guide no longer cites {path}:{line}"
