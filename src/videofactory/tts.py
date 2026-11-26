"""Local English narration with Kokoro. Synthesizes sentence by sentence so we know exactly when each sentence is spoken."""
from __future__ import annotations

import re
import wave
from functools import lru_cache
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

SENT_RE = re.compile(r"(?<=[.!?।])\s+")
EMPHASIS = re.compile(r"\d|\b(but|actually|surprisingly|in fact|imagine|that'?s why|the answer)\b", re.I)


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


KOKORO_DIR = Path(__file__).resolve().parents[2] / "models" / "kokoro"
KOKORO_VOICES = {  # best-rated English voices of Kokoro v1.0 (Apache 2.0)
    "af_heart": "American female, warm (default)", "af_bella": "American female, bright",
    "af_nicole": "American female, soft", "am_michael": "American male", "am_fenrir": "American male, deep",
    "bf_emma": "British female", "bm_george": "British male",
}


@lru_cache(maxsize=1)
def _kokoro():
    from kokoro_onnx import Kokoro

    model, voices = KOKORO_DIR / "kokoro-v1.0.onnx", KOKORO_DIR / "voices-v1.0.bin"
    if not model.exists() or not voices.exists():
        raise FileNotFoundError(f"Kokoro model files missing in {KOKORO_DIR} (kokoro-v1.0.onnx, voices-v1.0.bin)")
    return Kokoro(str(model), str(voices))


class Narrator:
    """Local English narration with Kokoro (82M parameters, runs on CPU)."""

    def __init__(self, voice: str = "af_heart", speed: float = 1.0):
        self.kokoro = _kokoro()
        if voice not in self.kokoro.get_voices():
            raise ValueError(f"Unknown Kokoro voice {voice!r}. Try one of: {', '.join(KOKORO_VOICES)}")
        self.voice, self.speed = voice, float(min(max(speed, 0.5), 2.0))
        self.sr = 24000

    def synth(self, text: str) -> np.ndarray:
        audio, sr = self.kokoro.create(text, voice=self.voice, speed=self.speed, lang="en-us")
        self.sr = sr
        audio = np.asarray(audio, dtype=np.float32)
        # trim leading/trailing near-silence so our own gaps control the pacing
        idx = np.flatnonzero(np.abs(audio) > 0.01)
        return audio[max(idx[0] - 240, 0): idx[-1] + 480] if idx.size else audio

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
                g = gap + (0.25 if EMPHASIS.search(sentence) else 0.0)  # breathe before a key fact
                parts.append(np.zeros(int(g * sr), np.float32))
                t += g
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
