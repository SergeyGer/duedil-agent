# Testing & Quality Gates

## The numbers

| Metric | Value |
|---|---|
| Tests | **79 passing** |
| Line coverage of `app/` | **90.1 %** |
| Coverage gate in CI | **88 %** (`fail_under` in `pyproject.toml`) |
| Runtime of the full suite | ≈6 s locally (offline, no network) |
| Python versions in CI | 3.11, 3.12, 3.13 |
| Application code | ≈1 850 lines |
| Test code | ≈800 lines |

The suite is fully **offline**: no API keys, no network, no cost. That is a design constraint,
not a happy accident — an untestable pipeline is an unmaintainable one.

## Layout

| File | Covers |
|---|---|
| `test_graph.py` | Graph wiring, `route_after_critic`, the loop cap, flag accumulation, the fallback memo — driven with a fake LLM |
| `test_critic.py` | Every deterministic Red-Flag rule, both directions of the team rule, the traffic threshold, missing ARR |
| `test_utils.py` | `parse_number` / `parse_count` / `find_team_mentions` / `find_traffic_mentions` / `compute_financials`, `[NOT_FOUND]` handling, `1.200.000`-style separators |
| `test_parser.py` | LlamaParse path and `pypdf` fallback, bytes input, `ParserError` |
| `test_report.py` | Markdown → PDF rendering |
| `test_tools.py` | Tavily wrapper (both integrations), result stringification |
| `test_config.py` | The LLM factory and its caching |
| `test_cli.py` | CLI end-to-end against a mocked graph, exit codes, artefact writing |
| `test_ui.py` | Streamlit smoke tests via `AppTest` |
| `test_state.py` | State initialisation |
| `test_i18n.py` | Translation tables: same keys, same placeholders, in all four languages |
| `test_tooling_pins.py` | The `ruff` pin agrees across `pyproject.toml`, `.pre-commit-config.yaml` and CI; lint scope is identical everywhere; Markdown stays excluded |
| `conftest.py` | Disables LangSmith tracing before the app is imported, so the suite can never call the network |

`test_tooling_pins.py` deserves the attention it gets: it exists because the repository once
shipped `ruff 0.8.4` in the hook and `0.16.8` in CI, which blocked contributors on code CI
considered clean. Tool drift is now a test failure, not a surprise.

## How the offline tests drive real code

```python
# tests/test_graph.py (shape)
def test_graph_runs_end_to_end(monkeypatch):
    monkeypatch.setattr(graph_module, "get_llm", lambda *a, **k: FakeLLM())
    monkeypatch.setattr(graph_module, "get_search_tool", lambda *a, **k: None)
    state = run_due_diligence("deck text", "")
    assert state["final_memo"]
```

Only two boundaries are ever replaced — the LLM and the search tool — because those are the
only things that leave the process. Everything else (routing, benchmarks, heuristics, state
merging, PDF rendering) is exercised for real.

## Quality gates

| Gate | Where | Threshold / rule |
|---|---|---|
| Unit tests | `ci.yml` | must pass on 3.11, 3.12, 3.13 |
| Coverage | `pyproject.toml` | `fail_under = 88` |
| Lint | `ruff` | `E`, `F`, `I`, `W`, `UP`, `B`; line length 100 |
| Formatting | `ruff format --check .` | must be clean |
| Whitespace hygiene | pre-commit | trailing whitespace, EOF newline, mixed line endings, merge conflicts, large files |
| Static analysis | `codeql.yml` | `security-and-quality` suite; **0 open alerts** |
| Supply chain | `dependabot.yml` + SHA pinning | every action pinned to a commit SHA; weekly grouped updates |
| Branch protection | repository ruleset | PR + required `Tests (…)` and `Lint (ruff)` checks before `main` |
| Secrets | `.gitignore` + `.dockerignore` | `.env` and `.git-token` excluded from git *and* from image layers |

## Reproducing locally

```bash
make test        # pytest
make cov         # pytest --cov=app --cov-report=term-missing
make lint        # ruff check .
make fmt         # ruff format .
pre-commit run --all-files
```

## Coverage badge

`coverage.yml` regenerates `.github/badges/coverage.svg` on every push to `main` and publishes
it as a `chore/coverage-badge` pull request. It cannot merge itself, and that is a GitHub
constraint rather than a bug: the job pushes with the built-in `GITHUB_TOKEN`, and GitHub
suppresses workflow runs for events created by that token, so the required status checks never
report on that branch. Merging the badge PR is therefore a human step — it only ever touches
the SVG.

## Code scanning

`codeql.yml` analyses Python and the workflow files with the `security-and-quality` query
suite on every push, every PR and weekly. Findings and their history:
[Security → Code scanning](https://github.com/SergeyGer/duedil-agent/security/code-scanning).

The first scan produced ten findings; all were resolved. The substantive ones:

| Finding | Resolution |
|---|---|
| `py/incomplete-url-substring-sanitization` ×2 | Tests asserted `"https://acme.ai" in out`, which would also pass for `https://acme.ai.evil.example` — they now compare the whole rendered line. |
| `actions/missing-workflow-permissions` ×2 | `ci.yml` now declares `permissions: contents: read` instead of inheriting the repository default. |
| `actions/unpinned-tag` ×3 | Every third-party action is pinned to a commit SHA with the release tag in a comment; `pypa/gh-action-pypi-publish` was tracking the mutable `release/v1` **branch**. |
| `py/unused-import`, `py/unused-global-variable` ×3 | Dead constants and a side-effect-only import removed. |

## Testing philosophy

1. **Boundaries only.** Replace what leaves the process; assert on everything else.
2. **Deterministic first.** Pure helpers carry the parsing and benchmark logic precisely so
   they can be tested exhaustively — that is where the arithmetic bugs would live.
3. **Test the guard-rails, not just the happy path.** Loop cap, coverage gate, tooling pins and
   the `[NOT_FOUND]` token set all have explicit tests, because those are the things that
   quietly rot.
4. **Documentation artefacts are reproducible.** The offline demo and the media capture script
   are checked in, so the demo can be regenerated instead of being manually staged.
