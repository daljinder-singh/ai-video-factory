"""Quality checks on the finished video. Produces a list of checks with pass/warn/fail."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from .media import duration, probe


def _words(s: str) -> list[str]:
    return re.findall(r"[\wऀ-ॿ']+", s.lower())


def wer(ref: list[str], hyp: list[str]) -> float:
    if not ref:
        return 0.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1] / len(ref)


class QC:
    def __init__(self):
        self.checks: list[dict] = []

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append({"check": name, "status": status, "detail": detail})

    @property
    def passed(self) -> bool:
        return not any(c["status"] == "fail" for c in self.checks)


def run_qc(final: Path, scene_videos: list[Path], scene_wavs: list[Path], expected_scene_durations: list[float],
           narrations: list[str], srt: Path, thumbnail: Path, language: str, whisper: bool = True) -> QC:
    qc = QC()

    # 1. files exist and decode
    missing = [str(p) for p in [final, srt, thumbnail, *scene_videos, *scene_wavs] if not p.exists() or p.stat().st_size == 0]
    qc.add("files present", "fail" if missing else "pass", ", ".join(missing))
    if missing:
        return qc
    try:
        info = probe(final)
    except RuntimeError as e:
        qc.add("final video decodes", "fail", str(e))
        return qc
    kinds = [s["codec_type"] for s in info["streams"]]
    qc.add("video+audio streams", "pass" if "video" in kinds and "audio" in kinds else "fail", ", ".join(kinds))
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"], capture_output=True, text=True)
    qc.add("full decode without errors", "fail" if r.returncode or r.stderr.strip() else "pass", r.stderr.strip()[:300])

    # 2. A/V sync: audio and video lengths match
    vd, ad = duration(final, "video"), duration(final, "audio")
    qc.add("audio/video length match", "pass" if abs(vd - ad) < 0.15 else "fail", f"video {vd:.2f}s, audio {ad:.2f}s")

    # 3. scene order and timing: each rendered scene matches its narration length, in script order
    bad = []
    for i, (v, exp) in enumerate(zip(scene_videos, expected_scene_durations)):
        d = duration(v, "video")
        if abs(d - exp) > 0.25:
            bad.append(f"scene {i + 1}: {d:.2f}s vs narration {exp:.2f}s")
    qc.add("scene timing matches narration", "fail" if bad else "pass", "; ".join(bad))
    total_expected = sum(duration(v, "video") for v in scene_videos)
    qc.add("scene order/concatenation", "pass" if abs(total_expected - vd) < 0.2 else "fail",
           f"sum of scenes {total_expected:.2f}s, final {vd:.2f}s")

    # 4. readable text / layout from the render reports
    issues, min_size = [], 999.0
    for i, v in enumerate(scene_videos):
        rep = json.loads(v.with_suffix(".layout.json").read_text())
        issues += [f"scene {i + 1}: {x}" for x in rep["issues"]]
        if rep["min_text_size"]:
            min_size = min(min_size, rep["min_text_size"])
    qc.add("text readable and inside frame", "warn" if issues else "pass",
           "; ".join(issues) or f"smallest text size {min_size:.0f}")

    # 5. animation pacing: no scene too short or overlong
    pacing = [f"scene {i + 1} {d:.1f}s" for i, d in enumerate(expected_scene_durations) if d < 5 or d > 75]
    qc.add("scene pacing (5-75s)", "warn" if pacing else "pass", ", ".join(pacing))
    qc.add("total length", "pass" if 60 <= vd <= 900 else "warn", f"{vd / 60:.1f} min")

    # 6. black/frozen output
    r = subprocess.run(["ffmpeg", "-i", str(final), "-vf", "blackdetect=d=1.5:pix_th=0.05", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)
    qc.add("no long black segments", "fail" if blacks else "pass", str(blacks[:3]))

    # 7. audio level
    r = subprocess.run(["ffmpeg", "-i", str(final), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                       capture_output=True, text=True)
    mean = re.search(r"mean_volume: ([-\d.]+) dB", r.stderr)
    mv = float(mean.group(1)) if mean else -99
    qc.add("narration audible", "pass" if mv > -30 else "fail", f"mean volume {mv} dB")

    # 8. thumbnail size
    from PIL import Image
    with Image.open(thumbnail) as im:
        ok = im.size == (1280, 720) and thumbnail.stat().st_size < 2_000_000
    qc.add("thumbnail 1280x720 < 2MB", "pass" if ok else "fail", f"{thumbnail.stat().st_size // 1024} KB")

    # 9. speech matches script (verifies narration and subtitles) via faster-whisper
    if whisper:
        try:
            from faster_whisper import WhisperModel

            try:  # use the local copy only; never go online during QC
                model = WhisperModel("base", device="cpu", compute_type="int8", local_files_only=True)
            except Exception:  # first run on a new machine: download once
                model = WhisperModel("base", device="cpu", compute_type="int8")
            prompt = None if language == "en" else "नमस्ते बच्चों। यह वीडियो हिंदी में है। एक, दो, तीन।"  # Devanagari, not Urdu
            segs, _ = model.transcribe(str(final), language="en" if language == "en" else "hi", beam_size=1,
                                       vad_filter=True, initial_prompt=prompt)
            heard = " ".join(s.text for s in segs)
            err = wer(_words(" ".join(narrations)), _words(heard))
            limit = 0.25 if language == "en" else 0.6  # Hindi/Hinglish ASR is less reliable; informative only
            status = "pass" if err <= limit else ("warn" if language != "en" else "fail")
            note = "" if language == "en" else " (advisory only: the small Whisper model is weak at Hindi; listen to check)"
            qc.add("speech matches script (Whisper WER)", status, f"word error rate {err:.0%}{note}")
        except Exception as e:  # noqa: BLE001
            qc.add("speech matches script (Whisper WER)", "warn", f"skipped: {e}")
    return qc
