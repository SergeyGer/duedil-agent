# 0003 — Missing data is reported as `[NOT_FOUND]`, never guessed

## Status

Accepted


## Context

Pitch decks are marketing documents: figures are chosen to look good and are sometimes absent on
purpose. An LLM asked to "extract ARR" will happily produce a plausible number when the deck
never states one. For an analysis whose entire value is the evidence trail, an invented figure is
worse than no figure — it silently turns a gap into a fact.

## Decision

The extraction contract uses a literal marker: a value the deck does not state comes back as
`[NOT_FOUND]`. The same token flows through the state, the financial benchmark (which then
reports that efficiency cannot be computed), the memo and the UI, which renders it as
`— (not in the deck)`.

Prompts state the rule; `tests/test_utils.py` and the offline agents assert it; the demo decks
contain deliberate `[NOT_FOUND]` values so the path is exercised on every run.

## Consequences

* The memo can say "cannot compute", which is the honest answer and also a finding.
* Downstream code must handle the marker everywhere — that is the cost, paid once in
  `is_missing()` and the display layer.
* Comparisons between two runs stay meaningful: a gap is visibly a gap.
* A model that ignores the contract is caught by the tests, not by a customer.

*Last reviewed: 2026-10-23 · Owner: [@SergeyGer](https://github.com/SergeyGer)*
