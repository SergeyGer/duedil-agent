# Architecture

DueDil.Agent is a five-node [LangGraph](https://github.com/langchain-ai/langgraph) pipeline
with a bounded critic feedback loop. Every node reads and writes a single typed state object
(`VentureState`); nodes never call each other directly.

> For the high-level overview see the [README](../README.md#architecture).

## High-level flow

```mermaid
flowchart LR
    START([Start]) --> EX[agent_extractor]
    EX --> SC[agent_scraper]
    SC --> FI[agent_financial]
    FI --> CR[agent_critic]
    CR -->|red_flags and loops < 2| SC
    CR -->|clean or loops >= 2| SU[agent_supervisor]
    SU --> END([End])
```

```
INPUT: pitch deck PDF + website URL
  |
  v
[1] Extractor  -> extracted_metrics        (structured claims; [NOT_FOUND] when absent)
  |
  v
[2] Scraper    -> market_data              (Tavily: competitors, traffic, founders)
  |
  v
[3] Financial  -> financial_benchmarks     (ARR / headcount vs. $100k SaaS benchmark)
  |
  v
[4] Critic     -> red_flags, critic_feedback, critic_loops_count
  |                |
  |  flags & < 2   |   clean or >= 2
  +-----> [2]      +-----> [5] Supervisor -> final_memo -> PDF
```

## Module map

| Module | Responsibility |
|--------|----------------|
| `app/state.py` | `VentureState` (`TypedDict`) and `initial_state()` |
| `app/config.py` | LLM factory (`gpt-4o` / `claude-*`), lazily constructed |
| `app/prompts.py` | System prompts for the extractor, critic and supervisor |
| `app/tools.py` | Tavily search tool (`langchain-tavily`, community fallback) |
| `app/parser.py` | PDF → Markdown (LlamaParse, `pypdf` fallback) |
| `app/graph.py` | Agent nodes, routing, graph assembly, loop guard |
| `app/utils.py` | Numeric parsing, financial benchmarks, Red-Flag heuristics |
| `app/report.py` | Markdown → PDF rendering (ReportLab) |
| `app/i18n.py` | UI translations (EN / DE / FR / RU) |
| `app/cli.py`, `app/ui.py` | Front-ends |

---

## Shared state

`VentureState` is a `TypedDict`. Each node returns a *partial* dict that LangGraph merges into
the running state, so nodes stay decoupled.

| Field | Type | Written by | Notes |
|-------|------|-----------|-------|
| `pitch_deck_raw` | `str` | CLI / UI | Markdown extracted from the deck |
| `website_url` | `str` | CLI / UI | Optional |
| `extracted_metrics` | `dict` | Extractor | Claims as strings; `[NOT_FOUND]` when absent |
| `market_data` | `list[str]` | Scraper | Raw search blocks (replaced on each pass) |
| `financial_benchmarks` | `dict` | Financial | Ratios + human-readable verdict |
| `red_flags` | `list[str]` | Critic | Accumulated and de-duplicated across passes |
| `critic_loops_count` | `int` | Critic | Incremented on every pass |
| `critic_feedback` | `str` | Critic | Drives the next Scraper query |
| `final_memo` | `str` | Supervisor | Markdown deal memo |
| `progress_log` | `list[str]` | all nodes | Uses an `Annotated[..., add]` reducer |

---

## Nodes

### 1. `agent_extractor` (`app/graph.py`)

- **In:** `pitch_deck_raw`.
- **Out:** `extracted_metrics`.
- **How:** a single LLM call with `EXTRACTOR_SYSTEM`, then defensive JSON parsing
  (`_safe_json` tolerates code fences and stray prose). The prompt forbids inventing data —
  any field that is not explicitly stated must be `"[NOT_FOUND]"`.

### 2. `agent_scraper` (`app/graph.py`)

- **In:** `extracted_metrics`, `critic_feedback`, `critic_loops_count`.
- **Out:** `market_data`.
- **How:** builds 3 default queries (competitors / traffic / founders+team) or, on a repeat
  pass, targets `critic_feedback`. Results are flattened by `stringify_search_results`.
- **Degrades:** if `TAVILY_API_KEY` is missing or the tool cannot be built, it records a
  placeholder instead of failing.

### 3. `agent_financial` (`app/graph.py`)

- **In:** `extracted_metrics`.
- **Out:** `financial_benchmarks`.
- **How:** pure Python (`app/utils.py`) — parses `arr` and `team_size` (`"$1.2M"`, `"50"`,
  `"10k"` …), computes `ARR / employee` and compares it against `DEFAULT_ARR_PER_EMPLOYEE_BENCHMARK`
  ($100k). Unknown inputs produce an explicit "insufficient data" verdict.

### 4. `agent_critic` (`app/graph.py`)

- **In:** `extracted_metrics`, `market_data`.
- **Out:** `red_flags`, `critic_feedback`, `critic_loops_count`.
- **How:** an LLM pass (`CRITIC_SYSTEM`) **plus** deterministic guards (`_deterministic_flags`):
  - team-size mismatch (deck says 50, external sources say 2),
  - leadership claim vs. near-zero website traffic,
  - missing ARR.
  Flags are appended to any existing ones and de-duplicated.

### 5. `agent_supervisor` (`app/graph.py`)

- **In:** the whole state.
- **Out:** `final_memo`.
- **How:** renders a context block (metrics + benchmarks + market data + flags) and asks the
  LLM for a Markdown memo following a fixed outline. If the call fails, `_fallback_memo`
  produces a deterministic memo with a rule-based recommendation.

---

## Routing & loop protection

The only conditional edge sits after the critic:

```python
def route_after_critic(state) -> str:
    flags = state.get("red_flags") or []
    loops = state.get("critic_loops_count", 0)
    if flags and loops < MAX_CRITIC_LOOPS:   # MAX_CRITIC_LOOPS = 2
        return "agent_scraper"               # targeted re-search
    return "agent_supervisor"                # stop and write the memo
```

The loop is **hard-capped at 2 passes**, which guarantees termination even if the critic
keeps finding problems. The first pass is a broad sweep; the second is targeted at
`critic_feedback`.

## Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant P as Parser
    participant G as Graph
    participant L as LLM
    participant T as Tavily

    U->>P: PDF
    P-->>G: pitch_deck_raw
    G->>L: extract metrics
    L-->>G: extracted_metrics
    G->>T: competitor / traffic / founder queries
    T-->>G: market_data
    G->>G: financial benchmarks
    G->>L: critique claims vs evidence
    L-->>G: red_flags + feedback
    alt flags and loops < 2
        G->>T: targeted re-search
        T-->>G: market_data
    end
    G->>L: write the memo
    L-->>U: final_memo -> PDF
```

## Design decisions

- **Sequential Extractor → Scraper.** The scraper needs the company name and sector, so the
  two cannot run in parallel.
- **Hybrid critic.** LLM judgement is nuanced but non-deterministic; rule-based guards make
  sure the obvious contradictions are always caught.
- **Lazy LLM construction.** `get_llm()` is called inside each node's `try`, so a missing key
  degrades to the fallback memo instead of crashing the graph — which also keeps the test
  suite offline.
- **Rendering is separate.** The graph emits Markdown; `app/report.py` turns it into a PDF.
- **Determinism where it matters.** Parsing numbers, benchmarking and the loop counter are
  pure functions in `app/utils.py`, fully unit-tested.

## Extension points

| Goal | Where |
|------|-------|
| Add a node | Define it in `app/graph.py`, `add_node(...)`, wire the edges |
| Change the benchmark | `DEFAULT_ARR_PER_EMPLOYEE_BENCHMARK` in `app/utils.py` |
| Change the pass cap | `MAX_CRITIC_LOOPS` in `app/graph.py` |
| Swap the LLM | `DUE_DIL_MODEL` env var, or `app/config.py` |
| Add a language | `TRANSLATIONS` in `app/i18n.py` (tests enforce key parity) |
| Adjust prompts | `app/prompts.py` |

---

## CI, releases and automation

All automation lives in `.github/workflows/`. It is deliberately split into three workflows:
the always-on checks (`ci.yml`) are read-only and run on every change, while the two workflows
that write somewhere (the repository itself, or a package registry) only run on `main` pushes
and tags.

| Workflow | Trigger | Writes to | Purpose |
|----------|---------|-----------|---------|
| `ci.yml` | `push` to `main`/`master`, every `pull_request`, `workflow_dispatch` | – (read-only) | Lint + test matrix |
| `coverage.yml` | `push` to `main`/`master`, `workflow_dispatch` | `.github/badges/coverage.svg` | Self-hosted coverage badge |
| `release.yml` | tag `v*.*.*`, `workflow_dispatch` | GitHub Releases, PyPI (opt-in) | Build, verify version, publish |

### Continuous integration (`ci.yml`)

Runs on every push and pull request. Both jobs must pass before a PR can be merged.

```mermaid
flowchart TD
    EVT["push to main<br/>pull_request<br/>workflow_dispatch"] --> CI{{ci.yml}}
    CI --> LINT["lint<br/><i>ubuntu-latest</i>"]
    CI --> TEST["test<br/><i>matrix, fail-fast: false</i>"]

    LINT --> LC["ruff check app tests"]
    LC --> LF["ruff format --check app tests"]

    TEST --> T311["Python 3.11"]
    TEST --> T312["Python 3.12"]
    TEST --> T313["Python 3.13"]
    T311 --> PTC["pip install -r requirements.txt<br/>pytest --cov=app --cov-report=term-missing"]
    T312 --> PTC
    T313 --> PTC

    LF --> GREEN([All jobs green])
    PTC --> GREEN
```

- **`concurrency`** cancels superseded runs (`cancel-in-progress: true`), so pushing twice to a
  branch does not queue two full matrices.
- **`fail-fast: false`** keeps all three interpreters running even if one fails — a Python 3.13
  regression must not hide a 3.11 result.
- The test job installs `requirements.txt` (fully pinned) instead of resolving loose ranges, so
  CI exercises exactly the versions the README asks users to install.
- `actions/setup-python` runs with `cache: pip`, keyed off the lock file.

### Coverage badge (`coverage.yml`)

The README badge is **self-hosted**: there is no third-party service, the SVG is generated in
CI and committed back to the repository.

```mermaid
flowchart TD
    PUSH["push to main"] --> WB{{coverage.yml}}
    WB --> GUARD{"head commit message<br/>contains &#91;skip ci&#93;?"}
    GUARD -->|yes| SKIP([skip — avoids an infinite loop])
    GUARD -->|no| COV["pytest --cov=app --cov-report="]
    COV --> GEN["scripts/coverage_badge.py<br/>.github/badges/coverage.svg"]
    GEN --> COMMIT["git-auto-commit-action<br/>chore: update coverage badge &#91;skip ci&#93;"]
    COMMIT --> PUSH
```

The `[skip ci]` sentinel in the commit message is what breaks the loop: the badge commit
itself triggers `push`, but the `if:` guard on the job filters it out.

### Release (`release.yml`)

Triggered by a semver tag. The build job is read-only; the GitHub Release and the PyPI publish
hang off it as dependent jobs.

```mermaid
flowchart TD
    TAG["push tag v*.*.*"] --> BUILD{{build}}
    BUILD --> VERIFY["verify tag == pyproject version"]
    VERIFY --> BLD["python -m build -> dist/"]
    BLD --> UP["upload-artifact: dist"]
    UP --> GHR{{github-release}}
    UP --> PYPI{{publish-pypi}}
    GHR --> DL["download-artifact: dist"]
    DL --> REL["softprops/action-gh-release<br/>dist/* + generated notes"]
    PYPI --> GATE{"vars.PUBLISH_TO_PYPI == 'true'?"}
    GATE -->|no| OFF([skipped — opt-in])
    GATE -->|yes| PUB["pypa/gh-action-pypi-publish<br/>OIDC / Trusted Publisher"]
```

- **Fail fast on mismatched versions.** `build` reads `[project].version` from `pyproject.toml`
  with `tomllib` and exits if it differs from the tag (minus the leading `v`). A release can
  never ship artefacts whose metadata disagrees with the tag.
- **GitHub Release** attaches `dist/*` and uses `generate_release_notes: true`.
  Tags containing `-rc` / `-beta` / `-alpha` are automatically marked as pre-releases.
- **PyPI publishing is opt-in.** The `publish-pypi` job only runs when the repository variable
  `PUBLISH_TO_PYPI` is `true`; it authenticates via OIDC (`id-token: write`) and a GitHub
  Environment named `pypi`, so no long-lived token is stored. See
  [Releasing](../README.md#releasing).

### Dependency updates

Dependabot (`.github/dependabot.yml`) opens at most 5 PRs, groups all `pip` and all
`github-actions` bumps into two PRs, and **ignores packages that are pinned transitively**
(`marshmallow`, `websockets`, `pydantic-core`, `uuid-utils`, `llama-cloud`). Those must move in
lock-step with their parents, so the correct procedure is to re-freeze the lock
(`pip install -U <pkg> && pip freeze`) rather than accept a PR.

> **Branch protection.** `main` is protected by a repository rule: direct pushes are rejected
> and changes must land through a pull request that passes the `ci.yml` checks.

---

## Testing strategy

All tests run **offline** (no API keys, no network):

- `test_graph.py` — full graph execution with `FakeListChatModel`, routing and the loop cap.
- `test_critic.py`, `test_utils.py` — deterministic heuristics and benchmarking.
- `test_parser.py`, `test_report.py`, `test_tools.py`, `test_config.py` — I/O edges with
  monkeypatched dependencies.
- `test_cli.py` — the CLI against a fake graph.
- `test_i18n.py`, `test_ui.py` — translation parity and a Streamlit smoke test (`AppTest`).

Coverage is measured with `pytest-cov` and enforced at 88% (`[tool.coverage.report]`).
