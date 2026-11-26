"""Subtle sound effects, synthesised locally (no samples, no licences). Events are placed on a track that is mixed
quietly under the narration: element appears -> pop, scene change -> whoosh, reveal -> impact, finale -> shimmer."""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 48000


def _env(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / SR
    return np.minimum(t / max(attack, 1e-4), 1) * np.exp(-t * decay)


def whoosh(d: float = 0.45) -> np.ndarray:
    n = int(SR * d)
    noise = np.random.default_rng(1).standard_normal(n)
    # sweep a simple low-pass (one-pole) from dark to bright and back
    out, y = np.zeros(n), 0.0
    cut = 0.02 + 0.25 * np.sin(np.linspace(0, np.pi, n))
    for i in range(n):
        y += cut[i] * (noise[i] - y)
        out[i] = y
    return out * np.sin(np.linspace(0, np.pi, n)) * 1.6


def pop(d: float = 0.12) -> np.ndarray:
    n = int(SR * d)
    t = np.arange(n) / SR
    f = 900 * np.exp(-t * 18) + 380
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 38) * 0.7


def click(d: float = 0.05) -> np.ndarray:
    n = int(SR * d)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2400 * t) * 0.6 + np.random.default_rng(2).standard_normal(n) * 0.2) * _env(n, 0.0005, 120)


def impact(d: float = 0.9) -> np.ndarray:
    n = int(SR * d)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(45 + 70 * np.exp(-t * 9)) / SR) * _env(n, 0.003, 4.5)
    hit = np.random.default_rng(3).standard_normal(n) * _env(n, 0.001, 30) * 0.35
    return (boom + hit) * 0.9


def shimmer(d: float = 1.2) -> np.ndarray:
    n = int(SR * d)
    t = np.arange(n) / SR
    tones = sum(np.sin(2 * np.pi * f * t) * _env(n, 0.01 + 0.06 * k, 3.0) for k, f in enumerate((1318.5, 1568.0, 2093.0, 2637.0)))
    return tones * 0.25


SOUNDS = {"whoosh": whoosh, "pop": pop, "click": click, "impact": impact, "shimmer": shimmer}
LEVEL = {"whoosh": 0.22, "pop": 0.16, "click": 0.12, "impact": 0.30, "shimmer": 0.18}


def build_track(events: list[tuple[float, str]], total: float, out: Path) -> int:
    """events: (time_seconds, sound_name). Writes a 48 kHz stereo WAV; returns the number of events placed."""
    buf = np.zeros(int(SR * (total + 1)))
    cache: dict[str, np.ndarray] = {}
    placed = 0
    last_at: dict[str, float] = {}
    for t, name in sorted(events):
        if name not in SOUNDS or t < 0 or t > total:
            continue
        if t - last_at.get(name, -9) < 0.35:  # never machine-gun the same sound
            continue
        last_at[name] = t
        sig = cache.setdefault(name, SOUNDS[name]() * LEVEL[name])
        i = int(t * SR)
        j = min(len(buf), i + len(sig))
        buf[i:j] += sig[: j - i]
        placed += 1
    buf = buf[: int(SR * total)]
    peak = float(np.max(np.abs(buf))) or 1.0
    if peak > 0.95:
        buf *= 0.95 / peak
    stereo = np.stack([buf, buf], axis=1)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((stereo * 32767).astype(np.int16).tobytes())
    return placed
