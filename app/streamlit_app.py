#!/usr/bin/env python3
"""Streamlit entry point used by the Docker image; selects the UI mode.

    DUEDIL_MODE=ui       (default) real pipeline — Streamlit UI
    DUEDIL_MODE=demo-ui  offline demo, no API keys (canned agents)

A single default command keeps `docker run` simple, while the standalone scripts
(``scripts/demo_offline.py``, ``scripts/demo_offline_ui.py``) still work for local
development.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for _path in (REPO_ROOT, REPO_ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

if (os.getenv("DUEDIL_MODE") or "ui").strip().lower() != "ui":
    from demo_offline import install_stubs

    install_stubs(delay=float(os.getenv("DUE_DIL_DEMO_DELAY", "0")))

from app.ui import main  # noqa: E402  (imported after the optional stubs)

main()
