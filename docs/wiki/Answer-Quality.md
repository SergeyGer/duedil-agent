# Answer Quality and Guardrails

How this project decides whether an LLM answer can be trusted, and what stops an unreliable
result from reaching the memo. Every mechanism below is a line of code or a test, not a promise.

*Last reviewed: 2026-10-23 · Owner: [@SergeyGer](https://github.com/SergeyGer)*

## What "quality" means here

An investment memo is only useful if a reader can tell **what was verified** from **what was
claimed**. Three properties follow from that, and each has a mechanism:

| Property | Meaning | Where it is enforced |
|---|---|---|
| **Groundedness** | Every figure in the memo is either corroborated by external evidence or explicitly marked as absent | `app/graph.py:184` (rules), `app/utils.py:46` (`is_missing`), `app/prompts.py:14` (`[NOT_FOUND]` contract) |
| **Traceable reasoning** | Each run leaves a record of what every node received and produced | `VentureState` + `progress_log`, LangSmith traces, `used_model` |
| **Graceful degradation** | A model outage, a bad key or a missing parser produces an honest weaker answer, never a fabricated one | `app/graph.py:328` (fallback memo), `app/offline_agents.py`, `app/parser.py` |

There is deliberately **no "confidence score"**. A number invented by an LLM to describe its own
confidence is exactly the kind of unverifiable output this project exists to avoid.

## Threat model: the ways an LLM answer goes wrong

| Failure mode | What it looks like | Mechanism that catches it | Test |
|---|---|---|---|
| **Hallucinated figure** | The deck says nothing about revenue; the model returns `"$1.2M"` | Prompt contract returns `[NOT_FOUND]`; `is_missing()` treats it as absent; the financial audit then reports it *cannot* compute efficiency instead of inventing one | `tests/test_utils.py::test_financials_missing_arr` |
| **Invented source** | "According to TechCrunch…" with no such source | The Critic only sees the *scraped* market text, and the memo is built from the state; claims are cross-checked against that text, not against the model's memory | `tests/test_graph.py`, `tests/test_critic.py` |
| **Silent gap** | A missing metric simply disappears from the memo | `[NOT_FOUND]` propagates through state → benchmark → memo → UI (`— (not in the deck)`) | `tests/test_offline_agents.py::test_figures_the_deck_does_not_state_are_reported_as_missing` |
| **Unchecked claim** | "We are the market leader" with no traffic | Leadership keywords (`app/graph.py:45`) + traffic peak `< 5 000` → Red Flag (`app/graph.py:216`) | `tests/test_critic.py::test_deterministic_leadership_vs_traffic` |
| **Implausible team size** | "300 employees" against external evidence of 15 | Rule: a 5× mismatch in either direction raises a flag (`app/graph.py:196`, `:201`) | `tests/test_critic.py::test_deterministic_team_mismatch` |
| **Runaway loop** | Critic keeps asking for more scraping | `MAX_CRITIC_LOOPS = 2` (`app/graph.py:42`), enforced by `route_after_critic` (`app/graph.py:280`) | `tests/test_graph.py::test_graph_loop_is_capped` |
| **Malformed JSON** | The model wraps JSON in prose or code fences | `_safe_json` (`app/graph.py:62`) strips fences and extracts the outermost object, returning `{}` rather than raising | `tests/test_graph.py::test_safe_json_variants` |
| **Model outage** | Timeout, `429`, revoked key | Node catches the exception, logs it, and the Supervisor writes the deterministic memo (`app/graph.py:328`) marked `_(Generated without LLM: …)_` | `tests/test_graph.py::test_graph_survives_llm_failure` |
| **Silent model drift** | A different model produced the memo and nobody noticed | `used_model` is recorded by the extractor and stamped into the memo, the CLI and the PDF footer | `tests/test_display.py` |

## The path of one figure

This is the concrete chain that turns a string in a deck into a line in a memo:

1. **Extraction** — `agent_extractor` (`app/graph.py:89`) sends the deck to the model with
   `EXTRACTOR_SYSTEM` (`app/prompts.py:9`): return *one JSON object*, with the literal string
   `[NOT_FOUND]` for any field the deck does not state, and "empty or ambiguous information →
   `[NOT_FOUND]`" (`app/prompts.py:32`). The reply goes through `_safe_json`; a parse failure
   yields `{}`, not an exception.
2. **Verification** — `agent_scraper` collects external text (Tavily). `agent_critic`
   (`app/graph.py:229`) sends claims + market text to `CRITIC_SYSTEM` (`app/prompts.py:35`),
   which explicitly lists "[NOT_FOUND] metrics any serious investor would demand" as a finding.
3. **Deterministic cross-check** — the same node merges `_deterministic_flags`
   (`app/graph.py:184`), which runs regardless of what the model said: team-size mismatch,
   leadership vs traffic, missing ARR (`app/graph.py:223`). A rule cannot be argued away by a confident model.
4. **Benchmarking** — `compute_financials` (`app/utils.py:101`) compares ARR ÷ headcount against
   `DEFAULT_ARR_PER_EMPLOYEE_BENCHMARK = 100 000` (`app/utils.py:13`). If either input is missing,
   the verdict is literally *"Cannot compute efficiency"* (`app/utils.py:125`) — a result, not a gap.
5. **Synthesis** — the Supervisor gets metrics, benchmarks, market text and flags as JSON
   (`_build_context`, `app/graph.py:309`) and writes the six fixed sections
   (`SUPERVISOR_SYSTEM`, `app/prompts.py:62`), which require the model to say so when data is
   missing.

## Determinism where it matters

| Lever | Choice | Where |
|---|---|---|
| Sampling | `temperature = 0.0` by default | `app/config.py:55` |
| Retries / timeout | 2 retries, 120 s — bounded, visible failures | `app/config.py:44` |
| Loop budget | 2 critic passes, then the graph must finish | `app/graph.py:42` |
| Rule thresholds | constants in code, not in a prompt | `app/graph.py:45`, `app/utils.py:13` |
| Dependencies | fully pinned `requirements.txt`; the container installs exactly it | `requirements.txt`, `Dockerfile` |
| Model identity | `used_model` recorded and displayed | `app/graph.py:89`, `app/display.py` |

Two runs of the same deck with the same model and the same web data should produce the same
flags. Where they cannot (live search results change), the memo still shows *which* evidence was
used, so a difference is explainable.

## Offline mode: quality without a model

When no API key is configured — the hosted demo — the LLM nodes are replaced by deterministic
agents (`app/offline_agents.py`): `OfflineExtractorLLM` reads titles, amounts and headcounts by
rule (`app/offline_agents.py:243`), and `OfflineSupervisorLLM` assembles the memo from that
reading (`app/offline_agents.py:383`). The
pipeline is the same; only the reader changes. The UI states that no model ran, and the memo
byline says `offline rules, deck_aware (no model)` — a weaker answer that is honest about being
weaker.

## How we measure it today

| Measurement | What it proves | Where |
|---|---|---|
| Unit tests on the rules with fixed inputs | thresholds fire exactly at the documented values | `tests/test_critic.py`, `tests/test_utils.py` |
| Graph tests with a fake LLM | routing, loop cap, JSON tolerance, survival of an LLM failure | `tests/test_graph.py` |
| Five real-company decks with known readings | the same class of deck produces the same *kind* of finding (Lovable: ARR `$100M`, 146 people, 6.85× the benchmark; Cognition: no ARR → "cannot compute") | `examples/`, `tests/test_offline_agents.py` |
| Coverage gate | 88 % of `app/` must be executed by tests; currently ~92 % | `pyproject.toml:101` |
| Static and dependency gates | CodeQL, ruff, Dependabot | `.github/workflows/`, `.github/dependabot.yml` |
| Trace review | a human can open any run and see each node's input/output | LangSmith (`LANGSMITH_TRACING`) |

**What is *not* measured yet:** there is no automated LLM-as-judge evaluation of memo quality, and
no golden-memo regression corpus. Quality today is enforced by contracts, deterministic
cross-checks and tests — not by scoring the prose. This is the honest gap, and it is on the
roadmap as *"an evaluation harness with golden memos to track analysis quality over time"* —
[issue #83](https://github.com/SergeyGer/duedil-agent/issues/83).

## If you change a prompt or a rule

1. **A prompt change needs a test that would fail without it.** The `[NOT_FOUND]` contract, for
   example, is asserted in `tests/test_utils.py`, `tests/test_offline_agents.py` and via the CI
   documentation check.
2. **A threshold change is a product decision**: update `app/graph.py` or `app/utils.py`, the
   matching test, and say in the PR which evidence motivated it (see
   [Ownership](../OWNERS.md)).
3. **Never let a model's output bypass a rule.** The rules run after the model, on state — that
   ordering is the safeguard.
4. **Run the real decks** (`make demo`, or the CLI on `examples/*.pdf`) before merging: the unit
   tests use fixed inputs, and the decks are the closest thing to a live run.

## Code map

| Concern | File |
|---|---|
| Nodes, routing, loop cap, fallback memo | `app/graph.py` |
| Prompt contracts (`[NOT_FOUND]`, JSON-only, memo structure) | `app/prompts.py` |
| Parsing helpers, benchmark, thresholds | `app/utils.py` |
| Deterministic agents for the no-key path | `app/offline_agents.py` |
| Model selection, temperature, retries | `app/config.py` |
| Result rendering (what a reader sees) | `app/display.py` |
| Rule and graph tests | `tests/test_critic.py`, `tests/test_graph.py`, `tests/test_utils.py` |
| Decisions behind these choices | [ADR 0002](../adr/0002-hybrid-red-flag-engine.md), [ADR 0003](../adr/0003-not-found-contract.md) |
