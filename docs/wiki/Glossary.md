# Glossary

The vocabulary this project uses, in the sense the code uses it. If a term is missing, add it
here in the same PR that introduces it.

*Last reviewed: 2026-10-23 · Owner: [@SergeyGer](https://github.com/SergeyGer)*

| Term | Meaning here |
|---|---|
| **ARR** | Annual recurring revenue. A figure the *deck claims*; the pipeline never computes it from usage data. |
| **MRR** | Monthly recurring revenue; same rules as ARR. |
| **TAM** | Total addressable market — the claimed size of the opportunity, not something we verify with a model. |
| **Benchmark** | `$100 000` of ARR per employee, the B2B SaaS reference used by the financial audit. |
| **Efficiency** | ARR ÷ team size, compared against the benchmark. Reported as *not computable* when either input is missing. |
| **Red Flag** | A finding that argues against the deck: a contradiction, an implausible number, a missing figure that matters. |
| **Critic loop** | One back-edge from the Critic to the Scraper. Hard-capped at `MAX_CRITIC_LOOPS = 2`, so the graph always terminates. |
| **`[NOT_FOUND]`** | The literal marker for "the deck does not state this". Never replaced by a guess — see [ADR 0003](../adr/0003-not-found-contract.md). |
| **Memo** | The six-section Markdown report produced by the Supervisor; the PDF is a render of it. |
| **Recommendation** | The memo's single verdict: `INVEST`, `DEEP AUDIT` or `REJECT`. |
| **VentureState** | The `TypedDict` carried between graph nodes; `progress_log` is append-only. |
| **Trace** | The LangSmith run tree of one execution, used to audit what each node did. |
| **Offline agents** | Deterministic replacements for the LLM nodes, used when no API key is configured (the hosted demo). They read the deck by rule and say so in the memo. |
| **Dev container** | The VS Code container defined in `.devcontainer/`, attached to the compose service `ui`. |
| **Instance** | One checkout's compose project: name, host port and data volume. Lets several developers run on one server. |

[probe broken link](No-Such-Page)
