# Design Decisions

Every entry below is a decision that could reasonably have gone the other way. The trade-off is
stated explicitly, because a decision without its cost is just a preference.

## 1. An explicit graph, not an autonomous agent

**Decision:** five nodes with a typed state and one bounded cycle, instead of a single
ReAct-style loop with tools.

**Why:** a due-diligence artefact has to be explainable to a third party. With a graph, the
cost is bounded (≤ 11 LLM calls), every step is individually testable, and the state carries an
audit trail. Free-running agents optimise for flexibility; this problem needs reproducibility.

**Cost:** less flexible — a new capability means a new node or an edited prompt, not a new tool
the model discovers.

## 2. The critic loop is capped at two passes

**Decision:** `MAX_CRITIC_LOOPS = 2`, hard-coded.

**Why:** "one pass" gives the critic no chance to act on its own findings; "until clean" does
not terminate, because a critic that always finds something new will loop forever. Two passes
means the second search is *targeted* by `critic_feedback`, which is where most of the extra
signal comes from (7 → 13 flags in the shipped demo).

**Cost:** a genuinely hard case might benefit from a third pass; the cap trades that away for a
guaranteed cost and latency ceiling.

## 3. Hybrid Red-Flag detection

**Decision:** LLM judgement **plus** deterministic rules, in the same node.

**Why:** LLM judgement catches narrative contradictions arithmetic cannot; deterministic rules
catch the obvious contradictions the model might miss on a bad day. Neither is sufficient
alone, and the deterministic half costs nothing and is exactly reproducible.

**Cost:** two sources of flags can overlap, so deduplication is required (it is a one-line list
comprehension, but it is a real step).

## 4. Metrics are strings in the state

**Decision:** `ExtractedMetrics` holds strings (`"$1.2M"`, `"12-15"`), not numbers.

**Why:** the deck is prose. Normalising at extraction time would hide the LLM's uncertainty
inside a number; keeping the raw claim means a reviewer can always compare it with the source.
Parsing happens once, in `app/utils.py`, where it is unit-tested to death.

**Cost:** every consumer must parse before comparing — acceptable, because parsing is
centralised and covered by tests.

## 5. Graceful degradation instead of failing fast

**Decision:** every external call is wrapped; a missing key or a failed request yields a
narrower analysis and a deterministic fallback memo.

**Why:** the artefact is more useful incomplete than absent. A memo that says "market data
unavailable" is honest; a stack trace is not. It also makes the entire test suite runnable
offline, which is what keeps it fast and free.

**Cost:** a misconfiguration can go unnoticed for a while, because the pipeline still
"works" — mitigated by writing the reason into the memo and into `progress_log`.

## 6. Separation of graph and rendering

**Decision:** the graph emits Markdown; PDF generation lives in `app/report.py`.

**Why:** ReportLab is a heavy dependency with its own failure modes. Keeping it out of the
graph means the pipeline is testable without it, and the memo can be consumed as Markdown by
anything else.

**Cost:** one extra module and an explicit conversion step.

## 7. Sequential extractor → scraper

**Decision:** the first two nodes are not parallelised.

**Why:** the scraper needs the company name and sector from the extractor to build meaningful
queries. Parallelising them would mean searching blind.

**Cost:** latency. This is the first thing to revisit with speculative queries — see
[Extending the System](Extending-the-System).

## 8. A `pip freeze` lockfile *and* an unbounded `pyproject.toml`

**Decision:** `requirements.txt` pins exact versions; `pyproject.toml` declares ranges.

**Why:** reproducibility for users (the lockfile) and sanity for the package metadata (ranges).
CI installs the lockfile, so what is tested is what is shipped.

**Cost:** two places to keep coherent — hence `test_tooling_pins.py` and the Dependabot groups
that keep transitive pins moving together.

## 9. Offline demo as a first-class artefact

**Decision:** ship `scripts/demo_offline.py`, which stubs exactly the LLM and the search tool
and runs the production graph.

**Why:** the README can then show a real end-to-end run, the video can be re-recorded at any
time, and contributors can see the whole pipeline without an account anywhere. The stubs are
keyed to the real system prompts, so an edit that breaks the demo is caught immediately.

**Cost:** one more script to maintain, and the canned payloads must be refreshed when prompts
change materially.

## 10. Documentation split: README for people, wiki for engineers

**Decision:** the README answers "what is this and why should I care"; the wiki answers "how
does it work and how do I operate it".

**Why:** the two audiences need different depths. A recruiter or evaluator should reach the
demo and the outcome in seconds; an engineer or PM needs the state machine, the thresholds and
the failure modes. Mixing them satisfies neither.

**Cost:** two artefacts to keep in sync — mitigated by keeping the wiki sources in
`docs/wiki/` and linking rather than duplicating.
