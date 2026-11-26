"""Recipe video pipeline: Wikibooks recipe -> scenes (verbatim English or checked translation) -> narration ->
kitchen scenes with Chef Tara -> music -> final video -> thumbnail -> YouTube text -> QC."""
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
from ..kids.music import make_music
from ..kids.narrate import narrate_parts, shown
from ..llm import Ollama
from ..media import duration, run_ffmpeg
from ..pipeline import Run, slug
from ..qc import run_qc
from ..thumbnail import make_thumbnail
from ..tts import Narrator, Segment
from .script import build_script
from .source import Recipe, pick_recipe

LANG_NAMES = {"en": "English", "hi": "Hindi", "hinglish": "Hindi (Hinglish)"}


def recipe_metadata(script: dict, offsets: list[float]) -> dict:
    name, lang = script["name"], script["lang"]
    title = (f"How to Make {name} | Easy Step-by-Step Recipe" if lang == "en"
             else f"{name} बनाने की आसान रेसिपी | {name} Recipe in Hindi")
    chapters, last = [], -99.0
    for sc, off in zip(script["scenes"], offsets):
        if off - last < 10:
            continue
        label = {"recipe_intro": "Introduction", "ingredients": "Ingredients", "recipe_final": "Ready to serve"}.get(
            sc["type"], f"Step {sc['data'].get('n', '')}")
        chapters.append((0.0 if not chapters else off, label))
        last = off
    ch = "\n".join(f"{int(t) // 60}:{int(t) % 60:02} {n}" for t, n in chapters) if len(chapters) >= 3 else ""
    desc = "\n".join([
        f"Learn how to make {name} at home, step by step." if lang == "en" else f"घर पर {name} बनाना सीखें, स्टेप बाय स्टेप।",
        "", "Ingredients:", *[f"- {i}" for i in script["ingredients"]], "",
        *(["Chapters:", ch, ""] if ch else []),
        f"#recipe #{slug(name).replace('-', '')} #indianfood", "",
        "Sources: Wikibooks Cookbook (CC BY-SA 4.0) · Pictures: Twemoji (CC-BY 4.0)"])
    tags = [name, f"{name} recipe", f"how to make {name}", "indian recipe", "easy recipe", "cooking", "home cooking",
            "step by step recipe"] + (["hindi recipe", "रेसिपी"] if lang != "en" else [])
    return {"title": title[:100], "description": desc[:4900], "tags": tags, "category": "Howto & Style",
            "language": LANG_NAMES[lang], "made_for_kids": False,
            "privacy_recommendation": "Upload as Private first, review, then publish."}


def make_recipe_video(settings: Settings, dish: str | None = None, seed: int | None = None,
                      resume: Path | None = None) -> Path:
    seed = seed if seed is not None else random.randrange(1_000_000)
    lang = "en"  # English only
    if resume and (resume / "recipe.json").exists():
        recipe = Recipe.from_dict(json.loads((resume / "recipe.json").read_text()))
        saved = json.loads((resume / "script.json").read_text()) if (resume / "script.json").exists() else {}
        lang, seed = saved.get("lang", lang), saved.get("seed", seed)
        run = Run(resume)
    else:
        recipe = pick_recipe(random.Random(seed), dish)
        run = Run(Path(settings.output_dir) / f"{datetime.now():%Y%m%d-%H%M}_recipe-{slug(recipe.title)}-{lang}")
        run.path("recipe.json").write_text(json.dumps(recipe.to_dict(), indent=2, ensure_ascii=False))
    run.log(f"RECIPE video: {recipe.title} ({len(recipe.ingredients)} ingredients, {len(recipe.steps)} steps), "
            f"language {lang}. Source: {recipe.url}")

    sp = run.path("script.json")
    if sp.exists():
        script = json.loads(sp.read_text())
    else:
        llm = None
        if lang != "en":
            llm = Ollama(settings.llm_model, settings.ollama_url)
            llm.check()
            run.log(f"Translating with {settings.llm_model} (numbers are checked line by line)...")
        script = build_script(recipe, lang, llm, log=run.log)
        script["seed"] = seed
        sp.write_text(json.dumps(script, indent=2, ensure_ascii=False))
    scenes = script["scenes"]

    np_ = run.path("narration.json")
    if np_.exists():
        narrs = json.loads(np_.read_text())
    else:
        narrator = Narrator(settings.recipe_voice, 0.95 * settings.speech_speed)
        narrs = [narrate_parts(narrator, sc["parts"], run.path("audio", f"scene_{sc['index']:02}.wav"),
                               gap=0.45, tail=1.6 if sc["type"] == "step" else 1.0) for sc in scenes]
        np_.write_text(json.dumps(narrs, indent=2, ensure_ascii=False))
    run.log(f"Narration: {sum(n['duration'] for n in narrs) / 60:.1f} min")

    w, h, fps = settings.resolution
    jobs = []
    for sc, nr in zip(scenes, narrs):
        out = run.path("scenes", f"scene_{sc['index']:02}.mp4")
        job = {"type": sc["type"], "data": sc["data"], "lang": "en" if lang == "en" else "hi", "topic": "kitchen",
               "mascot": "cooking", "index": sc["index"], "total": len(scenes),
               "duration": round(nr["duration"] * fps) / fps, "part_times": nr["part_times"],
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
                raise RuntimeError(f"Recipe scene {i + 1} failed to render:\n{err}")
    run.log(f"Rendering took {(time.time() - t_r) / 60:.1f} min")
    videos = [j[2] for j in jobs]
    wavs = [Path(n["wav"]) for n in narrs]

    offsets, t = [], 0.0
    for v in videos:
        offsets.append(t)
        t += duration(v, "video")
    segs = [[Segment(**s) for s in n["segments"]] for n in narrs]
    srt = run.path("subtitles.srt")
    subtitles.write_srt(subtitles.build_cues(segs, offsets), srt)
    music = run.path("music.wav")
    info = make_music(t, music, seed)
    run.log(f"Music: original tune in {info['key']} at {info['bpm']} BPM")
    final = run.path("final.mp4")
    asm.assemble(videos, wavs, run.dir, final, srt=srt, music=music, music_volume=0.10,
                 burn_subtitles=settings.burn_subtitles)
    run.log(f"Final video: {final} ({duration(final) / 60:.1f} min)")

    k = next((s["index"] for s in scenes if s["type"] == "recipe_final"), len(scenes) - 1)
    thumb = run.path("thumbnail.png")
    hook = f"How to make {script['name']}" if lang == "en" else f"{script['name']} रेसिपी"
    make_thumbnail(hook, "recipe", videos[k], duration(videos[k]) - 0.8, thumb, "#E53935", "#FFB74D", style="kids")
    meta = recipe_metadata(script, offsets)
    (run.dir / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    (run.dir / "youtube_upload.txt").write_text(
        f"TITLE\n{meta['title']}\n\nDESCRIPTION\n{meta['description']}\n\nTAGS\n{', '.join(meta['tags'])}\n\n"
        f"CATEGORY: {meta['category']}   LANGUAGE: {meta['language']}   MADE FOR KIDS: No\n"
        "Upload thumbnail.png as the custom thumbnail and subtitles.srt under Subtitles.\n", encoding="utf-8")
    run_ffmpeg("-i", str(final), "-vf", f"fps={min(1, 12 / t):.5f},scale=480:-2,tile=4x3", "-frames:v", "1",
               "-q:v", "3", str(run.path("preview.jpg")))

    run.log("Running quality checks...")
    qc = run_qc(final, videos, wavs, [json.loads(jp.read_text())["duration"] for _, jp, _ in jobs],
                [" ".join(s.text for s in sg) for sg in segs], srt, thumb, "en" if lang == "en" else "hi")
    (run.dir / "qc_report.json").write_text(json.dumps({"passed": qc.passed, "checks": qc.checks}, indent=2))
    for c in qc.checks:
        run.log(f"  [{c['status'].upper():4}] {c['check']}" + (f" - {c['detail']}" if c["detail"] else ""))
    run.log(f"QC {'PASSED' if qc.passed else 'FAILED'}. Output folder: {run.dir}")
    return run.dir
