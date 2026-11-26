"""Tests for the storytelling / Shorts / sound upgrade. Fast: no LLM, tiny synthetic media.

Usage: PYTHONPATH=src .venv/bin/python tests/test_upgrade.py
"""
import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

from videofactory import assemble as asm
from videofactory.captions import write_ass
from videofactory.config import ROOT, Settings
from videofactory.kids.music import make_music
from videofactory.media import duration, probe
from videofactory.planner import (BANNED_OPENERS, WIDE, assign_purposes, enforce_variety, pick_title, plan_scenes,
                                  quality_score)
from videofactory.sfx import build_track
from videofactory.specs import Scene, VideoScript
from videofactory.tts import Segment

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def test_planner():
    sc = [{"template": t, "key_points": kp} for t, kp in [
        ("title_card", ["x"]), ("process_flow", ["a"]), ("process_flow", ["b"]), ("bar_chart", ["no digits"]),
        ("process_flow", ["c"]), ("process_flow", ["d"]), ("summary", ["z"])]]
    assign_purposes(sc)
    enforce_variety(sc, "science")
    tpls = [s["template"] for s in sc]
    check("variety: no template twice in a row", all(a != b for a, b in zip(tpls, tpls[1:])), tpls)
    check("variety: no template more than twice", max(tpls.count(t) for t in tpls) <= 2)
    check("variety: number charts need numbers", "bar_chart" not in tpls)
    check("purposes: hook first, ending last", sc[0]["purpose"] == "hook" and sc[-1]["purpose"] == "ending")
    short = ([{"template": "title_card", "key_points": []}] + [{"template": "cycle", "key_points": []} for _ in range(3)]
             + [{"template": "summary", "key_points": []}])  # distinct dicts
    enforce_variety(short, "science", short=True)
    st = [s["template"] for s in short[1:-1]]
    check("variety (Shorts): each template once", len(st) == len(set(st)), st)
    plans = plan_scenes(tpls, [s["purpose"] for s in sc])
    cams = [p.camera for p in plans]
    check("camera: never the same move twice in a row",
          all(not (a == b and a != "none") for a, b in zip(cams, cams[1:])), cams)
    check("camera: not every scene moves", cams.count("none") >= 1)
    check("presenter steps aside for wide visuals",
          all(not p.presenter for p, t in zip(plans, tpls) if t in WIDE))
    check("Shorts: no presenter", not any(p.presenter for p in plan_scenes(tpls, [s["purpose"] for s in sc], short=True)))
    check("hook gets an impact sound", "impact" in plans[0].sound_effects)


def test_writing_rules():
    check("banned opener detected", BANNED_OPENERS.search("Hello everyone, today we learn"))
    check("hook without greeting allowed", not BANNED_OPENERS.search("What if the Sun vanished tonight?"))
    t = pick_title(["Why Is the Sky Blue?", "SHOCKING sky secret you won't believe", "Rayleigh Scattering"],
                   "Why is the sky blue? Rayleigh scattering", "Rayleigh scattering")
    check("title: curious and honest wins, clickbait rejected", t == "Why Is the Sky Blue?", t)


def test_backward_compat_and_quality():
    # a script.json in the format used before this upgrade (no purpose / plan / short / quality fields)
    old = {"topic": "Black hole", "category": "science", "language": "en", "title": "Black Holes Explained",
           "hook": "Black holes", "description": "d", "tags": ["space"], "source_title": "Black hole",
           "source_url": "https://en.wikipedia.org/wiki/Black_hole", "scenes": [
               {"index": i, "heading": h, "narration": n, "visual": v} for i, (h, n, v) in enumerate([
                   ("Intro", "Hello and welcome to the channel! Today we explore black holes and why they matter.",
                    {"template": "title_card", "title": "Black holes", "subtitle": "Gravity's prison"}),
                   ("Definition", "A black hole is a region where gravity is so strong that nothing escapes.",
                    {"template": "definition", "term": "Black hole", "definition": "A region where nothing escapes."}),
                   ("Summary", "Black holes bend space and time. They are invisible but detectable.",
                    {"template": "summary", "heading": "Key takeaways", "points": ["Gravity wins", "Invisible"]})])]}
    s = VideoScript.model_validate(old)
    check("old script.json still loads", s.scenes[0].plan.camera == "none" and s.short is False)
    q = quality_score(s.scenes)
    check("quality: 'Hello and welcome' hook scores low", q["hook"] <= 3, q)
    good = [Scene(index=0, heading="Hook", narration="What if the Sun vanished? Earth would keep moving for eight minutes.",
                  visual={"template": "title_card", "title": "The Sun vanishes", "subtitle": "What happens next"},
                  purpose="hook")]
    check("quality: question hook scores high", quality_score(good)["hook"] >= 7)


def test_captions(tmp: Path):
    segs = [[Segment("Your brain is hiding something from you every single night.", 0.5, 3.6),
             Segment("Dreams happen in 4 stages of sleep.", 3.9, 6.0)]]
    ass = tmp / "c.ass"
    n = write_ass(segs, [0.0], [["brain"]], ass, 1080, 1920)
    txt = ass.read_text()
    check("captions: written", n >= 2, f"{n} lines")
    check("captions: vertical play resolution", "PlayResX: 1080" in txt and "PlayResY: 1920" in txt)
    style = next(l for l in txt.splitlines() if l.startswith("Style: Cap"))
    marg_v = int(style.split(",")[-2])  # ... MarginL, MarginR, MarginV, Encoding
    check("captions: above the Shorts title area (>= 20% from bottom)", marg_v >= 0.2 * 1920, f"MarginV={marg_v}")
    events = [l for l in txt.splitlines() if l.startswith("Dialogue")]
    check("captions: max two lines", all(l.count("\\N") <= 1 for l in events))
    check("captions: key word highlighted", any("brain" in l and "\\c&H0045D7FF&" in l for l in events))
    check("captions: numbers highlighted", any("\\c&H0045D7FF&}4" in l for l in events))


def test_audio(tmp: Path):
    n = build_track([(0.5, "impact"), (2.0, "whoosh"), (3.0, "pop"), (3.1, "pop"), (4.0, "shimmer")], 6.0, tmp / "fx.wav")
    check("sfx: events placed, duplicates suppressed", n == 4, f"{n} placed")
    check("sfx: track length", abs(duration(tmp / "fx.wav") - 6.0) < 0.05)
    info = make_music(12, tmp / "m.wav", 3, "mysterious", [(0, 4, 1.0), (4, 12, 0.4)])
    check("music: mysterious mood is in a minor key", info["key"].endswith("minor"), info)
    with wave.open(str(tmp / "m.wav")) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float)
    sr = 44100 * 2
    loud, soft = np.sqrt(np.mean(x[sr * 1: sr * 3] ** 2)), np.sqrt(np.mean(x[sr * 7: sr * 9] ** 2))
    check("music: volume curve follows the story", soft < loud * 0.75, f"loud {loud:.0f} soft {soft:.0f}")
    kids = make_music(5, tmp / "k.wav", 1)
    check("music: kids default unchanged (major key)", kids["key"].endswith("major"))


def _tiny_scene(path: Path, color: str, seconds: float, w: int, h: int):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:r=15:d={seconds}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)


def _tone(path: Path, seconds: float, freq: float):
    sr = 22050
    t = np.arange(int(sr * seconds)) / sr
    a = (0.5 * np.sin(2 * np.pi * freq * t) * (np.sin(2 * np.pi * 3 * t) > 0)).astype(np.float32)
    with wave.open(str(path), "wb") as wv:
        wv.setnchannels(1)
        wv.setsampwidth(2)
        wv.setframerate(sr)
        wv.writeframes((a * 32767).astype(np.int16).tobytes())


def test_assembly(tmp: Path):
    vids, wavs = [], []
    for i, (c, d) in enumerate((("navy", 2.0), ("teal", 3.0))):
        v, a = tmp / f"s{i}.mp4", tmp / f"s{i}.wav"
        _tiny_scene(v, c, d, 540, 960)
        _tone(a, d - 0.4, 300 + 100 * i)
        vids.append(v)
        wavs.append(a)
    fx = tmp / "fx2.wav"
    build_track([(0.1, "impact"), (2.05, "whoosh")], 5.0, fx)
    music = tmp / "m2.wav"
    make_music(5.0, music, 2, "curious")
    ass = tmp / "cap.ass"
    write_ass([[Segment("First scene words here.", 0.2, 1.5)], [Segment("Second scene with 7 facts.", 0.2, 2.5)]],
              [0.0, 2.0], [["first"], []], ass, 540, 960)
    out = tmp / "final.mp4"
    offs = asm.assemble(vids, wavs, tmp, out, srt=None, music=music, music_volume=0.12, sfx=fx, captions_ass=ass)
    info = probe(out)
    vs = next(s for s in info["streams"] if s["codec_type"] == "video")
    check("assembly: vertical output kept", int(vs["height"]) > int(vs["width"]), f"{vs['width']}x{vs['height']}")
    check("assembly: scene offsets", offs == [0.0, 2.0], offs)
    vd, ad = duration(out, "video"), duration(out, "audio")
    check("assembly: audio and video in sync", abs(vd - ad) < 0.1, f"v {vd:.2f} a {ad:.2f}")
    r = subprocess.run(["ffmpeg", "-i", str(out), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    lufs = float(m[-1]) if m else -99
    check("assembly: loudness normalised near -14 LUFS", -18 <= lufs <= -11, f"{lufs} LUFS")


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        test_planner()
        test_writing_rules()
        test_backward_compat_and_quality()
        test_captions(tmp)
        test_audio(tmp)
        test_assembly(tmp)
    bad = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(bad)}/{len(RESULTS)} checks passed" + (f"; failed: {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
