#!/usr/bin/env python3
"""Record the demo screencast and the README screenshots against a running UI.

The recording is a real session with a real cursor: the sample deck is chosen, the analysis is
started, the results and the memo are scrolled. Timings of every action are written next to the
video, so ``scripts/build_demo_video.sh`` can cut the recording into the segments the narration
follows.

Designed to run inside the Playwright image, which ships Chromium and ffmpeg:

    docker run --rm --network host \
        -v "$PWD:/work" -w /work \
        mcr.microsoft.com/playwright/python:v1.49.1-noble \
        python scripts/make_demo_video.py --base-url http://127.0.0.1:8511

The screenshots land in ``docs/media/`` and the raw recording in ``/tmp/duedil-capture/``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
MEDIA = REPO_ROOT / "docs" / "media"

HERO = "Investment due diligence in minutes"
SAMPLE_BUTTON = "or open a sample deck"
RUN_BUTTON = "Analyse the deck"
DOWNLOAD = "Download the memo (PDF)"
RESULTS = "At a glance"

# Streamlit's own chrome ("Deploy", the running indicator, the toolbar) is not part of the
# product and must not appear in screenshots or in the video.
HIDE_CHROME = """
    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    div[data-testid="stStatusWidget"],
    footer { display: none !important; }
"""


def _settle(page: Page, ms: int = 600) -> None:
    page.wait_for_timeout(ms)


def _shot(page: Page, name: str) -> None:
    MEDIA.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(MEDIA / f"{name}.png"))
    print(f"  screenshot: docs/media/{name}.png")


def main() -> int:
    parser = argparse.ArgumentParser(description="Record the demo video and screenshots.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8511")
    parser.add_argument("--sample", default="cursor_deck.pdf", help="bundled deck to analyse")
    parser.add_argument(
        "--sample-label",
        default="Cursor — cursor_deck.pdf",
        help="exact button label in the dialog",
    )
    parser.add_argument("--out", default="/tmp/duedil-capture")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    video_dir = out / "video"
    video_dir.mkdir(exist_ok=True)

    timings: dict[str, float] = {}
    started = time.monotonic()

    def mark(name: str) -> None:
        timings[name] = round(time.monotonic() - started, 2)
        print(f"  t={timings[name]:>6.2f}s  {name}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(
            viewport={"width": args.width, "height": args.height},
            record_video_dir=str(video_dir),
            record_video_size={"width": args.width, "height": args.height},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.add_init_script(
            f"document.addEventListener('DOMContentLoaded', () => {{ const s = document.createElement('style'); s.textContent = `{HIDE_CHROME}`; document.head.appendChild(s); }});"
        )
        page.goto(args.base_url, wait_until="domcontentloaded")
        page.add_style_tag(content=HIDE_CHROME)
        page.get_by_text(HERO).wait_for(timeout=60_000)
        _settle(page, 1500)
        mark("idle")
        _shot(page, "ui-idle-en")

        # Choose a bundled deck, exactly as a visitor would.
        page.get_by_role("button", name=SAMPLE_BUTTON).click()
        _settle(page, 900)
        mark("dialog")
        page.get_by_role("button", name=f"📄 {args.sample_label}").click()
        _settle(page, 1200)
        mark("sample_selected")

        page.get_by_role("button", name=RUN_BUTTON).click()
        mark("run_clicked")
        _settle(page, 3500)
        _shot(page, "ui-running")

        # The live run takes a minute or two; the video speeds this part up.
        page.get_by_text(RESULTS).wait_for(timeout=420_000)
        mark("results")
        # The dataframes and the verdict block render a beat after the headline; capturing
        # immediately produced screenshots with half-drawn tables.
        _settle(page, 3000)
        _shot(page, "ui-results-en")

        page.get_by_text("What the deck claims").scroll_into_view_if_needed()
        _settle(page, 1800)
        mark("tables")

        try:
            # A clean run has no red flags at all: fail fast instead of stalling the recording.
            page.get_by_text("Red flags", exact=True).scroll_into_view_if_needed(timeout=2500)
            _settle(page, 900)
            _shot(page, "ui-redflags-en")
            mark("red_flags")
        except Exception:  # pragma: no cover - a clean run has no flags
            print("  (no red flags section: the run found none)")

        page.get_by_text("Investment memo", exact=True).scroll_into_view_if_needed()
        _settle(page, 900)
        mark("memo")

        # The PDF is the artefact an investor keeps: save exactly what the button produces.
        try:
            with page.expect_download(timeout=60_000) as download_info:
                page.get_by_role("button", name=DOWNLOAD).click()
            download = download_info.value
            download.save_as(str(out / "memo.pdf"))
            print("  saved: memo.pdf")
        except Exception as exc:  # pragma: no cover - download is best effort
            print(f"  (download failed: {exc})")

        mark("end")
        video = page.video
        context.close()
        if video:
            recorded = Path(video.path())
            target = out / "recording.webm"
            shutil.copy2(recorded, target)
            print(f"  recording: {target}")

    (out / "timings.json").write_text(json.dumps(timings, indent=2), encoding="utf-8")
    print(f"  timings: {out / 'timings.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
