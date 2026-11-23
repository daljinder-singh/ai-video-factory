"""Render one scene from a JSON job file:  python -m videofactory.render.render_scene job.json

Job fields: visual (validated spec dict), heading, category, index, total, duration, cues, width, height,
fps, out (mp4 path). Writes the mp4 and <out>.layout.json (text sizes, bounds, overlaps)."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
from manim import (DOWN, LEFT, RIGHT, UP, WHITE, AnimationGroup, Circle, FadeIn, FadeOut, Line,
                   Rectangle, Scene, VGroup, tempconfig, Create, linear)

from . import templates as tp

FRAME_W, FRAME_H = 14.222, 8.0
MIN_TEXT_SIZE = 20  # manim font size after all scaling; below this is hard to read on a phone


def dim(m, factor: float):
    """Fade a group to `factor` of its ORIGINAL opacities (keeps hollow icons hollow, translucent fills translucent)."""
    from manim import Transform
    target = m.copy()
    for t, src in zip(target.get_family(), m.get_family()):
        if not hasattr(src, "_op0"):
            src._op0 = (src.get_fill_opacity(), src.get_stroke_opacity())
        f0, s0 = src._op0
        t.set_fill(opacity=f0 * factor, family=False)
        t.set_stroke(opacity=s0 * factor, family=False)
    return Transform(m, target)


def core(m):
    """The element itself, without connector lines/arrows or highlight frames (for overlap checks)."""
    from manim import Arrow, CurvedArrow, Line, SurroundingRectangle, VMobject
    skip = (Arrow, CurvedArrow, Line, SurroundingRectangle)
    if isinstance(m, VGroup):
        kept = [c for c in m.submobjects if not isinstance(c, skip)]
        if kept and len(kept) < len(m.submobjects):
            return VGroup(*kept)
    return m


class SpecScene(Scene):
    job: dict = {}

    def setup_frame(self):
        j = self.job
        a = tp.ACCENTS.get(j["category"], "#64B5F6")
        bg = Rectangle(width=FRAME_W + 0.2, height=FRAME_H + 0.2, stroke_width=0, fill_opacity=1)
        bg.set_fill(color=[tp.BG, "#121A33"])
        bg.set_sheen_direction(UP + RIGHT)
        orbs = VGroup(*[Circle(radius=r, stroke_width=0, fill_color=c, fill_opacity=0.06)
                        .move_to(p) for r, c, p in ((3.2, a, [-6.5, -3.5, 0]), (2.4, a, [6.8, 3.6, 0]))])
        self.add(bg, orbs)
        self.persist = [bg, orbs]
        orbs.add_updater(lambda m, dt: m.rotate(0.03 * dt, about_point=[0, 0, 0]))  # slow ambient drift
        chip = tp.T(j["category"].upper(), 20, color=a, bold=True)
        chip.to_corner(UP + RIGHT, buff=0.45)
        track = Line([-FRAME_W / 2, -FRAME_H / 2 + 0.06, 0], [FRAME_W / 2, -FRAME_H / 2 + 0.06, 0],
                     stroke_width=6, color="#1E2747")
        frac_a, frac_b = j["index"] / j["total"], (j["index"] + 1) / j["total"]
        x0 = -FRAME_W / 2
        prog = Line([x0, track.get_y(), 0], [x0 + FRAME_W * max(frac_a, 0.001), track.get_y(), 0],
                    stroke_width=6, color=a)
        self.add(track, prog, chip)
        self.persist += [track, prog, chip]
        self.progress = (prog, x0 + FRAME_W * frac_b)
        header = VGroup()
        if j["visual"]["template"] not in ("title_card",) and j.get("heading"):
            title = tp.T(j["heading"], 46, bold=True, max_w=11.0)
            title.to_corner(UP + LEFT, buff=0.5)
            bar = Line(title.get_corner(DOWN + LEFT) + DOWN * 0.18,
                       title.get_corner(DOWN + LEFT) + DOWN * 0.18 + RIGHT * min(title.width, 3.0),
                       color=a, stroke_width=6)
            header = VGroup(title, bar)
        return header

    def construct(self):
        j = self.job
        a = tp.ACCENTS.get(j["category"], "#64B5F6")
        b = tp.SECOND.get(j["category"], "#F06292")
        duration = float(j["duration"])
        header = self.setup_frame()
        presenter = None
        if j.get("presenter"):
            from .presenter import Presenter, voice_envelope
            env = voice_envelope(j["wav"], j["fps"]) if j.get("wav") and Path(j["wav"]).exists() else []
            presenter = Presenter(j["category"], a, env, j["fps"], list(j["cues"]),
                                  wave_hello=j["visual"]["template"] == "title_card")
            presenter.place(3.7, np.array([7.0, -4.25, 0]))
            presenter.add_updater(lambda m: m.tick(self.time))
            self.add(presenter)
            self.persist.append(presenter)

        tp.CATEGORY = j["category"]
        built = tp.BUILDERS[j["visual"]["template"]](j["visual"], a, b)
        content = built.content
        # fit the content into the area under the heading
        top = tp.AREA_TOP if len(header) else 3.2
        avail_w, avail_h = (10.3 if presenter else tp.AREA_W), top - tp.AREA_BOTTOM
        cx = -1.55 if presenter else 0.0
        scale = min(1.0, avail_w / max(content.width, 1e-3), avail_h / max(content.height, 1e-3))
        if scale < 1.0:
            content.scale(scale)
        content.move_to([cx, (top + tp.AREA_BOTTOM) / 2, 0])
        swap = getattr(built, "swap", None)
        if swap:  # live counter must sit where the static number sits
            swap[0].clear_updaters()
            target = swap[1].get_center()
            swap[0].add_updater(lambda m: m.move_to(target))
            swap[0].update()
        self.layout_report(header, built)

        # timeline: header + intro, then units at cue times, then idle motion, then fade out
        prog, prog_end = self.progress
        if len(header):
            self.play(FadeIn(header[0], shift=RIGHT * 0.3), Create(header[1]),
                      prog.animate.put_start_and_end_on(prog.get_start(), [prog_end, prog.get_y(), 0]),
                      run_time=0.8)
        else:
            self.play(prog.animate.put_start_and_end_on(prog.get_start(), [prog_end, prog.get_y(), 0]),
                      run_time=0.6)
        if built.intro:  # fit the intro into the time before the first cue
            first = j["cues"][0] if j["cues"] else duration * 0.3
            each = float(np.clip((first - self.time - 0.1) / len(built.intro), 0.5, 1.2))
            for make in built.intro:
                anim = make()
                self.play(anim, run_time=max(each, getattr(anim, "run_time", 0) if getattr(anim, "run_time", 1) > 1.5 else each))
        if swap:
            self.remove(swap[0])
            self.add(swap[1])
        cues = list(j["cues"])
        transient = getattr(built, "transient", [])
        shown = []
        for k, make in enumerate(built.units):
            cue = cues[k] if k < len(cues) else self.time
            if cue > self.time:
                self.wait(cue - self.time)
            nxt = cues[k + 1] if k + 1 < len(cues) else duration - 0.8
            rt = float(np.clip(nxt - self.time - 0.15, 0.4, 1.2))
            anims = [make()]
            if built.focus and shown:  # keep attention on the newest element
                anims.append(AnimationGroup(*[dim(m, 0.4) for m in shown[-1:]]))
            anims += [FadeOut(h) for h in transient if h in self.mobjects]  # previous highlight only
            self.play(*anims, run_time=rt)
            shown.append(built.unit_mobs[k])
        remaining = duration - 0.6 - self.time
        if built.focus and shown and remaining > 1.5:
            self.play(*[dim(m, 1.0) for m in shown], run_time=0.5)
            remaining -= 0.5
        if remaining > 0.05:
            if built.idle:
                built.idle(self, remaining)
            else:
                self.wait(remaining)
        left = duration - self.time
        self.play(*[FadeOut(m) for m in self.mobjects if m not in self.base_mobs()], run_time=max(0.2, min(0.6, left)))

    def base_mobs(self):
        return self.persist  # background, orbs, progress bar, category chip and presenter stay on screen

    def layout_report(self, header, built):
        issues, sizes = [], []
        for t in tp.TEXT_LOG:
            if t not in header.submobjects and not any(t in getattr(m, "get_family", lambda: [])()
                                                       for m in [built.content, header]):
                continue
            size = tp.effective_size(t)
            sizes.append(round(size, 1))
            if size < MIN_TEXT_SIZE:
                issues.append(f"text too small ({size:.0f}): {t.text[:40]!r}")
        for m in [built.content, header]:
            if len(m) == 0:
                continue
            if m.get_left()[0] < -FRAME_W / 2 + 0.1 or m.get_right()[0] > FRAME_W / 2 - 0.1 \
                    or m.get_top()[1] > FRAME_H / 2 - 0.05 or m.get_bottom()[1] < -FRAME_H / 2 + 0.1:
                issues.append("content extends outside the frame")
        if len(header) and built.content.get_top()[1] > header.get_bottom()[1] + 0.05:
            issues.append("content overlaps the heading")
        boxes = []
        for m in built.unit_mobs:
            m = core(m)
            boxes.append((m.get_left()[0], m.get_right()[0], m.get_bottom()[1], m.get_top()[1]))
        overlaps = 0
        for i in range(len(boxes)):
            for k in range(i + 1, len(boxes)):
                l1, r1, b1, t1 = boxes[i]
                l2, r2, b2, t2 = boxes[k]
                ix, iy = min(r1, r2) - max(l1, l2), min(t1, t2) - max(b1, b2)
                if ix > 0.15 and iy > 0.15:
                    small = min((r1 - l1) * (t1 - b1), (r2 - l2) * (t2 - b2))
                    if ix * iy > 0.25 * small:
                        overlaps += 1
        if overlaps and not built.allow_overlap:
            issues.append(f"{overlaps} overlapping element pair(s)")
        self.report = {"min_text_size": min(sizes) if sizes else None, "issues": issues}


def render(job: dict) -> dict:
    out = Path(job["out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    tp.TEXT_LOG.clear()
    with tempfile.TemporaryDirectory() as tmp:
        cfg = {"pixel_width": job["width"], "pixel_height": job["height"], "frame_rate": job["fps"],
               "media_dir": tmp, "output_file": "scene", "disable_caching": True, "verbosity": "ERROR",
               "progress_bar": "none", "background_color": tp.BG, "write_to_movie": True}
        with tempconfig(cfg):
            SpecScene.job = job
            scene = SpecScene()
            scene.render()
            movie = Path(scene.renderer.file_writer.movie_file_path)
            shutil.move(str(movie), out)
            report = {**scene.report, "rendered_seconds": round(scene.time, 3)}
    out.with_suffix(".layout.json").write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    print(json.dumps(render(json.loads(Path(sys.argv[1]).read_text()))))
