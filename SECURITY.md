# Security Policy

## Supported versions

DueDil.Agent is pre-1.0; security fixes are applied to the latest release.

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |
| < 0.1   | No        |

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report privately through GitHub Security Advisories:

<https://github.com/SergeyGer/duedil-agent/security/advisories/new>

Where possible, include:

- a description of the issue and its impact,
- steps to reproduce (a minimal proof of concept),
- the affected version or commit,
- any suggested remediation.

## Response timeline

- Acknowledgement within **3 business days**.
- Triage and severity assessment within **7 business days**.
- A fix or mitigation for confirmed high-severity issues as soon as practical; you will be
  credited in the release notes unless you prefer to remain anonymous.

## Scope

**In scope**

- the application code under `app/`,
- dependency and supply-chain issues introduced by this project's configuration.

**Out of scope**

- vulnerabilities in third-party services (OpenAI, Anthropic, LlamaCloud, Tavily,
  LangSmith) — please report those to the respective vendor,
- issues that require a compromised local environment or leaked API keys,
- model quality concerns such as hallucination or prompt injection (still welcome as a
  regular issue, unless they lead to a concrete security impact).

## Handling of secrets

API keys are read from environment variables / a local `.env` file. Never commit `.env`; the
repository `.gitignore` already excludes it. If you believe a key has been exposed, rotate it
immediately with the provider.

## Known advisories

| Package | Advisory | Status |
|---------|----------|--------|
| `nltk` | [PYSEC-2026-3740](https://osv.dev/vulnerability/PYSEC-2026-3740) — path-sandbox bypass in `TransitionParser` / `AveragedPerceptron` model persistence | Transitive (via `llama-parse` which depends on `llama-index-core`). **Not reachable** from DueDil.Agent: the application never calls the affected `nltk` model import/export APIs, and `pathsec` enforcement is not enabled. No patched release exists upstream yet. |

DueDil.Agent uses no `nltk` APIs directly; the dependency is pulled in only for the optional
LlamaParse-based PDF parsing. Running with the built-in `pypdf` fallback (i.e. without
`llama-parse` installed) removes the dependency and the advisory entirely.

## Safe harbour

We will not pursue legal action against researchers who make a good-faith effort to comply
with this policy.
