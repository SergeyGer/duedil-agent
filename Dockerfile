# syntax=docker/dockerfile:1
#
# DueDil.Agent — Streamlit UI (default) + CLI runner.
#
# Build:
#   docker build -t duedil-agent .
#
# Run the web UI (http://localhost:8501):
#   docker run --rm -p 8501:8501 --env-file .env duedil-agent
#
# Run the CLI instead (the deck must be readable inside the container):
#   docker run --rm --env-file .env \
#     -v "$PWD/examples:/app/examples:ro" -v "$PWD/data:/app/data" \
#     duedil-agent python -m app.cli examples/sample_deck.pdf https://nimbusai.example
#
# Without an `.env` the pipeline still runs: PDF parsing falls back to pypdf and
# the memo is produced by the deterministic fallback instead of an LLM.

# --- Stage 1: build the wheels for the pinned lockfile ----------------------
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /build

# `requirements.txt` is generated with `pip freeze`, so every line is a binary
# wheel: building them here keeps the compiler toolchain out of the runtime image.
COPY requirements.txt ./
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# --- Stage 2: runtime -------------------------------------------------------
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="DueDil.Agent" \
      org.opencontainers.image.description="Autonomous multi-agent due-diligence system for technology startups (LangGraph + Streamlit)." \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/SergeyGer/duedil-agent"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONPATH=/app \
    HOME=/app \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Install the pinned lockfile first so application edits never invalidate it.
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* \
    && rm -rf /wheels

# Non-root runtime user; /app/data is the writable directory for generated memos.
RUN useradd --create-home --home-dir /app --shell /usr/sbin/nologin --uid 10001 duedil \
    && mkdir -p /app/data \
    && chown -R duedil:duedil /app

# Application code + the files the UI/CLI read at runtime.
COPY --chown=duedil:duedil app/ ./app/
COPY --chown=duedil:duedil scripts/ ./scripts/
COPY --chown=duedil:duedil .streamlit/ ./.streamlit/
COPY --chown=duedil:duedil examples/ ./examples/
COPY --chown=duedil:duedil pyproject.toml README.md LICENSE ./

USER duedil

EXPOSE 8501

# Streamlit's built-in health endpoint; stdlib only, so no curl in the image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).read()"

# Default: the web UI. Override with e.g. `python -m app.cli ...` for CLI runs, or
# set DUEDIL_MODE=demo-ui for the offline demo (no API keys, canned agents).
CMD ["python", "-m", "streamlit", "run", "app/streamlit_app.py"]
