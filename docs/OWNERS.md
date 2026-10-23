# Ownership

Who to ask, and what they are expected to review. One owner per area keeps the "who fixes this?"
question answerable without a meeting.

| Area | Owner | Reviews |
|---|---|---|
| Repository, CI, releases | [@SergeyGer](https://github.com/SergeyGer) | everything |
| Agent graph and prompts | [@SergeyGer](https://github.com/SergeyGer) | changes to `app/graph.py`, `app/prompts.py` |
| Red-Flag rules and thresholds | [@SergeyGer](https://github.com/SergeyGer) | `app/utils.py`, `app/graph.py` critic logic |
| Documentation (README + wiki) | [@SergeyGer](https://github.com/SergeyGer) | `README.md`, `docs/**` |
| Container and deployment | [@SergeyGer](https://github.com/SergeyGer) | `Dockerfile`, `docker-compose.yml`, `.devcontainer/`, `scripts/project.*` |
| Security posture | [@SergeyGer](https://github.com/SergeyGer) | `SECURITY.md`, dependency bumps, CodeQL findings |

## How reviews work here

* `main` is protected by the **Protect Main** ruleset: a pull request is required, and the
  required status checks must pass before the merge button works.
* The checks that must be green: `Lint (ruff)`, `Tests (Python 3.11)`, `Tests (Python 3.12)`,
  `Tests (Python 3.13)`, `Analyze (python)`, `Analyze (actions)`, `Docs · links + ADR`.
* A change to a Red-Flag threshold or to a prompt needs a note in the PR explaining what evidence
  motivated it — the rules are the product.
* Documentation changes are reviewed like code: the Docs check validates links, anchors, ADR
  structure and the generated reference page.

## Response expectations

| Kind of issue | Target |
|---|---|
| Security report | acknowledged within 3 working days (see [SECURITY.md](../SECURITY.md)) |
| Broken documentation or a failing demo | next working day |
| Feature request | triaged when the next release is planned |

*Last reviewed: 2026-10-23 · Owner: [@SergeyGer](https://github.com/SergeyGer)*
