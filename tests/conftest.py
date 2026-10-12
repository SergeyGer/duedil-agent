"""Shared pytest configuration.

Tracing must never be active during the test run: it would make real network
calls to LangSmith and slow the suite down. ``load_dotenv()`` does not override
already-set environment variables, so disabling tracing here (before the app is
imported) keeps the suite fully offline and deterministic even if a developer's
local ``.env`` enables it.

The same reasoning applies to the document parser. With ``LLAMA_CLOUD_API_KEY``
present the parser takes the LlamaParse path and returns Markdown; without it — the
case in CI — it falls back to ``pypdf`` and returns plain text. Test behaviour must
not depend on whose machine it runs on, so the suite always exercises the local
fallback. Tests that want the hosted parser install their own fake (see
``test_parser.py``).
"""

import os

os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_TRACING"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ.pop("LLAMA_CLOUD_API_KEY", None)
