# Example decks

Five pitch decks for real IT companies, used to exercise DueDil.Agent on inputs that are not
synthetic. Regenerate them all with:

```bash
python scripts/make_example_decks.py            # all five
python scripts/make_example_decks.py cursor     # one of them
python scripts/make_example_decks.py --list     # list the available ones
```

## Read this first

These are **not** the companies' original pitch decks. The real documents are proprietary —
Airbnb's and Uber's early decks circulated at conferences, but republishing them here would be a
copyright problem, and for companies founded two or three years ago no deck exists in public at
all.

Every file below is a **reconstructed case study**: written by
[`scripts/make_example_decks.py`](../scripts/make_example_decks.py) from publicly reported facts
(funding rounds, disclosed ARR, disclosed headcount, founding year), with its sources printed on
the last page of the deck itself. Each deck also says on its first page that it is a
reconstruction.

## The decks

| File | Company | Founded | Why it is in here |
|------|---------|---------|-------------------|
| [`airbnb_deck.pdf`](airbnb_deck.pdf) | Airbnb | 2008 | The canonical marketplace story: no inventory, commission only, trust as the product. |
| [`uber_deck.pdf`](uber_deck.pdf) | Uber | 2009 | City-by-city expansion where each launch repeats the same playbook. |
| [`cursor_deck.pdf`](cursor_deck.pdf) | Cursor (Anysphere) | 2022 | Reported as the fastest B2B company to $1B ARR; ~300 employees against a $500M+ run rate tests the financial benchmark at the top end. |
| [`lovable_deck.pdf`](lovable_deck.pdf) | Lovable | 2023 | ~$400M ARR with ~146 employees — the extreme end of revenue per headcount. |
| [`cognition_deck.pdf`](cognition_deck.pdf) | Cognition AI | 2023 | Sells autonomous execution with ~15 engineers, and publishes no ARR at all — the densest missing-data case. |

Two older decks sit in the same folder and are unrelated to this set: `sample_deck.pdf` (the
synthetic NimbusAI deck the tests and the offline demo use) and `sample_memo.pdf` (its generated
memo).

## What each deck is designed to trigger

The decks are written so the pipeline has something real to disagree with:

| Deck | Expected behaviour |
|------|--------------------|
| Airbnb, Uber | Headcount (`about 40 people`, `about 30 employees`) is parseable, so the team-size rule has something to work with against external sources. |
| Cursor | `About 300 employees` against a reported $500M+ run rate — roughly $1.7M per head, far above the $100k benchmark. Tests the healthy end of the financial audit. |
| Lovable | ~$400M ARR with ~146 employees — the same healthy signal at an even more extreme ratio. |
| Cognition | `About 15 engineers` is parseable, but no public ARR exists: the financial audit must say it cannot compute efficiency, and the critic must report the gap rather than invent a number. |
| Cognition, Cursor | Deliberate `[NOT_FOUND]` markers (TAM, and ARR for Cognition) so the missing-data path runs. |

The contrast is deliberate: the synthetic `sample_deck.pdf` lands **below** the benchmark and
produces a weak verdict, while Cursor and Lovable land far **above** it.

## Running the pipeline on one

```bash
# offline, no API keys: uses the synthetic deck the demo is pinned to
make demo

# real run with your keys (costs a few cents, needs .env)
python -m app.cli examples/cursor_deck.pdf https://cursor.com \
    --out data/cursor_memo.pdf --md data/cursor_memo.md
```

Note that the offline demo and the test suite stay pinned to `sample_deck.pdf`: their output is
asserted, so a deck whose public numbers change every quarter must not be part of them. The
tests only check that these five decks keep parsing into usable text (see
`tests/test_parser.py`).

## Keeping them accurate

Funding rounds and ARR figures move fast. If you regenerate or edit a deck, update the figures in
`COMPANIES` inside [`scripts/make_example_decks.py`](../scripts/make_example_decks.py) and the
source list on its last slide, then re-run the generator. The `deck_date` field in each entry
records the moment the numbers were taken from public reporting.
