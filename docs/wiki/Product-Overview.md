# Product Overview

## The problem

A first-pass technology due-diligence review is slow and inconsistent. An analyst re-reads the
pitch deck, searches for the founders, checks the competitors, sanity-checks the revenue
figures and writes a memo — and two analysts produce two different memos from the same deck.

The expensive part is not the writing. It is that **nothing in the deck is verified**, and the
verification is what takes the time.

## What DueDil.Agent does

Given a startup's pitch deck (PDF) and its website URL, the system produces a structured
investment memo:

1. **Extracts** the claimed metrics from the deck — company, sector, ARR, MRR, headcount, TAM,
   founders, business model, leadership claims.
2. **Verifies** them against live web data — competitors, website traffic, founder footprint,
   LinkedIn headcount.
3. **Benchmarks** the financials — `ARR / headcount` against the B2B-SaaS norm
   (>$100k per employee) with an explicit verdict.
4. **Cross-checks** every claim and accumulates **Red Flags**, combining LLM reasoning with
   deterministic rules that cannot be talked out of a contradiction.
5. **Writes** a Markdown memo — summary, metrics, market, financial audit, risks,
   recommendation — exported as a styled PDF.

The output recommendation is one of `INVEST`, `DEEP AUDIT` or `REJECT`.

## The core design principle: never trust the deck

| Situation | Behaviour |
|---|---|
| A figure is in the deck | Attributed to the deck, then checked externally when a source exists. |
| A figure is missing | Reported as `[NOT_FOUND]` and raised as a Red Flag — never guessed. |
| The deck contradicts external data | Flagged with both numbers quoted (e.g. claimed 14 employees vs. ~1 on LinkedIn). |
| An external call fails (no key, timeout, bad response) | Degrades to a deterministic memo instead of crashing the run. |
| A claim is unverifiable | Stated as unverifiable — not as false, and not as true. |

This matters because the failure mode of an LLM analyst is not "no answer" — it is a
confident, plausible, invented answer.

## Who it is for

| Role | Use |
|---|---|
| Investment analyst / associate | Compress the first pass to minutes; the memo is the starting point, not the conclusion. |
| Venture fund operations | A repeatable artefact per deal for the file, with the evidence trail attached. |
| Startup / founder (other side of the table) | Pre-check how a deck reads before sending it out. |
| Engineer / researcher | A worked example of a hybrid LLM + deterministic agent graph with a bounded loop. |

## What it is not

- **Not investment advice.** The output is machine-generated and may be wrong; it is a
  first-pass artefact that a human must verify. See [Security & Limits](Security-and-Limits).
- **Not a data room.** It reads public web data and one deck; it does not do cap-table,
  legal, or financial-statement diligence.
- **Not a single prompt.** The pipeline is an explicit graph with typed state, so every step
  is inspectable, testable in isolation, and reproducible.

## Product surface

| Surface | What you get |
|---|---|
| **Streamlit UI** | Upload a deck, watch the five agents run step by step, read the memo, download the PDF. Four UI languages (EN / DE / FR / RU). |
| **CLI** | `python -m app.cli deck.pdf https://startup.example` — writes PDF / Markdown / JSON, scriptable in batch. |
| **Python API** | `run_due_diligence(...)` returns the full typed state for use inside a larger system. |
| **Docker** | `docker compose up --build` — one command, no local Python. |

Details: [Interfaces](Interfaces) · [Installation & Deployment](Installation-and-Deployment)

## Non-functional properties

| Property | Value / mechanism |
|---|---|
| Determinism of the fallback path | Fully deterministic memo when no LLM is reachable. |
| Termination guarantee | The critic loop is hard-capped at `MAX_CRITIC_LOOPS = 2`. |
| Offline testability | The whole suite runs with no API keys and no network. |
| Coverage | 79 tests, **90.1 %** line coverage of `app/`; CI fails below **88 %**. |
| Static analysis | CodeQL (`security-and-quality`) on every push and PR, plus a weekly scan. |
| Supply chain | Every GitHub Action pinned to a commit SHA; Dependabot tracks updates weekly. |
| Failure mode | Graceful degradation everywhere; a missing key narrows the analysis, it does not fail the run. |

## Verified end-to-end behaviour

Two documented runs ship with the repository (see the [README demo section](https://github.com/SergeyGer/duedil-agent#demo)):

| Run | Inputs | Result |
|---|---|---|
| **Live** | Real `gpt-4o`, Tavily, LlamaParse | 12 Red Flags, two critic passes, **REJECT** |
| **Offline** | Canned LLM + search, real graph and heuristics | 13 Red Flags, **REJECT**, fully reproducible |

The offline run exists so the pipeline can be demonstrated, recorded and regression-checked
without spending tokens or depending on the network. It stubs exactly two boundaries — the LLM
and the search tool — and runs every other line of production code.
