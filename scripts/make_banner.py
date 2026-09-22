#!/usr/bin/env python3
"""Generate the 1280x640 GitHub social-preview banner (PNG + SVG).

The PNG is drawn with Pillow; the SVG mirrors the same layout. No network
access is required.

Usage::

    python scripts/make_banner.py [OUTPUT_DIR]   # default: assets/
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 640
OUT_DIR = Path("assets")

# --- palette ---------------------------------------------------------------
BG_TOP = (10, 23, 48)
BG_BOTTOM = (22, 48, 90)
GLOW = (60, 130, 220)
TITLE = (255, 255, 255)
SUBTITLE = (185, 203, 230)
SUBTITLE2 = (143, 166, 196)
MUTED = (124, 147, 179)
ACCENT = (76, 141, 255)
PILL_BG = (30, 58, 99)
PILL_BORDER = (46, 92, 153)
PILL_TEXT = (207, 224, 245)
FLAG = (255, 122, 89)

# --- layout ----------------------------------------------------------------
LEFT = 90
PILL_X, PILL_W, PILL_H, PILL_GAP, PILL_TOP = 850, 260, 46, 18, 169
STEP = PILL_H + PILL_GAP

TITLE_TEXT = "DueDil.Agent"
SUBTITLE_1 = "Autonomous multi-agent due diligence"
SUBTITLE_2 = "for technology startups"
TAGLINE = "Pitch deck \u2192 Red Flags \u2192 investment memo (PDF)"
URL_TEXT = "github.com/SergeyGer/duedil-agent"
LICENSE_TEXT = "MIT License"
CHIPS = ["LangGraph", "LangChain", "Tavily", "Streamlit", "OpenAI"]
STEPS = ["Extractor", "Scraper", "Financial", "Critic", "Supervisor"]

_FONTS = {
    False: [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    True: [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
}


def _font(size: int, bold: bool = False):
    for path in _FONTS[bold]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _gradient() -> Image.Image:
    img = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        color = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        draw.line([(0, y), (W, y)], fill=(*color, 255))
    return img


def _glow() -> Image.Image:
    """A smooth radial glow built at low resolution and then upscaled."""

    size = 512
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = glow.load()
    center = size / 2
    for y in range(size):
        for x in range(size):
            dist = ((x - center) ** 2 + (y - center) ** 2) ** 0.5 / center
            if dist < 1:
                pixels[x, y] = (*GLOW, int(120 * (1 - dist) ** 2))
    return glow.resize((1000, 1000), Image.LANCZOS)


def render_png(path: Path) -> None:
    img = _gradient()
    glow = _glow()
    # ``paste`` clips gracefully if the glow extends past the canvas.
    img.paste(glow, (980 - glow.width // 2, 320 - glow.height // 2), glow)
    draw = ImageDraw.Draw(img)

    f_title = _font(74, bold=True)
    f_sub = _font(30)
    f_tag = _font(23)
    f_chip = _font(20)
    f_pill = _font(22)
    f_small = _font(21)
    f_url = _font(22)

    draw.ellipse([LEFT, 90, LEFT + 56, 146], outline=ACCENT, width=9)
    draw.line([LEFT + 44, 134, LEFT + 78, 168], fill=ACCENT, width=11)

    draw.text((LEFT, 186), TITLE_TEXT, font=f_title, fill=TITLE)
    draw.text((LEFT + 2, 288), SUBTITLE_1, font=f_sub, fill=SUBTITLE)
    draw.text((LEFT + 2, 326), SUBTITLE_2, font=f_sub, fill=SUBTITLE)
    draw.text((LEFT + 2, 372), TAGLINE, font=f_tag, fill=SUBTITLE2)

    x, y = LEFT, 416
    for chip in CHIPS:
        width = draw.textlength(chip, font=f_chip) + 30
        draw.rounded_rectangle(
            [x, y, x + width, y + 38], radius=19, fill=PILL_BG, outline=PILL_BORDER, width=2
        )
        draw.text((x + 15, y + 9), chip, font=f_chip, fill=PILL_TEXT)
        x += width + 12

    cx = PILL_X + PILL_W // 2
    for i, step in enumerate(STEPS):
        top = PILL_TOP + i * STEP
        draw.rounded_rectangle(
            [PILL_X, top, PILL_X + PILL_W, top + PILL_H],
            radius=14,
            fill=PILL_BG,
            outline=PILL_BORDER,
            width=2,
        )
        tw = draw.textlength(step, font=f_pill)
        draw.text((cx - tw / 2, top + 11), step, font=f_pill, fill=PILL_TEXT)
        if i < len(STEPS) - 1:
            ay = top + PILL_H
            draw.line([cx, ay + 3, cx, ay + 14], fill=PILL_BORDER, width=3)
            draw.polygon([(cx - 6, ay + 12), (cx + 6, ay + 12), (cx, ay + 20)], fill=PILL_BORDER)

    rx = PILL_X + PILL_W + 36
    critic_y = PILL_TOP + 3 * STEP + PILL_H // 2
    scraper_y = PILL_TOP + 1 * STEP + PILL_H // 2
    mid = (critic_y + scraper_y) // 2
    draw.line([rx, critic_y, rx, scraper_y + 12], fill=FLAG, width=3)
    draw.polygon(
        [(rx - 7, scraper_y + 12), (rx + 7, scraper_y + 12), (rx, scraper_y - 2)], fill=FLAG
    )
    draw.text((rx + 12, mid - 16), "Red", font=f_small, fill=FLAG)
    draw.text((rx + 12, mid + 2), "Flags", font=f_small, fill=FLAG)

    draw.text((LEFT, 566), URL_TEXT, font=f_url, fill=MUTED)
    tw = draw.textlength(LICENSE_TEXT, font=f_small)
    draw.text((W - LEFT - tw, 568), LICENSE_TEXT, font=f_small, fill=MUTED)

    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, "PNG")


def _hex(color: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*color)


def render_svg(path: Path) -> None:
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, Helvetica, sans-serif">',
        "  <defs>",
        '    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">',
        f'      <stop offset="0" stop-color="{_hex(BG_TOP)}"/>',
        f'      <stop offset="1" stop-color="{_hex(BG_BOTTOM)}"/>',
        "    </linearGradient>",
        '    <radialGradient id="glow">',
        f'      <stop offset="0" stop-color="{_hex(GLOW)}" stop-opacity="0.45"/>',
        f'      <stop offset="1" stop-color="{_hex(GLOW)}" stop-opacity="0"/>',
        "    </radialGradient>",
        "  </defs>",
        f'  <rect width="{W}" height="{H}" fill="url(#bg)"/>',
        '  <circle cx="980" cy="320" r="500" fill="url(#glow)"/>',
        f'  <circle cx="{LEFT + 28}" cy="118" r="28" fill="none" stroke="{_hex(ACCENT)}" stroke-width="9"/>',
        f'  <line x1="{LEFT + 44}" y1="134" x2="{LEFT + 78}" y2="168" stroke="{_hex(ACCENT)}" '
        'stroke-width="11" stroke-linecap="round"/>',
        f'  <text x="{LEFT}" y="246" font-size="74" font-weight="700" fill="{_hex(TITLE)}">{TITLE_TEXT}</text>',
        f'  <text x="{LEFT + 2}" y="322" font-size="30" fill="{_hex(SUBTITLE)}">{SUBTITLE_1}</text>',
        f'  <text x="{LEFT + 2}" y="360" font-size="30" fill="{_hex(SUBTITLE)}">{SUBTITLE_2}</text>',
        f'  <text x="{LEFT + 2}" y="396" font-size="23" fill="{_hex(SUBTITLE2)}">{TAGLINE}</text>',
    ]

    x = LEFT
    for chip in CHIPS:
        width = len(chip) * 11 + 30
        parts.append(
            f'  <rect x="{x}" y="416" width="{width}" height="38" rx="19" '
            f'fill="{_hex(PILL_BG)}" stroke="{_hex(PILL_BORDER)}" stroke-width="2"/>'
        )
        parts.append(
            f'  <text x="{x + 15}" y="442" font-size="20" fill="{_hex(PILL_TEXT)}">{chip}</text>'
        )
        x += width + 12

    cx = PILL_X + PILL_W // 2
    for i, step in enumerate(STEPS):
        top = PILL_TOP + i * STEP
        parts.append(
            f'  <rect x="{PILL_X}" y="{top}" width="{PILL_W}" height="{PILL_H}" rx="14" '
            f'fill="{_hex(PILL_BG)}" stroke="{_hex(PILL_BORDER)}" stroke-width="2"/>'
        )
        parts.append(
            f'  <text x="{cx}" y="{top + 30}" text-anchor="middle" font-size="22" '
            f'fill="{_hex(PILL_TEXT)}">{step}</text>'
        )
        if i < len(STEPS) - 1:
            ay = top + PILL_H
            parts.append(
                f'  <line x1="{cx}" y1="{ay + 3}" x2="{cx}" y2="{ay + 14}" '
                f'stroke="{_hex(PILL_BORDER)}" stroke-width="3"/>'
            )
            parts.append(
                f'  <polygon points="{cx - 6},{ay + 12} {cx + 6},{ay + 12} {cx},{ay + 20}" '
                f'fill="{_hex(PILL_BORDER)}"/>'
            )

    rx = PILL_X + PILL_W + 36
    critic_y = PILL_TOP + 3 * STEP + PILL_H // 2
    scraper_y = PILL_TOP + 1 * STEP + PILL_H // 2
    mid = (critic_y + scraper_y) // 2
    parts.append(
        f'  <line x1="{rx}" y1="{critic_y}" x2="{rx}" y2="{scraper_y + 12}" '
        f'stroke="{_hex(FLAG)}" stroke-width="3"/>'
    )
    parts.append(
        f'  <polygon points="{rx - 7},{scraper_y + 12} {rx + 7},{scraper_y + 12} {rx},{scraper_y - 2}" '
        f'fill="{_hex(FLAG)}"/>'
    )
    parts.append(
        f'  <text x="{rx + 12}" y="{mid - 6}" font-size="21" fill="{_hex(FLAG)}">Red</text>'
    )
    parts.append(
        f'  <text x="{rx + 12}" y="{mid + 16}" font-size="21" fill="{_hex(FLAG)}">Flags</text>'
    )

    parts.append(
        f'  <text x="{LEFT}" y="586" font-size="22" fill="{_hex(MUTED)}">{URL_TEXT}</text>'
    )
    parts.append(
        f'  <text x="{W - LEFT}" y="586" text-anchor="end" font-size="21" fill="{_hex(MUTED)}">'
        f"{LICENSE_TEXT}</text>"
    )
    parts.append("</svg>")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT_DIR
    png = out_dir / "social-preview.png"
    svg = out_dir / "social-preview.svg"
    render_png(png)
    render_svg(svg)
    print(f"Wrote {png} and {svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
