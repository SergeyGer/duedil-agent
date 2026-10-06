#!/usr/bin/env python3
"""Capture screenshots and a walkthrough video of the Streamlit UI.

Drives a running DueDil.Agent UI with Playwright: it uploads a pitch deck,
clicks "Run due diligence", waits for the memo and saves the frames listed in
``--shots``. One video (``--video-out``) is recorded per run.

Designed to run inside the official Playwright image, which already ships
Chromium and the video codecs:

    docker run --rm --network host \
        -v "$PWD:/work" -v /tmp/capture:/capture -w /work \
        -e CAPTURE_BASE_URL=http://127.0.0.1:8501 \
        -e CAPTURE_DECK=examples/sample_deck.pdf \
        -e CAPTURE_OUT=/capture \
        -e CAPTURE_SHOTS=1 \
        mcr.microsoft.com/playwright/python:v1.49.1-noble \
        python scripts/capture_demo.py

The ``CAPTURE_*`` environment variables exist so the container needs no
arguments; the equivalent CLI flags take precedence.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

# UI strings the runner needs to find, per language.
STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "run": "Run due diligence",
        "download": "Download PDF",
        "running": "Running the agent pipeline",
    },
    "ru": {
        "run": "Запустить проверку",
        "download": "Скачать PDF",
        "running": "Пайплайн агентов выполняется",
    },
}

# Language selector option -> language code.
LANGUAGE_OPTIONS = {"English": "en", "Deutsch": "de", "Français": "fr", "Русский": "ru"}

SIDEBAR = 'section[data-testid="stSidebar"]'

# Hide Streamlit's own chrome so the captures show the application, not the host.
HIDE_CHROME = """
    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"] { display: none !important; }
    div[data-testid="stAppViewContainer"] > section.main > div.block-container,
    div[data-testid="stMainBlockContainer"] { padding-top: 2.5rem !important; }
"""


def _settle(page: Page, ms: int = 700) -> None:
    page.wait_for_timeout(ms)


def _parse_shots(raw: str) -> list[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def _select_language(page: Page, code: str) -> None:
    """Pick a UI language in the sidebar selector (triggers a Streamlit rerun)."""

    label = next(name for name, value in LANGUAGE_OPTIONS.items() if value == code)
    # Streamlit renders `st.selectbox` as a React Aria ComboBox: the trigger is a
    # readonly input inside `data-testid="stSelectbox"`, the options are generic
    # `role="option"` elements (not `<li>` as in older BaseWeb builds).
    box = page.locator(f'{SIDEBAR} div[data-testid="stSelectbox"]').first
    box.locator("input").first.click()
    _settle(page, 600)
    page.locator('[role="option"]', has_text=label).first.click()
    _settle(page, 2500)


def _upload(page: Page, deck: Path) -> None:
    page.set_input_files(f'{SIDEBAR} input[type="file"]', str(deck))
    _settle(page, 2500)


def _fill_url(page: Page, url: str) -> None:
    if not url:
        return
    field = page.locator(f'{SIDEBAR} input[type="text"]').first
    field.fill(url)
    field.press("Enter")
    _settle(page, 1200)


def _shot(page: Page, out: Path, name: str) -> None:
    page.screenshot(path=str(out / f"{name}.png"), full_page=True)
    print(f"  saved {name}.png")


def _run(page: Page, strings: dict[str, str], shots: list[str], out: Path, name: str) -> None:
    """Click the run button, optionally catch the in-flight state, wait for the memo."""

    page.get_by_role("button", name=strings["run"], exact=False).first.click()

    if "running" in shots:
        try:
            page.wait_for_selector(f"text={strings['running']}", timeout=30000)
            page.wait_for_timeout(900)
            _shot(page, out, f"ui-running{name}")
        except Exception as exc:  # pragma: no cover - only if the run is too fast to catch
            print(f"  note: could not capture the in-flight state ({exc})")

    # The download button only renders once the memo exists.
    page.wait_for_selector(f'button:has-text("{strings["download"]}")', timeout=180000)
    page.wait_for_timeout(2500)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url", default=os.getenv("CAPTURE_BASE_URL", "http://127.0.0.1:8501")
    )
    parser.add_argument("--deck", default=os.getenv("CAPTURE_DECK", "examples/sample_deck.pdf"))
    parser.add_argument("--url", default=os.getenv("CAPTURE_SITE_URL", "https://nimbusai.example"))
    parser.add_argument("--out", default=os.getenv("CAPTURE_OUT", "docs/media"))
    parser.add_argument("--lang", default=os.getenv("CAPTURE_LANG", "en"))
    parser.add_argument("--second-lang", default=os.getenv("CAPTURE_SECOND_LANG", "ru"))
    parser.add_argument("--video-out", default=os.getenv("CAPTURE_VIDEO_OUT", ""))
    parser.add_argument("--shots", default=os.getenv("CAPTURE_SHOTS", "1"))
    parser.add_argument("--width", type=int, default=1440)
    # Tall viewport: the whole result page (progress, metrics, red flags, memo and
    # the download button) fits in one frame without scrolling.
    parser.add_argument("--height", type=int, default=1600)
    args = parser.parse_args(argv)

    shots = _parse_shots(args.shots)
    lang = args.lang
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    video_dir = out / "_video"
    video_dir.mkdir(parents=True, exist_ok=True)

    deck = Path(args.deck).resolve()
    if not deck.exists():
        print(f"error: deck not found: {deck}", file=sys.stderr)
        return 2

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(
            viewport={"width": args.width, "height": args.height},
            device_scale_factor=2,
            record_video_dir=str(video_dir),
            record_video_size={"width": args.width, "height": args.height},
        )
        page = context.new_page()
        page.goto(args.base_url, wait_until="networkidle")
        page.add_style_tag(content=HIDE_CHROME)
        page.wait_for_timeout(2000)

        if lang != "en":
            _select_language(page, lang)

        if "idle" in shots:
            _shot(page, out, f"ui-idle-{lang}")

        _upload(page, deck)
        _fill_url(page, args.url)
        _run(page, STRINGS[lang], shots, out, "" if lang == "en" else f"-{lang}")

        if "results" in shots:
            _shot(page, out, f"ui-results-{lang}")

        if args.second_lang and args.second_lang != lang:
            # Switching the language resets the session, so the pipeline has to run
            # again for that language's screenshots to show real results.
            _select_language(page, args.second_lang)
            _upload(page, deck)
            _fill_url(page, args.url)
            _run(page, STRINGS[args.second_lang], [], out, f"-{args.second_lang}")
            if "results" in shots:
                _shot(page, out, f"ui-results-{args.second_lang}")

        video = page.video
        context.close()  # finalises the video file
        if video and args.video_out:
            recorded = Path(video.path())
            target = Path(args.video_out)
            target.parent.mkdir(parents=True, exist_ok=True)
            # The Playwright video lives under --out, which may be a different mount
            # than --video-out, so a plain rename would raise EXDEV.
            shutil.move(str(recorded), str(target))
            print(f"  saved {target}")
        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
