"""Shared pytest configuration.

Tracing must never be active during the test run: it would make real network
calls to LangSmith and slow the suite down. ``load_dotenv()`` does not override
already-set environment variables, so disabling tracing here (before the app is
imported) keeps the suite fully offline and deterministic even if a developer's
local ``.env`` enables it.
"""

import os

os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_TRACING"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
