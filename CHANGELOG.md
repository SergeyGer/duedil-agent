# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Bundled example decks in the demo**: the Streamlit sidebar offers the five decks from
  `examples/` (`airbnb`, `uber`, `cursor`, `lovable`, `cognition`), so the hosted demo runs in two
  clicks and prefills the matching website URL.
- **Model attribution everywhere**: the run summary, the CLI (`Model used : gpt-4o (OpenAI)`) and
  the exported PDF footer all state which model produced the analysis. The extractor records it in
  `VentureState.used_model`.
- **Reader-friendly results**: `app/display.py` renders the extracted metrics and the financial
  audit as tables (money grouped, ratios as `0.86× the benchmark`, missing figures labelled
  `— (not in the deck)`), and the audit's conclusion gets its own highlighted callout separated
  from the figures. `tests/test_display.py` covers the formatting rules.

### Changed

- The demo screenshots and the offline walkthrough video were re-recorded against the new UI
  (22 s, example picker visible).
- `find_team_mentions` also recognises `engineers` and `researchers` as headcount claims, which
  technical decks use.
- Test behaviour no longer depends on a developer's `.env`: `conftest.py` clears
  `LLAMA_CLOUD_API_KEY`, exactly as it already did for tracing.

### Fixed

- Dollar amounts in the UI are escaped before Markdown rendering, so Streamlit no longer parses
  `$85,714` as LaTeX and renders it as "85, 714".

### Added

- **Docker support**: multi-stage `Dockerfile` (pinned lockfile, non-root user, Streamlit
  `HEALTHCHECK`) plus `docker-compose.yml` with `ui` and `cli` services and a named data
  volume. `DUEDIL_MODE=demo-ui` starts the image in offline demo mode.
- **CodeQL code scanning** (`.github/workflows/codeql.yml`): Python + GitHub Actions analysis
  on every push, PR and weekly, using the `security-and-quality` query suite.
- **Reproducible demo tooling**: `scripts/demo_offline.py` (real graph, canned LLM/search, no
  API keys), `scripts/demo_offline_ui.py` and `scripts/capture_demo.py` (Playwright
  screenshots + walkthrough video).
- Demo artefacts in `docs/media/`: UI screenshots (EN/RU), CLI transcripts and two videos
  (offline demo, live `gpt-4o` run), all linked from the README.
- `.dockerignore`, `Makefile` targets (`docker-build`, `docker-run`, `docker-demo`,
  `docker-cli`, `demo`) and a `.gitignore` entry for a local `.git-token`.

### Fixed

- `multidict` is held at 6.x: `aiohttp` requires `multidict<7.0`, so the 7.0.0 bump made
  `pip install -r requirements.txt` fail with `ResolutionImpossible`. Dependabot now skips it
  until aiohttp allows 7.x.
- The `ruff` pin is kept in sync across `.pre-commit-config.yaml`, `pyproject.toml` and the CI
  lint job (0.16.9), which `tests/test_tooling_pins.py` enforces.
- The **coverage badge** workflow no longer pushes to `main` directly (the branch ruleset
  rejects that with `GH013`): it opens a `chore/coverage-badge` pull request and asks for
  auto-merge, so required checks still apply.

### Security

- Every workflow action is pinned to a commit SHA (release tag kept in a trailing comment),
  clearing CodeQL's `actions/unpinned-tag` findings; Dependabot still bumps them weekly.
- The first CodeQL scan's findings were resolved: two URL-substring assertions in
  `tests/test_tools.py` now compare whole rendered lines, `ci.yml` declares
  `permissions: contents: read`, and the unused helper constants/import are gone. See #14, #16.

## [0.1.0] - 2026-09-22

First public release.

### Added

- LangGraph pipeline of five agents: Extractor → Scraper → Financial → Critic → Supervisor.
- Typed `VentureState` shared between nodes (`app/state.py`).
- Critic feedback loop with a hard cap of two passes (`MAX_CRITIC_LOOPS`).
- Hybrid Red-Flag detection: LLM reasoning **and** deterministic rule-based checks.
- PDF → Markdown parsing via LlamaParse with a local `pypdf` fallback (`app/parser.py`).
- Tavily-powered web verification of competitors, traffic and founder footprint.
- Financial benchmarking: `ARR / headcount` vs. the B2B-SaaS norm (`app/utils.py`).
- Markdown → PDF deal-memo export via ReportLab (`app/report.py`).
- Streamlit web UI with step-by-step agent progress (`app/ui.py`), available in English,
  German, French and Russian (`app/i18n.py`).
- Command-line interface (`python -m app.cli …`) with PDF/Markdown/JSON output.
- Offline test suite (72 tests, ~92% coverage) and GitHub Actions CI.
- Automated tag-driven release workflow with optional PyPI publishing.
- Coverage tooling (`pytest-cov`) with a self-hosted badge (`scripts/coverage_badge.py`).
- Dependabot configuration; `SECURITY.md` and `CODE_OF_CONDUCT.md`.
- Social-preview banner (`assets/social-preview.png` / `.svg`) with a generator script.

### Changed

- Migrated the Tavily integration to the standalone `langchain-tavily` package (removes the
  `langchain-community` deprecation warning).
- Replaced the Codecov upload with a self-contained coverage-badge workflow.

[Unreleased]: https://github.com/SergeyGer/duedil-agent/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SergeyGer/duedil-agent/releases/tag/v0.1.0
