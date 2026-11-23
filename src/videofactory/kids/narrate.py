"""Kids narration: speak a list of sentences and pauses, recording when each part starts."""
from __future__ import annotations

import re
import wave
from pathlib import Path

import numpy as np

from ..tts import Narrator, Segment


MARKUP = re.compile(r"\[\[(.+?)\|(.+?)\]\]")


def shown(text: str) -> str:
    return MARKUP.sub(lambda m: m.group(1), text)


def spoken(text: str) -> str:
    return MARKUP.sub(lambda m: m.group(2), text)


def narrate_parts(narrator: Narrator, parts: list, out_wav: Path, lead: float = 0.7, gap: float = 0.5,
                  tail: float = 1.2) -> dict:
    sr = narrator.sr
    chunks = [np.zeros(int(lead * sr), np.float32)]
    t = lead
    part_times, segments = [], []
    for k, part in enumerate(parts):
        if k:
            chunks.append(np.zeros(int(gap * sr), np.float32))
            t += gap
        part_times.append(round(t, 3))
        if isinstance(part, (int, float)):  # a thinking pause (quiz) or a "say it with me" pause
            chunks.append(np.zeros(int(float(part) * sr), np.float32))
            t += float(part)
            continue
        audio = narrator.synth(spoken(part))
        segments.append(Segment(shown(part), round(t, 3), round(t + audio.size / sr, 3)))
        chunks.append(audio)
        t += audio.size / sr
    chunks.append(np.zeros(int(tail * sr), np.float32))
    audio = np.concatenate(chunks)
    audio = audio / (float(np.max(np.abs(audio))) or 1.0) * 0.89
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())
    return {"wav": str(out_wav), "duration": round(audio.size / sr, 3), "part_times": part_times,
            "segments": [s.__dict__ for s in segments]}
