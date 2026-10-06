# DueDil.Agent — Engineering Wiki

> Autonomous multi-agent due-diligence system for technology startups, built as a
> deterministic **LangGraph** pipeline. This wiki is the technical reference: architecture,
> algorithms, operations, testing and design rationale.

**Repository:** [SergeyGer/duedil-agent](https://github.com/SergeyGer/duedil-agent) ·
**Release:** v0.1.0 · **Python:** 3.11+ · **Tests:** 79 passing, 90.1 % line coverage of `app/`

---

## Where to start

| If you want to… | Read |
|---|---|
| Understand what the product does | [Product Overview](Product-Overview) |
| See how the agent graph is wired | [Architecture](Architecture) |
| Know exactly how a Red Flag is raised | [Red-Flag Engine](Red-Flag-Engine) |
| Run it locally or in Docker | [Installation & Deployment](Installation-and-Deployment) |
| Configure models, parsers and tracing | [Configuration](Configuration) |
| Call it from your own code | [Interfaces](Interfaces) |
| Understand the CI, quality gates and releases | [Testing & Quality Gates](Testing-and-Quality-Gates) |
| Know why a decision was made | [Design Decisions](Design-Decisions) |
| Extend the graph or swap a node | [Extending the System](Extending-the-System) |
| Understand the limits and the security posture | [Security & Limits](Security-and-Limits) |

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
