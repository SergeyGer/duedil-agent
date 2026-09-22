# Contributing to DueDil.Agent

Thanks for your interest in improving DueDil.Agent! 🎉

## Development setup

```bash
git clone https://github.com/SergeyGer/duedil-agent.git
cd duedil-agent
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"   # pytest, ruff, pre-commit
```

Install the git hooks (recommended):

```bash
pre-commit install
```

## Project conventions

- **Python**: 3.11+. Type hints everywhere, `from __future__ import annotations`.
- **Style**: [Ruff](https://github.com/astral-sh/ruff) with a 100-char line length.
  Run `ruff format app tests` and `ruff check app tests` (or `make fmt` / `make lint`).
- **Tests**: every new behaviour should come with a test in `tests/`. Prefer tests that
  run **offline** (no API keys / network) — use `FakeListChatModel` and monkeypatching,
  as the existing graph tests do.
- **Commits**: follow [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:` …).

## Quality gate

Before opening a pull request, make sure the following pass:

```bash
make test   # pytest
make cov    # pytest with a coverage report
make lint   # ruff check
make fmt    # ruff format (auto-fix)
```

The project enforces at least **88% line coverage** on `app/` (see `[tool.coverage.report]` in
`pyproject.toml`). New behaviour should come with tests that keep the suite green and the
coverage steady.

## Pull requests

1. Fork the repository and create a feature branch (`feat/short-description`).
2. Keep the change focused; update the README / CHANGELOG when relevant.
3. Ensure CI is green.
4. Fill in the pull-request template.

## Reporting bugs / requesting features

Use the GitHub issue templates. For security-sensitive reports, please contact the
maintainers privately instead of opening a public issue.

## License

By contributing you agree that your contributions are licensed under the
[MIT License](LICENSE).
