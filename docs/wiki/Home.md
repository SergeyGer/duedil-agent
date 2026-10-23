# DueDil.Agent — Engineering Wiki

> Autonomous multi-agent due-diligence system for technology startups, built as a
> deterministic **LangGraph** pipeline. This wiki is the technical reference: architecture,
> algorithms, operations, testing and design rationale.

**Repository:** [SergeyGer/duedil-agent](https://github.com/SergeyGer/duedil-agent) ·
**Release:** v0.1.0 · **Python:** 3.11+ · **Tests:** 140 passing, 92 % line coverage of `app/`

---

## Choose your path

Different readers need different pages, and the fastest way into a wiki is to recognise
yourself in one line.

| If you are… | Start with | Then |
|---|---|---|
| **A visitor** — you want to know what this is and whether it works | [Product Overview](Product-Overview) | the [live demo](https://duedil-agent-cnrm2wvfew6nstsu2tpsvh.streamlit.app), [Recipes](Recipes) |
| **An engineer** — you will read, run or change the code | [Architecture](Architecture) | [Answer Quality & Guardrails](Answer-Quality), [Testing & Quality Gates](Testing-and-Quality-Gates) |
| **An operator** — you deploy it, configure it or debug it | [Installation & Deployment](Installation-and-Deployment) | [Configuration](Configuration), [Troubleshooting](Troubleshooting) |

## Where to start

| If you want to… | Read |
|---|---|
| Understand what the product does | [Product Overview](Product-Overview) |
| See how the agent graph is wired | [Architecture](Architecture) |
| Know exactly how a Red Flag is raised | [Red-Flag Engine](Red-Flag-Engine) |
| Understand how LLM answers are kept honest and how quality is measured | [Answer Quality & Guardrails](Answer-Quality) |
| Run it locally or in Docker | [Installation & Deployment](Installation-and-Deployment) |
| Configure models, parsers and tracing | [Configuration](Configuration) |
| Call it from your own code | [Interfaces](Interfaces) |
| Understand the CI, quality gates and releases | [Testing & Quality Gates](Testing-and-Quality-Gates) |
| Know why a decision was made | [Design Decisions](Design-Decisions) |
| Extend the graph or swap a node | [Extending the System](Extending-the-System) |
| Understand the limits and the security posture | [Security & Limits](Security-and-Limits) |
| Copy a command for a routine task | [Recipes](Recipes) |
| Look up a term, a variable or a flag | [Glossary](Glossary), [Reference](Reference) |
| Know why a decision was made | [Design Decisions](Design-Decisions), [ADRs](https://github.com/SergeyGer/duedil-agent/tree/main/docs/adr) |

---

## The one-paragraph version

A pitch deck and a website URL go in. A **five-node graph** extracts the claimed metrics,
verifies them against live web data, benchmarks the financials, cross-checks the claims with
an LLM **and** deterministic rules, and writes a board-ready investment memo with a
recommendation of `INVEST` / `DEEP AUDIT` / `REJECT`. The graph never trusts the deck: a
number is either corroborated by external evidence or explicitly flagged — missing data is
reported as `[NOT_FOUND]` instead of being invented. The Critic can send the graph back to the
Scraper once, hard-capped at two passes, so termination is guaranteed by construction.

---

## Documentation map

```
README.md (repository)          →  what it is, how to run it, what to look at
docs/wiki/ (this wiki)          →  how it works, why it is built this way, how to operate it
docs/architecture.md            →  in-repo architecture notes (state, nodes, sequence diagram)
```

The wiki sources are versioned in the repository under
[`docs/wiki/`](https://github.com/SergeyGer/duedil-agent/tree/main/docs/wiki) so the technical
documentation is reviewed like code; a small script publishes them here.

*Last reviewed: 2026-10-23 · Owner: [@SergeyGer](https://github.com/SergeyGer)*
