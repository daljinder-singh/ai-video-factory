"""Settings. Defaults here; override with config.json in the project root, then with CLI flags."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

QUALITY = {  # name: (width, height, fps)
    "low": (854, 480, 15),
    "medium": (1280, 720, 30),
    "high": (1920, 1080, 30),
}


@dataclass
class Settings:
    llm_model: str = "qwen3:4b"
    ollama_url: str = "http://localhost:11434"
    language: str = "en"  # en | hi | hinglish
    voices: dict = field(default_factory=lambda: {
        "en": "en_US-lessac-medium",
        "hi": "hi_IN-pratham-medium",
        "hinglish": "hi_IN-pratham-medium",
    })
    speech_speed: float = 1.0  # 1.2 = 20% faster
    quality: str = "high"
    min_scenes: int = 6
    max_scenes: int = 9
    music_path: str | None = None  # optional background music file
    music_volume: float = 0.10
    burn_subtitles: bool = False  # also keep the .srt for YouTube either way
    presenter: bool = True  # animated cartoon host (character chosen by topic category)
    render_workers: int = 3
    output_dir: str = str(ROOT / "output" / "videos")
    models_dir: str = str(ROOT / "models")

    @property
    def resolution(self) -> tuple[int, int, int]:
        return QUALITY[self.quality]

    def voice_path(self) -> Path:
        return Path(self.models_dir) / "piper" / f"{self.voices[self.language]}.onnx"

    @classmethod
    def load(cls, **overrides) -> "Settings":
        data: dict = {}
        cfg = ROOT / "config.json"
        if cfg.exists():
            data.update(json.loads(cfg.read_text()))
        data.update({k: v for k, v in overrides.items() if v is not None})
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"Unknown settings: {sorted(unknown)}")
        s = cls(**data)
        if s.language not in ("en", "hi", "hinglish"):
            raise ValueError("language must be en, hi or hinglish")
        if s.quality not in QUALITY:
            raise ValueError(f"quality must be one of {list(QUALITY)}")
        if not 0.5 <= s.speech_speed <= 2.0:
            raise ValueError("speech_speed must be between 0.5 and 2.0")
        return s
