# Installation & Deployment

## Ways to run

| Mode | Best for | Command |
|---|---|---|
| **Hosted demo** | looking at the UI without installing anything | [duedil-agent.streamlit.app](https://duedil-agent-cnrm2wvfew6nstsu2tpsvh.streamlit.app) |
| **Published image** | running the current release without building | `docker run --rm -p 8501:8501 ghcr.io/sergeyger/duedil-agent:latest` |
| **Docker Compose** | a demo in one command from a clone | `docker compose up --build` |
| **Docker, offline demo** | seeing the pipeline with no keys and no cost | `docker run --rm -p 8501:8501 -e DUEDIL_MODE=demo-ui ghcr.io/sergeyger/duedil-agent:latest` |
| **Local virtualenv** | development, running the tests | `python -m venv .venv && pip install -r requirements.txt` |
| **Package install** | using `duedil` as a CLI tool | `pip install -e ".[dev]"` |

### Tags published for each release

[`.github/workflows/docker.yml`](https://github.com/SergeyGer/duedil-agent/blob/main/.github/workflows/docker.yml)
builds `linux/amd64` **and** `linux/arm64` and pushes a multi-arch manifest on every
`v*.*.*` tag:

| Tag | Meaning |
|---|---|
| `0.2.0` | exact release |
| `0.2` | latest patch of that minor line |
| `0`, `latest` | latest stable release |
| `edge` | head of a branch, published only by a manual `workflow_dispatch` run |

The same workflow smoke-tests the image it just published: it starts it and waits for Docker's
`HEALTHCHECK` (Streamlit's `/_stcore/health`) to report `healthy`, so a broken image fails the
release instead of reaching users. GitHub Packages storage and Actions minutes are free for
public repositories, and the build cache is reused between runs.

### The hosted demo

Streamlit Community Cloud deploys straight from `main` with `app/ui.py` as the entry point. It
has **no secrets configured on purpose**: without keys, PDF parsing falls back to the local
`pypdf` extractor, the agents run against a deterministic snapshot, and the pipeline still
produces a memo — so anyone can click it and it costs nothing. Apps without traffic for 12 hours
hibernate and wake on the next visit; the resource limits (~2 cores, 2.7 GB) leave comfortable
headroom.


## Prerequisites

| Requirement | Notes |
|---|---|
| Python **3.11+** (3.12 recommended) | CI covers 3.11, 3.12 and 3.13 |
| Docker 24+ | only for the container paths |
| `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` | without one the pipeline runs but produces the deterministic fallback memo |
| `LLAMA_CLOUD_API_KEY` | optional; PDF parsing falls back to local `pypdf` |
| `TAVILY_API_KEY` | optional; without it no external verification happens |

Windows note: if the install path is long, enable *Long Paths* (`LongPathsEnabled=1`), otherwise
packages such as `llama-index-core` fail to install.

## Docker

### Image design

| Aspect | Decision |
|---|---|
| Base | `python:3.12-slim`, two stages |
| Stage 1 | builds wheels for the pinned `requirements.txt` — keeps the compiler toolchain out of the final image |
| Stage 2 | installs those wheels only, then copies `app/`, `scripts/`, `examples/`, `.streamlit/` |
| User | non-root `duedil` (UID 10001); `HOME=/app` |
| Writable path | `/app/data`, owned by that user |
| Healthcheck | stdlib `urllib` against `http://127.0.0.1:8501/_stcore/health`, `--start-period=20s` |
| Entry point | `app/streamlit_app.py` — real UI by default, offline demo when `DUEDIL_MODE=demo-ui` |
| Secrets | `.dockerignore` excludes `.env` and `.git-token`, so they can never land in a layer |

Resulting image: **1.5 GB**, healthy in ≈10 s, `hadolint` clean.

### Compose services

```yaml
services:
  ui:                     # port 8501, named volume duedil-data → /app/data
    env_file: [{ path: .env, required: false }]
  cli:                    # profile "cli", entrypoint: python -m app.cli
    profiles: ["cli"]
```

`required: false` is intentional: the stack must boot **without** a `.env`, because "no keys"
is a supported mode (graceful degradation), not an error.

```bash
docker compose up --build                 # UI on http://localhost:8501
docker compose run --rm cli examples/sample_deck.pdf https://nimbusai.example
```

### Volumes and permissions

The container runs as UID 10001, so a root-owned bind mount is not writable. Two supported
options:

```bash
# a) named volume (default in compose) — the container owns /app/data
docker compose up

# b) bind mount — run as your own UID so files are not left root-owned
mkdir -p data
docker run --rm -u "$(id -u):$(id -g)" --env-file .env \
    -v "$PWD/data:/app/data" -v "$PWD/examples:/app/examples:ro" \
    duedil-agent:latest python -m app.cli examples/sample_deck.pdf https://nimbusai.example
```

## Local installation

```bash
git clone https://github.com/SergeyGer/duedil-agent.git
cd duedil-agent

python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt    # exact, reproducible pins
```

`requirements.txt` is a `pip freeze` lockfile; `pyproject.toml` declares the high-level,
unbounded dependencies. Use the lockfile for reproducibility and `pip install -e ".[dev]"` if
you want the package plus the dev tooling (pytest, ruff, pre-commit).

## Make targets

| Target | Effect |
|---|---|
| `make install` | create `.venv` and install the lockfile |
| `make test` / `make cov` | pytest / pytest with a coverage report |
| `make lint` / `make fmt` | `ruff check .` / `ruff format .` |
| `make run` | Streamlit UI (`app/ui.py`) |
| `make demo` | offline pipeline run, writes `data/nimbusai_memo.pdf` |
| `make docker-build` / `docker-run` / `docker-demo` / `docker-cli` | the four container workflows |

## Continuous integration

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | push to `main`, every PR | tests on Python 3.11/3.12/3.13 with coverage, `ruff check`, `ruff format --check`, all pre-commit hooks |
| `codeql.yml` | push, PR, weekly cron | CodeQL `security-and-quality` for Python **and** the GitHub Actions workflows, SARIF → code scanning |
| `coverage.yml` | push to `main` | regenerates `coverage.svg` and offers it as an auto-merge pull request |
| `release.yml` | tag `v*.*.*` | verifies tag ↔ `pyproject.toml`, builds sdist + wheel, publishes a GitHub Release, optional PyPI publish via Trusted Publishing |

Branch protection on `main` requires a pull request plus the `Tests (…)` and `Lint (ruff)`
status checks, so nothing reaches `main` without them.

## Releasing

```bash
# 1. bump version in pyproject.toml + add a CHANGELOG entry
# 2. commit and push to main
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

The workflow fails fast if the tag and the package version disagree, so a mismatch cannot
produce a release. Tags containing `-rc`, `-beta` or `-alpha` become pre-releases.

Optional PyPI publishing uses OIDC (`pypa/gh-action-pypi-publish`), enabled by setting the
repository variable `PUBLISH_TO_PYPI=true`; no long-lived token is stored.

## Production considerations

| Topic | Guidance |
|---|---|
| Scaling | The UI is stateless; run several replicas behind a proxy (Streamlit needs WebSocket support). |
| Secrets | Inject via the platform's secret store; `.env` is a local-development convenience. |
| Data retention | Uploaded decks and memos live in `/app/data`; nothing is sent anywhere except the configured LLM, LlamaParse, Tavily and LangSmith endpoints. |
| Cost control | Cost per run is bounded by the graph (`MAX_CRITIC_LOOPS = 2`); disable LangSmith tracing to avoid the extra span volume. |
| Keys | Prefer a workspace-scoped service key for the app rather than a personal token — see [Configuration](Configuration). |
