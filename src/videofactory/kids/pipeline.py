"""Kids video pipeline: lesson script -> narration -> scenes -> music -> final video -> thumbnail -> metadata -> QC."""
from __future__ import annotations

import json
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from .. import assemble as asm
from .. import subtitles
from ..config import ROOT, Settings
from ..media import duration, run_ffmpeg
from ..pipeline import Run
from ..qc import run_qc
from ..tts import Narrator, Segment
from .lessons import TOPICS
from .music import make_music
from .narrate import narrate_parts, shown
from .script import build_script

KIDS_SPEED = 0.85  # slower, clearer speech for toddlers


def kids_metadata(script: dict, lang: str, offsets: list[float], total: float) -> dict:
    t_en, t_hi = script["title_en"], script["title_hi"]
    sub = f" {script['subtitle']}" if script.get("subtitle") else ""
    items = []
    for sc in script["scenes"]:
        d = sc["data"]
        if sc["type"] in ("colour", "shape", "animal", "fruit", "vehicle", "letter"):
            items.append(d["letter"] if sc["type"] == "letter" else (d["hi"] if lang == "hi" else d["en"]))
    if lang == "hi":
        title = f"{t_hi}{sub} | बच्चों के लिए | Learn {t_en} in Hindi for Kids"
        desc = (f"आओ बच्चों, {t_hi} सीखें! इस वीडियो में: {', '.join(items[:8])}।\n"
                f"Fun learning video for toddlers and preschoolers (age 0-5) in Hindi.")
    else:
        title = f"Learn {t_en}{sub} for Kids | {', '.join(i.title() for i in items[:3])} & More | Toddler Learning"
        desc = (f"Let's learn {t_en.lower()}{sub} together! In this video: {', '.join(items[:8])}.\n"
                "A fun, gentle learning video for toddlers and preschoolers (age 0-5) with Bubbles the Bear.")
    chapters = []
    names = {"intro": "Hello!", "quiz": "Quiz time", "count_quiz": "Quiz time", "outro": "Bye bye!",
             "colour_mix": "Mixing colours", "shape_sides": "Counting sides", "compare": "Which has more?",
             "sort_where": "Where do they go?", "fruit_groups": "Sorting fruits"}
    last = -99.0
    for sc, off in zip(script["scenes"], offsets):
        if off - last < 10:
            continue
        d = sc["data"]
        label = names.get(sc["type"]) or (d.get("letter") or d.get("en", "")).title() or str(d.get("n", ""))
        chapters.append((0.0 if not chapters else off, label))
        last = off
    ch_txt = "\n".join(f"{int(t) // 60}:{int(t) % 60:02} {n}" for t, n in chapters) if len(chapters) >= 3 else ""
    description = "\n".join(x for x in [desc, "", "Chapters:" if ch_txt else "", ch_txt, "",
                                        "#kidslearning #toddlers #preschool", "",
                                        "Pictures: Twemoji (CC-BY 4.0)"] if x is not None)
    tags = ["kids learning", "toddler learning", "preschool", t_en.lower(), f"learn {t_en.lower()}", "for kids",
            "educational video for kids", "nursery", "kindergarten", "baby learning"]
    if lang == "hi":
        tags += ["hindi kids", "बच्चों के लिए", t_hi]
    return {"title": title[:100], "description": description[:4900], "tags": tags, "category": "Education",
            "language": "Hindi" if lang == "hi" else "English", "made_for_kids": True,
            "privacy_recommendation": "Upload as Private first, review, then publish. Mark as 'Made for Kids'."}


def write_upload_txt(meta: dict, folder: Path) -> None:
    (folder / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    (folder / "youtube_upload.txt").write_text(
        f"TITLE\n{meta['title']}\n\nDESCRIPTION\n{meta['description']}\n\nTAGS\n{', '.join(meta['tags'])}\n\n"
        f"CATEGORY: {meta['category']}   LANGUAGE: {meta['language']}\n"
        "AUDIENCE: Yes, it's MADE FOR KIDS (required by YouTube/COPPA for content aimed at children).\n"
        "Upload thumbnail.png as the custom thumbnail and subtitles.srt under Subtitles.\n", encoding="utf-8")


def make_kids_video(settings: Settings, topic: str | None = None, lang: str = "en", seed: int | None = None,
                    resume: Path | None = None) -> Path:
    if resume and (resume / "script.json").exists():  # continue exactly the saved video
        saved = json.loads((resume / "script.json").read_text())
        topic, lang, seed = saved["topic"], saved["lang"], saved.get("seed", seed)
    lang = "en"  # English only
    seed = seed if seed is not None else random.randrange(1_000_000)
    topic = topic or random.Random(seed).choice(list(TOPICS))
    folder = resume or Path(settings.output_dir) / f"{datetime.now():%Y%m%d-%H%M}_kids-{topic}-{lang}"
    run = Run(folder)
    run.log(f"KIDS video: topic {topic}, language {lang}, seed {seed}")

    sp = run.path("script.json")
    if sp.exists():
        script = json.loads(sp.read_text())
    else:
        script = build_script(topic, lang, seed)
        script["seed"] = seed
        sp.write_text(json.dumps(script, indent=2, ensure_ascii=False))
    scenes = script["scenes"]
    run.log(f"Script: {len(scenes)} scenes ({', '.join(s['type'] for s in scenes)})")

    np_ = run.path("narration.json")
    if np_.exists():
        narrs = json.loads(np_.read_text())
    else:
        narrator = Narrator(settings.kids_voice, KIDS_SPEED * settings.speech_speed)
        narrs = [narrate_parts(narrator, sc["parts"], run.path("audio", f"scene_{sc['index']:02}.wav")) for sc in scenes]
        np_.write_text(json.dumps(narrs, indent=2, ensure_ascii=False))
    run.log(f"Narration: {sum(n['duration'] for n in narrs) / 60:.1f} min")

    w, h, fps = settings.resolution
    jobs = []
    for sc, nr in zip(scenes, narrs):
        out = run.path("scenes", f"scene_{sc['index']:02}.mp4")
        job = {"type": sc["type"], "data": sc["data"], "lang": lang, "topic": topic, "index": sc["index"],
               "total": len(scenes), "duration": round(nr["duration"] * fps) / fps, "part_times": nr["part_times"],
               "shown_parts": [shown(p) for p in sc["parts"] if isinstance(p, str)], "wav": nr["wav"],
               "width": w, "height": h, "fps": fps, "out": str(out), "seed": seed + sc["index"]}
        jp = run.path("scenes", f"scene_{sc['index']:02}.job.json")
        jp.write_text(json.dumps(job, indent=2, ensure_ascii=False))
        jobs.append((sc["index"], jp, out))

    def render(item):
        i, jp, out = item
        if out.exists() and out.with_suffix(".layout.json").exists():
            return i, None
        r = subprocess.run([sys.executable, "-m", "videofactory.kids.render_kids", str(jp)], capture_output=True,
                           text=True, cwd=ROOT, env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/local/bin:/usr/bin:/bin",
                                                     "HOME": str(Path.home())})
        return i, (r.stderr[-2500:] if r.returncode else None)

    run.log(f"Rendering {len(jobs)} scenes at {w}x{h}@{fps}...")
    t_r = time.time()
    with ThreadPoolExecutor(settings.render_workers) as ex:
        for i, err in ex.map(render, jobs):
            if err:
                raise RuntimeError(f"Kids scene {i + 1} failed to render:\n{err}")
            run.log(f"  scene {i + 1} rendered")
    run.log(f"Rendering took {(time.time() - t_r) / 60:.1f} min")
    videos = [j[2] for j in jobs]
    wavs = [Path(n["wav"]) for n in narrs]

    offsets, t = [], 0.0
    for v in videos:
        offsets.append(t)
        t += duration(v, "video")
    total = t
    segs = [[Segment(**s) for s in n["segments"]] for n in narrs]
    srt = run.path("subtitles.srt")
    subtitles.write_srt(subtitles.build_cues(segs, offsets), srt)
    music = run.path("music.wav")
    info = make_music(total, music, seed)
    run.log(f"Music: original tune in {info['key']} at {info['bpm']} BPM")
    final = run.path("final.mp4")
    asm.assemble(videos, wavs, run.dir, final, srt=srt, music=music, music_volume=0.16,
                 burn_subtitles=settings.burn_subtitles)
    run.log(f"Final video: {final} ({duration(final) / 60:.1f} min)")

    from ..thumbnail import make_thumbnail
    k = next((s["index"] for s in scenes if s["type"] not in ("intro", "outro")), 1)
    thumb = run.path("thumbnail.png")
    hook = (script["title_hi"] if lang == "hi" else f"Learn {script['title_en']}!")
    make_thumbnail(hook, "for kids", videos[k], duration(videos[k]) - 1.0, thumb, "#FF7043", "#FFD54F", style="kids")
    meta = kids_metadata(script, lang, offsets, total)
    write_upload_txt(meta, run.dir)
    run_ffmpeg("-i", str(final), "-vf", f"fps={min(1, 12 / total):.5f},scale=480:-2,tile=4x3", "-frames:v", "1",
               "-q:v", "3", str(run.path("preview.jpg")))

    run.log("Running quality checks...")
    qc = run_qc(final, videos, wavs, [json.loads(jp.read_text())["duration"] for _, jp, _ in jobs],
                [" ".join(s.text for s in sg) for sg in segs], srt, thumb, lang)
    (run.dir / "qc_report.json").write_text(json.dumps({"passed": qc.passed, "checks": qc.checks}, indent=2))
    for c in qc.checks:
        run.log(f"  [{c['status'].upper():4}] {c['check']}" + (f" - {c['detail']}" if c["detail"] else ""))
    run.log(f"QC {'PASSED' if qc.passed else 'FAILED'}. Output folder: {run.dir}")
    return run.dir
