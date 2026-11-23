"""Render one scene of every kids scene type (plus some Hindi ones) at low quality; report issues; contact sheet.

Usage: PYTHONPATH=src .venv/bin/python tests/test_kids_scenes.py
Output: output/dev/kids/scenes/<name>.mp4 and output/dev/kids/scenes/sheet.png
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from videofactory.config import QUALITY, ROOT
from videofactory.kids.lessons import TOPICS
from videofactory.kids.narrate import narrate_parts, shown
from videofactory.kids.script import build_script
from videofactory.tts import Narrator

OUT = ROOT / "output" / "dev" / "kids" / "scenes"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    w, h, fps = QUALITY["low"]
    voices = {lang: Narrator(ROOT / "models" / "piper" / f"{v}.onnx", 0.85)
              for lang, v in (("en", "en_US-lessac-medium"), ("hi", "hi_IN-pratham-medium"))}
    picks, seen = [], set()
    for lang in ("en", "hi"):
        for topic in TOPICS:
            for sc in build_script(topic, lang, 5)["scenes"]:
                key = sc["type"] if lang == "en" else f"hi_{sc['type']}"
                if key in seen or (lang == "hi" and sc["type"] not in ("intro", "count", "letter", "animal")):
                    continue
                seen.add(key)
                picks.append((key, topic, lang, sc))
    jobs = []
    for key, topic, lang, sc in picks:
        nr = narrate_parts(voices[lang], sc["parts"], OUT / f"{key}.wav")
        job = {"type": sc["type"], "data": sc["data"], "lang": lang, "topic": topic, "index": 1, "total": 10,
               "duration": round(nr["duration"] * fps) / fps, "part_times": nr["part_times"],
               "shown_parts": [shown(p) for p in sc["parts"] if isinstance(p, str)], "wav": nr["wav"],
               "width": w, "height": h, "fps": fps, "out": str(OUT / f"{key}.mp4"), "seed": 3}
        jp = OUT / f"{key}.job.json"
        jp.write_text(json.dumps(job, ensure_ascii=False))
        jobs.append((key, jp, job["duration"]))

    def run(item):
        key, jp, dur = item
        r = subprocess.run([sys.executable, "-m", "videofactory.kids.render_kids", str(jp)], capture_output=True, text=True,
                           env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin", "HOME": str(Path.home())})
        return key, dur, r

    bad = 0
    with ThreadPoolExecutor(3) as ex:
        for key, dur, r in ex.map(run, jobs):
            if r.returncode:
                bad += 1
                print(f"FAIL {key}\n{r.stderr[-1800:]}")
                continue
            rep = json.loads(r.stdout.strip().splitlines()[-1])
            bad += bool(rep["issues"])
            print(f"{'WARN' if rep['issues'] else 'OK  '} {key:<16} {dur:5.1f}s min text {rep['min_text_size']} {rep['issues']}")
    frames = []
    for key, _, dur in jobs:
        png = OUT / f"{key}.png"
        if (OUT / f"{key}.mp4").exists():
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{max(dur - 1.0, 0):.2f}", "-i", str(OUT / f"{key}.mp4"),
                            "-frames:v", "1", "-vf", "scale=640:-2", str(png)])
            frames.append(png)
    imgs = [Image.open(f) for f in frames if f.exists()]
    if imgs:
        fw, fh = imgs[0].size
        sheet = Image.new("RGB", (fw * 4, fh * ((len(imgs) + 3) // 4)))
        for k, im in enumerate(imgs):
            sheet.paste(im, ((k % 4) * fw, (k // 4) * fh))
        sheet.save(OUT / "sheet.png")
    print(f"\n{len(jobs) - bad}/{len(jobs)} scenes clean. Sheet: {OUT / 'sheet.png'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
