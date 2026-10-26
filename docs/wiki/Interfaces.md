# Interfaces

Four surfaces, one graph. The UI, the CLI, the library entry point and the GitHub Action all
build the same compiled graph, so behaviour cannot drift between them.

## Streamlit UI

```bash
streamlit run app/ui.py           # or: make run
```

| Element | Behaviour |
|---|---|
| Sidebar | Language selector, PDF uploader, a single **📂 Browse examples/** button, website URL, **Run due diligence** button. |
| Progress | One chip per graph node: pending → success, updated live from the graph's `updates` stream. |
| Run summary | A headline strip: company, Red Flags found, critic passes used (of 2), and **which model produced the analysis**. |
| Results | Extracted metrics and the financial audit as **readable tables** — money grouped, ratios as `0.86× the benchmark`, missing figures labelled `— (not in the deck)` — instead of raw JSON. |
| Verdict | The conclusion of the financial audit gets its own highlighted callout: ✅ above the benchmark, ⚠️ below, ❔ not computable. It is deliberately not a table row, so it cannot be read as another input figure. |
| Red Flags | One warning panel per flag, below the verdict. |
| Export | **Download PDF** button — rendered in memory via `markdown_to_pdf_bytes()`, nothing written to disk; the footer names the model that wrote the memo. |
| Languages | English (default), German, French, Russian (`app/i18n.py`). |
| Expander | The raw `progress_log`, for when a step needs explaining. |

### What the app does when there are no API keys

The hosted demo runs without secrets, so the real LLM nodes cannot work. Two things follow,
and both are deliberate:

1. The app switches to **rule-based offline agents** (`app/offline_agents.py`): the Extractor
   reads the deck it was given — titles, amounts, headcounts — and the Supervisor assembles the
   memo from those readings, marking anything the deck does not state as `[NOT_FOUND]`. It is a
   mechanical reading, not a model's judgement, and the UI says so in a warning above the
   results while the memo and the PDF repeat it in their byline
   (`offline rules, deck_aware (no model)`).
2. A different deck therefore produces a **different** analysis. Before this, every input fell
   through to the same static fallback memo — `Investment Memo — Unknown Startup` for all five
   examples — which made the picker meaningless and looked like a bug.

`DUE_DIL_OFFLINE_MODE` selects the mode explicitly (`deck_aware` for the above, `canned` for the
recorded payloads the committed example memo was produced from); without it the app decides from
the environment, and a deployment that has its keys runs the real pipeline. The legacy
`DUEDIL_MODE` switch still works and defaults to `canned`, so existing recordings stay
reproducible.

### Why the bundled decks are behind a button, not a list

The sidebar holds one uploader and one button that opens a dialog listing `examples/`. The list is
not always on screen because it is not the normal path — most visitors come to analyse their own
deck.

It cannot be folded into the uploader itself: **`st.file_uploader`'s "Browse files" dialog is the
browser's own file picker and can only see the visitor's machine**, never the server's filesystem.
Streamlit 1.65 has no parameter for a server-side folder, so an app that wants to offer files it
ships must render its own listing. That is what the dialog is.

Picking a deck prefills the matching website URL, shows `Selected example: <file>` with a **Clear
selection** button, and an explicit upload always wins over a remembered example.

The page is deliberately thin: everything that turns state into something readable lives in
`app/display.py`, which is pure and unit-tested without a browser (`tests/test_display.py`).
That is where the formatting rules live — how money is grouped, how a `[NOT_FOUND]` figure is
labelled, which metric comes first, and why the verdict is not just another row.

Session behaviour worth knowing: switching the language triggers a Streamlit rerun and resets
the run, so a language change always precedes a fresh run — this is why the documentation
screenshots are captured in a single language.

## CLI

```bash
python -m app.cli <deck.pdf> [url] [-o OUT] [--md PATH] [--json PATH] [--model ID] [--quiet]
```

| Flag | Effect |
|---|---|
| `-o, --out` | Output PDF path (default `data/<company>_memo.pdf`, slugified company name). |
| `--md` | Also write the raw Markdown memo. |
| `--json` | Dump the full final `VentureState` — metrics, market data, benchmarks, flags, memo, log. |
| `--model` | Override the LLM id for this run (e.g. `claude-3-5-sonnet`). |
| `--quiet` | Print only the memo (useful in scripts and CI). |
| `--version` | Print `duedil <version>`. |

Exit codes are meaningful, so the CLI composes in a pipeline:

| Code | Meaning |
|---|---|
| `0` | Memo produced and artefacts written. |
| `2` | No deck argument, or the file does not exist. |
| `3` | The PDF could not be parsed (`ParserError`). |
| `4` | The graph raised unexpectedly. |
| `5` | The run finished without a memo. |

Streaming output looks like this — the same lines the UI renders as chips:

```
DueDil.Agent
  deck  : examples/sample_deck.pdf
  url   : https://nimbusai.example
  model : gpt-4o

[1/2] Parsing PDF -> Markdown ...
      extracted 768 characters

[2/2] Running the agent graph:
      done  Extractor   — extracting pitch-deck metrics
      done  Scraper     — gathering market data (Tavily)
      done  Financial   — computing ARR / employee benchmarks
      done  Critic      — cross-checking claims & Red Flags
      done  Scraper     — gathering market data (Tavily)     ← critic loop, pass 2
      done  Financial   — computing ARR / employee benchmarks
      done  Critic      — cross-checking claims & Red Flags
      done  Supervisor  — assembling the deal memo

Red flags  : 12
Financials : Weak: ARR/employee of $85,714 sits below the B2B SaaS benchmark of $100,000.
```

Batch usage (the loop cap keeps the cost per deck predictable):

```bash
for deck in decks/*.pdf; do
  python -m app.cli "$deck" --quiet > "${deck%.pdf}.md"
done
```

## GitHub Action

`action.yml` at the repository root wraps the CLI, so a workflow can analyse a deck without
writing any Python.

```yaml
- uses: SergeyGer/duedil-agent@v0.3.0
  id: duedil
  with:
    deck: decks/acme.pdf
    url: https://acme.example
```

| Input | Default | Purpose |
|---|---|---|
| `deck` | — (required) | Path to the PDF, relative to the repository root |
| `url` | `""` | Startup website used for the market-data search |
| `output-dir` | `duedil-output` | Where the artefacts are written (relative or absolute) |
| `model` | `""` | LLM id override, ignored in offline runs |
| `offline` | `auto` | `auto` runs the rule-based agents when no LLM key is present; `true`/`false` force it |
| `python-version` | `3.12` | Interpreter for the pipeline |
| `install-dependencies` | `true` | Install the action's pinned `requirements.txt` |

| Output | Contents |
|---|---|
| `memo` | Absolute path to the PDF memo |
| `markdown` | Absolute path to the Markdown memo |
| `comment` | Short Markdown summary, ready for `gh pr comment --body-file` |
| `state` | Full final state as JSON |
| `recommendation` | `INVEST`, `DEEP AUDIT` or `REJECT` |

Two deliberate constraints:

* **The action writes files, it does not post them.** Commenting stays in the caller's workflow,
  so the action needs no token and no `pull-requests: write` permission.
* **The dependencies are the action's own** (`requirements.txt` next to `action.yml`), not the
  caller's, so a consumer's lockfile cannot change the analysis.

The summary is also appended to `$GITHUB_STEP_SUMMARY`, so the verdict is visible in the run
without opening the pull request. `--comment-file` produces the same text from the CLI.

## Python API

```python
from app.parser import parse_pdf_to_markdown
from app.graph import run_due_diligence
from app.report import markdown_to_pdf

deck_text = parse_pdf_to_markdown("deck.pdf")           # path, bytes or Path
state = run_due_diligence(deck_text, website_url="https://acme.ai")

print(state["financial_benchmarks"]["verdict"])
for flag in state["red_flags"]:
    print("RED FLAG:", flag)

markdown_to_pdf(state["final_memo"], "memo.pdf")
```

| Function | Module | Notes |
|---|---|---|
| `parse_pdf_to_markdown(source, *, prefer_llamaparse=True)` | `app.parser` | Accepts a path or raw bytes; normalises to a temp file internally and cleans up. Raises `ParserError` when nothing is extractable. |
| `build_graph()` | `app.graph` | Compiles the state graph. Cheap; call once and reuse. |
| `run_due_diligence(text, url="", *, app=None)` | `app.graph` | Convenience wrapper: `graph.invoke(initial_state(...))`. Pass `app=` to inject a custom compiled graph (this is how the tests drive it). |
| `initial_state(text, url)` | `app.state` | Fully-initialised state, including `progress_log=["[init] run started"]`. |
| `markdown_to_pdf(text, path)` / `markdown_to_pdf_bytes(text)` | `app.report` | File or in-memory rendering. |

To observe the run step by step, stream it instead of invoking it:

```python
from app.graph import build_graph
from app.state import initial_state

graph = build_graph()
state = initial_state(deck_text, "https://acme.ai")
for chunk in graph.stream(state, stream_mode="updates"):
    for node, update in (chunk or {}).items():
        print("finished:", node)
        state.update({k: v for k, v in (update or {}).items() if k != "progress_log"})
```

## Output artefacts

| Artefact | Producer | Content |
|---|---|---|
| PDF memo | `app/report.py` | Styled A4 document: headings, lists, tables, blockquotes, inline bold/italic/code/links, generation timestamp. |
| Markdown memo | graph (`final_memo`) | The same content with no rendering step. |
| State JSON | `--json` | The complete `VentureState`, including the raw market evidence — the audit trail behind every flag. |

Shipped examples: [`examples/sample_memo.pdf`](https://github.com/SergeyGer/duedil-agent/blob/main/examples/sample_memo.pdf),
[`sample_memo.md`](https://github.com/SergeyGer/duedil-agent/blob/main/examples/sample_memo.md),
[`sample_memo.json`](https://github.com/SergeyGer/duedil-agent/blob/main/examples/sample_memo.json),
plus `sample_offline_run.json` (the canned external responses used by the offline demo).

*Last reviewed: 2026-10-23 · Owner: [@SergeyGer](https://github.com/SergeyGer)*
