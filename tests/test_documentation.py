"""The documentation is validated in CI and here.

`scripts/validate_docs.py` is the single implementation; running it from the test suite means
a broken link or a stale generated page fails `make test` too, long before a release.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = REPO_ROOT / "scripts" / "validate_docs.py"


def _load_validator():
    name = "validate_docs_under_test"
    spec = importlib.util.spec_from_file_location(name, VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_documentation_passes_its_own_validator():
    validator = _load_validator()
    assert validator.main([]) == 0


def test_links_are_actually_followed():
    """Guard: the validator must find links, not silently skip them all."""

    validator = _load_validator()
    errors: list[str] = []
    verbose: list[str] = []
    checked = validator.check_links(errors, verbose)
    assert checked > 80, f"only {checked} local links were checked"
    assert not errors, errors
