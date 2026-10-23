#!/usr/bin/env python3
"""Validate the documentation: links, anchors, ADRs, wiki metadata and generated pages.

Documentation rots silently: a page is renamed, an image is moved, a decision record loses a
section, and nobody notices until a reader hits a dead end. This script makes those failures
visible in CI (the ``Docs · links + ADR`` check) and in the test suite.

It is standard-library only, so the Docs workflow can run it before installing the
application dependencies.

What it checks
--------------
1. **Local links and images** in ``README.md`` and every ``docs/**/*.md`` — including
   anchors (``page.md#section``) and the wiki's extension-less page links.
2. **ADR records** — each file has Status / Context / Decision / Consequences, and the
   index lists every record.
3. **Wiki hygiene** — every page ends with ``*Last reviewed: <date> · Owner: …*``, and
   ``_Sidebar.md`` links every page, so nothing becomes unreachable.
4. **Generated pages** — ``docs/wiki/Reference.md`` matches what the generator produces.
5. **Wording rules** — the project does not use the word this file bans (a product decision:
   the documentation addresses visitors, engineers and operators, not recruiters).

Usage::

    python scripts/validate_docs.py            # exit 1 on any finding
    python scripts/validate_docs.py --verbose  # list everything that was checked
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
WIKI = DOCS / "wiki"
ADR = DOCS / "adr"
README = ROOT / "README.md"

#: Wording the documentation must not use (see the module docstring).
BANNED_WORDS = ("recruiter", "рекрут")

ADR_SECTIONS = ("## Status", "## Context", "## Decision", "## Consequences")
WIKI_META_RE = re.compile(r"^\*Last reviewed: \d{4}-\d{2}-\d{2} · Owner: .+\*$", re.MULTILINE)

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HTML_LINK_RE = re.compile(r'(?:src|href)="([^"]+)"')
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
SKIP_SCHEMES = ("http://", "https://", "mailto:", "tel:", "data:")


def _docs() -> list[Path]:
    files = [README] if README.is_file() else []
    files.extend(sorted(DOCS.rglob("*.md")))
    return [path for path in files if path.is_file()]


def _anchors(path: Path) -> set[str]:
    """Approximate GitHub heading anchors for a Markdown file."""

    anchors: set[str] = set()
    for match in HEADING_RE.finditer(path.read_text(encoding="utf-8")):
        raw = re.sub(r"<[^>]+>", "", match.group(2))
        raw = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", raw)
        base = re.sub(r"[^\w\s-]", "", raw.replace("`", "").lower(), flags=re.UNICODE).strip()
        if not base:
            continue
        slug = base.replace(" ", "-")
        anchors.update({slug, re.sub(r"-+", "-", slug)})
    return anchors


def _resolve(target: str, source: Path) -> tuple[Path | None, str]:
    """Return the file a link points at (or ``None``) and the anchor part."""

    path_part, _, anchor = target.partition("#")
    if not path_part:
        return source, anchor
    candidate = (source.parent / path_part).resolve()
    if candidate.is_dir():
        return candidate, anchor
    if candidate.is_file():
        return candidate, anchor
    # The GitHub wiki drops the .md extension: [Home](Home) means Home.md.
    for suffix in (".md", ".md#"):
        alternative = candidate.with_name(candidate.name + suffix.rstrip("#"))
        if alternative.is_file():
            return alternative, anchor
    return None, anchor


def check_links(errors: list[str], verbose: list[str]) -> int:
    checked = 0
    for path in _docs():
        text = path.read_text(encoding="utf-8")
        for raw in LINK_RE.findall(text) + HTML_LINK_RE.findall(text):
            target = raw.strip().strip("<>")
            if not target or target.startswith(SKIP_SCHEMES):
                continue
            checked += 1
            resolved, anchor = _resolve(target, path)
            if resolved is None:
                errors.append(f"{path.relative_to(ROOT)}: broken link -> {target}")
                continue
            if resolved.is_dir() or not anchor:
                continue
            anchors = _anchors(resolved)
            if anchors and anchor not in anchors:
                errors.append(
                    f"{path.relative_to(ROOT)}: missing anchor #{anchor} in "
                    f"{resolved.relative_to(ROOT)}"
                )
    verbose.append(f"links: {checked} local targets checked")
    return checked


def check_adr(errors: list[str], verbose: list[str]) -> int:
    if not ADR.is_dir():
        errors.append("docs/adr/ is missing")
        return 0
    records = sorted(p for p in ADR.glob("*.md") if p.name != "README.md")
    if not records:
        errors.append("docs/adr/ has no decision records")
        return 0
    for path in records:
        text = path.read_text(encoding="utf-8")
        missing = [section for section in ADR_SECTIONS if section not in text]
        if missing:
            errors.append(f"{path.relative_to(ROOT)}: missing sections {missing}")
        if not re.search(r"^\*\*Status:\*\*|^## Status\s*\n+\s*\w", text, re.MULTILINE):
            errors.append(f"{path.relative_to(ROOT)}: no status line")
    index = (ADR / "README.md").read_text(encoding="utf-8")
    for path in records:
        if path.name not in index:
            errors.append(f"docs/adr/README.md does not list {path.name}")
    verbose.append(f"adr: {len(records)} records checked")
    return len(records)


def check_wiki(errors: list[str], verbose: list[str]) -> int:
    if not WIKI.is_dir():
        errors.append("docs/wiki/ is missing")
        return 0
    pages = sorted(p for p in WIKI.glob("*.md") if p.name != "_Sidebar.md")
    sidebar = (WIKI / "_Sidebar.md").read_text(encoding="utf-8")
    for path in pages:
        text = path.read_text(encoding="utf-8")
        if not WIKI_META_RE.search(text):
            errors.append(f"{path.relative_to(ROOT)}: missing '*Last reviewed: <date> · Owner: …*'")
        if f"]({path.stem})" not in sidebar:
            errors.append(f"{path.relative_to(ROOT)}: not linked from _Sidebar.md")
    verbose.append(f"wiki: {len(pages)} pages checked")
    return len(pages)


def check_reference(errors: list[str], verbose: list[str]) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from make_wiki_reference import OUTPUT, render  # noqa: PLC0415 - local helper script

    if not OUTPUT.is_file():
        errors.append("docs/wiki/Reference.md is missing — run `make wiki-reference`")
        return
    if OUTPUT.read_text(encoding="utf-8") != render():
        errors.append("docs/wiki/Reference.md is stale — run `make wiki-reference`")
    verbose.append("reference: generated page compared")


def check_wording(errors: list[str], verbose: list[str]) -> None:
    for path in _docs():
        lowered = path.read_text(encoding="utf-8").lower()
        for word in BANNED_WORDS:
            if word in lowered:
                errors.append(f"{path.relative_to(ROOT)}: uses the banned word {word!r}")
    verbose.append(f"wording: {len(BANNED_WORDS)} banned words checked")


def check_readme(errors: list[str], verbose: list[str]) -> None:
    if not README.is_file():
        errors.append("README.md is missing")
        return
    text = README.read_text(encoding="utf-8")
    lowered = text.lower()
    if "## choose your path" not in lowered:
        errors.append("README.md: missing the '## Choose your path' routing block")
    for role in ("visitor", "engineer", "operator"):
        # Case-insensitive: the prose says "A visitor", the heading says "Visitor".
        if role not in lowered:
            errors.append(f"README.md: the routing block does not mention {role!r}")
    verbose.append("readme: entry-point routing present")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the documentation.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    errors: list[str] = []
    verbose: list[str] = []

    check_links(errors, verbose)
    check_adr(errors, verbose)
    check_wiki(errors, verbose)
    check_reference(errors, verbose)
    check_wording(errors, verbose)
    check_readme(errors, verbose)

    if args.verbose:
        for line in verbose:
            print(f"  {line}")
    if errors:
        print(f"\n{len(errors)} documentation problem(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("documentation ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
