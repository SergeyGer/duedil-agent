# Extending the System

The graph is small on purpose, which makes the extension points few and obvious. This page
lists them with the concrete edit each one requires.

## Add a node

```python
# app/graph.py
def agent_market_sizing(state: VentureState) -> dict:
    metrics = state.get("extracted_metrics") or {}
    tam = parse_money(metrics.get("tam"))
    bottom_up = (state.get("financial_benchmarks") or {}).get("arr")
    ...
    return {"financial_benchmarks": {...}, "progress_log": ["[sizing] checked TAM"]}

# wiring
graph.add_node("agent_market_sizing", agent_market_sizing)
graph.add_edge("agent_financial", "agent_market_sizing")
graph.add_edge("agent_market_sizing", "agent_critic")
```

Rules that keep the graph healthy:

1. **Return partial updates only.** Never mutate the state you received; LangGraph merges what
   you return (and applies reducers, e.g. `progress_log`'s `add`).
2. **Append to `progress_log`.** The UI, the CLI and the JSON audit trail all read it.
3. **Catch your own exceptions.** A node that raises takes the whole run down; a node that
   degrades produces a narrower memo plus a reason.
4. **Write one new state field instead of overloading an existing one,** and declare it in
   `app/state.py`.

## Use the domain vocabulary

`app/prompts.py` exists so prompt edits are reviewable in one place. When you add an agent,
add its system prompt there rather than inlining a string in `graph.py`, and keep the
"never invent data" instruction — the `[NOT_FOUND]` contract is what the deterministic rules
rely on.

## Tune the risk appetite

| Lever | File | Default | Effect of raising it |
|---|---|---|---|
| `MAX_CRITIC_LOOPS` | `app/graph.py` | `2` | More targeted re-verification per run; linear cost growth. |
| `DEFAULT_ARR_PER_EMPLOYEE_BENCHMARK` | `app/utils.py` | `100_000` | Stricter financial bar; fewer `above` verdicts. |
| Team-mismatch ratio (`5×`) | `app/graph.py` | `5` | Fewer team flags (more tolerance for stale snippets). |
| Traffic threshold (`5 000`) | `app/graph.py` | `5 000` | Fewer "implausible leadership" flags. |
| `_LEADERSHIP_KEYWORDS` | `app/graph.py` | 10 terms | More claims treated as leadership claims. |
| `DEFAULT_MAX_RESULTS` | `app/tools.py` | `5` | More evidence per query, more context tokens. |

Each is asserted by a test, so a change is visible in review rather than silent.

## Swap a boundary

| Boundary | Production | Test / offline | How to substitute |
|---|---|---|---|
| LLM | `app.config.get_llm()` | `FakeLLM` / `CannedLLM` | Patch `app.graph.get_llm`; the nodes call it through the module namespace. |
| Web search | `app.tools.get_search_tool()` | `CannedSearchTool` | Patch `app.graph.get_search_tool`. |
| PDF parsing | LlamaParse | `pypdf` | Unset `LLAMA_CLOUD_API_KEY`, or pass `prefer_llamaparse=False`. |
| PDF rendering | ReportLab | — | Not plugged in; the graph never renders. |

Because the nodes resolve these through module globals, substitution needs no dependency
injection framework — see `scripts/demo_offline.py` for a complete example.

## Add a sector benchmark

`compute_financials()` takes the benchmark as an argument and `agent_financial` passes the
module default. A per-sector table is therefore a small change:

```python
SECTOR_BENCHMARKS = {"b2b saas": 100_000, "marketplace": 250_000, "fintech": 150_000}

benchmark = SECTOR_BENCHMARKS.get(
    (metrics.get("sector") or "").strip().lower(),
    DEFAULT_ARR_PER_EMPLOYEE_BENCHMARK,
)
```

The roadmap item is exactly this, with the lookup table configuration-driven.

## Parallelise the scraper

The three default queries are independent and currently sequential. `agent_scraper` could fan
them out with a thread pool and join before returning `market_data`; the state shape does not
change, because the node already returns one list. Watch the Tavily rate limit and keep the
per-query error handling — a failed query must degrade to an inline note, not an exception.

## Add a language to the UI

1. Add the code and endonym to `LANGUAGES` in `app/i18n.py`.
2. Add the full key set to `TRANSLATIONS`.
3. Run `pytest tests/test_i18n.py` — it fails on a missing key or a mismatched placeholder, by
   design.

No UI code changes are needed: the interface reads every string through `translate()`.

## Add an output format

`app/report.py` is the model to follow: a pure function from the memo text to bytes, plus a
thin file-writing wrapper. For DOCX or HTML, add `markdown_to_<format>_bytes()` next to the PDF
renderer, expose it through the CLI flag set, and add a test that the output is parseable.

## What is intentionally out of scope

| Not planned | Why |
|---|---|
| Autonomous tool selection | Breaks cost predictability and the termination guarantee — see [Design Decisions](Design-Decisions). |
| A database of past deals | The system is stateless by design; persistence belongs to the caller. |
| Scraping behind authentication | Legal and ethical boundary: the system reads public sources only. |
| Letting the LLM decide the recommendation alone | The deterministic rules must stay able to contradict the model. |

## Extension checklist

- [ ] New state field declared in `app/state.py` and initialised in `initial_state()`.
- [ ] Node catches its own exceptions and logs to `progress_log`.
- [ ] Prompt lives in `app/prompts.py`.
- [ ] Deterministic logic goes into `app/utils.py` as a pure function.
- [ ] Test added offline, no keys required.
- [ ] `make lint`, `make test` clean; coverage stays above 88 %.
- [ ] Wiki page updated if behaviour or a threshold changed.
