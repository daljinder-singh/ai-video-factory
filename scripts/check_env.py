#!/usr/bin/env python3
"""Phase 0: verify every dependency the video factory needs. Exit code 1 if a required item is missing."""
from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OK, WARN, FAIL = "\033[32mOK  \033[0m", "\033[33mWARN\033[0m", "\033[31mFAIL\033[0m"
failures = 0


def report(status: str, name: str, detail: str = "") -> None:
    global failures
    if status == FAIL:
        failures += 1
    print(f"[{status}] {name:<28} {detail}")


def check_module(mod: str, required: bool = True, hint: str = "") -> None:
    try:
        m = importlib.import_module(mod)
        report(OK, f"python: {mod}", getattr(m, "__version__", ""))
    except Exception as e:  # noqa: BLE001
        report(FAIL if required else WARN, f"python: {mod}", f"{type(e).__name__}: {e} {hint}".strip())


def main() -> int:
    print(f"Python {sys.version.split()[0]} at {sys.executable}\n")

    # --- LLM (Ollama) ---
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
            models = [m["name"] for m in json.load(r)["models"]]
        report(OK, "ollama server", ", ".join(models) or "(no models pulled)")
        if not any(m.startswith(("qwen", "llama", "gemma", "mistral")) for m in models):
            report(WARN, "ollama text model", "pull one: ollama pull qwen3:4b")
    except Exception as e:  # noqa: BLE001
        report(FAIL, "ollama server", f"not reachable ({e}); run: ollama serve")

    # --- ffmpeg (system or bundled static binary) ---
    ff = shutil.which("ffmpeg")
    if not ff:
        try:
            import imageio_ffmpeg

            ff = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:  # noqa: BLE001
            ff = None
    if ff:
        ver = subprocess.run([ff, "-version"], capture_output=True, text=True).stdout.split("\n")[0]
        report(OK if shutil.which("ffmpeg") else WARN, "ffmpeg",
               ver[:60] + ("" if shutil.which("ffmpeg") else "  (bundled only; manim wants system ffmpeg)"))
    else:
        report(FAIL, "ffmpeg", "sudo apt install ffmpeg")

    # --- Manim + its native deps ---
    check_module("manim", hint="-> sudo apt install libcairo2-dev libpango1.0-dev ffmpeg, then pip install manim")
    for tex in ("latex", "dvisvgm"):
        report(OK if shutil.which(tex) else WARN, tex,
               "" if shutil.which(tex) else "optional (MathTex); sudo apt install texlive-latex-extra dvisvgm")

    # --- Voice / subtitles ---
    check_module("piper")
    voices = sorted(p.stem for p in (ROOT / "models" / "piper").glob("*.onnx"))
    report(OK if voices else FAIL, "piper voices", ", ".join(voices) or "none in models/piper/")
    check_module("faster_whisper")

    # --- Fonts for Hindi text in animations/thumbnails ---
    fc = subprocess.run(["fc-list", ":lang=hi", "family"], capture_output=True, text=True).stdout.strip()
    report(OK if fc else WARN, "devanagari font", fc.split("\n")[0] if fc else "sudo apt install fonts-noto")

    # --- YouTube upload ---
    check_module("googleapiclient", required=False, hint="(needed in upload phase)")
    secret = ROOT / "secrets" / "client_secret.json"
    report(OK if secret.exists() else WARN, "youtube oauth client", str(secret) if secret.exists()
           else "add secrets/client_secret.json (upload phase)")

    print(f"\n{'All required checks passed.' if not failures else f'{failures} required check(s) failed.'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
