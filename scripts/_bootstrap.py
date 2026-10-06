"""Make the repository root and this directory importable from any entry point.

The scripts in this folder are run in three different ways — as ``python
scripts/<name>.py``, as ``streamlit run scripts/demo_offline_ui.py`` and as
``streamlit run app/streamlit_app.py`` inside the Docker image. In every case the
process has to be able to import both ``app`` and the sibling demo helpers, so the
path set-up lives here instead of being repeated (and half-forgotten) per file.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent

for _path in (REPO_ROOT, SCRIPTS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
