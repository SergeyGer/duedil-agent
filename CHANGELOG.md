# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Test-coverage tooling (`pytest-cov`) with a self-hosted coverage badge.
- `SECURITY.md` and `CODE_OF_CONDUCT.md`.
- Tag-driven release workflow (`.github/workflows/release.yml`) with optional PyPI publish.

### Changed

- Replaced the Codecov upload with a self-contained coverage-badge workflow
  (`scripts/coverage_badge.py`), because Codecov is not reachable from every region.

## [0.1.0] - 2025-01-01

### Added

- LangGraph pipeline of five agents: Extractor → Scraper → Financial → Critic → Supervisor.
- Typed `VentureState` shared between nodes (`app/state.py`).
- Critic feedback loop with a hard cap of two passes (`MAX_CRITIC_LOOPS`).
- Hybrid Red-Flag detection: LLM reasoning **and** deterministic rule-based checks.
- PDF → Markdown parsing via LlamaParse with a local `pypdf` fallback (`app/parser.py`).
- Tavily-powered web verification of competitors, traffic and founder footprint.
- Financial benchmarking: `ARR / headcount` vs. the B2B-SaaS norm (`app/utils.py`).
- Markdown → PDF deal-memo export via ReportLab (`app/report.py`).
- Streamlit web UI with step-by-step agent progress (`app/ui.py`).
- Command-line interface (`python -m app.cli …`) with PDF/Markdown/JSON output.
- Offline test suite (56 tests, ~94% coverage) and GitHub Actions CI.

[Unreleased]: https://github.com/SergeyGer/duedil-agent/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SergeyGer/duedil-agent/releases/tag/v0.1.0
