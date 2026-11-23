"""SRT subtitles built from the exact sentence timings of the narration."""
from __future__ import annotations

import textwrap
from pathlib import Path

from .tts import Segment

MAX_LINE = 42
MAX_CUE = MAX_LINE * 2


def _ts(t: float) -> str:
    ms = int(round(max(t, 0) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def _chunks(text: str) -> list[str]:
    words, out, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > MAX_CUE:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    # avoid a tiny last chunk
    if len(out) > 1 and len(out[-1]) < 18:
        merged = out[-2] + " " + out[-1]
        out[-2:] = [merged] if len(merged) <= MAX_CUE + 18 else out[-2:]
    return out


def build_cues(scene_segments: list[list[Segment]], offsets: list[float]) -> list[tuple[float, float, str]]:
    cues = []
    for segs, off in zip(scene_segments, offsets):
        for seg in segs:
            parts = _chunks(seg.text)
            total = sum(len(p) for p in parts) or 1
            t = seg.start
            span = seg.end - seg.start
            for p in parts:
                d = span * len(p) / total
                cues.append((off + t, off + t + d, p))
                t += d
    return cues


def write_srt(cues: list[tuple[float, float, str]], path: Path) -> None:
    lines = []
    for i, (a, b, text) in enumerate(cues, 1):
        wrapped = "\n".join(textwrap.wrap(text, MAX_LINE + 6)[:2]) if len(text) > MAX_LINE else text
        lines += [str(i), f"{_ts(a)} --> {_ts(b)}", wrapped, ""]
    path.write_text("\n".join(lines), encoding="utf-8")
