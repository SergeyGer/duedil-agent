# Interfaces

Three surfaces, one graph. The UI, the CLI and the library entry point all build the same
compiled graph, so behaviour cannot drift between them.

## Streamlit UI

```bash
streamlit run app/ui.py           # or: make run
```

| Element | Behaviour |
|---|---|
| Sidebar | Language selector, PDF uploader, website URL, **Run due diligence** button. |
| Progress | One chip per graph node: pending → success, updated live from the graph's `updates` stream. |
| Results | Extracted metrics and financial benchmarks as JSON, one warning panel per Red Flag, the full memo rendered as Markdown. |
| Export | **Download PDF** button — rendered in memory via `markdown_to_pdf_bytes()`, nothing written to disk. |
| Languages | English (default), German, French, Russian (`app/i18n.py`). |
| Expander | The raw `progress_log`, for when a step needs explaining. |

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
