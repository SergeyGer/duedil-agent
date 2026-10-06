#!/usr/bin/env python3
"""Launch the Streamlit UI in offline demo mode (no API keys, no network).

The UI itself is used unmodified — ``install_stubs()`` swaps the LLM and the web
search for the canned versions from :mod:`demo_offline` before ``app.ui.main()``
runs.

Usage::

    streamlit run scripts/demo_offline_ui.py
    DUE_DIL_DEMO_DELAY=1.2 streamlit run scripts/demo_offline_ui.py   # slower, for recording
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Streamlit runs this file as a script, so neither the repository root nor this
# directory is on sys.path yet; both `app` and `demo_offline` are needed below.
SCRIPTS_DIR = Path(__file__).resolve().parent
for _path in (SCRIPTS_DIR.parent, SCRIPTS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from demo_offline import install_stubs  # noqa: E402

install_stubs(delay=float(os.getenv("DUE_DIL_DEMO_DELAY", "0")))

from app.ui import main  # noqa: E402  (import after the stubs are in place)

main()
