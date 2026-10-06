# Configuration

All configuration is environment-based (`.env` locally, platform secrets in production).
`app/config.py` calls `load_dotenv()` at import, and every external integration is optional —
a missing key narrows the analysis instead of failing the run.

## Variable reference

### LLM providers

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | one of | Enables `gpt-4o` (and any `gpt-*` id) via `langchain-openai`. |
| `ANTHROPIC_API_KEY` | one of | Enables `claude-*` ids via `langchain-anthropic`. |
| `DUE_DIL_MODEL` | no | Model id, default `gpt-4o`. A `claude…` prefix selects Anthropic; anything else goes to OpenAI. |

The LLM is built **lazily and cached** per `(model, temperature)`:

```python
@lru_cache(maxsize=4)
def _cached_llm(model: str, temperature: float): ...

def get_llm(temperature: float = 0.0, model: str | None = None): ...
```

Consequences: importing the module (and building the graph) needs no keys, the same client is
reused across nodes, and tests can replace `get_llm` with a fake without touching the nodes.

### Document parsing

| Variable | Required | Purpose |
|---|---|---|
| `LLAMA_CLOUD_API_KEY` | no | Enables LlamaParse, which produces layout-aware Markdown (headings, tables) instead of raw text. |

Without it, `app/parser.py` falls back to local `pypdf`. The fallback is not a degraded mode so
much as a different one: LlamaParse preserves structure, `pypdf` extracts plain text. Both are
tested.

### Web verification

| Variable | Required | Purpose |
|---|---|---|
| `TAVILY_API_KEY` | no | Enables live search for competitors, traffic and founder footprint. |

Without it the scraper records a single `[market_data unavailable: TAVILY_API_KEY is not
configured]` block, so the memo is explicit about the missing evidence rather than silently
thinner.

### Observability (LangSmith)

| Variable | Purpose |
|---|---|
| `LANGSMITH_TRACING` / `LANGCHAIN_TRACING_V2` | `true` to send traces. |
| `LANGSMITH_API_KEY` / `LANGCHAIN_API_KEY` | A **service key** (`lsv2_sk_…`) scoped to the target workspace is recommended for the application; `lsv2_pt_…` is a personal token. |
| `LANGSMITH_ENDPOINT` / `LANGCHAIN_ENDPOINT` | API origin, default `https://api.smith.langchain.com`. |
| `LANGSMITH_PROJECT` / `LANGCHAIN_PROJECT` | Project name, e.g. `DueDil.Agent`. |
| `LANGSMITH_WORKSPACE_ID` | Workspace UUID; only needed when the key is scoped to several workspaces. |

The current SDK reads the `LANGSMITH_*` names; the historical `LANGCHAIN_*` names remain
supported as aliases, so both work and the repository documents both.

> **Region trap (cost us a debugging session).** The LangSmith **instance** is a property of the
> *organization*, not of the key. An EU organization addressed through the US endpoint answers
> `403 Forbidden` for every call — personal tokens and service keys alike — while the public
> `/info` still answers `200`, which makes it look like a broken key. Set the endpoint to
> `https://eu.api.smith.langchain.com` for EU organizations.
>
> `scripts/langsmith_key_check.py <key> [workspace-id]` probes both instances and prints the
> verdict plus the exact lines to put in `.env`.

### Application

| Variable | Default | Purpose |
|---|---|---|
| `DUEDIL_MODE` | `ui` | Docker entry point mode: `ui` (real pipeline) or `demo-ui` (offline demo). |
| `DUE_DIL_DEMO_DELAY` | `0` | Adds latency to each canned agent call; used when recording demo video so the progress is visible. |
| `STREAMLIT_SERVER_*`, `STREAMLIT_BROWSER_*` | image defaults | Port, bind address, headless mode, usage stats. |

## Defaults and failure behaviour

| Missing piece | Consequence | Visible where |
|---|---|---|
| LLM key | Deterministic fallback memo; extractor returns empty metrics | `[extractor] FAILED …`, `_(Generated without LLM: …)_` in the memo |
| LlamaParse key | Local `pypdf` extraction | `Extractor` still runs, structure is flatter |
| Tavily key | No external verification; deterministic traffic/team rules stay silent | `[market_data unavailable: …]` in the memo's market section |
| LangSmith key/tracing | No traces; a 403 is logged once and ignored | `Failed to send compressed multipart ingest …` in the log |
| Any single call fails mid-run | That node degrades, the graph continues | `progress_log` entry for that node |

## Hard-coded constants worth knowing

| Constant | Value | Location |
|---|---|---|
| `MAX_CRITIC_LOOPS` | `2` | `app/graph.py` — the termination guarantee |
| `DEFAULT_ARR_PER_EMPLOYEE_BENCHMARK` | `100_000` USD | `app/utils.py` |
| Team-mismatch ratio | `5×` | `app/graph.py` |
| Traffic "implausible" threshold | `< 5 000` visits | `app/graph.py` |
| Extraction window | first `24 000` chars of the deck | `app/graph.py` (extractor) |
| Critic window | first `20 000` chars of market data | `app/graph.py` (critic) |
| Tavily results per query | `5` | `app/tools.py` |
| Coverage gate | `88 %` | `pyproject.toml` (`fail_under`) |

These are the levers to tune first for a new sector or a different risk appetite; each is
covered by tests, so changing one is a deliberate, reviewable act.
