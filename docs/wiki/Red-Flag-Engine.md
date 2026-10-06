# Red-Flag Engine

The Red-Flag engine is the part of the system that decides **what is wrong with the deal**. It
is deliberately hybrid:

> **LLM judgement is powerful but non-deterministic. Deterministic rules guarantee that obvious
> contradictions are always caught, no matter what the model says that day.**

Both streams feed a single deduplicated list in `VentureState.red_flags`.

## Pipeline

```
                ┌──────────────────────────────┐
   metrics ────►│ LLM critic (CRITIC_SYSTEM)   │──┐
   market_data ─┤                              │  │
                └──────────────────────────────┘  ├──► dedupe ──► red_flags
                ┌──────────────────────────────┐  │
                │ deterministic heuristics     │──┘
                └──────────────────────────────┘
```

The two run in the same node, so a failure of one never suppresses the other:

```python
try:
    parsed = _safe_json(llm.invoke([...]))
except Exception as exc:
    parsed = {"red_flags": [], "critic_feedback": f"critic failed: {exc}"}

new_flags = llm_flags + _deterministic_flags(state)   # deterministic part always runs
combined  = existing + [f for f in new_flags if f not in existing]
```

## Deterministic rules

All three rules live in `app/graph.py::_deterministic_flags` and use helpers from
`app/utils.py`. They are unit-tested without an LLM (see `tests/test_critic.py`).

### 1. Team-size contradiction

| | |
|---|---|
| **Inputs** | `metrics["team_size"]` vs. every headcount figure found in `market_data` |
| **Extraction** | `find_team_mentions()` matches `«N» employees / people / staff / team members / headcount`, including `k`/`m` scales |
| **Rule** | flag when the two sides differ by **≥ 5×** in either direction |
| **Why 5×** | search snippets routinely quote ranges (`11-50 employees`) and stale counts. A 2× gap is noise; a 5× gap is a different company. |

```python
if external * 5 <= claimed:      # deck inflates the team
    flags.append(f"Team-size mismatch: the deck claims {claimed} employees but "
                 f"external sources indicate only about {external}.")
elif claimed * 5 <= external:    # deck understates it
    flags.append(f"Team-size mismatch: the deck states {claimed} employees while "
                 f"external sources suggest about {external}.")
```

The strongest real example from the shipped demo: the deck claims **14 employees**, the
LinkedIn block shows **1** associated member → flagged.

### 2. Leadership claim vs. traffic reality

| | |
|---|---|
| **Input** | `claimed_leadership` and `key_claims` matched against a keyword list |
| **Keywords** | `leader`, `market leader`, `#1`, `no.1`, `number one`, `the only`, `dominant`, `best-in-class`, `unrivalled`, `unrivaled` |
| **Trigger** | the claim exists **and** at least one traffic figure is present |
| **Threshold** | flag when the **peak** traffic mentioned anywhere is **< 5 000** visits |
| **Why** | "market leader" and "~26 visits/month" cannot both be true. The rule stays silent when no traffic data was found at all — absence of evidence is not a flag. |

### 3. Missing critical metric

| | |
|---|---|
| **Input** | `metrics["arr"]` |
| **Rule** | flag when `is_missing()` matches: empty, `-`, `n/a`, `none`, `null`, `unknown`, `not found`, `[NOT_FOUND]` |
| **Why** | a revenue-less deck is not a neutral fact; on a seed deck it is the single most important omission. |

Note the asymmetry: rules 1 and 2 require *positive evidence* to fire, rule 3 fires on explicit
absence. That is the only case where "no data" is itself the finding.

## What the LLM adds

The deterministic rules cover contradictions between a number and a number. The critic prompt
covers what arithmetic cannot:

- claims contradicted by narrative context (a "market leader" absent from every competitor list);
- unsupported financials (ARR with no customers, no pricing, no case studies);
- inflated market sizing (a $14B TAM for a niche the search shows as crowded);
- missing maturity signals (no founding year, no funding history, no investors);
- internal inconsistencies between two statements in the same deck.

The LLM is asked for JSON (`{"red_flags": [...], "critic_feedback": "..."}`) and the parser
tolerates code fences and surrounding prose. Malformed output degrades to "no LLM flags",
never to an exception.

## Loop, accumulation and the second pass

1. Pass 1 runs after the first scrape. Flags are stored; `critic_feedback` summarises what is
   disputed.
2. If flags exist and `critic_loops_count < 2`, the router sends the graph back to the scraper.
3. Pass 2 queries the web **about the feedback**, not about the generic template:

   ```python
   queries = [f"{company} {feedback}", f"{company} employees LinkedIn {sector}"]
   ```

4. New flags are appended, existing ones are not duplicated, and `critic_loops_count`
   increments. Once the budget is spent, the router goes to the supervisor.

Consequence: the second pass is *targeted re-verification*, which is why the demo's flag count
grows from 7 (pass 1) to 13 (pass 2) instead of repeating itself.

## How flags influence the recommendation

`_recommendation()` in `app/graph.py` is the deterministic fallback used when the LLM
supervisor is unavailable:

| Condition | Recommendation |
|---|---|
| No flags **and** `ARR/employee ≥ benchmark` | `INVEST` |
| ≥ 3 flags **or** `ARR/employee < benchmark` | `REJECT` |
| otherwise | `DEEP AUDIT` |

When the LLM supervisor *is* available it writes the memo and the recommendation itself, but it
receives `RED FLAGS` as part of its context, so the deterministic findings are always visible
to it. A model that ignores a 14-vs-1 headcount contradiction is contradicted by the state it
was handed.

## Examples from the shipped runs

| Source | Example flag |
|---|---|
| Deterministic (rule 1) | `Team-size mismatch: the deck claims 14 employees but external sources indicate only about 1.` |
| Deterministic (rule 2) | `Implausible leadership: the deck claims market leadership but external traffic data indicates only ~26 visits.` |
| LLM (pass 1) | `The ARR of $1.2M and MRR of $100K seem high given the lack of significant web traffic or notable market presence.` |
| LLM (pass 2) | `There is no evidence of any funding rounds or investors, which raises questions about the financial backing and sustainability.` |

## Testing

| Test file | Covers |
|---|---|
| `tests/test_critic.py` | each deterministic rule, both directions of the team rule, the traffic threshold, the missing-ARR case |
| `tests/test_utils.py` | `parse_number` / `parse_count` / `find_team_mentions` / `find_traffic_mentions` / `compute_financials`, including the `[NOT_FOUND]` token set and `1.200.000`-style separators |
| `tests/test_graph.py` | routing (`route_after_critic`), the loop cap, accumulation and memo fallback with a fake LLM |

The rules are pure functions over the state, so they need no network, no keys and no model —
which is exactly why they are trusted when the model is not.
