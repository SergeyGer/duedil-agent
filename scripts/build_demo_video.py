#!/usr/bin/env python3
"""Build the narrated demo video from a recorded session.

Inputs (produced by ``scripts/make_demo_video.py``):

* ``<capture>/recording.webm`` — the real session, with the cursor
* ``<capture>/timings.json`` — where each action happened
* ``<capture>/memo.pdf`` — the memo the UI downloaded
* ``docs/media/ui-*.png`` — the screenshots taken during the same session

Output: ``docs/media/demo.mp4`` — 1600x900, 30 fps, H.264 + AAC, with a narration track.

The narration is synthesised with Edge TTS (``pip install edge-tts``) and each segment lasts as
long as its voiceover, so the picture always matches the words. Cards are drawn with Pillow and
PDF pages are rasterised with pypdfium2.

Run:

    python scripts/build_demo_video.py \
        --capture /tmp/duedil-capture \
        --out docs/media/demo.mp4 \
        --ffmpeg /tmp/pw-browsers/ffmpeg-1010/ffmpeg-linux
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1600, 900
NAVY = (11, 37, 69)
ACCENT = (46, 107, 230)
INK = (24, 33, 46)
MUTED = (92, 106, 125)
PAPER = (247, 249, 252)

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(str(FONT_DIR / name), size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _card(path: Path, title: str, subtitle: str, footer: str, *, light: bool = False) -> Path:
    background = PAPER if light else NAVY
    heading = INK if light else (255, 255, 255)
    body = MUTED if light else (196, 212, 235)

    image = Image.new("RGB", (WIDTH, HEIGHT), background)
    draw = ImageDraw.Draw(image)

    if not light:
        draw.rectangle([0, 0, WIDTH, 10], fill=ACCENT)

    title_font = _font(76 if not light else 68, bold=True)
    subtitle_font = _font(34)
    footer_font = _font(26)

    y = 250
    for line in _wrap(draw, title, title_font, WIDTH - 240):
        draw.text((120, y), line, font=title_font, fill=heading)
        y += 92

    y += 26
    for line in _wrap(draw, subtitle, subtitle_font, WIDTH - 300):
        draw.text((120, y), line, font=subtitle_font, fill=body)
        y += 48

    draw.text((120, HEIGHT - 120), footer, font=footer_font, fill=body if not light else MUTED)
    draw.rectangle([120, HEIGHT - 150, 120 + 72, HEIGHT - 146], fill=ACCENT)

    image.save(path)
    return path


NARRATION = {
    "hook": (
        "Venture funds drown in first-pass screening. An analyst can spend three days on a single "
        "pitch deck, hunting for hidden risks by hand. DueDil compresses those three days into "
        "three minutes."
    ),
    "upload": "Upload the deck, add the company's website, and the analysis starts on its own.",
    "pipeline": (
        "It reads every figure the founders claim, benchmarks the numbers against the market, "
        "and looks for contradictions between them."
    ),
    "value": (
        "What comes back is the memo an analyst would have written: a clear recommendation, the "
        "deck's figures next to market reality, and the red flags it found — with the evidence "
        "that produced them."
    ),
    "trust": (
        "This public demo runs on deterministic rules rather than a language model, so nothing is "
        "invented; with a key, the same pipeline gets a model's judgement. DueDil is open source "
        "- run it with one Docker command, or try the live demo."
    ),
}

VOICE = "en-US-AndrewNeural"


async def _synthesise(text: str, path: Path, voice: str) -> None:
    """Synthesise one clip, retrying: the service occasionally returns no audio on bursts."""

    import edge_tts

    last: Exception | None = None
    for attempt in range(4):
        try:
            await edge_tts.Communicate(text, voice, rate="+2%").save(str(path))
            if path.is_file() and path.stat().st_size > 1000:
                return
        except Exception as exc:  # noqa: BLE001 - retried below
            last = exc
        await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Edge TTS returned no audio for {path.name}") from last


def _duration(ffmpeg: str, path: Path) -> float:
    out = subprocess.run(
        [ffmpeg, "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
    ).stderr
    for line in out.splitlines():
        if "Duration:" in line:
            stamp = line.split("Duration:")[1].split(",")[0].strip()
            hours, minutes, seconds = stamp.split(":")
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    raise RuntimeError(f"cannot read the duration of {path}")


def _run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(command[:6])}… failed:\n{result.stderr[-2500:]}")


def _image_segment(
    ffmpeg: str, image: Path, seconds: float, out: Path, *, zoom: bool = True, fade: bool = False
) -> None:
    frames = max(int(seconds * 30), 30)
    if zoom:
        video = (
            f"scale={WIDTH * 2}:{HEIGHT * 2},"
            f"zoompan=z='min(zoom+0.00035,1.06)':d={frames}:s={WIDTH}x{HEIGHT}:fps=30,"
        )
        # A fade belongs on the opening card only: fading every slide makes the montage flicker
        # and washes light cards out to grey for the first half-second.
        if fade:
            video += "fade=t=in:st=0:d=0.6,"
        video += "format=yuv420p"
    else:
        video = f"scale={WIDTH}:{HEIGHT},format=yuv420p"
    _run(
        [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-framerate",
            "30",
            "-i",
            str(image),
            "-t",
            f"{seconds:.2f}",
            "-vf",
            video,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ]
    )


def _clip(
    ffmpeg: str,
    source: Path,
    start: float,
    end: float,
    seconds: float,
    out: Path,
    *,
    speed: float = 1.0,
) -> None:
    """Cut ``source`` between two marks, optionally speed it up, and stretch it to ``seconds``."""

    video = f"fps=30,scale={WIDTH}:{HEIGHT},setpts=(PTS-STARTPTS)/{speed:.4f}"
    video += f",tpad=stop_mode=clone:stop_duration={max(seconds, 1) + 2:.1f}"
    video += ",format=yuv420p"
    _run(
        [
            ffmpeg,
            "-y",
            "-ss",
            f"{start:.2f}",
            "-to",
            f"{end:.2f}",
            "-i",
            str(source),
            "-t",
            f"{seconds:.2f}",
            "-vf",
            video,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(out),
        ]
    )


def _mux(ffmpeg: str, video: Path, audio: Path, seconds: float, out: Path) -> None:
    _run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-filter_complex",
            "[1:a]apad,atrim=0:" + f"{seconds:.2f}" + ",asetpts=N/SR/TB[a]",
            "-map",
            "0:v",
            "-map",
            "[a]",
            "-t",
            f"{seconds:.2f}",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            str(out),
        ]
    )


def _framed_page(page_path: Path, out_path: Path) -> Path:
    """Centre a full A4 page on a neutral canvas, unscaled beyond fitting the frame.

    The report is the artefact: it is shown whole, with a hairline shadow, never cropped and
    never zoomed — a moving or partial page reads as a screenshot, not as a document.
    """

    page = Image.open(page_path).convert("RGB")
    canvas = Image.new("RGB", (WIDTH, HEIGHT), (236, 240, 246))
    page.thumbnail((WIDTH - 140, HEIGHT - 70), Image.LANCZOS)

    x = (WIDTH - page.width) // 2
    y = (HEIGHT - page.height) // 2
    shadow = Image.new("RGB", (page.width + 10, page.height + 10), (205, 212, 222))
    canvas.paste(shadow, (x - 5, y - 5))
    canvas.paste(page, (x, y))
    canvas.save(out_path)
    return out_path


def _slideshow(
    ffmpeg: str, images: list[tuple[Path, float]], out: Path, *, zoom: bool = True
) -> None:
    """Build a segment from stills with gentle zoom, hard cuts between them."""

    parts = []
    with tempfile.TemporaryDirectory() as tmp:
        for index, (image, seconds) in enumerate(images):
            part = Path(tmp) / f"part{index}.mp4"
            _image_segment(ffmpeg, image, seconds, part, zoom=zoom)
            parts.append(part)
        listing = Path(tmp) / "list.txt"
        listing.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
        _run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(listing),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-an",
                str(out),
            ]
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the narrated demo video.")
    parser.add_argument("--capture", required=True)
    parser.add_argument("--out", default="docs/media/demo.mp4")
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--voice", default=VOICE)
    parser.add_argument("--keep", default="", help="keep the intermediate files in this directory")
    args = parser.parse_args()

    capture = Path(args.capture)
    timings = json.loads((capture / "timings.json").read_text(encoding="utf-8"))
    media = Path("docs/media")
    work = Path(tempfile.mkdtemp(prefix="duedil-video-"))

    # 1) voiceover
    voices: dict[str, Path] = {}
    for key, text in NARRATION.items():
        path = work / f"{key}.mp3"
        asyncio.run(_synthesise(text, path, args.voice))
        voices[key] = path
        print(f"  voice {key}: {_duration(args.ffmpeg, path):.1f}s")

    # 2) cards and PDF pages
    title_card = _card(
        work / "title.png",
        "Investment due diligence in minutes",
        "From a pitch deck to an investment memo — with a recommendation, benchmarked "
        "financials and red flags.",
        "DueDil",
    )
    outro_card = _card(
        work / "outro.png",
        "Automate your deal flow",
        "Open source on GitHub · live demo · one Docker command",
        "github.com/SergeyGer/duedil-agent",
        light=True,
    )

    pdf = pdfium.PdfDocument(str(capture / "memo.pdf"))
    pages = []
    for index in range(min(3, len(pdf))):
        page = pdf[index].render(scale=2.2).to_pil()
        path = work / f"pdf-{index}.png"
        page.save(path)
        pages.append(path)

    # 3) segments, each as long as its narration
    # A little air after each sentence: the picture holds, the voice can breathe.
    padding = {"hook": 2.8, "upload": 1.6, "pipeline": 1.2, "value": 3.2, "trust": 2.4}

    def seconds_of(key: str) -> float:
        return _duration(args.ffmpeg, voices[key]) + padding[key]

    run_at = timings["run_clicked"]
    results_at = timings["results"]
    end = timings["end"]

    segments: list[tuple[Path, str]] = []
    for name, seconds, key in (
        ("A", seconds_of("hook"), "hook"),
        ("B", seconds_of("upload"), "upload"),
        ("C", seconds_of("pipeline"), "pipeline"),
        ("D", seconds_of("value"), "value"),
        ("E", seconds_of("trust"), "trust"),
    ):
        video_path = work / f"{name}-video.mp4"
        if name == "A":
            _image_segment(args.ffmpeg, title_card, seconds, video_path, fade=True)
        elif name == "B":
            _clip(args.ffmpeg, capture / "recording.webm", 0, run_at, seconds, video_path)
        elif name == "C":
            speed = max((results_at - run_at) / seconds, 1.0)
            _clip(
                args.ffmpeg,
                capture / "recording.webm",
                run_at,
                results_at,
                seconds,
                video_path,
                speed=speed,
            )
        elif name == "D":
            # The results part of the recording, then the red flags and the memo as stills.
            clip_seconds = max(end - results_at, 1.0)
            if clip_seconds < seconds:
                left = seconds - clip_seconds
                slides = [
                    (media / "ui-redflags-en.png", left * 0.55),
                    (media / "ui-results-en.png", left * 0.45),
                ]
                stills = work / "D-stills.mp4"
                _slideshow(args.ffmpeg, slides, stills)
                listing = work / "D-list.txt"
                _clip(
                    args.ffmpeg,
                    capture / "recording.webm",
                    results_at,
                    end,
                    clip_seconds,
                    work / "D-clip.mp4",
                )
                listing.write_text(
                    f"file '{work / 'D-clip.mp4'}'\nfile '{stills}'\n", encoding="utf-8"
                )
                _run(
                    [
                        args.ffmpeg,
                        "-y",
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        str(listing),
                        "-c:v",
                        "libx264",
                        "-preset",
                        "medium",
                        "-crf",
                        "20",
                        "-pix_fmt",
                        "yuv420p",
                        "-an",
                        str(video_path),
                    ]
                )
            else:
                _clip(args.ffmpeg, capture / "recording.webm", results_at, end, seconds, video_path)
        elif name == "E":
            # The cover is the document's face: hold it, then walk the pages at reading size.
            framed = [
                _framed_page(page, work / f"framed-{index}.png") for index, page in enumerate(pages)
            ]
            cover_hold = 6.0
            rest = max(seconds - cover_hold - 2.5, 3.0)
            body_seconds = rest / max(len(framed) - 1, 1)
            slides = (
                [(framed[0], cover_hold)]
                + [(page, body_seconds) for page in framed[1:]]
                + [(outro_card, 2.5)]
            )
            _slideshow(args.ffmpeg, slides, video_path, zoom=False)

        muxed = work / f"{name}.mp4"
        _mux(args.ffmpeg, video_path, voices[key], seconds, muxed)
        segments.append((muxed, key))
        print(f"  segment {name}: {seconds:.1f}s")

    # 4) concatenate
    listing = work / "segments.txt"
    listing.write_text("".join(f"file '{p}'\n" for p, _ in segments), encoding="utf-8")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            args.ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(out),
        ]
    )
    print(f"  video: {out} ({_duration(args.ffmpeg, out):.1f}s)")

    if args.keep:
        shutil.copytree(work, Path(args.keep), dirs_exist_ok=True)
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
