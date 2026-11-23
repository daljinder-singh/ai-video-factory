"""Manim visual templates. Each builder receives a validated spec and returns positioned mobjects plus
animation factories. Builders never receive free-form code: only the fields defined in specs.py."""
from __future__ import annotations

import math
import re
import textwrap
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from manim import (BOLD, DOWN, LEFT, ORIGIN, RIGHT, UL, UP, WHITE, Animation, AnimationGroup, AnnularSector,
                   Arc, Arrow, Axes, Circle, Code, Create, CurvedArrow, DashedLine, Dot, DrawBorderThenFill,
                   FadeIn, FadeOut, Flash, GrowArrow, GrowFromCenter, GrowFromEdge, Indicate, Intersection, Line,
                   LaggedStart, ManimColor, Mobject, MoveAlongPath, Polygon, Rectangle, Rotate, RoundedRectangle,
                   Scene, SurroundingRectangle, SVGMobject, Text, Triangle, ValueTracker, VGroup, VMobject, Write,
                   always_redraw, interpolate_color, linear, smooth, there_and_back)

from ..icons import icon_for, icon_path, icons_for

FONT = "Noto Sans"
MONO = "DejaVu Sans Mono"
BG = "#0B1020"
PANEL = "#151D36"
MUTED = "#9AA6C3"
ACCENTS = {
    "mathematics": "#4FC3F7", "science": "#66BB6A", "programming": "#FFB74D", "finance": "#FFD54F",
    "ai": "#B388FF", "business": "#4DB6AC", "history": "#E0A96D", "psychology": "#F48FB1",
    "technology": "#64B5F6",
}
SECOND = {
    "mathematics": "#F06292", "science": "#29B6F6", "programming": "#4DD0E1", "finance": "#81C784",
    "ai": "#4DD0E1", "business": "#FFB74D", "history": "#90CAF9", "psychology": "#80CBC4",
    "technology": "#FFB74D",
}
# content area below the heading (manim units; frame is 14.22 x 8)
AREA_W, AREA_TOP, AREA_BOTTOM = 13.0, 2.45, -3.35
TEXT_LOG: list[Text] = []


def wrap(s: str, width: int) -> str:
    return "\n".join(textwrap.wrap(s, width=width, break_long_words=False)) or s


def T(s: str, size: float, color=WHITE, bold: bool = False, width: int | None = None,
      max_w: float | None = None, font: str = FONT) -> Text:
    s = wrap(s, width) if width else s
    m = Text(s, font=font, font_size=size, color=color, weight=BOLD if bold else "NORMAL", line_spacing=0.9)
    m.base_size, m.base_h = size, m.height  # effective size = base_size * current height / base_h
    if max_w and m.width > max_w:
        m.scale_to_fit_width(max_w)
    TEXT_LOG.append(m)
    return m


def effective_size(m: Text) -> float:
    base_h = getattr(m, "base_h", m.height) or 1
    return getattr(m, "base_size", 0) * m.height / base_h


@dataclass
class Built:
    content: VGroup
    intro: list[Callable[[], Animation]] = field(default_factory=list)
    units: list[Callable[[], Animation]] = field(default_factory=list)
    unit_mobs: list[Mobject] = field(default_factory=list)
    idle: Callable[[Scene, float], None] | None = None  # fills remaining time with meaningful motion
    focus: bool = True  # dim earlier units when a new one appears
    allow_overlap: bool = False  # elements overlap by design (curves, pie slices, Venn circles)


def pause(scene: Scene, t: float) -> None:
    if t > 1 / 60:
        scene.wait(t)


def card(w: float, h: float, accent: str, fill=PANEL, stroke_opacity=0.9) -> RoundedRectangle:
    return RoundedRectangle(corner_radius=0.18, width=w, height=h, fill_color=fill, fill_opacity=1,
                            stroke_color=accent, stroke_width=3, stroke_opacity=stroke_opacity)


def boxed(label: str, w: float, h: float, accent: str, size: float = 30, chars: int = 14) -> VGroup:
    box = card(w, h, accent)
    txt = T(label, size, width=chars, max_w=w - 0.3)
    if txt.height > h - 0.25:
        txt.scale_to_fit_height(h - 0.25)
    return VGroup(box, txt.move_to(box))


# ---------------------------------------------------------------- icons
CATEGORY = ""  # set by the scene runner


def icon(name: str, color, h: float = 0.9) -> VMobject:
    m = SVGMobject(str(icon_path(name)))
    m.set_fill(opacity=0).set_stroke(color=color, width=max(2.5, 4.2 * h), opacity=1)
    m.scale_to_fit_height(h)
    return m


def icon_disc(name: str, color, r: float = 0.55) -> VGroup:
    disc = Circle(radius=r, fill_color=PANEL, fill_opacity=1, stroke_color=color, stroke_width=3)
    glow = Circle(radius=r * 1.25, stroke_width=0, fill_color=color, fill_opacity=0.10)
    ic = icon(name, color, h=r * 1.05).move_to(disc)
    return VGroup(glow, disc, ic)


def pop(g: VGroup) -> Animation:
    """Disc grows, then its icon is drawn stroke by stroke."""
    return AnimationGroup(GrowFromCenter(VGroup(g[0], g[1])), Create(g[2]), lag_ratio=0.35)


def labelled_icon(label: str, name: str, color, r: float = 0.5, size: float = 26, chars: int = 14,
                  max_w: float = 2.8) -> VGroup:
    d = icon_disc(name, color, r)
    t = T(label, size, width=chars, max_w=max_w)
    return VGroup(d, t.next_to(d, DOWN, buff=0.2))


def pop_labelled(g: VGroup) -> Animation:
    return AnimationGroup(pop(g[0]), FadeIn(g[1], shift=UP * 0.15), lag_ratio=0.3)


# ---------------------------------------------------------------- templates
def title_card(spec, a, b) -> Built:
    hero = icon_disc(icon_for(spec["title"] + " " + spec["subtitle"], CATEGORY), a, r=0.85)
    title = T(spec["title"], 76, bold=True, width=22, max_w=12)
    bar = Line(LEFT * 2.5, RIGHT * 2.5, color=a, stroke_width=8)
    sub = T(spec["subtitle"], 36, color=MUTED, width=42, max_w=11.5)
    g = VGroup(hero, title, bar, sub).arrange(DOWN, buff=0.4)
    # orbiting particles around the hero icon
    orbit_r = 1.35
    dots = VGroup(*[Dot(radius=0.07, color=c).move_to(hero.get_center() + orbit_r * np.array([math.cos(t), math.sin(t), 0]))
                    for t, c in ((0, a), (2.1, b), (4.2, WHITE))])
    content = VGroup(g, dots)

    def idle(scene: Scene, t: float):
        dots.add_updater(lambda m, dt: m.rotate(1.2 * dt, about_point=hero.get_center()))
        scene.play(hero[2].animate.scale(1.08), rate_func=there_and_back, run_time=t)
        dots.clear_updaters()

    return Built(content,
                 intro=[lambda: pop(hero), lambda: AnimationGroup(Write(title), GrowFromCenter(bar), FadeIn(dots), lag_ratio=0.3)],
                 units=[lambda: FadeIn(sub, shift=UP * 0.3)], unit_mobs=[sub], idle=idle, focus=False)


def definition(spec, a, b) -> Built:
    hero = icon_disc(icon_for(spec["term"] + " " + spec["definition"], CATEGORY), a, r=0.6)
    term = T(spec["term"], 64, color=a, bold=True, max_w=10.5)
    head = VGroup(hero, term).arrange(RIGHT, buff=0.45)
    body = T(spec["definition"], 38, width=44, max_w=11.2)
    box = card(max(body.width + 1.0, 8), body.height + 0.9, a)
    body.move_to(box)
    quote = T("“", 120, color=a).next_to(box, UL, buff=-0.35)
    g = VGroup(head, VGroup(box, body, quote)).arrange(DOWN, buff=0.6)

    def idle(scene: Scene, t: float):
        scene.play(Indicate(term, color=a, scale_factor=1.06), Rotate(hero[2], angle=2 * math.pi, rate_func=smooth),
                   run_time=min(1.5, t))
        if t > 1.5:
            pause(scene, t - 1.5)

    return Built(g, intro=[lambda: AnimationGroup(pop(hero), Write(term), lag_ratio=0.4)],
                 units=[lambda: AnimationGroup(Create(box), FadeIn(quote), Write(body, run_time=2.0))],
                 unit_mobs=[VGroup(box, body, quote)], idle=idle, focus=False)


def bullet_list(spec, a, b) -> Built:
    names = icons_for(spec["items"], CATEGORY)
    rows = []
    for i, (item, name) in enumerate(zip(spec["items"], names)):
        disc = icon_disc(name, a if i % 2 == 0 else b, r=0.42)
        txt = T(item, 36, width=44, max_w=10.2)
        rows.append(VGroup(disc, txt).arrange(RIGHT, buff=0.45))
    g = VGroup(*rows).arrange(DOWN, buff=0.4, aligned_edge=LEFT)
    return Built(g, units=[(lambda r=r: AnimationGroup(pop(r[0]), FadeIn(r[1], shift=RIGHT * 0.4), lag_ratio=0.3))
                           for r in rows], unit_mobs=rows)


def process_flow(spec, a, b) -> Built:
    steps = spec["steps"]
    n = len(steps)
    names = icons_for(steps, CATEGORY)
    per_row = n if n <= 4 else 3
    w = min(3.0, (AREA_W - 0.9 * (per_row - 1)) / per_row)
    h = 2.5 if n <= 4 else 2.25
    boxes = []
    for i, (s, name) in enumerate(zip(steps, names)):
        col = a if i % 2 == 0 else b
        box = card(w, h, col)
        ic = icon(name, col, h=0.85 if n <= 4 else 0.6)
        txt = T(s, 28, width=max(8, int(w * 4.4)), max_w=w - 0.3)
        if txt.height > h * 0.5:
            txt.scale_to_fit_height(h * 0.5)
        inner = VGroup(ic, txt).arrange(DOWN, buff=0.22).move_to(box)
        num = Circle(radius=0.26, fill_color=col, fill_opacity=1, stroke_width=0)
        num_t = T(str(i + 1), 24, color=BG, bold=True).move_to(num)
        VGroup(num, num_t).move_to(box.get_corner(UL))
        boxes.append(VGroup(box, inner, num, num_t))
    rows = [VGroup(*boxes[i:i + per_row]).arrange(RIGHT, buff=0.9) for i in range(0, n, per_row)]
    VGroup(*rows).arrange(DOWN, buff=0.9)
    if len(rows) == 2:  # snake: second row runs right-to-left, starting under the last box of row 1
        x_right = boxes[per_row - 1].get_x()
        for k, bx in enumerate(boxes[per_row:]):
            bx.set_x(x_right - k * (w + 0.9))
    arrows = [None]
    for i in range(1, n):
        p, q = boxes[i - 1][0], boxes[i][0]
        if abs(p.get_y() - q.get_y()) < 0.1:
            l2r = q.get_x() > p.get_x()
            arr = Arrow(p.get_right() if l2r else p.get_left(), q.get_left() if l2r else q.get_right(),
                        buff=0.08, color=MUTED, stroke_width=5)
        else:
            arr = Arrow(p.get_bottom(), q.get_top(), buff=0.08, color=MUTED, stroke_width=5)
        arrows.append(arr)
    content = VGroup(*boxes, *[x for x in arrows if x])

    def show(bx):
        return AnimationGroup(GrowFromCenter(bx[0]), Create(bx[1][0]), FadeIn(bx[1][1], shift=UP * 0.15),
                              FadeIn(VGroup(bx[2], bx[3])), lag_ratio=0.2)

    units, mobs = [], []
    for i, bx in enumerate(boxes):
        arr = arrows[i]
        if arr is None:
            units.append(lambda bx=bx: show(bx))
            mobs.append(bx)
        else:
            units.append(lambda bx=bx, arr=arr: AnimationGroup(GrowArrow(arr), show(bx), lag_ratio=0.35))
            mobs.append(VGroup(arr, bx))

    def idle(scene: Scene, t: float):  # a glowing pulse travels along the arrows, lighting each step
        if n < 2 or t < 1.5:
            pause(scene, t)
            return
        per = (t - 0.3) / (n - 1)
        pulse = Dot(radius=0.13, color=WHITE)
        scene.add(pulse)
        for i in range(1, n):
            arr = arrows[i]
            pulse.move_to(arr.get_start())
            scene.play(pulse.animate.move_to(arr.get_end()), Indicate(boxes[i][1][0], color=WHITE, scale_factor=1.15),
                       run_time=per, rate_func=smooth)
        scene.play(FadeOut(pulse), run_time=0.3)

    return Built(content, units=units, unit_mobs=mobs, idle=idle)


def cycle(spec, a, b) -> Built:
    stages = spec["stages"]
    n = len(stages)
    names = icons_for(stages, CATEGORY)
    center = Circle(radius=1.0, fill_color=a, fill_opacity=0.15, stroke_color=a, stroke_width=4)
    cicon = icon(icon_for(spec["center"], CATEGORY, set(names)), a, h=0.6)
    ctext = T(spec["center"], 26, bold=True, width=10, max_w=1.7)
    VGroup(cicon, ctext).arrange(DOWN, buff=0.12).move_to(center)
    nodes, arrows = [], []
    RX, RY = 4.3, 2.35
    angles = [math.pi / 2 - 2 * math.pi * i / n for i in range(n)]
    for i, (s, ang, name) in enumerate(zip(stages, angles, names)):
        pos = np.array([RX * math.cos(ang), RY * math.sin(ang), 0])
        nd = labelled_icon(s, name, a if i % 2 == 0 else b, r=0.48, size=24, chars=14, max_w=2.6)
        if math.sin(ang) > 0.3:
            nd[1].next_to(nd[0], UP, buff=0.15)
        nd.shift(pos - nd[0].get_center())
        nodes.append(nd)
    for i in range(n):
        p, q = nodes[i][0], nodes[(i + 1) % n][0]
        arrows.append(CurvedArrow(p.get_center(), q.get_center(), angle=-0.5, color=MUTED, stroke_width=4)
                      .scale(0.62, about_point=(p.get_center() + q.get_center()) / 2))
    content = VGroup(center, cicon, ctext, *nodes, *arrows)
    units, mobs = [], []
    for i in range(n):
        if i > 0:
            units.append(lambda i=i: AnimationGroup(Create(arrows[i - 1]), pop_labelled(nodes[i]), lag_ratio=0.35))
            mobs.append(VGroup(arrows[i - 1], nodes[i]))
        else:
            units.append(lambda: pop_labelled(nodes[0]))
            mobs.append(nodes[0])

    def idle(scene: Scene, t: float):  # close the loop, then a particle keeps circulating through the stages
        scene.play(Create(arrows[-1]), run_time=min(0.8, t))
        rest = t - min(0.8, t)
        if rest > 0.6:
            path = VMobject().set_points_smoothly([nd[0].get_center() for nd in nodes] + [nodes[0][0].get_center()])
            dot = Dot(radius=0.12, color=WHITE).move_to(path.get_start())
            scene.add(dot)
            scene.play(MoveAlongPath(dot, path), Rotate(cicon, angle=2 * math.pi), run_time=rest, rate_func=linear)
            scene.remove(dot)
        else:
            pause(scene, rest)

    return Built(content, intro=[lambda: AnimationGroup(GrowFromCenter(center), Create(cicon), FadeIn(ctext), lag_ratio=0.3)],
                 units=units, unit_mobs=mobs, idle=idle, focus=False)


def comparison(spec, a, b) -> Built:
    def column(title, items, color):
        hero = icon_disc(icon_for(title + " " + " ".join(items), CATEGORY), color, r=0.5)
        head = T(title, 36, color=color, bold=True, max_w=5.2)
        rows = VGroup(*[T("• " + it, 28, width=30, max_w=5.4) for it in items]).arrange(DOWN, buff=0.3,
                                                                                      aligned_edge=LEFT)
        inner = VGroup(hero, head, rows).arrange(DOWN, buff=0.35)
        box = card(6.0, max(inner.height + 0.8, 4.4), color)
        inner.move_to(box)
        return VGroup(box, inner)

    left = column(spec["left_title"], spec["left_items"], a)
    right = column(spec["right_title"], spec["right_items"], b)
    h = max(left[0].height, right[0].height)
    for c in (left, right):
        c[0].stretch_to_fit_height(h)
        c[1].move_to(c[0])
    VGroup(left, right).arrange(RIGHT, buff=1.0)
    vs = VGroup(Circle(radius=0.42, fill_color=BG, fill_opacity=1, stroke_color=WHITE, stroke_width=3),
                T("VS", 28, bold=True))
    vs[1].move_to(vs[0])
    vs.move_to((left.get_right() + right.get_left()) / 2)

    def col_in(c, d):
        return AnimationGroup(FadeIn(c[0], shift=d * 0.4), pop(c[1][0]), FadeIn(c[1][1]),
                              LaggedStart(*[FadeIn(r, shift=d * 0.2) for r in c[1][2]], lag_ratio=0.3), lag_ratio=0.25)

    return Built(VGroup(left, right, vs),
                 units=[lambda: col_in(left, RIGHT),
                        lambda: AnimationGroup(GrowFromCenter(vs), col_in(right, LEFT), lag_ratio=0.3)],
                 unit_mobs=[left, VGroup(right, vs)], focus=False)


def timeline(spec, a, b) -> Built:
    events = spec["events"]
    n = len(events)
    names = icons_for([e["label"] for e in events], CATEGORY)
    axis = Line(LEFT * 6.2, RIGHT * 6.2, color=MUTED, stroke_width=4)
    xs = np.linspace(-5.0, 5.0, n) if n > 1 else [0]
    items = []
    for i, (e, x, name) in enumerate(zip(events, xs, names)):
        up = i % 2 == 0
        col = a if up else b
        disc = icon_disc(name, col, r=0.42).move_to([x, 0, 0])
        when = T(e["when"], 32, color=col, bold=True, max_w=2.6)
        label = T(e["label"], 26, width=14, max_w=2.6)
        txt = VGroup(when, label).arrange(DOWN, buff=0.12)
        txt.next_to(disc, UP if up else DOWN, buff=0.35)
        items.append(VGroup(disc, txt))
    marker = Triangle(color=WHITE, fill_opacity=1).scale(0.14).rotate(-math.pi / 2).move_to([-6.2, 0, 0])
    content = VGroup(axis, *items, marker)  # marker moves with the layout
    units = []
    for i, it in enumerate(items):  # target read at play time, after the layout is fitted
        units.append(lambda it=it: AnimationGroup(marker.animate.move_to(it[0].get_center() + LEFT * 0.62),
                                                         AnimationGroup(pop(it[0]), FadeIn(it[1], shift=UP * 0.2)),
                                                         lag_ratio=0.5))
    return Built(content, intro=[lambda: Create(axis), lambda: FadeIn(marker)], units=units, unit_mobs=items)


def concept_map(spec, a, b) -> Built:
    nodes = spec["nodes"]
    n = len(nodes)
    names = icons_for(nodes, CATEGORY)
    hub = Circle(radius=1.15, fill_color=a, fill_opacity=0.18, stroke_color=a, stroke_width=5)
    hub_icon = icon(icon_for(spec["center"], CATEGORY, set(names)), a, h=0.6)
    hub_t = T(spec["center"], 28, bold=True, width=10, max_w=1.9)
    VGroup(hub_icon, hub_t).arrange(DOWN, buff=0.12).move_to(hub)
    items = []
    for i, (label, name) in enumerate(zip(nodes, names)):
        ang = math.pi / 2 - 2 * math.pi * i / n + (math.pi / n if n % 2 == 0 else 0)
        pos = np.array([4.5 * math.cos(ang), 2.2 * math.sin(ang), 0])
        nd = labelled_icon(label, name, b if i % 2 else a, r=0.45, size=24, chars=14, max_w=2.7)
        if math.sin(ang) > 0.3:  # upper half: label above the icon, away from the hub
            nd[1].next_to(nd[0], UP, buff=0.15)
        nd.shift(pos - nd[0].get_center())
        direction = nd[0].get_center() - hub.get_center()
        unit = direction / np.linalg.norm(direction)
        link = DashedLine(hub.get_center() + unit * 1.2, nd[0].get_center() - unit * 0.6, color=MUTED,
                          stroke_width=3, dash_length=0.12)
        items.append(VGroup(link, nd))
    content = VGroup(hub, hub_icon, hub_t, *items)

    def idle(scene: Scene, t: float):  # sparks travel from the hub to every idea
        if t < 1.0:
            pause(scene, t)
            return
        sparks = [Dot(radius=0.08, color=WHITE).move_to(it[0].get_start()) for it in items]
        scene.add(*sparks)
        run = min(t - 0.3, 2.5)
        scene.play(*[MoveAlongPath(s, Line(it[0].get_start(), it[0].get_end())) for s, it in zip(sparks, items)],
                   *[Indicate(it[1][0][2], color=WHITE, scale_factor=1.2) for it in items], run_time=run)
        scene.remove(*sparks)
        pause(scene, t - run)

    return Built(content, intro=[lambda: AnimationGroup(GrowFromCenter(hub), Create(hub_icon), FadeIn(hub_t), lag_ratio=0.3)],
                 units=[(lambda it=it: AnimationGroup(Create(it[0]), pop_labelled(it[1]), lag_ratio=0.35))
                        for it in items], unit_mobs=items, idle=idle)


# ---------------------------------------------------------------- graphic templates
def _axes(x_len=9.5, y_len=4.6, y_min=0.0, y_max=10.0, x_min=0.0, x_max=10.0) -> Axes:
    return Axes(x_range=[x_min, x_max, (x_max - x_min) / 4], y_range=[y_min, y_max, (y_max - y_min) / 4],
                x_length=x_len, y_length=y_len, tips=True,
                axis_config={"color": MUTED, "stroke_width": 3, "include_ticks": False, "include_numbers": False})


SHAPES = {
    "linear": lambda x: 0.55 * x + 0.6,
    "exponential": lambda x: 0.45 * math.exp(0.3 * x),
    "logarithmic": lambda x: 3.3 * math.log(1 + x),
    "quadratic": lambda x: 0.09 * x * x + 0.2,
    "s_curve": lambda x: 9 / (1 + math.exp(-1.1 * (x - 5))),
    "bell": lambda x: 8.5 * math.exp(-((x - 5) ** 2) / (2 * 1.5 ** 2)) + 0.3,
    "decay": lambda x: 9 * math.exp(-0.35 * x) + 0.3,
    "sine": lambda x: 5 + 3.5 * math.sin(1.1 * x),
    "flat": lambda x: 4.0,
}


def function_graph(spec, a, b) -> Built:
    ax = _axes()
    xl = T(spec["x_label"], 26, color=MUTED, max_w=4).next_to(ax.x_axis.get_end(), DOWN, buff=0.25).shift(LEFT * 0.6)
    yl = T(spec["y_label"], 26, color=MUTED, max_w=4).next_to(ax.y_axis.get_end(), RIGHT, buff=0.25)
    palette = [a, b, "#F06292"]
    curves, labels, areas = [], [], []
    for i, c in enumerate(spec["curves"]):
        f = SHAPES[c["shape"]]
        col = palette[i % 3]
        g = ax.plot(f, x_range=[0, 10], color=col, stroke_width=6)
        areas.append(ax.get_area(g, x_range=[0, 10], color=col, opacity=0.12))
        curves.append(g)
        labels.append(T(c["label"], 26, color=col, bold=True, max_w=3.0).next_to(ax.c2p(10, f(10)), RIGHT, buff=0.2))
    # keep end labels from colliding
    order = sorted(range(len(labels)), key=lambda k: labels[k].get_y())
    for prev, cur in zip(order, order[1:]):
        if labels[cur].get_bottom()[1] < labels[prev].get_top()[1] + 0.1:
            labels[cur].shift(UP * (labels[prev].get_top()[1] + 0.1 - labels[cur].get_bottom()[1]))
    content = VGroup(ax, xl, yl, *areas, *curves, *labels)
    units = [(lambda k=k: AnimationGroup(Create(curves[k], run_time=1.6), FadeIn(areas[k]), FadeIn(labels[k], shift=LEFT * 0.2),
                                         lag_ratio=0.5)) for k in range(len(curves))]

    def idle(scene: Scene, t: float):  # tracer dots ride along every curve
        if t < 1.0:
            pause(scene, t)
            return
        tracers = [Dot(radius=0.1, color=WHITE).move_to(cv.get_start()) for cv in curves]
        scene.add(*tracers)
        scene.play(*[MoveAlongPath(d, cv) for d, cv in zip(tracers, curves)], run_time=t - 0.3, rate_func=smooth)
        scene.play(*[FadeOut(d) for d in tracers], run_time=0.3)

    return Built(content, intro=[lambda: AnimationGroup(Create(ax), FadeIn(xl), FadeIn(yl))], units=units,
                 unit_mobs=[VGroup(c, l) for c, l in zip(curves, labels)], idle=idle, focus=False, allow_overlap=True)


def line_chart(spec, a, b) -> Built:
    pts = spec["points"]
    n = len(pts)
    vals = [p["value"] for p in pts]
    lo, hi = min(0.0, min(vals)), max(vals)
    span = (hi - lo) or 1.0
    ax = _axes(x_len=10.0, y_len=4.3, y_min=lo, y_max=hi + span * 0.18, x_min=-0.5, x_max=n - 0.5)
    yl = T(spec.get("y_label") or "", 26, color=MUTED, max_w=4).next_to(ax.y_axis.get_end(), RIGHT, buff=0.25) \
        if spec.get("y_label") else None
    dots, vlabels, xlabels, segs = [], [], [], []
    for i, p in enumerate(pts):
        pos = ax.c2p(i, p["value"])
        dots.append(Dot(pos, radius=0.12, color=a))
        vlabels.append(T(_fmt(p["value"]), 26, bold=True, max_w=1.8).next_to(pos, UP, buff=0.18))
        xlabels.append(T(p["label"], 22, color=MUTED, width=10, max_w=10.0 / n - 0.1)
                       .next_to(ax.c2p(i, lo), DOWN, buff=0.25))
        if i:
            segs.append(Line(ax.c2p(i - 1, pts[i - 1]["value"]), pos, color=a, stroke_width=6))
    area = Polygon(ax.c2p(0, lo), *[ax.c2p(i, v) for i, v in enumerate(vals)], ax.c2p(n - 1, lo),
                   stroke_width=0, fill_color=a, fill_opacity=0.15)
    content = VGroup(ax, area, *segs, *dots, *vlabels, *xlabels, *([yl] if yl else []))
    units = []
    for i in range(n):
        parts = [GrowFromCenter(dots[i]), FadeIn(vlabels[i], shift=UP * 0.2), FadeIn(xlabels[i])]
        if i:
            parts.insert(0, Create(segs[i - 1]))
        units.append(lambda parts=parts: AnimationGroup(*parts, lag_ratio=0.3))
    k = int(np.argmax(vals))

    def idle(scene: Scene, t: float):
        scene.play(FadeIn(area), Flash(dots[k], color=WHITE, line_length=0.3), Indicate(vlabels[k], color=b),
                   run_time=min(1.2, t))
        pause(scene, t - min(1.2, t))

    intro = [lambda: AnimationGroup(Create(ax), *([FadeIn(yl)] if yl else []))]
    return Built(content, intro=intro, units=units,
                 unit_mobs=[VGroup(dots[i], vlabels[i], xlabels[i]) for i in range(n)], idle=idle, focus=False)


def pie_chart(spec, a, b) -> Built:
    slices = spec["slices"]
    total = sum(s["value"] for s in slices) or 1.0
    palette = [a, b, "#F06292", "#81C784", "#FFB74D", "#4DD0E1"]
    R, r_in = 2.3, 1.05
    sectors, legend = [], []
    start = math.pi / 2
    unit = spec.get("unit") or ""
    for i, s in enumerate(slices):
        ang = -2 * math.pi * s["value"] / total
        sec = AnnularSector(inner_radius=r_in, outer_radius=R, angle=ang, start_angle=start,
                            fill_color=palette[i % 6], fill_opacity=1, stroke_color=BG, stroke_width=4)
        sec.mid_angle = start + ang / 2
        sectors.append(sec)
        start += ang
        sw = RoundedRectangle(corner_radius=0.06, width=0.36, height=0.36, fill_color=palette[i % 6],
                              fill_opacity=1, stroke_width=0)
        lab = T(s["label"], 28, max_w=4.2)
        val = T(_fmt(s["value"]) + (unit if len(unit) <= 2 else " " + unit), 28, color=palette[i % 6], bold=True, max_w=1.8)
        legend.append(VGroup(sw, lab, val).arrange(RIGHT, buff=0.25))
    pie = VGroup(*sectors).move_to(LEFT * 3.0)
    leg = VGroup(*legend).arrange(DOWN, buff=0.35, aligned_edge=LEFT).move_to(RIGHT * 3.2)
    centre_icon = icon(icon_for(spec["heading"], CATEGORY), WHITE, h=0.8).move_to(pie.get_center())
    content = VGroup(pie, leg, centre_icon)
    units = [(lambda i=i: AnimationGroup(FadeIn(sectors[i], scale=0.85), FadeIn(legend[i], shift=LEFT * 0.3), lag_ratio=0.2))
             for i in range(len(slices))]
    big = int(np.argmax([s["value"] for s in slices]))

    def idle(scene: Scene, t: float):  # the largest slice pops out and back
        if t < 1.2:
            pause(scene, t)
            return
        d = 0.3 * np.array([math.cos(sectors[big].mid_angle), math.sin(sectors[big].mid_angle), 0])
        scene.play(sectors[big].animate.shift(d), Indicate(legend[big], color=WHITE), run_time=0.8)
        pause(scene, t - 1.6)
        scene.play(sectors[big].animate.shift(-d), run_time=0.8)

    return Built(content, intro=[lambda: Create(centre_icon)], units=units,
                 unit_mobs=[VGroup(s, l) for s, l in zip(sectors, legend)], idle=idle, focus=False, allow_overlap=True)


def pyramid(spec, a, b) -> Built:
    levels = spec["levels"]  # bottom first
    n = len(levels)
    names = icons_for(levels, CATEGORY)
    H, W0 = 5.2, 7.6
    lh = H / n
    bottom = -H / 2
    tiers = []
    for i, (label, name) in enumerate(zip(levels, names)):
        y0, y1 = bottom + i * lh, bottom + (i + 1) * lh - 0.08
        w0, w1 = W0 * (1 - i / n), W0 * (1 - (i + 1) / n)
        col = interpolate_color(ManimColor(a), ManimColor(b), i / max(n - 1, 1))
        shape = Polygon([-w0 / 2, y0, 0], [w0 / 2, y0, 0], [w1 / 2, y1, 0], [-w1 / 2, y1, 0],
                        fill_color=col, fill_opacity=0.9, stroke_color=BG, stroke_width=3)
        ic = icon(name, BG, h=min(0.55, lh * 0.55)).move_to([0, (y0 + y1) / 2 - (0.05 if i < n - 1 else lh * 0.15), 0])
        txt = T(label, 28, bold=True, max_w=4.6)
        txt.move_to([W0 / 2 + 0.4 + txt.width / 2, (y0 + y1) / 2, 0])
        lead = DashedLine([(w0 + w1) / 4 + 0.1, (y0 + y1) / 2, 0], [W0 / 2 + 0.3, (y0 + y1) / 2, 0],
                          color=MUTED, stroke_width=2, dash_length=0.08)
        tiers.append(VGroup(shape, ic, lead, txt))
    content = VGroup(*tiers)
    units = [(lambda tr=tr: AnimationGroup(FadeIn(tr[0], shift=UP * 0.3), Create(tr[1]), Create(tr[2]),
                                           FadeIn(tr[3], shift=LEFT * 0.2), lag_ratio=0.25)) for tr in tiers]

    def idle(scene: Scene, t: float):
        scene.play(Indicate(tiers[-1][0], color=WHITE, scale_factor=1.06), run_time=min(1.2, t))
        pause(scene, t - min(1.2, t))

    return Built(content, units=units, unit_mobs=tiers, idle=idle)


def venn(spec, a, b) -> Built:
    c1 = Circle(radius=2.2, fill_color=a, fill_opacity=0.22, stroke_color=a, stroke_width=4).shift(LEFT * 1.45)
    c2 = Circle(radius=2.2, fill_color=b, fill_opacity=0.22, stroke_color=b, stroke_width=4).shift(RIGHT * 1.45)
    mid = Intersection(c1, c2, fill_color=WHITE, fill_opacity=0.18, stroke_width=0)
    names = icons_for([spec["left"], spec["right"], spec["overlap"]], CATEGORY)

    def side(text, name, col, x, w):
        g = VGroup(icon(name, col, h=0.6), T(text, 28, bold=True, width=12, max_w=w)).arrange(DOWN, buff=0.15)
        return g.move_to([x, 0, 0])

    left = side(spec["left"], names[0], a, -2.45, 1.9)
    right = side(spec["right"], names[1], b, 2.45, 1.9)
    mid_icon = icon(names[2], WHITE, h=0.55).move_to(mid)
    both_t = T(spec["overlap"], 30, bold=True, max_w=5.0).move_to([0, -2.95, 0])
    pointer = Arrow(both_t.get_top(), mid.get_center() + DOWN * 0.45, buff=0.1, color=WHITE, stroke_width=4)
    both = VGroup(mid_icon, both_t, pointer)
    content = VGroup(c1, c2, mid, left, right, both)
    return Built(content, units=[lambda: AnimationGroup(DrawBorderThenFill(c1), FadeIn(left), lag_ratio=0.4),
                                 lambda: AnimationGroup(DrawBorderThenFill(c2), FadeIn(right), lag_ratio=0.4),
                                 lambda: AnimationGroup(FadeIn(mid), Create(mid_icon), FadeIn(both_t, shift=UP * 0.2),
                                                        GrowArrow(pointer), lag_ratio=0.25)],
                 unit_mobs=[VGroup(c1, left), VGroup(c2, right), VGroup(mid, both)], focus=False, allow_overlap=True)


def network(spec, a, b) -> Built:
    layers = spec["layers"]
    L = len(layers)
    xs = np.linspace(-5.0, 5.0, L)
    cols, nodes = [], []
    for i, (lay, x) in enumerate(zip(layers, xs)):
        k = lay["nodes"]
        col = a if i in (0, L - 1) else b
        ys = np.linspace((k - 1) * 0.42, -(k - 1) * 0.42, k) + 0.3
        ns = [Circle(radius=0.27, fill_color=PANEL, fill_opacity=1, stroke_color=col, stroke_width=4).move_to([x, y, 0])
              for y in ys]
        nodes.append(ns)
        lab = T(lay["label"], 24, width=12, max_w=min(2.6, 10.0 / L)).move_to([x, -2.75, 0])
        cols.append(VGroup(*ns, lab))
    edges = []
    for i in range(1, L):
        edges.append(VGroup(*[Line(p.get_center(), q.get_center(), buff=0.29, stroke_width=1.8, color=MUTED,
                                   stroke_opacity=0.55) for p in nodes[i - 1] for q in nodes[i]]))
    content = VGroup(*edges, *cols)
    units = []
    for i in range(L):
        anims = [LaggedStart(*[GrowFromCenter(n_) for n_ in nodes[i]], lag_ratio=0.1), FadeIn(cols[i][-1], shift=UP * 0.2)]
        if i:
            anims.insert(0, Create(edges[i - 1], lag_ratio=0.02))
        units.append(lambda anims=anims: AnimationGroup(*anims, lag_ratio=0.3))
    rng = np.random.default_rng(7)

    def idle(scene: Scene, t: float):  # signals flow forward through the network
        if L < 2 or t < 1.2:
            pause(scene, t)
            return
        waves = max(1, int(t // 1.6))
        per = t / waves
        for _ in range(waves):
            paths = []
            for _ in range(4):
                pts = [nodes[i][rng.integers(len(nodes[i]))].get_center() for i in range(L)]
                paths.append(VMobject().set_points_as_corners(pts))
            sig = [Dot(radius=0.08, color=WHITE).move_to(p.get_start()) for p in paths]
            scene.add(*sig)
            scene.play(*[MoveAlongPath(s, p) for s, p in zip(sig, paths)], run_time=per, rate_func=linear)
            scene.remove(*sig)

    return Built(content, units=units, unit_mobs=cols, idle=idle, focus=False)


def _fmt(v: float) -> str:
    if v >= 1e9:
        return f"{v / 1e9:.3g}B"
    if v >= 1e6:
        return f"{v / 1e6:.3g}M"
    if v >= 1e4:
        return f"{v:,.0f}"
    return f"{v:g}"


def bar_chart(spec, a, b) -> Built:
    bars = spec["bars"]
    n = len(bars)
    vmax = max(x["value"] for x in bars) or 1
    H, W = 4.2, min(1.6, 10.5 / n - 0.4)
    base_y = -2.4
    xs = np.linspace(-(n - 1) * (W + 0.55) / 2, (n - 1) * (W + 0.55) / 2, n)
    baseline = Line([xs[0] - W, base_y, 0], [xs[-1] + W, base_y, 0], color=MUTED, stroke_width=3)
    groups = []
    for i, (bar, x) in enumerate(zip(bars, xs)):
        h = max(0.04, H * bar["value"] / vmax)
        rect = Rectangle(width=W, height=h, fill_color=a if i % 2 == 0 else b, fill_opacity=0.95, stroke_width=0)
        rect.move_to([x, base_y + h / 2, 0])
        val = T(_fmt(bar["value"]) + (" " + spec["unit"] if spec.get("unit") and len(spec["unit"]) <= 4 else ""),
                28, bold=True, max_w=W + 0.5).next_to(rect, UP, buff=0.15)
        lab = T(bar["label"], 24, color=MUTED, width=10, max_w=W + 0.5).next_to(baseline, DOWN, buff=0.2)
        lab.set_x(x)
        groups.append(VGroup(rect, val, lab))
    unit_note = T(spec["unit"], 24, color=MUTED, max_w=4) if spec.get("unit") and len(spec["unit"]) > 4 else None
    content = VGroup(baseline, *groups)
    if unit_note:
        unit_note.next_to(baseline, UP, buff=H + 0.3).align_to(baseline, LEFT)
        content.add(unit_note)
    units = [(lambda g=g: AnimationGroup(GrowFromEdge(g[0], DOWN), FadeIn(g[2]), FadeIn(g[1], shift=UP * 0.2),
                                         lag_ratio=0.3)) for g in groups]
    intro = [lambda: Create(baseline)] + ([lambda: FadeIn(unit_note)] if unit_note else [])
    return Built(content, intro=intro, units=units, unit_mobs=groups)


NUM_PARSE = re.compile(r"^([^\d]*)(\d[\d,]*(?:\.\d+)?)(.*)$")


def big_number(spec, a, b) -> Built:
    value = spec["value"]
    caption = T(spec["caption"], 38, color=MUTED, width=40, max_w=11)
    m = NUM_PARSE.match(value)
    sizing = T(value, 110, color=a, bold=True, max_w=10)
    TEXT_LOG.remove(sizing)
    glow = RoundedRectangle(corner_radius=0.5, width=sizing.width + 1.4, height=sizing.height + 1.0,
                            stroke_color=a, stroke_width=5, stroke_opacity=0.55)
    if m and len(m.group(2).replace(",", "")) <= 12:
        pre, num, post = m.groups()
        target = float(num.replace(",", ""))
        decimals = len(num.split(".")[1]) if "." in num else 0
        tracker = ValueTracker(0)

        def make():
            v = tracker.get_value()
            s = f"{v:,.{decimals}f}" if "," in num else f"{v:.{decimals}f}"
            t = Text(pre + s + post, font=FONT, font_size=110, color=a, weight=BOLD)
            if t.width > final.width:
                t.scale_to_fit_width(final.width)
            return t.move_to(glow.get_center())

        final = T(value, 110, color=a, bold=True, max_w=10)
        number = always_redraw(make)
        VGroup(glow, caption).arrange(DOWN, buff=0.5)
        final.move_to(glow)
        number.update()
        units = [lambda: FadeIn(caption, shift=UP * 0.3)]
        intro = [lambda: AnimationGroup(Create(glow), FadeIn(number)),
                 lambda: tracker.animate(run_time=1.8, rate_func=smooth).set_value(target)]
        content = VGroup(glow, final, caption)
        built = Built(content, intro=intro, units=units, unit_mobs=[caption], focus=False)
        built.swap = (number, final)  # replace live counter with static text after counting
        return built
    final = T(value, 110, color=a, bold=True, max_w=10)
    VGroup(glow, caption).arrange(DOWN, buff=0.5)
    final.move_to(glow)
    return Built(VGroup(glow, final, caption), intro=[lambda: AnimationGroup(Create(glow), Write(final))],
                 units=[lambda: FadeIn(caption, shift=UP * 0.3)], unit_mobs=[caption], focus=False)


def _glyph_slice(text_mob: Text, full: str, sub: str) -> VGroup | None:
    """Glyphs of `sub` inside a Text (Text submobjects exclude whitespace)."""
    compact = re.sub(r"\s", "", full)
    target = re.sub(r"\s", "", sub)
    i = compact.find(target)
    if i < 0 or not target or len(text_mob) != len(compact):
        return None
    return VGroup(*text_mob[i:i + len(target)])


def formula(spec, a, b) -> Built:
    f = T(spec["formula"], 72, bold=True, max_w=12, font=MONO)
    fbox = card(f.width + 1.0, f.height + 0.9, a)
    f.move_to(fbox)
    top = VGroup(fbox, f)
    rows, highlights = [], []
    for term in spec["terms"]:
        sym = T(term["symbol"], 34, color=a, bold=True, font=MONO)
        dash = T("=", 30, color=MUTED)
        mean = T(term["meaning"], 32, width=40, max_w=8.5)
        rows.append(VGroup(sym, dash, mean).arrange(RIGHT, buff=0.3))
    legend = VGroup(*rows).arrange(DOWN, buff=0.3, aligned_edge=LEFT) if rows else VGroup()
    content = VGroup(top, legend).arrange(DOWN, buff=0.7) if rows else top
    for term, row in zip(spec["terms"], rows):
        glyphs = _glyph_slice(f, spec["formula"], term["symbol"])
        highlights.append(SurroundingRectangle(glyphs, color=b, buff=0.08, corner_radius=0.08) if glyphs else None)
    units = []
    for row, hl in zip(rows, highlights):
        if hl is not None:
            units.append(lambda row=row, hl=hl: AnimationGroup(FadeIn(row, shift=RIGHT * 0.3), Create(hl)))
        else:
            units.append(lambda row=row: FadeIn(row, shift=RIGHT * 0.3))
    mobs = [VGroup(r, h) if h is not None else r for r, h in zip(rows, highlights)]
    built = Built(content, intro=[lambda: Create(fbox), lambda: Write(f, run_time=1.6)], units=units, unit_mobs=mobs, focus=False)
    built.transient = [h for h in highlights if h is not None]  # remove previous highlight when next appears
    content.add(*built.transient)  # so highlights move/scale with the formula (they are only shown by animation)
    if not rows:  # formula only: reveal is the formula itself
        built.intro = [lambda: Create(fbox)]
        built.units = [lambda: Write(f, run_time=1.6)]
        built.unit_mobs = [f]
    return built


def code(spec, a, b) -> Built:
    src = "\n".join(line[:60] for line in spec["code"].strip("\n").splitlines()[:12])
    lang = "text" if spec["language"] == "pseudocode" else spec["language"]
    c = Code(code_string=src, language=lang, formatter_style="monokai", background="window",
             add_line_numbers=True, paragraph_config={"font": MONO, "font_size": 26})
    if c.width > 12:
        c.scale_to_fit_width(12)
    if c.height > 4.6:
        c.scale_to_fit_height(4.6)
    cap = T(spec["caption"], 32, color=MUTED, width=56, max_w=12)
    content = VGroup(c, cap).arrange(DOWN, buff=0.45)
    lines = c.code_lines if hasattr(c, "code_lines") else None

    def idle(scene: Scene, t: float):  # walk through the code line by line
        if lines is None or len(lines) == 0 or t < 1.0:
            pause(scene, t)
            return
        hl = SurroundingRectangle(lines[0], color=a, buff=0.06, stroke_width=2)
        scene.play(Create(hl), run_time=0.3)
        step = (t - 0.6) / len(lines)
        for ln in lines[1:]:
            pause(scene, max(step - 0.3, 0))
            scene.play(hl.animate.become(SurroundingRectangle(ln, color=a, buff=0.06, stroke_width=2)), run_time=0.3)
        pause(scene, max(step - 0.3, 0))
        scene.play(hl.animate.set_stroke(opacity=0), run_time=0.3)

    return Built(content, intro=[lambda: FadeIn(c, shift=UP * 0.2)], units=[lambda: FadeIn(cap, shift=UP * 0.2)],
                 unit_mobs=[cap], idle=idle, focus=False)


def summary(spec, a, b) -> Built:
    rows = []
    for i, p in enumerate(spec["points"]):
        badge = VGroup(Circle(radius=0.32, fill_color=a, fill_opacity=1, stroke_width=0),
                       T(str(i + 1), 26, color=BG, bold=True))
        badge[1].move_to(badge[0])
        txt = T(p, 36, width=46, max_w=10.6)
        rows.append(VGroup(badge, txt).arrange(RIGHT, buff=0.4))
    g = VGroup(*rows).arrange(DOWN, buff=0.5, aligned_edge=LEFT)
    return Built(g, units=[(lambda r=r: AnimationGroup(GrowFromCenter(r[0]), FadeIn(r[1], shift=RIGHT * 0.3),
                                                      lag_ratio=0.3)) for r in rows], unit_mobs=rows)

BUILDERS = {
    "title_card": title_card, "definition": definition, "bullet_list": bullet_list,
    "process_flow": process_flow, "cycle": cycle, "comparison": comparison, "timeline": timeline,
    "bar_chart": bar_chart, "big_number": big_number, "formula": formula, "code": code,
    "concept_map": concept_map, "summary": summary, "function_graph": function_graph,
    "line_chart": line_chart, "pie_chart": pie_chart, "pyramid": pyramid, "venn": venn, "network": network,
}
