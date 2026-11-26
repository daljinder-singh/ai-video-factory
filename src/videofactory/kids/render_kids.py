"""Render one kids scene:  python -m videofactory.kids.render_kids job.json

Bright drawn scenery per topic, big Twemoji pictures, Baloo 2 text, Bubbles the Bear mascot (lip-synced),
and bouncy animations timed to the narration parts."""
from __future__ import annotations

import json
import math
import random
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
from manim import (BOLD, DOWN, LEFT, RIGHT, UP, WHITE, AnimationGroup, Arc, Circle, Create, DashedLine,
                   DrawBorderThenFill, Ellipse, FadeIn, FadeOut, Flash, GrowFromCenter, Indicate, LaggedStart,
                   Line, MoveAlongPath, Polygon, Rectangle, RoundedRectangle, Scene, Square, Star, SVGMobject,
                   Text, Transform, Triangle, Union, VGroup, VMobject, Wiggle, rate_functions, tempconfig)

from ..render.presenter import Presenter, voice_envelope

ROOT = Path(__file__).resolve().parents[3]
EMOJI = ROOT / "assets" / "emoji" / "twemoji"
FONT = "Baloo 2"
INK = "#3A2E5C"
PALETTE = ["#E53935", "#FB8C00", "#FDD835", "#43A047", "#1E88E5", "#8E24AA", "#EC407A"]
FW, FH = 14.222, 8.0
CX, CY = -1.4, 0.55  # centre of the content area (mascot stands on the right)
GROUND_Y = -2.75
TEXTS: list[Text] = []
bounce = rate_functions.ease_out_back


def KT(s: str, size: float, color: str = INK, max_w: float | None = None, outline: bool = True) -> Text:
    t = Text(s, font=FONT, weight=BOLD, font_size=size, color=color)
    t.base_size, t.base_h = size, t.height
    if max_w and t.width > max_w:
        t.scale_to_fit_width(max_w)
    if outline:
        t.set_stroke(WHITE, width=size / 9, background=True)
    TEXTS.append(t)
    return t


_SVG_TMP: Path | None = None


def private_svg(src) -> str:
    """Manim writes a temporary '<name>_.svg' next to an SVG while loading it, which races when several render
    processes load the same file at once. Give each process its own copy of every SVG it uses."""
    global _SVG_TMP
    import shutil as _sh
    import tempfile as _tf

    if _SVG_TMP is None:
        _SVG_TMP = Path(_tf.mkdtemp(prefix="svg_"))
    src = Path(src)
    dst = _SVG_TMP / f"{src.parent.name}_{src.name}"
    if not dst.exists():
        _sh.copyfile(src, dst)
    return str(dst)


def E(code: str, h: float) -> SVGMobject:
    return SVGMobject(private_svg(EMOJI / f"{code}.svg")).scale_to_fit_height(h)


def readable(color: str) -> str:
    """Darken light colours (yellow, pale green...) so text stays readable on bright backgrounds."""
    r, g, b = (int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    if lum < 0.62:
        return color
    k = 0.62 / lum * 0.85
    return "#{:02X}{:02X}{:02X}".format(int(r * k), int(g * k), int(b * k))


def name_label(d: dict, lang: str, size: float, color: str = INK) -> VGroup:
    """Big name in the video language; Hindi videos also show the English word small (helps parents)."""
    color = readable(color)
    main = KT(d["hi"] if lang == "hi" else d["en"], size, color, max_w=7)
    if lang == "hi":
        sub = KT(d["en"], size * 0.42, "#6B6280", max_w=5)
        return VGroup(main, sub).arrange(DOWN, buff=0.08)
    return VGroup(main)


def pop(m, **kw):
    return GrowFromCenter(m, rate_func=bounce, **kw)


def card(w, h, color, fill=WHITE):
    return RoundedRectangle(corner_radius=0.3, width=w, height=h, fill_color=fill, fill_opacity=1,
                            stroke_color=color, stroke_width=8)


def shape_mob(kind: str, color: str, size: float = 2.8):
    style = dict(fill_color=color, fill_opacity=1, stroke_color=WHITE, stroke_width=10)
    if kind == "circle":
        return Circle(radius=size / 2, **style)
    if kind == "square":
        return Square(side_length=size * 0.95, **style)
    if kind == "triangle":
        return Triangle(**style).scale_to_fit_height(size)
    if kind == "rectangle":
        return Rectangle(width=size * 1.5, height=size * 0.8, **style)
    if kind == "star":
        return Star(n=5, outer_radius=size / 1.9, inner_radius=size / 4.2, **style)
    if kind == "heart":
        r = size * 0.29
        sq = Square(side_length=2 * r).rotate(math.pi / 4)
        c1 = Circle(radius=r).move_to(sq.get_center() + np.array([-r / math.sqrt(2), r / math.sqrt(2), 0]))
        c2 = Circle(radius=r).move_to(sq.get_center() + np.array([r / math.sqrt(2), r / math.sqrt(2), 0]))
        return Union(sq, c1, c2, **style).scale_to_fit_height(size * 0.9)
    if kind == "oval":
        return Ellipse(width=size * 1.25, height=size * 0.85, **style)
    raise ValueError(kind)


def option_visual(d: dict, topic: str, h: float):
    if d.get("shape"):
        return shape_mob(d["shape"], d["color"], h)
    if topic == "colours":
        return Circle(radius=h / 2, fill_color=d["color"], fill_opacity=1, stroke_color=WHITE, stroke_width=8)
    if topic == "abc":
        return KT(d["letter"], h * 60, d["color"])
    return E(d["emoji"], h)


def speech_bubble(text: str, near, size: float = 56):
    t = KT(text, size, INK, max_w=4.6, outline=False)
    box = RoundedRectangle(corner_radius=0.35, width=t.width + 0.7, height=t.height + 0.5, fill_color=WHITE,
                           fill_opacity=1, stroke_color=INK, stroke_width=5)
    tail = Polygon(box.get_bottom() + LEFT * 0.4, box.get_bottom() + LEFT * 0.05, box.get_bottom() + LEFT * 0.75 + DOWN * 0.45,
                   fill_color=WHITE, fill_opacity=1, stroke_color=INK, stroke_width=5)
    t.move_to(box)
    g = VGroup(tail, box, t)
    g.next_to(near, UP + RIGHT, buff=-0.25)
    if g.get_top()[1] > FH / 2 - 0.25:  # keep the bubble inside the frame
        g.shift(DOWN * (g.get_top()[1] - (FH / 2 - 0.25)))
    return g


# --------------------------------------------------------------------------- scenery
def scenery(topic: str, rng: random.Random) -> tuple[VGroup, list]:
    """Drawn background art for each topic + ambient updaters (clouds drift, sun turns)."""
    sky_top, sky_bottom = {"animals": ("#8FD3FF", "#E6F7FF"), "vehicles": ("#8FD3FF", "#E6F7FF"),
                           "fruits": ("#A5E1FF", "#F1FBFF"), "colours": ("#FFE6F2", "#FFF8E1"),
                           "shapes": ("#E8EAFF", "#FFF4E0"), "numbers": ("#FFF1D6", "#E9F7FF"),
                           "abc": ("#E9FFE9", "#FFF0F6"), "kitchen": ("#FFF3E0", "#FFE7C7")}.get(topic, ("#E6F7FF", "#FFF8E1"))
    sky = Rectangle(width=FW + 0.2, height=FH + 0.2, stroke_width=0, fill_opacity=1)
    sky.set_fill(color=[sky_bottom, sky_top])
    sky.set_sheen_direction(UP)
    g = VGroup(sky)
    movers = []
    outdoor = topic in ("animals", "vehicles", "fruits", "colours")
    if outdoor:
        rays = [Line(np.array([math.cos(a), math.sin(a), 0]) * 0.7, np.array([math.cos(a), math.sin(a), 0]) * 0.95,
                     color="#FFD54F", stroke_width=7) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
        sun = VGroup(Circle(radius=0.55, fill_color="#FFD54F", fill_opacity=1, stroke_width=0), *rays)
        sun.move_to([-5.9, 3.0, 0])
        g.add(sun)
        movers.append((sun, lambda m, dt: m.rotate(0.25 * dt)))
        for k in range(3):
            cloud = VGroup(*[Circle(radius=r, fill_color=WHITE, fill_opacity=0.95, stroke_width=0).shift(RIGHT * x + UP * y)
                             for r, x, y in ((0.45, 0, 0), (0.6, 0.55, 0.15), (0.45, 1.1, 0), (0.4, 0.55, -0.15))])
            cloud.move_to([rng.uniform(-4, 6), rng.uniform(2.3, 3.4), 0]).scale(rng.uniform(0.7, 1.1))
            g.add(cloud)
            speed = rng.uniform(0.12, 0.25)
            movers.append((cloud, lambda m, dt, s=speed: m.shift(RIGHT * s * dt) if m.get_left()[0] < FW / 2
                           else m.shift(LEFT * (FW + m.width + 0.5))))
    if topic == "colours":
        for i, c in enumerate(PALETTE):
            arc = Circle(radius=4.6 - i * 0.22, stroke_color=c, stroke_width=12, stroke_opacity=0.2).move_to([-1.4, -3.2, 0])
            g.add(arc)
    if topic in ("animals", "fruits"):
        g.add(Ellipse(width=11, height=3.2, fill_color="#7CCB5A", fill_opacity=1, stroke_width=0).move_to([-4.5, GROUND_Y - 0.6, 0]),
              Ellipse(width=12, height=3.0, fill_color="#66BB4A", fill_opacity=1, stroke_width=0).move_to([4.8, GROUND_Y - 0.7, 0]))
        if topic == "fruits":
            for x in (-6.4, 6.3):
                g.add(Rectangle(width=0.35, height=1.4, fill_color="#8D6E63", fill_opacity=1, stroke_width=0).move_to([x, GROUND_Y + 0.6, 0]),
                      Circle(radius=0.95, fill_color="#4CAF50", fill_opacity=1, stroke_width=0).move_to([x, GROUND_Y + 1.8, 0]),
                      *[Circle(radius=0.12, fill_color="#E53935", fill_opacity=1, stroke_width=0).move_to([x + dx, GROUND_Y + 1.8 + dy, 0])
                        for dx, dy in ((-0.4, 0.2), (0.3, 0.4), (0.1, -0.3))])
        else:
            for x in np.arange(-7, 7.5, 0.9):  # little fence
                g.add(Rectangle(width=0.14, height=0.7, fill_color="#FFF3E0", fill_opacity=1, stroke_width=0).move_to([x, GROUND_Y + 0.1, 0]))
            g.add(Rectangle(width=FW, height=0.1, fill_color="#FFF3E0", fill_opacity=1, stroke_width=0).move_to([0, GROUND_Y + 0.2, 0]))
    if topic == "vehicles":
        g.add(Rectangle(width=FW + 0.2, height=1.6, fill_color="#78909C", fill_opacity=1, stroke_width=0).move_to([0, -3.3, 0]),
              DashedLine([-7.2, -3.3, 0], [7.2, -3.3, 0], dash_length=0.5, color=WHITE, stroke_width=6),
              Rectangle(width=FW + 0.2, height=0.25, fill_color="#81C784", fill_opacity=1, stroke_width=0).move_to([0, -2.45, 0]))
    if topic in ("shapes", "numbers", "abc"):
        floaters = VGroup()
        for i in range(10):
            col = PALETTE[i % len(PALETTE)]
            if topic == "shapes":
                m = [Circle(radius=0.3), Square(side_length=0.5), Triangle().scale(0.35), Star(outer_radius=0.32)][i % 4]
                m.set_fill(col, 0.18).set_stroke(width=0)
            else:
                ch = str(i) if topic == "numbers" else "ABCDEFGHIJ"[i]
                m = Text(ch, font=FONT, weight=BOLD, font_size=60, color=col).set_opacity(0.16)
            m.move_to([rng.uniform(-6.8, 6.8), rng.uniform(-3.6, 3.6), 0])
            floaters.add(m)
        g.add(floaters)
        movers.append((floaters, lambda m, dt: [f.shift(UP * 0.12 * dt * (1 if k % 2 else -1)) for k, f in enumerate(m)]))
        g.add(Rectangle(width=FW + 0.2, height=0.9, fill_color="#FFE0B2", fill_opacity=1, stroke_width=0).move_to([0, -3.7, 0]))
    if topic == "kitchen":
        for x in np.arange(-7.1, 7.2, 0.9):  # wall tiles
            g.add(Line([x, -2.4, 0], [x, 4.1, 0], color="#F3D9B5", stroke_width=2))
        for y in np.arange(-2.4, 4.1, 0.9):
            g.add(Line([-7.2, y, 0], [7.2, y, 0], color="#F3D9B5", stroke_width=2))
        g.add(Rectangle(width=FW + 0.2, height=1.7, fill_color="#B07A50", fill_opacity=1, stroke_width=0).move_to([0, -3.3, 0]),
              Rectangle(width=FW + 0.2, height=0.22, fill_color="#D6A274", fill_opacity=1, stroke_width=0).move_to([0, -2.45, 0]))
        for k, (code, x) in enumerate((("1fad9", -6.3), ("1f9c2", -5.5), ("1fad2", 6.4))):  # jars on the counter
            if (EMOJI / f"{code}.svg").exists():
                g.add(E(code, 0.75).move_to([x, -2.0, 0]))
    return g, movers


# --------------------------------------------------------------------------- scene builders
class B:
    """Events: list of (part_index, [animation factories]); idle(scene, seconds)."""

    def __init__(self):
        self.events: list[tuple[int, list]] = []
        self.mobs = VGroup()
        self.idle = None

    def at(self, part: int, *factories):
        self.events.append((part, list(factories)))


def b_intro(d, lang, topic):
    b = B()
    title = KT(d["title_hi"] if lang == "hi" else d["title_en"], 110, max_w=9.5)
    for i, ch in enumerate(title):
        ch.set_fill(PALETTE[i % len(PALETTE)])
    big = E(d["emoji"], 1.5)
    head = VGroup(big, title).arrange(DOWN, buff=0.25).move_to([CX, CY + 0.9, 0])
    row = VGroup(*[E(c, 1.05) for c in d["emojis"]]).arrange(RIGHT, buff=0.4).move_to([CX, CY - 2.0, 0])
    if row.width > 9.5:
        row.scale_to_fit_width(9.5)
    b.mobs.add(head, row)
    b.at(0, lambda: pop(big), lambda: LaggedStart(*[FadeIn(c, shift=UP * 0.6, scale=0.4) for c in title], lag_ratio=0.06))
    b.at(1, lambda: LaggedStart(*[pop(e) for e in row], lag_ratio=0.15))

    def idle(scene, t):
        scene.play(LaggedStart(*[e.animate(rate_func=rate_functions.there_and_back).shift(UP * 0.35) for e in row],
                               lag_ratio=0.12), Wiggle(big), run_time=max(t, 0.1))
    b.idle = idle
    return b


def b_colour(d, lang, topic):
    b = B()
    blob = Circle(radius=1.45, fill_color=d["color"], fill_opacity=1, stroke_color=WHITE, stroke_width=12)
    name = name_label(d, lang, 120, d["color"])
    top = VGroup(blob, name).arrange(RIGHT, buff=0.7).move_to([CX, CY + 1.0, 0])
    exs = VGroup(*[E(c, 1.35) for c in d["examples"]]).arrange(RIGHT, buff=0.9).move_to([CX, CY - 1.85, 0])
    b.mobs.add(top, exs)
    b.at(0, lambda: pop(blob), lambda: FadeIn(name, shift=LEFT * 0.4))
    b.at(1, lambda: Indicate(name, scale_factor=1.25, color=d["color"]))
    for k, e in enumerate(exs):
        b.at(2 + k, lambda e=e: pop(e))
    b.at(2 + len(exs), lambda: Wiggle(name, scale_value=1.2), lambda: Flash(blob, color=d["color"], line_length=0.4))
    return b


def b_colour_mix(d, lang, topic):
    b = B()
    blobs = [Circle(radius=0.85, fill_color=d[k]["color"], fill_opacity=1, stroke_color=WHITE, stroke_width=10) for k in "abc"]
    plus, eq = KT("+", 110), KT("=", 110)
    row = VGroup(blobs[0], plus, blobs[1], eq, blobs[2]).arrange(RIGHT, buff=0.45).move_to([CX, CY + 0.5, 0])
    labels = [name_label(d[k], lang, 52, d[k]["color"]).next_to(bl, DOWN, buff=0.25) for k, bl in zip("abc", blobs)]
    title = KT("Colour magic!" if lang == "en" else "रंगों का जादू!", 80, "#8E24AA").move_to([CX, CY + 2.5, 0])
    b.mobs.add(row, *labels, title)
    b.at(0, lambda: FadeIn(title, shift=DOWN * 0.3, scale=0.6))
    b.at(1, lambda: pop(blobs[0]), lambda: FadeIn(labels[0]), lambda: FadeIn(plus), lambda: pop(blobs[1]),
         lambda: FadeIn(labels[1]))
    ghost_a, ghost_b = blobs[0].copy(), blobs[1].copy()

    def merge():
        ghost_a.move_to(blobs[0])
        ghost_b.move_to(blobs[1])
        return AnimationGroup(FadeIn(eq), ghost_a.animate.move_to(blobs[2]).set_opacity(0),
                              ghost_b.animate.move_to(blobs[2]).set_opacity(0), pop(blobs[2]), FadeIn(labels[2]),
                              lag_ratio=0.15)
    b.at(2, merge)
    b.at(3, lambda: Flash(blobs[2], color=d["c"]["color"], line_length=0.5, num_lines=14),
         lambda: Indicate(labels[2], scale_factor=1.3, color=d["c"]["color"]))
    return b


def b_shape(d, lang, topic):
    b = B()
    shp = shape_mob(d["shape"], d["color"], 2.9)
    name = name_label(d, lang, 110, d["color"])
    top = VGroup(shp, name).arrange(RIGHT, buff=0.8).move_to([CX, CY + 0.85, 0])
    exs = VGroup(*[E(c, 1.3) for c in d["examples"]]).arrange(RIGHT, buff=1.2).move_to([CX, CY - 1.95, 0])
    b.mobs.add(top, exs)
    b.at(0, lambda: DrawBorderThenFill(shp), lambda: FadeIn(name, shift=LEFT * 0.4))
    b.at(1, lambda: Indicate(name, scale_factor=1.25, color=d["color"]))
    for k, e in enumerate(exs):
        b.at(2 + k, lambda e=e: pop(e))

    def trace():  # a sparkle draws the shape in the air
        path = shp.copy() if not isinstance(shp, Union) else shp.copy()
        dot = Star(n=5, outer_radius=0.22, inner_radius=0.1, fill_color="#FFD54F", fill_opacity=1, stroke_width=0)
        dot.move_to(path.point_from_proportion(0))
        return AnimationGroup(FadeIn(dot), MoveAlongPath(dot, path, run_time=2.2), lag_ratio=0.1)
    b.at(2 + len(exs), trace)
    return b


def b_shape_sides(d, lang, topic):
    b = B()
    shp = shape_mob(d["shape"], d["color"], 3.1).move_to([CX, CY - 0.35, 0])
    shp.set_fill(opacity=0.35)
    verts = shp.get_vertices()
    centre = shp.get_center()
    sides, nums = [], []
    for i in range(d["sides"]):
        p, q = verts[i], verts[(i + 1) % d["sides"]]
        sides.append(Line(p, q, color="#FF6F00", stroke_width=18))
        mid = (p + q) / 2
        out = (mid - centre) / (np.linalg.norm(mid - centre) or 1)
        nums.append(KT(str(i + 1), 80, "#E53935").move_to(mid + out * 0.55))
    name = name_label(d, lang, 80, d["color"]).move_to([CX, CY + 2.45, 0])
    b.mobs.add(shp, name, *sides, *nums)
    b.at(0, lambda: FadeIn(name), lambda: DrawBorderThenFill(shp))
    for i in range(d["sides"]):
        b.at(1 + i, lambda i=i: AnimationGroup(Create(sides[i]), pop(nums[i])))
    b.at(1 + d["sides"], lambda: LaggedStart(*[Indicate(n, scale_factor=1.4) for n in nums], lag_ratio=0.15),
         lambda: Indicate(shp, scale_factor=1.06))
    return b


def _grid(code, n, h=0.95, per_row=5):
    items = [E(code, h) for _ in range(n)]
    rows = [VGroup(*items[i:i + per_row]).arrange(RIGHT, buff=0.35) for i in range(0, n, per_row)]
    return items, VGroup(*rows).arrange(DOWN, buff=0.55)


def b_count(d, lang, topic):
    b = B()
    n = d["n"]
    num = KT(str(n), 220, PALETTE[(n - 1) % len(PALETTE)])
    items, grid = _grid(d["emoji"], n, h=1.7 if n <= 3 else 1.3 if n <= 6 else 0.95)
    labels = [KT(str(i + 1), 40, INK).next_to(it, DOWN, buff=0.05) for i, it in enumerate(items)]
    VGroup(num, VGroup(grid, *labels)).arrange(RIGHT, buff=0.9).move_to([CX, CY, 0])
    for it, lb in zip(items, labels):
        lb.next_to(it, DOWN, buff=0.05)
    b.mobs.add(num, grid, *labels)
    b.at(0, lambda: pop(num))
    for i in range(n):
        b.at(1 + i, lambda i=i: AnimationGroup(pop(items[i]), FadeIn(labels[i], shift=UP * 0.2)))
    b.at(1 + n, lambda: LaggedStart(*[it.animate(rate_func=rate_functions.there_and_back).shift(UP * 0.4) for it in items],
                                    lag_ratio=0.08), lambda: Indicate(num, scale_factor=1.2))
    return b


def b_compare(d, lang, topic):
    b = B()
    cols = []
    for k, n in enumerate((d["left"], d["right"])):
        stack = VGroup(*[E(d["emoji"], 0.62) for _ in range(n)]).arrange(UP, buff=0.12)
        bar = RoundedRectangle(corner_radius=0.2, width=1.5, height=stack.height + 0.4,
                               fill_color=PALETTE[1 + 3 * k], fill_opacity=0.35, stroke_color=PALETTE[1 + 3 * k], stroke_width=6)
        stack.move_to(bar)
        cnt = KT(str(n), 90, PALETTE[1 + 3 * k]).next_to(bar, UP, buff=0.15)
        cols.append(VGroup(bar, stack, cnt))
    for c in cols:
        c.align_to(np.array([0, CY - 2.4, 0]), DOWN)
    VGroup(*cols).arrange(RIGHT, buff=2.6, aligned_edge=DOWN).move_to([CX, CY - 0.5, 0])
    base = Line([CX - 3.2, cols[0][0].get_bottom()[1], 0], [CX + 3.2, cols[0][0].get_bottom()[1], 0], color=INK, stroke_width=6)
    big = 0 if d["left"] > d["right"] else 1
    crown = Star(n=5, outer_radius=0.5, inner_radius=0.22, fill_color="#FFD54F", fill_opacity=1, stroke_color=WHITE,
                 stroke_width=5).next_to(cols[big][2], UP, buff=0.1)
    b.mobs.add(base, *cols, crown)
    b.at(0, lambda: Create(base), lambda: AnimationGroup(*[AnimationGroup(GrowFromCenter(c[0]), LaggedStart(*[pop(e) for e in c[1]],
                                                                                                          lag_ratio=0.1))
                                                          for c in cols]))
    b.at(1, lambda: AnimationGroup(*[Indicate(c[1], scale_factor=1.05) for c in cols]))
    b.at(2, lambda: AnimationGroup(*[FadeIn(c[2], shift=DOWN * 0.2) for c in cols]), lambda: pop(crown),
         lambda: Indicate(cols[big][0], scale_factor=1.08, color="#FFD54F"))
    return b


def b_letter(d, lang, topic):
    b = B()
    L = d["letter"]
    letters = KT(f"{L}{L.lower()}", 230, d["color"])
    pic = E(d["emoji"], 2.6)
    word = KT(d["hi"] if lang == "hi" else d["en"], 90, INK, max_w=6)
    if lang != "hi":
        word[0].set_fill(d["color"])
    right = VGroup(pic, word).arrange(DOWN, buff=0.3)
    VGroup(letters, right).arrange(RIGHT, buff=1.2).move_to([CX, CY, 0])
    b.mobs.add(letters, right)
    b.at(0, lambda: LaggedStart(*[pop(c) for c in letters], lag_ratio=0.3))
    b.at(1, lambda: pop(pic), lambda: FadeIn(word, shift=UP * 0.3))
    b.at(2, lambda: Indicate(letters, scale_factor=1.15, color=d["color"]), lambda: Wiggle(pic))
    return b


def b_animal(d, lang, topic):
    b = B()
    pic = E(d["emoji"], 3.0).move_to([CX - 0.6, CY + 0.2, 0])
    name = name_label(d, lang, 96, d["color"]).next_to(pic, DOWN, buff=0.25)
    bubble = speech_bubble(d["sound"].rstrip("!") + "!", pic)
    b.mobs.add(pic, name, bubble)
    b.at(0, lambda: AnimationGroup(FadeIn(pic, shift=DOWN * 2.5, rate_func=bounce), FadeIn(name, shift=UP * 0.3)))
    b.at(1, lambda: pop(bubble), lambda: Wiggle(pic, scale_value=1.15))
    b.at(2, lambda: Indicate(bubble, scale_factor=1.15), lambda: Wiggle(pic))
    return b


def b_fruit(d, lang, topic):
    b = B()
    pic = E(d["emoji"], 3.0)
    name = name_label(d, lang, 100, d["color"])
    VGroup(pic, name).arrange(RIGHT, buff=0.8).move_to([CX, CY + 0.7, 0])
    sparkles = VGroup(*[Star(n=4, outer_radius=0.25, inner_radius=0.08, fill_color="#FFD54F", fill_opacity=1, stroke_width=0)
                        .move_to(pic.get_center() + 1.9 * np.array([math.cos(a), math.sin(a), 0]))
                        for a in np.linspace(0, 2 * math.pi, 6, endpoint=False)])
    b.mobs.add(pic, name, sparkles)
    b.at(0, lambda: AnimationGroup(GrowFromCenter(pic, rate_func=bounce), FadeIn(name, shift=LEFT * 0.4)))
    b.at(1, lambda: Indicate(name, scale_factor=1.15, color=d["color"]))
    b.at(2, lambda: LaggedStart(*[pop(s) for s in sparkles], lag_ratio=0.08), lambda: Wiggle(pic, scale_value=1.15))
    return b


def b_vehicle(d, lang, topic):
    b = B()
    pic = E(d["emoji"], 2.6).move_to([CX - 0.4, CY + 0.1, 0])
    name = name_label(d, lang, 96, d["color"]).next_to(pic, DOWN, buff=0.3)
    bubble = speech_bubble(d["sound"].rstrip("!") + "!", pic)
    b.mobs.add(pic, name, bubble)
    start = pic.get_center() + RIGHT * 9

    def drive():
        target = pic.get_center()
        pic.move_to(start)
        return AnimationGroup(pic.animate(rate_func=rate_functions.ease_out_cubic, run_time=1.3).move_to(target),
                              FadeIn(name, shift=UP * 0.3))
    b.at(0, drive)
    b.at(1, lambda: Indicate(name, scale_factor=1.12, color=d["color"]))
    b.at(2, lambda: pop(bubble), lambda: Wiggle(pic, scale_value=1.1))
    return b


ZONES = {"road": ("#90A4AE", "1f6e3"), "sky": ("#81D4FA", "2601"), "water": ("#4FC3F7", "1f30a")}
ZONE_NAMES = {"road": ("Road", "सड़क"), "sky": ("Sky", "आसमान"), "water": ("Water", "पानी")}


def b_sort_where(d, lang, topic):
    b = B()
    panels = []
    for it in d["items"]:
        col, icon = ZONES[it["zone"]]
        box = RoundedRectangle(corner_radius=0.3, width=3.0, height=3.6, fill_color=col, fill_opacity=0.55,
                               stroke_color=col, stroke_width=8)
        lab = KT(ZONE_NAMES[it["zone"]][1 if lang == "hi" else 0], 56, INK)
        ic = E(icon, 0.7) if (EMOJI / f"{icon}.svg").exists() else VGroup()
        head = VGroup(ic, lab).arrange(RIGHT, buff=0.15).next_to(box, UP, buff=0.15)
        panels.append(VGroup(box, head))
    VGroup(*panels).arrange(RIGHT, buff=0.45).move_to([CX, CY - 0.1, 0])
    pics = [E(it["emoji"], 1.7).move_to(p[0]) for it, p in zip(d["items"], panels)]
    b.mobs.add(*panels, *pics)
    b.at(0, lambda: LaggedStart(*[FadeIn(p, shift=UP * 0.3) for p in panels], lag_ratio=0.2))
    for k, pic in enumerate(pics):
        def fly(pic=pic):
            target = pic.get_center()
            pic.move_to([CX, CY + 4.5, 0])
            return pic.animate(rate_func=bounce, run_time=1.1).move_to(target)
        b.at(1 + k, fly)
    return b


def b_fruit_groups(d, lang, topic):
    b = B()
    baskets, contents = [], []
    for g in d["groups"]:
        c = g["colour"]["color"]
        box = RoundedRectangle(corner_radius=0.35, width=4.4, height=2.6, fill_color=c, fill_opacity=0.18,
                               stroke_color=c, stroke_width=8)
        lab = name_label(g["colour"], lang, 64, c).next_to(box, UP, buff=0.15)
        fruits = VGroup(*[E(f["emoji"], 1.2) for f in g["items"]]).arrange(RIGHT, buff=0.3).move_to(box)
        baskets.append(VGroup(box, lab))
        contents.append(fruits)
    row = VGroup(*[VGroup(bk, ct) for bk, ct in zip(baskets, contents)]).arrange(RIGHT, buff=0.8).move_to([CX, CY - 0.2, 0])
    b.mobs.add(row)
    b.at(0, lambda: LaggedStart(*[FadeIn(bk, shift=UP * 0.3) for bk in baskets], lag_ratio=0.3))
    for k, ct in enumerate(contents):
        b.at(1 + k, lambda ct=ct: LaggedStart(*[FadeIn(f, shift=DOWN * 1.5, rate_func=bounce) for f in ct], lag_ratio=0.2))
    return b


def b_quiz(d, lang, topic, question: str):
    b = B()
    q = KT(question, 64, INK, max_w=10)
    cards = []
    for o in d["options"]:
        c = card(2.9, 2.9, "#B39DDB")
        v = option_visual(o, topic, 1.9).move_to(c)
        cards.append(VGroup(c, v))
    row = VGroup(*cards).arrange(RIGHT, buff=0.5)
    VGroup(q, row).arrange(DOWN, buff=0.6).move_to([CX, CY + 0.1, 0])
    ok = cards[d["answer"]]
    ring = RoundedRectangle(corner_radius=0.35, width=3.3, height=3.3, stroke_color="#43A047", stroke_width=14).move_to(ok)
    b.mobs.add(q, row, ring)
    b.at(0, lambda: FadeIn(q, shift=DOWN * 0.3), lambda: LaggedStart(*[pop(c) for c in cards], lag_ratio=0.2))
    b.at(1, lambda: LaggedStart(*[Indicate(c, scale_factor=1.06, color="#B39DDB") for c in cards], lag_ratio=0.45, run_time=2.0))
    others = [c for c in cards if c is not ok]
    b.at(2, lambda: Create(ring), lambda: ok.animate.scale(1.12), lambda: Flash(ok, color="#FFD54F", line_length=0.6, num_lines=16),
         lambda: AnimationGroup(*[c.animate.set_opacity(0.35) for c in others]))
    return b


def b_count_quiz(d, lang, topic, question: str):
    b = B()
    q = KT(question, 64, INK, max_w=10)
    items, grid = _grid(d["emoji"], d["n"], h=1.2, per_row=6)
    VGroup(q, grid).arrange(DOWN, buff=0.7).move_to([CX, CY + 0.3, 0])
    labels = [KT(str(i + 1), 48, "#E53935").next_to(it, DOWN, buff=0.05) for i, it in enumerate(items)]
    answer = KT(str(d["n"]), 150, "#43A047").next_to(grid, RIGHT, buff=0.8)
    b.mobs.add(q, grid, *labels, answer)
    b.at(0, lambda: FadeIn(q), lambda: LaggedStart(*[pop(i) for i in items], lag_ratio=0.12))
    b.at(1, lambda: LaggedStart(*[Indicate(i, scale_factor=1.15) for i in items], lag_ratio=0.3, run_time=2.2))
    b.at(2, lambda: LaggedStart(*[FadeIn(l, shift=UP * 0.2) for l in labels], lag_ratio=0.1), lambda: pop(answer))
    return b


def b_outro(d, lang, topic):
    b = B()
    head = KT("Great job!" if lang == "en" else "बहुत बढ़िया!", 130, max_w=9.5)
    for i, ch in enumerate(head):
        ch.set_fill(PALETTE[i % len(PALETTE)])
    stars = VGroup(*[Star(n=5, outer_radius=0.45, inner_radius=0.2, fill_color=PALETTE[i % 7], fill_opacity=1,
                          stroke_color=WHITE, stroke_width=4) for i in range(5)]).arrange(RIGHT, buff=0.5)
    bye = KT("Bye bye!" if lang == "en" else "बाय बाय!", 90, "#1E88E5")
    VGroup(head, stars, bye).arrange(DOWN, buff=0.5).move_to([CX, CY + 0.2, 0])
    b.mobs.add(head, stars, bye)
    b.at(0, lambda: LaggedStart(*[FadeIn(c, shift=UP * 0.6, scale=0.4) for c in head], lag_ratio=0.05))
    b.at(1, lambda: LaggedStart(*[pop(s) for s in stars], lag_ratio=0.12))
    b.at(2, lambda: FadeIn(bye, shift=UP * 0.4, scale=0.6), lambda: LaggedStart(*[Flash(s, color=s.get_fill_color()) for s in stars],
                                                                            lag_ratio=0.1))
    return b


# --------------------------------------------------------------------------- recipe scenes
def _plate(code: str, h: float) -> VGroup:
    plate = Ellipse(width=h * 1.9, height=h * 0.55, fill_color=WHITE, fill_opacity=1, stroke_color="#E0D6C8", stroke_width=6)
    dish = E(code, h).next_to(plate.get_top(), UP, buff=-h * 0.35)
    return VGroup(plate, dish)


def b_recipe_intro(d, lang, topic):
    b = B()
    hero = _plate(d["emoji"], 2.2)
    title = KT(d["name"], 104, "#C62828", max_w=9.5)
    sub = KT(d["subtitle"], 52, "#6D4C41")
    VGroup(hero, title, sub).arrange(DOWN, buff=0.3).move_to([CX, CY + 0.1, 0])
    steam = VGroup(*[Arc(radius=0.25, start_angle=-math.pi / 2, angle=math.pi, color="#BDBDBD", stroke_width=6)
                     .move_to(hero[1].get_top() + np.array([x, 0.35 + 0.15 * k, 0])) for k, x in enumerate((-0.35, 0.05, 0.45))])
    b.mobs.add(hero, title, sub, steam)
    b.at(0, lambda: pop(hero), lambda: LaggedStart(*[FadeIn(c, shift=UP * 0.5, scale=0.4) for c in title], lag_ratio=0.04))
    b.at(1, lambda: FadeIn(sub, shift=UP * 0.3), lambda: LaggedStart(*[Create(s_) for s_ in steam], lag_ratio=0.3))

    def idle(scene, t):
        scene.play(*[s_.animate(rate_func=rate_functions.there_and_back).shift(UP * 0.3).set_opacity(0.2) for s_ in steam],
                   Wiggle(hero[1], scale_value=1.05, rotation_angle=0.03), run_time=max(t, 0.1))
    b.idle = idle
    return b


def b_ingredients(d, lang, topic):
    b = B()
    cards = []
    for it in d["items"]:
        box = RoundedRectangle(corner_radius=0.25, width=5.3, height=1.4, fill_color=WHITE, fill_opacity=1,
                               stroke_color="#FFB74D", stroke_width=5)
        ic = E(it["emoji"], 0.95)
        if lang == "en":  # quantity in small red above the ingredient name
            n = KT(it["name"], 40, INK, max_w=4.0, outline=False)
            txt = VGroup(KT(it["qty"], 30, "#C62828", outline=False), n).arrange(DOWN, aligned_edge=LEFT, buff=0.04) \
                if it["qty"] else VGroup(n)
        else:
            import textwrap
            txt = KT("\n".join(textwrap.wrap(it["line"], 22)[:2]), 34, INK, max_w=4.0, outline=False)
        if txt.height > 1.2:
            txt.scale_to_fit_height(1.2)
        row = VGroup(ic, txt).arrange(RIGHT, buff=0.3)
        row.move_to(box).align_to(box.get_left() + RIGHT * 0.25, LEFT)
        cards.append(VGroup(box, row))
    grid = VGroup(*cards).arrange_in_grid(cols=2, buff=(0.35, 0.3)).move_to([CX, CY - 0.2, 0])
    head = KT("Ingredients" if lang == "en" else "सामग्री", 70, "#C62828").next_to(grid, UP, buff=0.35)
    b.mobs.add(head, grid)
    b.at(0, lambda: FadeIn(head, shift=DOWN * 0.3))
    for k, c in enumerate(cards):
        b.at(1 + k, lambda c=c: AnimationGroup(pop(c[0]), pop(c[1][0]), FadeIn(c[1][1], shift=LEFT * 0.2)))
    return b


def _action_motion(code: str, m) -> list:
    """A short motion that fits the cooking action (used repeatedly while the step is explained)."""
    if code == "1f373":  # pan: shake
        return [m.animate(rate_func=rate_functions.wiggle).shift(RIGHT * 0.25)]
    if code == "1f52a":  # knife: chop
        return [m.animate(rate_func=rate_functions.there_and_back).rotate(-0.5).shift(DOWN * 0.2)]
    if code == "1f963":  # bowl: stir
        return [m.animate(rate_func=rate_functions.wiggle).rotate(0.25)]
    return [m.animate(rate_func=rate_functions.there_and_back).shift(UP * 0.25)]


def b_step(d, lang, topic):
    b = B()
    badge = VGroup(RoundedRectangle(corner_radius=0.3, width=2.6, height=0.8, fill_color="#C62828", fill_opacity=1,
                                    stroke_width=0),
                   KT(("Step" if lang == "en" else "स्टेप") + f" {d['n']}/{d['total']}", 40, WHITE, outline=False))
    badge[1].move_to(badge[0])
    disc = Circle(radius=1.45, fill_color=WHITE, fill_opacity=1, stroke_color="#FFB74D", stroke_width=8)
    main = E(d["icons"][0], 1.8).move_to(disc)
    side = E(d["icons"][1], 0.9).move_to(disc.get_corner(DOWN + RIGHT) + LEFT * 0.15 + UP * 0.15) if len(d["icons"]) > 1 else VGroup()
    left = VGroup(disc, main, side)
    words = d["text"]
    width = 26 if lang == "en" else 24
    import textwrap
    lines = textwrap.wrap(words, width)
    size = 46 if len(lines) <= 4 else 40 if len(lines) <= 6 else 34
    lines = textwrap.wrap(words, int(width * 44 / size))
    txt = KT("\n".join(lines[:9]), size, INK, max_w=7.0, outline=False)
    panel = RoundedRectangle(corner_radius=0.3, width=txt.width + 0.6, height=txt.height + 0.5, fill_color=WHITE,
                             fill_opacity=0.9, stroke_width=0)
    txt.move_to(panel)
    right = VGroup(panel, txt)
    body = VGroup(left, right).arrange(RIGHT, buff=0.6)
    timer = VGroup()
    if d.get("minutes"):
        ring_bg = Circle(radius=0.55, stroke_color="#E0E0E0", stroke_width=10)
        ring = Arc(radius=0.55, start_angle=math.pi / 2, angle=-2 * math.pi + 1e-3, stroke_color="#43A047", stroke_width=10)
        lab = KT(f"{d['minutes']} min", 30, INK, outline=False).next_to(ring_bg, DOWN, buff=0.1)
        timer = VGroup(ring_bg, ring, lab)
        timer.next_to(disc, DOWN, buff=0.25)
    VGroup(badge, VGroup(body, timer)).arrange(DOWN, buff=0.4).move_to([CX, CY - 0.1, 0])
    timer_target = timer.copy() if len(timer) else None
    b.mobs.add(badge, body, timer)
    b.at(0, lambda: FadeIn(badge, shift=DOWN * 0.3), lambda: pop(disc), lambda: pop(main),
         *([lambda: pop(side)] if len(side) else []))
    b.at(1, lambda: FadeIn(right, shift=LEFT * 0.3), *([lambda: FadeIn(VGroup(timer[0], timer[2]))] if len(timer) else []))

    def idle(scene, t):
        if t < 0.6:
            pause_(scene, t)
            return
        anims = []
        if len(timer):
            anims.append(Create(timer[1], rate_func=rate_functions.linear))
        reps = max(1, int(t // 1.4))
        per = t / reps
        for r in range(reps):
            scene.play(*_action_motion(d["icons"][0], main), *(anims if r == 0 else []), run_time=per)
    b.idle = idle
    return b


def pause_(scene, t):
    if t > 1 / 60:
        scene.wait(t)


def b_recipe_final(d, lang, topic):
    b = B()
    hero = _plate(d["emoji"], 2.6)
    msg = KT("Enjoy!" if lang == "en" else "मज़े से खाइए!", 110, "#C62828")
    VGroup(hero, msg).arrange(DOWN, buff=0.35).move_to([CX, CY + 0.1, 0])
    sparkles = VGroup(*[Star(n=4, outer_radius=0.28, inner_radius=0.09, fill_color="#FFD54F", fill_opacity=1, stroke_width=0)
                        .move_to(hero.get_center() + np.array([2.3 * math.cos(a), 1.5 * math.sin(a), 0]))
                        for a in np.linspace(0, 2 * math.pi, 7, endpoint=False)])
    b.mobs.add(hero, msg, sparkles)
    b.at(0, lambda: pop(hero))
    b.at(1, lambda: FadeIn(msg, shift=UP * 0.4, scale=0.6), lambda: LaggedStart(*[pop(s_) for s_ in sparkles], lag_ratio=0.08))
    return b


def build(job) -> B:
    t, d, lang, topic = job["type"], job["data"], job["lang"], job["topic"]
    if t == "quiz":
        return b_quiz(d, lang, topic, job["shown_parts"][0])
    if t == "count_quiz":
        return b_count_quiz(d, lang, topic, job["shown_parts"][0])
    return globals()[f"b_{t}"](d, lang, topic)


# --------------------------------------------------------------------------- scene
class KidsScene(Scene):
    job: dict = {}

    def construct(self):
        j = self.job
        rng = random.Random(j.get("seed", 0))
        bg, movers = scenery(j["topic"], rng)
        self.add(bg)
        for m, f in movers:
            m.add_updater(f)
        persist = [bg]
        env = voice_envelope(j["wav"], j["fps"])
        built = build(j)
        times = j["part_times"]
        cue_times = sorted({times[p] for p, _ in built.events if p < len(times)})
        mascot = Presenter(j.get("mascot", "kids"), "#FF7043", env, j["fps"], cue_times,
                           wave_hello=j["type"] in ("intro", "outro", "recipe_intro", "recipe_final"))
        mascot.place(3.5, np.array([7.0, -4.05, 0]))
        mascot.add_updater(lambda m: m.tick(self.time))
        self.add(mascot)
        persist.append(mascot)
        fit_safe_area(built.mobs)
        self.report = layout_report(built)

        duration = float(j["duration"])
        events = sorted(((times[p] if p < len(times) else times[-1]), fs) for p, fs in built.events)
        k = 0
        while k < len(events):
            t0 = events[k][0]
            group = []
            while k < len(events) and abs(events[k][0] - t0) < 1e-3:
                group += events[k][1]
                k += 1
            if t0 > self.time:
                self.wait(t0 - self.time)
            nxt = events[k][0] if k < len(events) else duration - 0.6
            rt = float(np.clip(nxt - self.time - 0.05, 0.35, 1.3))
            anims = [f() for f in group]
            self.play(*anims, run_time=rt)
        remaining = duration - 0.55 - self.time
        if remaining > 0.05:
            if built.idle:
                built.idle(self, remaining)
            else:
                self.wait(remaining)
        left = max(0.2, duration - self.time)
        self.play(*[FadeOut(m) for m in self.mobjects if m not in persist], run_time=min(0.5, left))


SAFE = (-FW / 2 + 0.35, 4.9, FH / 2 - 0.2, -FH / 2 + 0.3)  # left, right (mascot), top, bottom


def fit_safe_area(m) -> None:
    """Shrink and nudge the scene content so it never touches the frame edges or the mascot."""
    if not len(m):
        return
    left, right, top, bottom = SAFE
    k = min(1.0, (right - left) / max(m.width, 1e-3), (top - bottom) / max(m.height, 1e-3))
    if k < 1.0:
        m.scale(k)
    dx = max(0.0, left - m.get_left()[0]) - max(0.0, m.get_right()[0] - right)
    dy = max(0.0, bottom - m.get_bottom()[1]) - max(0.0, m.get_top()[1] - top)
    m.shift(np.array([dx, dy, 0]))


def layout_report(built: B) -> dict:
    issues, sizes = [], []
    for t in TEXTS:
        if t not in built.mobs.get_family():
            continue
        size = t.base_size * t.height / (t.base_h or 1)
        sizes.append(round(size, 1))
        if size < 28:
            issues.append(f"text too small for kids ({size:.0f}): {t.text[:30]!r}")
    m = built.mobs
    if len(m) and (m.get_left()[0] < SAFE[0] - 0.05 or m.get_right()[0] > SAFE[1] + 0.05
                   or m.get_top()[1] > SAFE[2] + 0.05 or m.get_bottom()[1] < SAFE[3] - 0.05):
        issues.append("content outside the safe area (frame edge or mascot)")
    return {"min_text_size": min(sizes) if sizes else None, "issues": issues}


def render(job: dict) -> dict:
    out = Path(job["out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    TEXTS.clear()
    with tempfile.TemporaryDirectory() as tmp:
        cfg = {"pixel_width": job["width"], "pixel_height": job["height"], "frame_rate": job["fps"], "media_dir": tmp,
               "output_file": "scene", "disable_caching": True, "verbosity": "ERROR", "progress_bar": "none",
               "write_to_movie": True}
        with tempconfig(cfg):
            KidsScene.job = job
            scene = KidsScene()
            scene.render()
            shutil.move(str(Path(scene.renderer.file_writer.movie_file_path)), out)
            report = {**scene.report, "rendered_seconds": round(scene.time, 3)}
    out.with_suffix(".layout.json").write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    print(json.dumps(render(json.loads(Path(sys.argv[1]).read_text()))))
