"""Original background music, synthesised from scratch (no samples, no copyright issues).

Cheerful major-key loop: marimba-like melody (A A B A phrase form), soft chord pad, bass, light percussion.
Every video gets a different tune from its random seed."""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100
MAJOR = [0, 2, 4, 5, 7, 9, 11]
PROGRESSIONS = [[0, 4, 5, 3], [0, 3, 4, 0], [0, 5, 3, 4], [0, 3, 0, 4]]  # I-V-vi-IV etc. (scale degrees)
RHYTHMS = [[1, 1, 1, 1], [0.5, 0.5, 1, 1, 1], [1, 0.5, 0.5, 2], [0.5, 0.5, 0.5, 0.5, 1, 1], [1.5, 0.5, 1, 1]]


def _freq(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _degree_to_midi(root: int, degree: int) -> int:
    octave, idx = divmod(degree, 7)
    return root + 12 * octave + MAJOR[idx]


def _marimba(f: float, dur: float) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    tone = np.sin(2 * np.pi * f * t) * np.exp(-t * 5.5) + 0.25 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 22)
    attack = np.minimum(t / 0.004, 1)
    return tone * attack


def _pad(freqs: list[float], dur: float, detune: float) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    env = np.minimum(t / 0.25, 1) * np.minimum((dur - t) / 0.3, 1).clip(0, 1)
    s = sum(np.sin(2 * np.pi * f * (1 + detune) * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t) for f in freqs)
    return s * env / len(freqs)


def _bass(f: float, dur: float) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    return (np.sin(2 * np.pi * f * t) + 0.2 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t * 3) * np.minimum(t / 0.01, 1)


def _kick(dur: float = 0.25) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    f = 50 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)


def _shaker(rng: np.random.Generator, dur: float = 0.07) -> np.ndarray:
    n = rng.standard_normal(int(SR * dur))
    n = np.diff(n, prepend=0)  # crude high-pass
    t = np.arange(len(n)) / SR
    return n * np.exp(-t * 60) * 0.5


def _add(buf: np.ndarray, sig: np.ndarray, start: float) -> None:
    i = int(start * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


def _phrase(rng: np.random.Generator, prog: list[int]) -> list[tuple[float, float, int]]:
    """4 bars of melody: list of (start_beat, length_beats, scale_degree)."""
    notes, deg = [], 7 + rng.integers(0, 3)
    for bar, chord in enumerate(prog):
        rhythm = RHYTHMS[rng.integers(len(RHYTHMS))]
        beat = 0.0
        for k, length in enumerate(rhythm):
            chord_tones = [chord + 7, chord + 9, chord + 11, chord + 14]
            if k == 0 or length >= 1.5:  # strong beats land on chord tones
                deg = min(chord_tones, key=lambda c: abs(c - deg))
            else:
                deg = int(np.clip(deg + rng.choice([-2, -1, 1, 2, 0]), 5, 16))
            notes.append((bar * 4 + beat, length, deg))
            beat += length
    return notes


def make_music(duration: float, out: Path, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    bpm = int(rng.choice([96, 104, 110, 116]))
    beat = 60.0 / bpm
    root = int(rng.choice([60, 62, 65, 67]))  # C, D, F, G major
    prog = PROGRESSIONS[rng.integers(len(PROGRESSIONS))]
    a, b = _phrase(rng, prog), _phrase(rng, prog[::-1] if prog[0] == prog[-1] else prog[1:] + prog[:1])
    section = [(a, prog), (a, prog), (b, prog[1:] + prog[:1]), (a, prog)]  # A A B A = 16 bars

    n = int(SR * (duration + 1))
    left, right = np.zeros(n), np.zeros(n)
    t0 = 0.0
    while t0 < duration:
        for phrase, chords in section:
            for bar, chord in enumerate(chords):
                bar_t = t0 + bar * 4 * beat
                tones = [_freq(_degree_to_midi(root - 12, chord + d)) for d in (0, 2, 4)]
                _add(left, 0.16 * _pad(tones, 4 * beat, -0.002), bar_t)
                _add(right, 0.16 * _pad(tones, 4 * beat, 0.002), bar_t)
                bass_f = _freq(_degree_to_midi(root - 24, chord))
                for bt in (0, 2):
                    sig = 0.32 * _bass(bass_f, 2 * beat)
                    _add(left, sig, bar_t + bt * beat)
                    _add(right, sig, bar_t + bt * beat)
                    _add(left, 0.22 * _kick(), bar_t + bt * beat)
                    _add(right, 0.22 * _kick(), bar_t + bt * beat)
                for half in range(8):
                    s = 0.07 * _shaker(rng)
                    _add(left if half % 2 else right, s, bar_t + half * beat / 2)
            for start, length, deg in phrase:
                sig = 0.33 * _marimba(_freq(_degree_to_midi(root, deg)), length * beat + 0.4)
                _add(left, sig * 0.9, t0 + start * beat)
                _add(right, sig, t0 + start * beat)
            t0 += 16 * beat
            if t0 >= duration:
                break

    mix = np.stack([left, right], axis=1)[: int(SR * duration)]
    fade_in, fade_out = int(SR * 1.0), int(SR * 3.0)
    mix[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    mix[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
    mix /= np.max(np.abs(mix)) or 1
    mix *= 0.85
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return {"bpm": bpm, "key": ["C", "D", "F", "G"][[60, 62, 65, 67].index(root)] + " major", "seed": seed}
