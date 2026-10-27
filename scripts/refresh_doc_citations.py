#!/usr/bin/env python3
"""Refresh the code citations in the Answer-Quality page from the actual sources.

`docs/wiki/Answer-Quality.md` cites concrete lines ("the rule lives at `app/graph.py:208`"), and
`tests/test_answer_quality_docs.py` pins those citations in both directions. Any change that moves
a function breaks the guard — by design: a page that points at the wrong line lies.

This script rewrites the numbers in both files from the symbols' current positions, so refreshing
them is one command instead of a hunt:

    python scripts/refresh_doc_citations.py

Run it after moving code, then review the diff: the symbols must be in the same places, only the
numbers should change.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "tests" / "test_answer_quality_docs.py"
GUIDE = ROOT / "docs" / "wiki" / "Answer-Quality.md"

CITATION_RE = re.compile(
    r'\(\s*"(?P<path>app/[^"]+)",\s*(?P<line>\d+),\s*'
    r'(?P<quote>["\'])(?P<token>.*?)(?P=quote)\s*\)'
)


def actual_line(path: str, token: str) -> int:
    """Return the line where ``token`` is defined, or where it first appears.

    Definitions win: a module docstring can mention ``MAX_CRITIC_LOOPS`` long before the constant
    is declared, and the citation means the declaration.
    """

    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, 1):
        if line.strip().startswith(token.rstrip(" =(")):
            return number
    for number, line in enumerate(lines, 1):
        if token in line:
            return number
    raise SystemExit(f"token {token!r} not found in {path}")


def _quoted(token: str) -> str:
    """Quote a token for the test tuple without breaking on inner double quotes."""

    return f"'{token}'" if '"' in token else f'"{token}"'


def main() -> int:
    text = TEST.read_text(encoding="utf-8")
    moves: list[tuple[str, int, int]] = []

    for match in CITATION_RE.finditer(text):
        path, old, token = match.group("path"), int(match.group("line")), match.group("token")
        current = (ROOT / path).read_text(encoding="utf-8").splitlines()
        if old <= len(current) and token in current[old - 1]:
            # The cited line already carries the symbol: leave it alone, even if the token also
            # appears earlier in a docstring.
            continue
        new = actual_line(path, token)
        if new != old:
            moves.append((path, old, new))

    if not moves:
        print("citations are current")
        return 0

    # Rewrite the test first: same tokens, new numbers.
    def _test_repl(match: re.Match[str]) -> str:
        path, token = match.group("path"), match.group("token")
        return f'("{path}", {actual_line(path, token)}, {_quoted(token)})'

    TEST.write_text(CITATION_RE.sub(_test_repl, text), encoding="utf-8")

    # Then the guide, with a simultaneous replacement so `A→B` and `B→C` cannot chain.
    guide = GUIDE.read_text(encoding="utf-8")
    placeholders: dict[str, str] = {}
    for index, (path, old, _new) in enumerate(moves):
        marker = f"@@CITE{index}@@"
        placeholders[marker] = path
        guide = re.sub(rf"(?<![\d]){re.escape(path)}:{old}(?![\d])", marker, guide)
    for index, (path, _old, new) in enumerate(moves):
        guide = guide.replace(f"@@CITE{index}@@", f"{path}:{new}")
    GUIDE.write_text(guide, encoding="utf-8")

    for path, old, new in moves:
        print(f"  {path}:{old} -> {new}")
    print(f"{len(moves)} citation(s) refreshed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
