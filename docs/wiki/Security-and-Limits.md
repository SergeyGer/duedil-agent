# Security & Limits

## Security posture

### Secrets

| Control | Implementation |
|---|---|
| No secrets in git | `.env` and `.git-token` are in `.gitignore`; `env.example` holds placeholders only. |
| No secrets in images | `.dockerignore` excludes `.env`, `.env.*` and `.git-token`, so they cannot reach a layer even by accident. |
| No secrets in logs | Keys are read from the environment and never printed; the app logs failures, not values. |
| Least privilege | The container runs as a non-root user (UID 10001) with a single writable directory (`/app/data`). |
| Repository scanning | GitHub secret scanning and push protection are enabled; Dependabot alerts on. |
| Key hygiene | A workspace-scoped **service key** is recommended for the application instead of a personal token; LangSmith keys are revocable per workspace. |

### Supply chain

| Control | Implementation |
|---|---|
| Action pinning | Every `uses:` in every workflow points at a 40-character commit SHA with the release tag in a comment. |
| Update discipline | Dependabot groups updates weekly; packages that must move together (parent/child pins) are listed explicitly in `.github/dependabot.yml` with a reason. |
| Static analysis | CodeQL `security-and-quality` for Python and the workflow files; currently **0 open alerts**. |
| Reproducible installs | CI installs the `pip freeze` lockfile, so the tested set is the shipped set. |
| Release integrity | The release workflow refuses to build when the git tag and `pyproject.toml` version disagree. |

### Data flow and privacy

| Data | Where it goes |
|---|---|
| Pitch deck (PDF) | Parsed locally, or sent to LlamaParse when `LLAMA_CLOUD_API_KEY` is set. |
| Extracted metrics, market text | Sent to the configured LLM provider (OpenAI or Anthropic). |
| Company and founder queries | Sent to Tavily. |
| Prompts, responses, timings | Sent to LangSmith **only** when tracing is enabled. |
| Memos and uploads | Written to `data/` (or the `duedil-data` volume); nothing else is persisted. |

**Consequence:** a confidential deck is third-party data the moment a hosted parser, model or
search API is involved. For sensitive material, run with the local `pypdf` fallback, a
self-hosted or on-premise model endpoint, tracing disabled, and Tavily either disabled or
replaced. None of those are code changes — they are configuration.

## Known limits

### Model-dependent quality

Output quality tracks the model and the search results. The deterministic rules are stable, but
the LLM's contribution (narrative contradictions, market plausibility) varies between runs. Two
runs on the same deck can produce a different flag *wording*, and occasionally a different flag
*count* — the shipped live run reported 12 flags, the offline golden run 13.

### Heuristic number parsing

`parse_number` handles `$1.2M`, `1,200,000`, `1.200.000`, `50 employees`, `about 20`, and the
`[NOT_FOUND]` token set. It will not handle every convention (lakh/crore, spelled-out numbers,
ranges with a dash are read as their first endpoint). Unusual formats need manual review.

### Search-result dependence

Traffic and headcount rules fire on what the search returns. A company with a common name, or
one whose LinkedIn page is not indexed, produces weak evidence — and the rules deliberately
stay silent rather than flag on absence of evidence. Silence is not a clean bill of health; read
the market section of the memo.

### Loop budget

`MAX_CRITIC_LOOPS = 2` is a cost/quality trade-off, not a statement that two passes are always
enough. A deck whose contradictions only surface in a third line of questioning will keep them.

### Not a substitute for diligence

The memo is a **first-pass artefact**. It does not do cap-table, legal, IP, reference-call or
financial-statement work, and it cannot verify anything that is not publicly documented.

### Language coverage

The **UI** is translated (EN/DE/FR/RU). The **analysis** is English-centric: the prompts,
keyword lists and number heuristics are English. Decks in other languages will extract, but the
Red-Flag rules will fire less reliably.

## Failure modes and what they look like

| Failure | Symptom | Impact |
|---|---|---|
| No LLM key | `[extractor] FAILED …` in the log, empty metrics, fallback memo with a `_(Generated without LLM: …)_` footer | Pipeline completes; analysis is shallow |
| LLM rate limit / timeout | Same as above for that node only | Other nodes still contribute |
| LangSmith 403 (wrong region) | `Failed to send compressed multipart ingest …` once | Traces missing; analysis unaffected |
| Tavily failure | `[search error: …]` inside the market block | Fewer flags; the memo states the gap |
| Unparseable PDF | CLI exit code `3`, `ParserError` | Nothing produced — fail fast is correct here |
| Model returns prose instead of JSON | `_safe_json()` returns `{}` | Falls back to deterministic flags |

## Reporting a vulnerability

Do not open a public issue. Use GitHub Security Advisories:
<https://github.com/SergeyGer/duedil-agent/security/advisories/new>

See [`SECURITY.md`](https://github.com/SergeyGer/duedil-agent/blob/main/SECURITY.md) for the
response timeline, the scope, and the one accepted transitive advisory (`nltk`, unreachable from
this code and removed entirely by running without `llama-parse`).

## Disclaimer

DueDil.Agent is an **automated analysis tool**. Its output is generated by LLMs and web search
and may contain errors or omissions. It does **not** constitute investment advice. Always verify
findings independently before making any investment decision.
