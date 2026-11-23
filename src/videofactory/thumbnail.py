"""YouTube thumbnail (1280x720): bold hook text + a real frame from the video's most visual scene."""
from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .media import run_ffmpeg

W, H = 1280, 720
VISUAL_PRIORITY = ["process_flow", "cycle", "bar_chart", "formula", "concept_map", "timeline", "comparison",
                   "code", "big_number", "definition"]


def _font(family: str, bold: bool = True, size: int = 100) -> ImageFont.FreeTypeFont:
    pattern = f"{family}:{'bold' if bold else 'regular'}"
    path = subprocess.run(["fc-match", "-f", "%{file}", pattern], capture_output=True, text=True).stdout.strip()
    font = ImageFont.truetype(path, size)
    if bold:
        try:  # variable fonts (e.g. Baloo 2) need the weight chosen explicitly
            font.set_variation_by_name("ExtraBold" if "Baloo" in family else "Bold")
        except (OSError, ValueError, AttributeError):
            pass
    return font


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def pick_frame_scene(templates: list[str]) -> int:
    for t in VISUAL_PRIORITY:
        if t in templates:
            return templates.index(t)
    return min(1, len(templates) - 1)


def make_thumbnail(hook: str, category: str, frame_video: Path, frame_time: float, out: Path,
                   accent: str, second: str, style: str = "dark") -> None:
    kids = style == "kids"
    family = "Baloo 2" if kids else "Noto Sans"
    frame_png = out.with_name("thumb_frame.png")
    run_ffmpeg("-ss", f"{frame_time:.2f}", "-i", str(frame_video), "-frames:v", "1", str(frame_png))
    a, b = _hex(accent), _hex(second)

    # background: dark gradient with an accent glow
    img = Image.new("RGB", (W, H), (255, 243, 176) if kids else (11, 16, 32))
    glow = Image.new("RGB", (W, H), (255, 243, 176) if kids else (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((W * 0.45, -H * 0.4, W * 1.4, H * 1.2), fill=tuple(int(x * 0.45) for x in a))
    gd.ellipse((-W * 0.3, H * 0.55, W * 0.4, H * 1.5), fill=tuple(int(x * 0.25) for x in b))
    if kids:  # bright, sunny background
        gd.ellipse((W * 0.45, -H * 0.4, W * 1.4, H * 1.2), fill=(255, 182, 213))
        gd.ellipse((-W * 0.3, H * 0.55, W * 0.4, H * 1.5), fill=(160, 220, 255))
        img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(120)), 0.85)
    else:
        img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(120)), 0.9)

    # the real video frame, tilted card on the right
    frame = Image.open(frame_png).convert("RGB")
    fw = 600
    frame = frame.resize((fw, int(fw * frame.height / frame.width)), Image.LANCZOS)
    border = Image.new("RGBA", (frame.width + 16, frame.height + 16), a + (255,))
    border.paste(frame, (8, 8))
    shadow = Image.new("RGBA", (border.width + 80, border.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle((40, 40, 40 + border.width, 40 + border.height), fill=(0, 0, 0, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    card = Image.new("RGBA", shadow.size, (0, 0, 0, 0))
    card.alpha_composite(shadow, (12, 16))
    card.alpha_composite(border, (40, 40))
    card = card.rotate(-4, resample=Image.BICUBIC, expand=True)
    img = img.convert("RGBA")
    img.alpha_composite(card, (W - card.width + 70, (H - card.height) // 2 + 20))

    d = ImageDraw.Draw(img)
    # category pill
    pf = _font(family, True, 30)
    label = category.upper()
    tw = d.textlength(label, font=pf)
    d.rounded_rectangle((48, 44, 48 + tw + 40, 96), radius=26, fill=a + (255,))
    d.text((68, 50), label, font=pf, fill=(11, 16, 32))

    # hook text: whole words only, up to 3 lines, as large as fits left of the screenshot card
    words = (hook if kids else hook.upper()).split()
    max_w, best = W * 0.44, None
    for size in range(150, 40, -4):
        f = _font(family, True, size)
        if any(d.textlength(w, font=f) > max_w for w in words):
            continue  # a single word is too wide at this size
        lines, cur = [], ""
        for w in words:  # greedy wrap by measured pixel width, never splitting a word
            trial = f"{cur} {w}".strip()
            if cur and d.textlength(trial, font=f) > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        lines.append(cur)
        if len(lines) <= 3:
            best = (f, lines)
            break
    f, lines = best or (_font(family, True, 48), [" ".join(words)])
    line_h = int(f.size * 1.08)
    y = (H - line_h * len(lines)) // 2 + 30
    for i, line in enumerate(lines):
        if kids:  # playful: dark ink with a thick white outline, last line in the accent colour
            color = a if i == len(lines) - 1 else (58, 46, 92)
            d.text((56, y), line, font=f, fill=color, stroke_width=max(6, f.size // 12), stroke_fill=(255, 255, 255))
        else:
            color = a if i == len(lines) - 1 else (255, 255, 255)
            d.text((56 + 5, y + 6), line, font=f, fill=(0, 0, 0, 220))  # hard drop shadow for contrast
            d.text((56, y), line, font=f, fill=color)
        y += line_h
    d.rectangle((56, y + 12, 56 + 220, y + 24), fill=b + (255,))
    img.convert("RGB").save(out, quality=95)
    frame_png.unlink(missing_ok=True)
