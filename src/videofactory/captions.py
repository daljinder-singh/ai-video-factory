"""Styled, burned-in captions (ASS): large, max two lines, key words highlighted, subtle fade/pop, placed in a
mobile-safe zone (above the Shorts title area and clear of the right-hand action buttons)."""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

from .tts import Segment

HIGHLIGHT_COLOUR = "&H0045D7FF&"  # #FFD745 (ASS colours are BGR)
STYLES = {  # name: (font size, line chars, margin L, margin R, margin V) in pixels for the video's own resolution
    "vertical": (76, 18, 70, 170, 430),
    "landscape": (54, 42, 120, 120, 60),
}


def _ts(t: float) -> str:
    t = max(t, 0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02}:{s:05.2f}"


def _chunks(text: str, max_chars: int) -> list[str]:
    """Phrase-sized pieces of at most two lines, split at natural breaks where possible."""
    words, out, cur = text.split(), [], ""
    limit = max_chars * 2
    for w in words:
        if cur and len(cur) + 1 + len(w) > limit:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
            if len(cur) > max_chars and re.search(r"[,;:]$", w):  # break after a clause once a line is full
                out.append(cur)
                cur = ""
    if cur:
        out.append(cur)
    return out


def _style_words(text: str, highlight: set[str]) -> str:
    def fmt(word: str) -> str:
        bare = re.sub(r"[^\wऀ-ॿ]", "", word).lower()
        if bare and (bare in highlight or re.search(r"\d", bare)):
            return f"{{\\c{HIGHLIGHT_COLOUR}}}{word}{{\\c&H00FFFFFF&}}"
        return word
    return " ".join(fmt(w) for w in text.split())


def write_ass(scene_segments: list[list[Segment]], offsets: list[float], highlights: list[list[str]], out: Path,
              width: int, height: int, font: str = "Noto Sans") -> int:
    kind = "vertical" if height > width else "landscape"
    size, line_chars, ml, mr, mv = STYLES[kind]
    scale = height / (1920 if kind == "vertical" else 1080)  # styles are defined for full HD
    size, ml, mr, mv = int(size * scale), int(ml * scale), int(mr * scale), int(mv * scale)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H7F000000,-1,0,0,0,100,100,0,0,1,{max(2, size // 16)},{max(1, size // 30)},2,{ml},{mr},{mv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines, count = [], 0
    for segs, off, hl in zip(scene_segments, offsets, highlights):
        words = {re.sub(r"[^\wऀ-ॿ]", "", w).lower() for h in hl for w in h.split() if w}
        for seg in segs:
            parts = _chunks(seg.text, line_chars)
            total = sum(len(p) for p in parts) or 1
            t = seg.start
            for p in parts:
                d = (seg.end - seg.start) * len(p) / total
                body = "\\N".join(_style_words(line, words) for line in textwrap.wrap(p, line_chars + 4)[:2])
                anim = "{\\fad(90,60)\\fscx94\\fscy94\\t(0,140,\\fscx100\\fscy100)}"
                lines.append(f"Dialogue: 0,{_ts(off + t)},{_ts(off + t + d)},Cap,,0,0,0,,{anim}{body}")
                t += d
                count += 1
    out.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")
    return count
