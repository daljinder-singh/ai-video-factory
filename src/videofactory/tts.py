"""Local narration with Piper. Synthesizes sentence by sentence so we know exactly when each sentence is spoken."""
from __future__ import annotations

import re
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

SENT_RE = re.compile(r"(?<=[.!?।])\s+")


@dataclass
class Segment:
    text: str
    start: float
    end: float


@dataclass
class Narration:
    wav: str
    duration: float
    segments: list[Segment]

    def to_dict(self) -> dict:
        return {"wav": self.wav, "duration": self.duration, "segments": [asdict(s) for s in self.segments]}

    @classmethod
    def from_dict(cls, d: dict) -> "Narration":
        return cls(d["wav"], d["duration"], [Segment(**s) for s in d["segments"]])


def split_sentences(text: str, max_words: int = 28) -> list[str]:
    out: list[str] = []
    for s in SENT_RE.split(text.strip()):
        s = s.strip()
        if not s:
            continue
        words = s.split()
        if len(words) <= max_words:
            out.append(s)
            continue
        # long sentence: split at a comma near the middle so subtitles stay readable
        parts = re.split(r"(?<=[,;:])\s+", s)
        cur = ""
        for p in parts:
            if cur and len((cur + " " + p).split()) > max_words:
                out.append(cur)
                cur = p
            else:
                cur = f"{cur} {p}".strip()
        if cur:
            out.append(cur)
    return out


class Narrator:
    def __init__(self, voice_path: Path, speed: float = 1.0):
        from piper import PiperVoice, SynthesisConfig

        if not Path(voice_path).exists():
            raise FileNotFoundError(f"Piper voice not found: {voice_path}")
        self.voice = PiperVoice.load(str(voice_path))
        self.cfg = SynthesisConfig(length_scale=1.0 / speed)
        self.sr = self.voice.config.sample_rate

    def synth(self, text: str) -> np.ndarray:
        chunks = [c.audio_float_array for c in self.voice.synthesize(text, syn_config=self.cfg)]
        audio = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
        # trim leading/trailing near-silence so our own gaps control the pacing
        idx = np.flatnonzero(np.abs(audio) > 0.01)
        return audio[max(idx[0] - 200, 0): idx[-1] + 400] if idx.size else audio

    def narrate(self, text: str, out_wav: Path, lead: float = 0.5, gap: float = 0.35,
                tail: float = 0.9) -> Narration:
        sr = self.sr
        parts = [np.zeros(int(lead * sr), np.float32)]
        segments: list[Segment] = []
        t = lead
        for i, sentence in enumerate(split_sentences(text)):
            a = self.synth(sentence)
            if a.size == 0:
                continue
            if i:
                parts.append(np.zeros(int(gap * sr), np.float32))
                t += gap
            segments.append(Segment(sentence, round(t, 3), round(t + a.size / sr, 3)))
            parts.append(a)
            t += a.size / sr
        if not segments:
            raise ValueError("Narration produced no audio")
        parts.append(np.zeros(int(tail * sr), np.float32))
        audio = np.concatenate(parts)
        peak = float(np.max(np.abs(audio))) or 1.0
        audio = audio / peak * 0.89  # normalize to about -1 dBFS
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out_wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes((audio * 32767).astype(np.int16).tobytes())
        return Narration(str(out_wav), round(audio.size / sr, 3), segments)
