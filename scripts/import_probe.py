#!/usr/bin/env python3
"""Staged import probe: find which import kills a hosted deployment.

Written while debugging a Streamlit Community Cloud deployment that served a blank
page: the platform log ended at `Uvicorn server started`, no traceback was emitted,
and the same code ran fine locally. A three-line app proved the platform itself was
healthy, which left the project's own import graph — and this probe walks it one step
at a time.

How to use it (the platform no longer exposes a branch / main-file switcher for apps
that already exist, so this needs its own app):

1. Streamlit Community Cloud → **Create app** → deploy from this repository;
2. **Main file path**: ``scripts/import_probe.py``, branch: whichever one you are
   testing (``main`` is fine);
3. open the app and read the step list.

Every import is wrapped individually, so one failure does not hide the rest, and each
step is written to the page **and** to stdout — if the process dies mid-way, the last
line in the Cloud log names the import that killed it. When every import succeeds the
probe renders the real UI, so it can be used as a drop-in entry point.

This is a diagnostic, not part of the application: nothing imports it, and the test
suite ignores it.
"""

from __future__ import annotations

import os
import sys
import traceback
from importlib import import_module

import streamlit as st

st.title("import probe")
st.write(f"python {sys.version.split()[0]} | cwd={os.getcwd()}")
st.write(f"sys.path[:4] = {sys.path[:4]}")

# Ordered so the first failure is the innermost cause: third-party packages before the
# project's own modules, and app.graph (the heaviest) before app.ui.
STEPS = [
    ("langchain_core.messages", "langchain_core.messages"),
    ("langgraph.graph", "langgraph.graph"),
    ("langchain_openai", "langchain_openai"),
    ("langchain_anthropic", "langchain_anthropic"),
    ("langchain_tavily", "langchain_tavily"),
    ("llama_parse", "llama_parse"),
    ("reportlab.platypus", "reportlab.platypus"),
    ("pypdf", "pypdf"),
    ("app.state", "app.state"),
    ("app.utils", "app.utils"),
    ("app.prompts", "app.prompts"),
    ("app.config", "app.config"),
    ("app.tools", "app.tools"),
    ("app.parser", "app.parser"),
    ("app.report", "app.report"),
    ("app.i18n", "app.i18n"),
    ("app.graph", "app.graph"),
    ("app.ui", "app.ui"),
]

results: list[tuple[str, str, str]] = []
for label, target in STEPS:
    try:
        import_module(target)
        results.append((label, "ok", ""))
    except BaseException:  # noqa: BLE001 - a probe must survive anything, incl. SystemExit
        results.append((label, "FAILED", traceback.format_exc()))

for label, status, detail in results:
    print(f"PROBE {status:6} {label}", flush=True)
    if status == "ok":
        st.success(f"{label}: ok")
    else:
        st.error(f"{label}: FAILED")
        st.code(detail)

st.divider()
if all(status == "ok" for _, status, _ in results):
    st.success("every import succeeded — the failure is not an import")
    try:
        from app.ui import main

        main()
        st.success("the real UI rendered")
    except BaseException:  # noqa: BLE001 - report instead of dying silently
        st.error("the real UI raised:")
        st.code(traceback.format_exc())
else:
    failed = [label for label, status, _ in results if status != "ok"]
    st.warning(f"stopped at: {', '.join(failed)}")
