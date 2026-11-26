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
    "short": (1080, 1920, 30),  # vertical 9:16 (YouTube Shorts / Reels)
    "short_low": (540, 960, 15),  # fast vertical preview
}


@dataclass
class Settings:
    llm_model: str = "qwen3:4b"
    ollama_url: str = "http://localhost:11434"
    language: str = "en"  # English only
    voice: str = "af_heart"  # Kokoro voice for explainers and Shorts
    kids_voice: str = "af_bella"  # Kokoro voice for kids videos
    recipe_voice: str = "af_heart"  # Kokoro voice for recipe videos
    speech_speed: float = 1.0  # 1.2 = 20% faster
    quality: str = "high"
    min_scenes: int = 6
    max_scenes: int = 9
    music_path: str | None = None  # optional background music file
    music_volume: float = 0.12
    burn_subtitles: bool = False  # also keep the .srt for YouTube either way
    presenter: bool = True  # animated cartoon host (character chosen by topic category)
    short: bool = False  # vertical 9:16 YouTube Short (30-45 s); sets quality "short"
    sfx: bool = True  # subtle synthesised sound effects on scene events
    auto_music: bool = True  # original background score that follows the story's mood
    render_workers: int = 3
    output_dir: str = str(ROOT / "output" / "videos")
    models_dir: str = str(ROOT / "models")

    @property
    def resolution(self) -> tuple[int, int, int]:
        return QUALITY[self.quality]

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
        if s.language != "en":
            raise ValueError("Only English videos are supported (language must be 'en')")
        if s.short and not s.quality.startswith("short"):
            s.quality = "short"
        if s.quality not in QUALITY:
            raise ValueError(f"quality must be one of {list(QUALITY)}")
        if not 0.5 <= s.speech_speed <= 2.0:
            raise ValueError("speech_speed must be between 0.5 and 2.0")
        return s
