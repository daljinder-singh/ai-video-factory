"""ffmpeg/ffprobe helpers."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def ffmpeg_bin() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not found; install it with: sudo apt install ffmpeg")
    return exe


def run_ffmpeg(*args: str) -> None:
    r = subprocess.run([ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error", *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(args)[:300]}\n{r.stderr[-1500:]}")


def probe(path: Path | str) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe could not read {path}: {r.stderr.strip()[:300]}")
    return json.loads(r.stdout)


def duration(path: Path | str, kind: str = "format") -> float:
    """kind: 'format', 'video' or 'audio'."""
    info = probe(path)
    if kind == "format":
        return float(info["format"]["duration"])
    for s in info["streams"]:
        if s["codec_type"] == kind and "duration" in s:
            return float(s["duration"])
    raise RuntimeError(f"No {kind} stream with duration in {path}")
