# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **A recommendation policy that reflects materiality, not a flag count.** The supervisor now
  receives a deterministic screen (`INVEST` / `DEEP AUDIT` / `REJECT`) computed from the evidence:
  a failing benchmark rejects, an uncomputable one defers, and a company at several times the
  benchmark can carry a contradiction as a condition. The memo must state that verdict, and if the
  model writes another one the bold verdict is replaced — the document never contradicts the
  recommendation the product shows next to it.
- Three new bundled decks: Artisan AI, Figure AI and TensorWave.

### Fixed

- The critic no longer raises a Red Flag for a metric the deck simply omits: omissions go to
  `critic_feedback` as verification tasks, and a flag now needs quoting evidence that contradicts
  the claim.
- Headcount read from the web prefers an explicit `Team Size: N` over the top of a LinkedIn band
  (`51-200 employees` used to become 200), and a number above 100 000 is discarded as a parsing
  accident — both produced a wrong ARR/employee benchmark.
- When the deck states no headcount, the benchmark uses the external figure and says so.

### Added

- **The PDF is a report, not a printout.** It opens with a cover: report type, company, date, a
  colour-coded recommendation (INVEST / DEEP AUDIT / REJECT), four key figures and a table of
  contents; every following page carries a running header and a page number. Tables get a navy
  header row and zebra striping, quotes render as callout boxes.

### Fixed

- Metric values lose the deck's own markdown (`## **Business model** …`) before they reach a
  table or the report cover: the dashboard showed the formatting instead of the fact.

### Changed

- **The run button is disabled until there is something to analyse** — an uploaded deck or a
  chosen sample — with the reason as its tooltip.
- **Details are collapsed by default**: the step-by-step analysis panel, and the memo's
  *Market Analysis* section, which opens only when a reader wants the reasoning.
- The offline demo no longer mixes the recorded market notes (about another company) into a
  deck-aware run, and its memo is cleaned before rendering: no deck `##` headings, no
  `[NOT_FOUND]` tokens, money formatted, and no phantom red flag from a literal "none".
- The demo video now shows an **INVEST** run (Cursor), holds on the report's cover for six
  seconds, and shows the PDF pages statically — no zoom, no pan.

### Added

- **A narrated demo video** (`docs/media/demo.mp4`): a real session — sample deck, live run,
  verdict, red flags, memo and the PDF — with a professional English voiceover, title and outro
  cards. Reproducible with `scripts/make_demo_video.py` (records the session and the screenshots)
  and `scripts/build_demo_video.py` (synthesises the narration, cuts the segments and muxes them).

### Changed

- **A landing screen for investors, not for engineers.** The first screen now says what the
  product does and what the reader gets — "Investment due diligence in minutes", three value
  cards, a three-step "How it works" — with no framework or vendor names anywhere in the UI
  (a test enforces that). The run flow reads as a business process: *reading the figures*,
  *checking claims against public sources*, *benchmarking revenue per employee*, *writing the
  memo*. Results lead with the recommendation, the tables have real column headers, and the
  step chips disappear once the analysis is done.
- Screenshots in the README and the wiki were re-recorded from the new interface.

### Fixed

- **No more black boxes in the PDF.** ReportLab's built-in fonts only encode cp1252, so any
  character outside it (Cyrillic names, arrows, emoji) was drawn as a tofu square. The renderer
  now registers a real Unicode font (DejaVu Sans; installed in the container image, found on
  macOS and Windows), maps typographic characters to plain equivalents (`→` → `->`), and strips
  emoji before layout. `app/textsafe.py` holds the mapping; a test asserts the extracted text
  contains nothing the font cannot draw.

## [0.3.0] - 2026-10-26

### Added

- **The repository is a GitHub Action** (`action.yml`): point it at a pitch deck and it writes the
  PDF memo, the Markdown memo, the full state JSON and a short Markdown summary sized for a pull
  request. A workflow can post that summary with `gh pr comment --body-file` and keep the memo as
  an artifact.
  - `offline: auto` (the default) falls back to the rule-based agents when neither
    `OPENAI_API_KEY` nor `ANTHROPIC_API_KEY` is set, so the action works in a repository with no
    secrets and never pretends a model ran.
  - The action installs its own pinned `requirements.txt`, so a consumer's lockfile cannot change
    the analysis, and it writes files only — commenting stays in the caller's workflow, which is
    why the action needs no token.
  - `scripts/action_entrypoint.sh` maps inputs to the CLI, resolves paths, publishes `$GITHUB_OUTPUT`
    and appends the summary to `$GITHUB_STEP_SUMMARY`.
  - `examples/github-action.yml` is a copyable workflow; this repository dogfoods the action in
    `.github/workflows/due-diligence-demo.yml`, which comments on pull requests that touch a deck
    or the action.
- **`duedil --comment-file FILE`** writes the same short summary from the CLI, and
  **`duedil --offline`** runs the rule-based agents on any deck without keys or network — with no
  canned market notes, so the memo never quotes evidence about a different company.
- `tests/test_comment.py` and `tests/test_github_action.py` pin the summary format, the action's
  interface (inputs, outputs, SHA-pinned `uses`) and the workflows that demonstrate it.

### Security

- Every artefact the CLI writes now passes through `app/redact.py`: credential-shaped strings
  (`sk-…`, `lsv2_…`, `tvly-…`, `llx-…`, `ghp_…`) are replaced with `[REDACTED]` in the Markdown
  memo, the PDF, the JSON state and the pull-request summary, so a provider error quoted into the
  memo cannot leak a key into a build artifact. The model label — which comes from an environment
  variable — is validated before it is written.

### Changed

- The README roadmap and the wiki's extension notes now link to the GitHub issues that track
  them (#79–#88), so the plan and the tracker cannot drift apart.

### Fixed

- The coverage-badge workflow no longer pushes `chore/coverage-badge` when the badge is already
  current. It used to create a branch pointing at the same commit as `main` on every push, then
  fail to open a pull request ("No commits between …"), leaving a stray branch behind.

## [0.2.1] - 2026-10-24

### Changed

- Routine dependency refresh: `langchain-core` 1.6.13, `langsmith` 0.14.12, `nltk` 3.10.4,
  `httpcore2`/`httpx2` 2.16.0 and the rest of the grouped bump. `anthropic` stays at 1.15.0:
  `langchain-anthropic 1.7.6` requires `anthropic<2.0.0`, so the major is blocked in
  `.github/dependabot.yml` until the integration supports it.
- Grouped action bumps (`actions/setup-python`, `github/codeql-action`, the coverage, release and
  docs workflows), with the Docs workflow's actions pinned by commit SHA like every other workflow.
- `requirements.txt` explains the two security pins inline (`pillow==13.0.0`, `pypdf==6.21.2`).

## [0.2.0] - 2026-10-23

### Added

- **[Answer Quality & Guardrails](docs/wiki/Answer-Quality.md)**: how the project decides whether
  an LLM answer is trustworthy — the failure modes, the mechanism that catches each one, and the
  exact place in the code (`app/graph.py:184` for the deterministic rules, `app/graph.py:62` for
  tolerant JSON parsing, `app/graph.py:328` for the fallback memo, `app/prompts.py:14` for the
  `[NOT_FOUND]` contract, and so on) — plus an honest note on what is *not* measured yet.
  `tests/test_answer_quality_docs.py` fails when a cited line stops containing the cited symbol.


- **Entry-point routing in the README**: a "Choose your path" table for the three readers —
  visitor, engineer, operator — a Mermaid diagram of the graph, and a documentation map that says
  which page answers which question.
- **Docs as code**: `scripts/validate_docs.py` (standard library only) checks local links and
  anchors, ADR structure, wiki metadata, the generated reference page and the project's wording
  rules; the `Docs · links + ADR` workflow runs it on every push and pull request, and the test
  suite runs the same validator.
- **ADRs**: `docs/adr/` with four backfilled decisions (five-node pipeline, hybrid Red-Flag
  engine, `[NOT_FOUND]` contract, container/network posture) plus `docs/VERSIONING.md` and
  `docs/OWNERS.md`.
- **Wiki restructured for findability**: a four-block sidebar (Start / How it works / Operate /
  Reference), new [Recipes](docs/wiki/Recipes.md) and [Glossary](docs/wiki/Glossary.md) pages, and
  a [Reference](docs/wiki/Reference.md) page generated from `env.example`, `app/cli.py` and
  `scripts/` by `scripts/make_wiki_reference.py` (`make wiki-reference`). Every page now states its
  owner and when it was last reviewed.


- **Per-developer instances**: `./scripts/project.sh instance [auto|<name> [port]]` writes
  `COMPOSE_PROJECT_NAME` and `DUEDIL_PORT` into `.env`, so several developers can run the stack on
  one server without sharing containers, volumes or ports. Names are always namespaced
  (`duedil-agent-<name>`).
- **`scripts/personal-sync.sh`** (`status` / `pull` / `push`): moves the gitignored personal files
  (`.env`, `Run_Stop_Project.docx`) between the server and a laptop with plain `scp`, which works
  from PowerShell, Git Bash, WSL, macOS and Linux.
- **Extended Run & Stop guide** (13 sections): SSH keys for a new laptop, Dev Containers on the
  server versus locally, several developers on one server, environment synchronisation, one
  developer with several laptops, cloning plus personal files, DeepSeek Harness access through an
  SSH tunnel, and a security chapter (fail2ban, ufw, secrets, auditing).


- **Bundled example decks in the demo**: the sidebar's **📂 Browse examples/** button opens a
  dialog listing the five decks from `examples/` (`airbnb`, `uber`, `cursor`, `lovable`,
  `cognition`), so the hosted demo runs without the visitor having a PDF to hand. Picking a deck
  prefills the matching website URL; an upload always wins over a remembered example. The listing
  is rendered by the app because `st.file_uploader`'s own dialog can only see the visitor's
  filesystem, never the server's.
- **Model attribution everywhere**: the run summary, the CLI (`Model used : gpt-4o (OpenAI)`) and
  the exported PDF footer all state which model produced the analysis. The extractor records it in
  `VentureState.used_model`.
- **Reader-friendly results**: `app/display.py` renders the extracted metrics and the financial
  audit as tables (money grouped, ratios as `0.86× the benchmark`, missing figures labelled
  `— (not in the deck)`), and the audit's conclusion gets its own highlighted callout separated
  from the figures. `tests/test_display.py` covers the formatting rules.

### Changed

- **The published port binds to `127.0.0.1` by default** (`DUEDIL_BIND`): the app is no longer
  reachable from the network unless someone asks for it with `DUEDIL_BIND=0.0.0.0`.
- **`container_name` is gone** and the compose project name comes from
  `${COMPOSE_PROJECT_NAME:-duedil-agent}`, which is what makes a second checkout on the same host
  possible. The scripts resolve the container id from compose instead of assuming a name.


- The demo screenshots and the offline walkthrough video were re-recorded against the new UI
  (22 s, example picker visible).
- `find_team_mentions` also recognises `engineers` and `researchers` as headcount claims, which
  technical decks use.
- Test behaviour no longer depends on a developer's `.env`: `conftest.py` clears
  `LLAMA_CLOUD_API_KEY`, exactly as it already did for tracing.

### Added

- **Explicit container control**: `scripts/project.sh` (Linux/macOS/WSL) and
  `scripts/project.ps1` (Windows) with the same commands — `start`, `stop`, `restart`,
  `status`, `logs`, `build`, `rebuild`, `shell`, `cli`, `clean`, `autostart` — plus
  one-line wrappers `start.sh` / `stop.sh` / `start.cmd` / `stop.cmd` in the repository
  root and matching `make up|down|status|logs|shell` targets.
- **VS Code dev container**: `.devcontainer/devcontainer.json` reuses the compose service
  `ui`, so the dev environment is the deployed image (pinned dependencies, non-root user),
  with `/app/.venv` providing ruff and port 8501 forwarded.
- `scripts/make_run_stop_doc.py` generates `Run_Stop_Project.docx`, a personal walkthrough
  of starting and stopping the stack. The document is gitignored on purpose.

### Changed

- **The stack no longer starts on its own.** `restart: "no"` replaced
  `restart: unless-stopped` on the UI service, and the compose project is pinned to the
  name `duedil-agent`. Verified by restarting the Docker daemon with the stack up: the
  container stays `Exited (0)`. Stopping frees port 8501; the data volume is kept.

### Security

- **`pillow` 12.3.0 → 13.0.0**: 41 open Dependabot advisories against the pinned version were
  only fixed in 13.0.0 (heap overflows in JPEG/TIFF decoding, Ghostscript argument injection,
  several denial-of-service paths). `streamlit` 1.66.0 pinned `pillow<13`, so the ceiling was
  blocking the fix; **`streamlit` 1.66.1** relaxes it to `pillow<14`, which makes the upgrade
  possible. The Dependabot ignore rule that kept `pillow` at 12.x is removed.
- **`pypdf` 6.21.1 → 6.21.2**: three high-severity advisories about long runtimes on malformed
  cross-reference tables and repeated missing objects.

### Fixed

- **The hosted demo no longer answers the same thing for every deck.** Without API keys
  the real nodes cannot run, so the app fell back to a static memo and every example
  produced `Investment Memo — Unknown Startup`. `app/ui.py` now detects that no LLM is
  configured (or honours `DUE_DIL_OFFLINE_MODE`) and switches to rule-based agents that
  read the deck it was given, with an on-screen notice that no model ran. The five
  example decks now produce five different analyses (Lovable: ARR `$100M`, 146 people,
  `6.85×` the benchmark).
- `app/offline_agents.py`: the deterministic Extractor/Supervisor behind that mode. It
  reads titles, amounts and headcounts from the deck text and reports anything the deck
  does not state as `[NOT_FOUND]` rather than guessing.
- Offline artefacts no longer claim a model ran: the memo/PDF byline reads
  `offline rules, deck_aware (no model)`.
- `extract_company_name` accepts a plain-text title as well as a Markdown heading. The
  `pypdf` fallback (used where `LLAMA_CLOUD_API_KEY` is absent, e.g. the hosted demo)
  does not emit `#`, which is how the demo ended up calling every deck "Unknown Startup".

- Added `tests/test_call_signatures.py`: it walks the AST of `app/` and fails when a call passes
  a keyword argument that no definition accepts. It reproduces the incident where a hosted
  deployment served a new `app/ui.py` with a stale `app/report.py` (same file and line number),
  so the mismatch is now caught in CI rather than by a visitor. The wiki's Troubleshooting page
  documents how to identify and clear that stale-deployment state.

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

[Unreleased]: https://github.com/SergeyGer/duedil-agent/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/SergeyGer/duedil-agent/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/SergeyGer/duedil-agent/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/SergeyGer/duedil-agent/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/SergeyGer/duedil-agent/releases/tag/v0.1.0
