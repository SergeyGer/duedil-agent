# 0001 — Five-node LangGraph pipeline with a bounded critic loop

## Status

Accepted


## Context

Due diligence is a sequence of dependent steps: read the deck, gather external evidence,
benchmark the numbers, challenge the claims, write the memo. Doing that in one prompt makes the
result unreviewable — nobody can tell which claim was checked, and the same deck produces a
different memo on every run.

We also needed the pipeline to terminate for any input, with a trace that shows what happened.

## Decision

Model the work as an explicit LangGraph state machine with five nodes — **Extractor → Scraper →
Financial → Critic → Supervisor** — and one back-edge: the Critic may send the graph to the
Scraper again, hard-capped at `MAX_CRITIC_LOOPS = 2`. State is a `TypedDict` (`VentureState`)
with a reducer on `progress_log`, so every node appends to the audit trail without clobbering
the others.

## Consequences

* Every step is a separate function with its own tests; the graph wiring is tested with a fake
  LLM.
* The cap guarantees termination; the second pass exists because external data often contradicts
  a first scrape.
* Costs a little latency (two scrape passes on contested decks) and more state plumbing than a
  single agent with tools.
* Adding a node changes the graph contract, so it is a deliberate act, not an accident.

*Last reviewed: 2026-10-23 · Owner: [@SergeyGer](https://github.com/SergeyGer)*
