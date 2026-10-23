# 0002 — Red Flags come from an LLM **and** deterministic rules

## Status

Accepted


## Context

The Critic has to decide whether a deck is credible. An LLM is good at reading a claim in
context ("ARR of $1.2M on 14 people") and bad at guarantees: it forgets a rule, phrases the same
finding differently every run, and cannot be unit-tested. Pure rules are the opposite — precise
and repeatable, but blind to claims nobody thought to encode.

## Decision

Run both, and merge the results:

1. an **LLM critic** returns structured findings and a `critic_feedback` string that can trigger
   a second scrape;
2. a set of **deterministic rules** in `app/utils.py` and the Financial/Critic nodes cover the
   checks that must never be missed — team-size mismatch (≥ 5× the external headcount), claimed
   leadership against a traffic peak below 5 000 visits, missing ARR.

Rules are pure functions with explicit thresholds and their own tests; the merged list is what
the memo reports.

## Consequences

* The deterministic part is testable and stable; the LLM part adapts to decks nobody anticipated.
* A failing rule cannot be argued away by a confident model.
* Two sources can disagree — the memo shows both rather than hiding the conflict.
* Thresholds are now a maintained asset: changing one is a reviewed decision, not a prompt tweak.

*Last reviewed: 2026-10-23 · Owner: [@SergeyGer](https://github.com/SergeyGer)*
