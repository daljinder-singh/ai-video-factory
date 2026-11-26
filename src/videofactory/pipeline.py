"""End-to-end pipeline: topic -> research -> script -> narration -> animation -> assembly -> thumbnail -> QC.

Each stage writes its result into the run folder; re-running with --resume <folder> skips finished stages.
"""
from __future__ import annotations

import json
import random
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from . import assemble as asm
from . import metadata as meta
from . import research, subtitles, thumbnail
from .config import ROOT, Settings
from .llm import Ollama
from .media import duration, run_ffmpeg
from .qc import run_qc
from .render.templates import ACCENTS, SECOND
from .scriptwriter import ScriptWriter
from .specs import VideoScript, reveal_units
from .timing import cue_times
from .topics import Topic, category_of, pick_topic
from .tts import Narration, Narrator

LANG_NAMES = {"en": "English", "hi": "Hindi", "hinglish": "Hindi (Hinglish)"}


class Run:
    def __init__(self, folder: Path):
        self.dir = folder
        self.dir.mkdir(parents=True, exist_ok=True)
        self.logf = open(folder / "log.txt", "a", encoding="utf-8")
        self.t0 = time.time()

    def log(self, msg: str) -> None:
        line = f"[{time.time() - self.t0:6.0f}s] {msg}"
        print(line, flush=True)
        self.logf.write(line + "\n")
        self.logf.flush()

    def path(self, *parts: str) -> Path:
        p = self.dir.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def make_video(settings: Settings, topic: str | None = None, category: str | None = None,
               resume: Path | None = None, seed: int | None = None, series: str | None = None) -> Path:
    from . import series as series_mod

    rng = random.Random(seed)
    trend_queue: list[dict] = []
    # ---------------- topic
    if resume:
        run = Run(resume)
        t = json.loads((resume / "topic.json").read_text())
    else:
        if series == "trending":
            from .trending import candidates

            trend_queue = candidates(Path(settings.output_dir), log=print)[:8]
            if not trend_queue:
                raise RuntimeError("No educational trending topic found today; try --series random")
            c = trend_queue.pop(0)
            t = {"category": c["category"], "title": c["title"], "question": c["title"], "series": "trending",
                 "trending_reason": c["description"]}
        elif series:
            s, question, article = series_mod.pick(series, rng)
            t = {"category": s.category, "title": article, "question": question, "series": s.key}
        elif topic:
            t = {"category": category or category_of(topic), "title": topic}
        else:
            c = pick_topic(category, rng)
            t = {"category": c.category, "title": c.title}
        run = Run(Path(settings.output_dir) / (f"{datetime.now():%Y%m%d-%H%M}_{slug(t.get('question') or t['title'])}"
                                               + ("_short" if settings.short else "")))
    chosen = Topic(t["category"], t["title"])
    brief = ""
    if t.get("series") == "trending":
        brief = (f"'{t['question']}' is trending today. Explain what it is, the key background and why it matters, "
                 "using only facts in the sources. Do not speculate about current news beyond the sources. Pick a "
                 "catchy but accurate title.")
    elif t.get("series"):
        brief = series_mod.SERIES[t["series"]].brief.format(q=t["question"])
    run.log(f"Topic: {t.get('question') or chosen.title} ({t.get('series') or chosen.category}), "
            f"language {settings.language}, quality {settings.quality}")

    # ---------------- research (if an article is too short, a series picks another topic)
    rp = run.path("research.json")
    if rp.exists():
        source = research.Source(**json.loads(rp.read_text()))
    else:
        run.log("Researching on Wikipedia...")
        for attempt in range(5):
            try:
                source = research.fetch(chosen.title)
                break
            except LookupError as e:
                if not t.get("series") or attempt == 4:
                    raise
                run.log(f"  {e}; picking another topic")
                if t["series"] == "trending":
                    if not trend_queue:
                        raise
                    c = trend_queue.pop(0)
                    t.update(title=c["title"], question=c["title"], category=c["category"],
                             trending_reason=c["description"])
                    chosen = Topic(c["category"], c["title"])
                    brief = brief.replace(brief.split("'")[1], c["title"], 1) if "'" in brief else brief
                    continue
                s, question, article = series_mod.pick(t["series"], rng)
                t.update(title=article, question=question)
                chosen = Topic(t["category"], article)
                brief = s.brief.format(q=question)
        # extra reliable sources (Wikidata facts, OpenStax textbook section, NASA) appended to the research text
        from . import sources as extra_sources

        sm = series_mod.SERIES.get(t.get("series") or "")
        extra, credits = extra_sources.gather(chosen.title, t.get("question") or chosen.title,
                                              sm.books if sm else (), sm.nasa if sm else False, log=run.log)
        if extra:
            source.text = source.text[:7000] + "\n\n" + extra[:5000]
            source.credits = credits
            run.log("  extra sources: " + ", ".join(c["name"] for c in credits))
        rp.write_text(json.dumps(source.to_dict(), indent=2, ensure_ascii=False))
    run.path("topic.json").write_text(json.dumps(t, ensure_ascii=False))
    run.log(f"Source: {source.url} ({len(source.text)} chars)")

    # ---------------- script + scene specs
    sp = run.path("script.json")
    if sp.exists():
        script = VideoScript.model_validate_json(sp.read_text())
    else:
        llm = Ollama(settings.llm_model, settings.ollama_url)
        llm.check()
        run.log(f"Writing script with {settings.llm_model} (this is the slow part on CPU)...")
        script = ScriptWriter(llm, settings.language, settings.min_scenes, settings.max_scenes,
                              log=run.log, short=settings.short).write(source, t.get("question") or chosen.title,
                                                                       chosen.category, brief)
        sp.write_text(script.model_dump_json(indent=2))
        run.log(f"Script done in {llm.total_seconds / 60:.1f} min of LLM time")
    run.log(f"Title: {script.title} | {len(script.scenes)} scenes")
    # ---------------- scene plan (staging rules: camera, transition, sound, music mood, presenter)
    from .planner import plan_scenes, quality_score

    plans = plan_scenes([sc.visual.template for sc in script.scenes], [sc.purpose for sc in script.scenes],
                        short=script.short or settings.short, presenter_enabled=settings.presenter)
    for sc, pl in zip(script.scenes, plans):
        sc.plan = pl
    if not script.quality:
        script.quality = quality_score(script.scenes, script.short)
    sp.write_text(script.model_dump_json(indent=2))
    run.log("Plan: " + " | ".join(f"{sc.purpose}:{sc.visual.template}/{sc.plan.camera}/{sc.plan.transition}"
                                  + ("" if sc.plan.presenter else "/no-host") for sc in script.scenes))
    run.log(f"Quality: {script.quality}")

    # ---------------- narration
    np_ = run.path("narration.json")
    if np_.exists():
        narrs = [Narration.from_dict(d) for d in json.loads(np_.read_text())]
    else:
        run.log(f"Narrating with Kokoro voice {settings.voice} (speed {settings.speech_speed})...")
        narrator = Narrator(settings.voice, settings.speech_speed)
        narrs = [narrator.narrate(sc.narration, run.path("audio", f"scene_{sc.index:02}.wav")) for sc in script.scenes]
        np_.write_text(json.dumps([n.to_dict() for n in narrs], indent=2, ensure_ascii=False))
    run.log(f"Narration: {sum(n.duration for n in narrs) / 60:.1f} min total")

    # ---------------- animation (parallel, one subprocess per scene)
    w, h, fps = settings.resolution
    jobs = []
    for sc, nr in zip(script.scenes, narrs):
        dur = round(nr.duration * fps) / fps
        cues = cue_times(reveal_units(sc.visual), nr.segments, dur)
        out = run.path("scenes", f"scene_{sc.index:02}.mp4")
        heading = getattr(sc.visual, "heading", None) or sc.heading  # the visual's own heading fits it best
        job = {"visual": sc.visual.model_dump(), "heading": heading, "category": script.category,
               "index": sc.index, "total": len(script.scenes), "duration": dur, "cues": cues,
               "width": w, "height": h, "fps": fps, "out": str(out),
               "presenter": settings.presenter and sc.plan.presenter, "wav": nr.wav,
               "plan": sc.plan.model_dump(), "purpose": sc.purpose,
               "label": (series_mod.SERIES[t["series"]].name if t.get("series") in series_mod.SERIES
                         else ("Trending" if t.get("series") == "trending" else script.category))}
        jp = run.path("scenes", f"scene_{sc.index:02}.job.json")
        jp.write_text(json.dumps(job, indent=2, ensure_ascii=False))
        jobs.append((sc.index, jp, out))

    def render(item):
        i, jp, out = item
        if out.exists() and out.with_suffix(".layout.json").exists():
            return i, None
        r = subprocess.run([sys.executable, "-m", "videofactory.render.render_scene", str(jp)],
                           capture_output=True, text=True, cwd=ROOT,
                           env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/local/bin:/usr/bin:/bin",
                                "HOME": str(Path.home())})
        return i, (r.stderr[-2000:] if r.returncode else None)

    run.log(f"Rendering {len(jobs)} scenes at {w}x{h}@{fps} with {settings.render_workers} workers...")
    t_r = time.time()
    with ThreadPoolExecutor(settings.render_workers) as ex:
        for i, err in ex.map(render, jobs):
            if err:
                raise RuntimeError(f"Scene {i + 1} failed to render:\n{err}")
            run.log(f"  scene {i + 1} rendered")
    run.log(f"Rendering took {(time.time() - t_r) / 60:.1f} min")
    scene_videos = [j[2] for j in jobs]
    scene_wavs = [Path(n.wav) for n in narrs]

    # ---------------- subtitles + assembly
    offsets, clock = [], 0.0  # (not "t": that name holds the topic)
    for v in scene_videos:
        offsets.append(clock)
        clock += duration(v, "video")
    srt = run.path("subtitles.srt")
    subtitles.write_srt(subtitles.build_cues([n.segments for n in narrs], offsets), srt)

    # sound effects, placed on real events (scene changes, element reveals, big reveals)
    sfx_path = None
    if settings.sfx:
        from .sfx import build_track

        events = []
        for (_, jp, _), off, sc in zip(jobs, offsets, script.scenes):
            cues = json.loads(jp.read_text())["cues"]
            fx = sc.plan.sound_effects
            if "whoosh" in fx:
                events.append((off + 0.02, "whoosh"))
            if "impact" in fx:
                events.append((off + (cues[0] if cues else 0.4), "impact"))
            if "shimmer" in fx:
                events.append((off + (cues[-1] if cues else 0.8), "shimmer"))
            if "pop" in fx:
                events += [(off + c, "pop") for c in cues]
        sfx_path = run.path("assembly", "sfx.wav")
        run.log(f"Sound effects: {build_track(events, clock, sfx_path)} events")

    # music: a user file, or an original score whose mood and loudness follow the story
    music_path = Path(settings.music_path) if settings.music_path else None
    if music_path is None and settings.auto_music:
        from .kids.music import make_music

        gains = {"hook": 1.0, "reveal": 0.95, "payoff": 0.95, "ending": 0.9, "setup": 0.65, "explain": 0.6}
        env = [(off, off + duration(v, "video"), gains.get(sc.purpose, 0.7))
               for off, v, sc in zip(offsets, scene_videos, script.scenes)]
        music_path = run.path("assembly", "music.wav")
        info = make_music(clock, music_path, abs(hash(script.title)) % 100000, script.scenes[0].plan.music_mood, env)
        run.log(f"Music: original {info['mood']} score in {info['key']} at {info['bpm']} BPM")

    captions = None
    if settings.short or settings.burn_subtitles:
        from .captions import write_ass

        captions = run.path("captions.ass")
        n_cap = write_ass([n.segments for n in narrs], offsets, [sc.highlight for sc in script.scenes], captions, w, h)
        run.log(f"Captions: {n_cap} styled caption lines (burned in)")
    final = run.path("final.mp4")
    run.log("Assembling final video...")
    asm.assemble(scene_videos, scene_wavs, run.dir, final, srt=srt, music=music_path,
                 music_volume=settings.music_volume, burn_subtitles=False, sfx=sfx_path, captions_ass=captions)
    total = duration(final)
    run.log(f"Final video: {final} ({total / 60:.1f} min)")

    # ---------------- thumbnail + metadata
    templates = [sc.visual.template for sc in script.scenes]
    k = thumbnail.pick_frame_scene(templates)
    thumb = run.path("thumbnail.png")
    thumbnail.make_thumbnail(script.hook, script.category, scene_videos[k], duration(scene_videos[k]) - 1.0, thumb,
                             ACCENTS.get(script.category, "#64B5F6"), SECOND.get(script.category, "#F06292"))
    m = meta.build(script, offsets, total, LANG_NAMES[settings.language])
    if source.credits:
        extra = " · ".join(f"{c['name']} ({c['license']})" for c in source.credits)
        m["description"] = (m["description"] + " · " + extra)[:4900]
    if t.get("series") == "money":
        m["description"] = ("This video is for general education only and is not financial advice.\n\n"
                            + m["description"])[:4900]
    m["title_options"] = [x for x in script.title_options if x != m["title"]]
    if script.short:  # YouTube recognises vertical videos under 3 min as Shorts; the tag helps discovery
        if len(m["title"]) <= 92:
            m["title"] = m["title"] + " #Shorts"
        m["description"] = ("#Shorts\n" + m["description"])[:4900]
        cover = run.path("cover_vertical.png")
        thumbnail.make_vertical_cover(script.hook, scene_videos[k], duration(scene_videos[k]) - 1.0, cover,
                                      ACCENTS.get(script.category, "#64B5F6"))
    meta.write(m, run.dir)
    run.log("Thumbnail and YouTube metadata written")

    # ---------------- preview contact sheet
    preview = run.path("preview.jpg")
    run_ffmpeg("-i", str(final), "-vf", f"fps={min(1, 12 / total):.5f},scale=480:-2,tile=4x3", "-frames:v", "1",
               "-q:v", "3", str(preview))

    # ---------------- QC
    run.log("Running quality checks (includes Whisper transcription)...")
    qc = run_qc(final, scene_videos, scene_wavs, [json.loads(jp.read_text())["duration"] for _, jp, _ in jobs],
                [sc.narration for sc in script.scenes], srt, thumb, settings.language, short=script.short)
    (run.dir / "qc_report.json").write_text(json.dumps({"passed": qc.passed, "checks": qc.checks}, indent=2))
    for c in qc.checks:
        run.log(f"  [{c['status'].upper():4}] {c['check']}" + (f" - {c['detail']}" if c["detail"] else ""))
    run.log(f"QC {'PASSED' if qc.passed else 'FAILED'}. Output folder: {run.dir}")
    return run.dir
