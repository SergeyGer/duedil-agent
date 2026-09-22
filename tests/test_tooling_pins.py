"""Guard the pinned tooling versions so the hook, CI and dev installs agree.

``ruff format`` output and the set of enabled lint rules change between releases, so the
version has to be identical in three places:

* ``pyproject.toml`` -> ``[project.optional-dependencies].dev`` (``pip install -e ".[dev]"``)
* ``.pre-commit-config.yaml`` -> the ``astral-sh/ruff-pre-commit`` ``rev``
* ``.github/workflows/ci.yml`` -> the lint job

When they drift, a contributor can be blocked by the pre-commit hook on code that CI
considers clean (this repository shipped with ruff 0.8.4 in the hook and 0.16.8 in CI,
where 0.8.4 raised UP038 on ``app/utils.py`` and ``app/parser.py``). These tests fail
loudly instead.

The file *scope* has to agree too. Ruff 0.16 also reformats the Python snippets inside
Markdown, and ``pyproject.toml`` excludes them, so CI, the Makefile and the hook must all
run over the whole repository rather than a hardcoded subdirectory list.
"""

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
PRECOMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
MAKEFILE = REPO_ROOT / "Makefile"

RUFF_PRECOMMIT_REPO = "astral-sh/ruff-pre-commit"

_REV_LINE = re.compile(r"^\s*rev:\s*v?(\d+\.\d+\.\d+)\s*$", re.MULTILINE)
_HOOK_ID = re.compile(r"^\s*-\s*id:\s*([\w-]+)\s*$", re.MULTILINE)
_PINNED_RUFF = re.compile(r"ruff==(\d[\w.]*)")
_EXACT_PIN = re.compile(r"ruff==\d+\.\d+\.\d+")


def _dev_extra_ruff_pins():
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dev = data["project"]["optional-dependencies"]["dev"]
    return [dep for dep in dev if dep.startswith("ruff")]


def _ruff_version_from_dev_extra():
    pins = _dev_extra_ruff_pins()
    assert len(pins) == 1, f"expected exactly one `ruff` entry in [dev], found {pins}"
    assert "==" in pins[0], f"`ruff` must be pinned exactly in pyproject.toml, found {pins[0]!r}"
    return pins[0].split("==", 1)[1]


def _ruff_precommit_block():
    text = PRECOMMIT_CONFIG.read_text(encoding="utf-8")
    assert RUFF_PRECOMMIT_REPO in text, ".pre-commit-config.yaml no longer configures ruff"
    return text[text.index(RUFF_PRECOMMIT_REPO) :]


def test_dev_extra_pins_ruff_exactly():
    pins = _dev_extra_ruff_pins()
    assert len(pins) == 1, f"expected exactly one `ruff` entry in [dev], found {pins}"
    assert _EXACT_PIN.fullmatch(pins[0]), f"expected `ruff==x.y.z`, found {pins[0]!r}"


def test_pre_commit_ruff_rev_matches_dev_extra():
    match = _REV_LINE.search(_ruff_precommit_block())
    assert match is not None, "the ruff-pre-commit repo has no `rev:` line"
    assert match.group(1) == _ruff_version_from_dev_extra()


def test_pre_commit_runs_both_ruff_hooks():
    hooks = set(_HOOK_ID.findall(_ruff_precommit_block()))
    assert {"ruff", "ruff-format"} <= hooks


def test_ci_lint_job_pins_the_same_ruff_version():
    versions = set(_PINNED_RUFF.findall(CI_WORKFLOW.read_text(encoding="utf-8")))
    assert versions, "the CI workflow no longer pins a `ruff==x.y.z` version"
    assert versions == {_ruff_version_from_dev_extra()}


def test_every_entry_point_lints_the_same_scope():
    ci = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "ruff check ." in ci
    assert "ruff format --check ." in ci

    makefile = MAKEFILE.read_text(encoding="utf-8")
    assert "ruff check ." in makefile
    assert "ruff format ." in makefile

    # The hook must not narrow the scope with a `files:` filter either.
    assert "files:" not in _ruff_precommit_block()


def test_markdown_is_excluded_from_ruff():
    # Ruff 0.16 would reformat the Python snippets in README.md and
    # docs/architecture.md, undoing their deliberate column alignment.
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert "*.md" in data["tool"]["ruff"]["extend-exclude"]
