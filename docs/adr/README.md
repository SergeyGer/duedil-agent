# Architecture Decision Records

Every significant decision gets a short record in this folder: what we chose, what we gave up,
and what would make us revisit it. The format is fixed — `Status`, `Context`, `Decision`,
`Consequences` — and `scripts/validate_docs.py` fails the Docs check if a record loses a section
or is missing from the index below.

| # | Decision | Status |
|---|---|---|
| [0001](0001-five-node-langgraph-pipeline.md) | Five-node LangGraph pipeline with a bounded critic loop | Accepted |
| [0002](0002-hybrid-red-flag-engine.md) | Red Flags come from an LLM **and** deterministic rules | Accepted |
| [0003](0003-not-found-contract.md) | Missing data is reported as `[NOT_FOUND]`, never guessed | Accepted |
| [0004](0004-container-and-network-posture.md) | Non-root container, loopback-only publishing | Accepted |

## Writing a new record

1. Copy the structure of an existing record; number it with the next free four-digit prefix.
2. Keep it under a page: one decision per record.
3. Add it to the table above — the validator checks that every file is listed.
4. Status is one of `Proposed`, `Accepted`, `Superseded by 00xx`, `Deprecated`.

*Last reviewed: 2026-10-23 · Owner: [@SergeyGer](https://github.com/SergeyGer)*
