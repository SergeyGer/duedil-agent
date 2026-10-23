# Versioning

DueDil.Agent follows [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

| Part | Bumped when |
|---|---|
| **MAJOR** | The CLI, the state schema or the memo structure changes incompatibly |
| **MINOR** | New capability with a backwards-compatible interface (new node, new Red-Flag rule, new interface) |
| **PATCH** | Fixes, dependency refreshes, documentation and test changes |

## Releases

* A release is a git tag `vX.Y.Z` on `main`; the **Release** workflow builds the package and the
  **Publish image** workflow pushes the container image.
* Container tags produced from a release: `X.Y.Z`, `X.Y`, `latest`. Manual builds from a branch
  are tagged `edge`.
* The changelog is the source of truth for what changed; every PR that changes behaviour adds an
  entry under `## [Unreleased]`.

## Compatibility promises

| Surface | Promise |
|---|---|
| `python -m app.cli` options | Options are only added within a MAJOR; existing ones keep their meaning |
| `VentureState` keys | Read-only for consumers; new keys may appear in a MINOR |
| Memo sections | The six numbered sections are stable; wording inside them is not |
| Environment variables | Never removed within a MAJOR; deprecated ones keep working with a comment in `env.example` |
| `[NOT_FOUND]` marker | Part of the contract — see [ADR 0003](adr/0003-not-found-contract.md) |

## Python support

CI runs the suite on Python 3.11, 3.12 and 3.13; the container image pins 3.12. Dropping a
version is a MINOR change and is announced in the changelog.

*Last reviewed: 2026-10-23 · Owner: [@SergeyGer](https://github.com/SergeyGer)*
