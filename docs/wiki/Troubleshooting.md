# Troubleshooting

Real problems this project has hit, with the diagnosis and the fix. Each entry states the
symptom first, because that is what you will actually see.

## LangSmith

### Every API call returns `403 Forbidden`, but `/info` answers `200`

**Symptom**

```
Failed to POST https://api.smith.langchain.com/runs/multipart in LangSmith API.
HTTPError('403 Client Error: Forbidden …', '{"error":"Forbidden"}\n')
```

The same happens with a personal token (`lsv2_pt_…`) and with a brand-new service key
(`lsv2_sk_…`), with or without `X-Tenant-Id`, and `/info` still returns `200` — so it looks like
a broken key.

**Cause:** the LangSmith **instance is a property of the organization**, not of the key. An
organization hosted on the EU instance addressed through the US endpoint is unknown there, so
the request is rejected before any scope check. The identical 403 for a valid key, an invalid
key, and a random tenant id is the tell.

**Fix**

```bash
python3 scripts/langsmith_key_check.py lsv2_sk_... <workspace-id>
#    US  https://api.smith.langchain.com     -> 403
# OK EU  https://eu.api.smith.langchain.com  -> 200
```

```dotenv
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
LANGCHAIN_ENDPOINT=https://eu.api.smith.langchain.com
```

**Related traps in the same area**

| Symptom | Cause |
|---|---|
| `403` only on some resources | An organization-scoped service key needs the workspace header; the SDK sends it when `LANGSMITH_WORKSPACE_ID` is set. |
| Setting `LANGCHAIN_ORG_ID` changes nothing | The SDK never reads it. It uses `LANGSMITH_WORKSPACE_ID`. |
| Traces appear in the wrong project | `LANGSMITH_PROJECT` unset, or the key belongs to another workspace. |
| A key shows in the UI but is rejected | It was revoked, or the user who created the PAT is no longer in the organization (PATs inherit the creator's access). |

### Tracing is enabled but no runs appear

1. Confirm the app can reach the API: `python3 scripts/langsmith_key_check.py <key>`.
2. Check the project name — `LANGSMITH_PROJECT` defaults to a value that may not be yours.
3. Look for a single ingest error in the log: tracing failures are logged, never fatal.
4. Remember the free/Developer tier has hourly and monthly trace ceilings; exceeding them is
   reported as `429`, not `403`.

## Docker

### `Permission denied` when the container writes to `data/`

The image runs as UID 10001, so a root-owned bind mount is not writable. Either use the compose
named volume, or run as your own UID:

```bash
docker run --rm -u "$(id -u):$(id -g)" --env-file .env \
    -v "$PWD/data:/app/data" duedil-agent:latest python -m app.cli ...
```

### The container is `unhealthy`

```bash
docker inspect --format '{{json .State.Health}}' duedil-agent-ui | python3 -m json.tool
curl -sS http://127.0.0.1:8501/_stcore/health   # expect: ok
```

The healthcheck has a 20 s start period; a slow first boot on a loaded machine can need a retry.

### `.env` seems ignored inside the container

`docker compose` reads `.env` for **variable interpolation**, not to inject it into the
container. The compose file sets `env_file: .env` explicitly — if you run `docker run` by hand,
pass `--env-file .env`.

## Application

### The memo says `_(Generated without LLM: …)_`

The LLM call failed. The parenthesised reason is the actual error. Usual causes: no
`OPENAI_API_KEY`, an expired key, or no egress to the provider. The pipeline is designed to
finish in this state, so it is a warning about depth, not a crash.

### "Market data unavailable" in the memo

`TAVILY_API_KEY` is unset. The analysis continues without external verification, which also
silences the traffic-based rules by design.

### Every deck extracts as `[NOT_FOUND]`

The LLM is not returning JSON. Check the model id in `DUE_DIL_MODEL` and whether the provider is
reachable; `_safe_json()` tolerates code fences, but not prose.

### PDF parsing fails with `ParserError` on a scanned deck

Scanned pages are images. `pypdf` extracts nothing from them; LlamaParse (with
`LLAMA_CLOUD_API_KEY`) handles them far better. If neither works, the deck needs OCR.

### A hosted app answers `303` to `curl` — that is not a privacy problem

Checking the hosted demo with `curl` returns `303` with a `location` pointing at
`share.streamlit.io/-/auth/app`, which looks exactly like an app that is private. It is not:
Streamlit Cloud answers the same way for **any** app, including ones that are certainly public
(verified against `llm-examples.streamlit.app`), because the `303` is how it handles a request
that is not a browser session. Use a real browser to judge visibility — a public app loads its
UI and returns `200` with the app's own `Server`/HTML; a private one never renders.

### The hosted app loads but stays empty (spinner, no content)

The frontend is served while the Python process is not serving the app — the page returns `200`
with zero rendered text. Distinguish the causes:

| Observation in the Cloud logs | Cause |
|---|---|
| ends after `Uvicorn server started on :::8501`, nothing after | the script never ran, or the container was killed; check resource limits and the viewport at the bottom of *Manage app* |
| `ModuleNotFoundError` / `ResolutionImpossible` | dependency install failed |
| the app was recently made public or renamed | a redeploy is in flight — *Reboot* the app |

Before blaming the code, reproduce the exact environment locally; it is cheap and decisive:

```bash
docker build -t repro -f - . <<'EOF'
FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY .streamlit ./.streamlit
CMD ["python", "-m", "streamlit", "run", "app/ui.py", "--server.port=8501", "--server.address=0.0.0.0"]
EOF
docker run --rm -p 8501:8501 repro
```

If that renders and the hosted one does not, the difference is the platform — start with the
Python runtime shown in the log (`Using Python X.Y.Z environment`) and try another version.

### Streamlit reruns and loses the result

Any widget change — including the language selector — triggers a rerun and clears the previous
run. Change settings first, then run. This is expected Streamlit behaviour, not a bug.

## CI

### `Tests (…)` fails with `ResolutionImpossible` after a dependency bump

A transitive pin moved out of lock-step with its parent (the classic: `aiohttp` requires
`multidict<7`). Fix by re-freezing the lock rather than editing one line, and add the package to
the `ignore:` list in `.github/dependabot.yml` with a note until upstream allows it.

### `test_tooling_pins.py` fails after bumping `ruff`

The `ruff` version is pinned in three places — `.pre-commit-config.yaml`,
`pyproject.toml [dev]`, and the CI lint job. All three must move together; the test exists
precisely because they once drifted and blocked contributors. The same applies to a
`ruff-pre-commit` Dependabot PR, which only touches one of the three.

### The coverage badge workflow opens a pull request that never merges

Expected. The job pushes with `GITHUB_TOKEN`, and GitHub suppresses workflow runs for events
created by that token, so the required status checks never report on that branch. Merge the
badge PR manually — it only touches `docs/…/coverage.svg`.

## Getting help

| Channel | Use for |
|---|---|
| [GitHub Issues](https://github.com/SergeyGer/duedil-agent/issues) | Bugs, unexpected behaviour, documentation gaps. |
| [Security advisories](https://github.com/SergeyGer/duedil-agent/security/advisories/new) | Vulnerabilities — never a public issue. |
| `SECURITY.md` | Response timeline and scope. |

When reporting an application bug, attach the `progress_log` from the state JSON — it records
which node failed and why, which usually identifies the cause immediately.
