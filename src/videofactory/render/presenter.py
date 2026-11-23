"""Animated cartoon presenter, chosen by topic category.

Drawn entirely from Manim shapes (no external art), so it renders fast and stays identical across videos.
It lip-syncs to the narration (mouth opening follows the voice loudness), blinks, breathes, and points at
each new element when it appears on screen."""
from __future__ import annotations

import math
import wave
from dataclasses import dataclass

import numpy as np
from manim import (DOWN, LEFT, RIGHT, UP, Arc, Circle, Dot, Ellipse, Line, Polygon, Rectangle,
                   RoundedRectangle, VGroup)

INK = "#1B1B26"


@dataclass(frozen=True)
class Look:
    name: str
    kind: str  # human | robot | dome
    skin: str
    hair: str
    outfit: str
    trim: str
    accessories: tuple[str, ...]


LOOKS = {
    "science": Look("Dr. Nova", "human", "#E8B48F", "#5B3A29", "#F4F6FA", "#66BB6A", ("labcoat", "goggles")),
    "mathematics": Look("Professor Pi", "human", "#F1C7A5", "#C9CED6", "#3E5C8A", "#F06292", ("glasses", "bowtie")),
    "programming": Look("Byte", "robot", "#B8C4D6", "#4DD0E1", "#2B3245", "#FFB74D", ("antenna",)),
    "ai": Look("Aiko", "dome", "#E6EAF2", "#B388FF", "#3A3360", "#4DD0E1", ("antenna",)),
    "finance": Look("Penny", "human", "#C68A62", "#2B1B14", "#2F3B52", "#FFD54F", ("tie",)),
    "business": Look("Max", "human", "#F0C3A0", "#3B2A20", "#24564F", "#FFB74D", ("glasses", "lanyard")),
    "history": Look("Indy", "human", "#D9A47C", "#4A2F1D", "#8A6A43", "#E0A96D", ("hat", "scarf")),
    "psychology": Look("Dr. Mira", "human", "#B9785A", "#1E1410", "#7B4B6A", "#F48FB1", ("bun", "glasses")),
    "cooking": Look("Chef Tara", "human", "#C68A62", "#2B1B14", "#F7F7F2", "#E53935", ("chefhat", "neckerchief")),
    "kids": Look("Bubbles", "bear", "#B9855B", "#F4B4A4", "#FF7043", "#FFD54F", ("star",)),
    "technology": Look("Volt", "human", "#F2CDB0", "#20232E", "#33476B", "#64B5F6", ("headset", "hoodie")),
}


def voice_envelope(wav_path: str, fps: int) -> list[float]:
    """Mouth openness 0..1 per video frame, from the narration's loudness."""
    with wave.open(wav_path, "rb") as w:
        sr, n = w.getframerate(), w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
        if w.getnchannels() > 1:
            data = data.reshape(-1, w.getnchannels()).mean(axis=1)
    hop = sr / fps
    frames = int(len(data) / hop) + 1
    rms = np.array([np.sqrt(np.mean(data[int(i * hop): int((i + 1) * hop)] ** 2) + 1e-12) for i in range(frames)])
    ref = np.percentile(rms[rms > 1e-4], 90) if np.any(rms > 1e-4) else 1.0
    env = np.clip((rms / ref - 0.12) / 0.88, 0, 1)
    # light smoothing so the mouth doesn't flicker
    env = np.convolve(env, [0.25, 0.5, 0.25], mode="same")
    return [round(float(x), 3) for x in env]


class Presenter(VGroup):
    """Head is centred at the origin before placement; call .place() then .tick(t) every frame."""

    def __init__(self, category: str, accent: str, envelope: list[float], fps: int, cues: list[float],
                 wave_hello: bool = False):
        super().__init__()
        self.look = LOOKS.get(category, LOOKS["science"])
        self.accent, self.env, self.fps, self.cues = accent, envelope, fps, cues
        self.wave_hello = wave_hello
        lk = self.look
        robot = lk.kind in ("robot", "dome")

        # ---- torso + neck
        self.torso = RoundedRectangle(corner_radius=0.45, width=2.0, height=1.9, fill_color=lk.outfit,
                                      fill_opacity=1, stroke_width=0).move_to([0, -1.55, 0])
        neck = Rectangle(width=0.34, height=0.35, fill_color=lk.skin if not robot else "#7C879B",
                         fill_opacity=1, stroke_width=0).move_to([0, -0.62, 0])
        body = VGroup(self.torso, neck)
        if "labcoat" in lk.accessories:
            body.add(Polygon([-0.25, -0.7, 0], [0, -1.25, 0], [0.25, -0.7, 0], fill_color="#4B6B8C", fill_opacity=1,
                             stroke_width=0),
                     Line([-0.28, -0.72, 0], [-0.05, -1.9, 0], color="#C9D1DE", stroke_width=4),
                     Line([0.28, -0.72, 0], [0.05, -1.9, 0], color="#C9D1DE", stroke_width=4),
                     RoundedRectangle(corner_radius=0.04, width=0.36, height=0.28, stroke_color="#C9D1DE",
                                      stroke_width=3, fill_opacity=0).move_to([0.55, -1.3, 0]),
                     Line([0.48, -1.12, 0], [0.48, -1.36, 0], color=lk.trim, stroke_width=5))
        if "tie" in lk.accessories:
            body.add(Polygon([-0.22, -0.72, 0], [0.22, -0.72, 0], [0, -0.95, 0], fill_color="#F4F6FA",
                             fill_opacity=1, stroke_width=0),
                     Polygon([-0.08, -0.8, 0], [0.08, -0.8, 0], [0.13, -1.6, 0], [0, -1.75, 0], [-0.13, -1.6, 0],
                             fill_color=lk.trim, fill_opacity=1, stroke_width=0))
        if "bowtie" in lk.accessories:
            body.add(Polygon([0, -0.8, 0], [-0.26, -0.66, 0], [-0.26, -0.94, 0], fill_color=lk.trim,
                             fill_opacity=1, stroke_width=0),
                     Polygon([0, -0.8, 0], [0.26, -0.66, 0], [0.26, -0.94, 0], fill_color=lk.trim,
                             fill_opacity=1, stroke_width=0),
                     Dot([0, -0.8, 0], radius=0.06, color=lk.trim))
        if "lanyard" in lk.accessories:
            body.add(Line([-0.3, -0.72, 0], [0, -1.3, 0], color=lk.trim, stroke_width=4),
                     Line([0.3, -0.72, 0], [0, -1.3, 0], color=lk.trim, stroke_width=4),
                     RoundedRectangle(corner_radius=0.04, width=0.34, height=0.42, fill_color="#F4F6FA",
                                      fill_opacity=1, stroke_width=0).move_to([0, -1.5, 0]))
        if "scarf" in lk.accessories:
            body.add(RoundedRectangle(corner_radius=0.12, width=0.95, height=0.24, fill_color="#C0392B",
                                      fill_opacity=1, stroke_width=0).move_to([0, -0.78, 0]),
                     RoundedRectangle(corner_radius=0.08, width=0.2, height=0.55, fill_color="#C0392B",
                                      fill_opacity=1, stroke_width=0).move_to([0.25, -1.05, 0]).rotate(-0.2))
        if "neckerchief" in lk.accessories:
            body.add(Polygon([-0.32, -0.7, 0], [0.32, -0.7, 0], [0, -1.08, 0], fill_color=lk.trim, fill_opacity=1,
                             stroke_width=0),
                     *[Dot([x, y, 0], radius=0.05, color="#B0B4BC") for x in (-0.3, 0.3) for y in (-1.3, -1.6)])
        if "star" in lk.accessories:  # star badge on the t-shirt
            from manim import Star
            body.add(Star(n=5, outer_radius=0.26, inner_radius=0.12, fill_color=lk.trim, fill_opacity=1,
                          stroke_width=0).move_to([0, -1.35, 0]))
        if "hoodie" in lk.accessories:
            body.add(Arc(radius=0.55, start_angle=math.pi * 1.1, angle=math.pi * 0.8, color="#2A3A5A",
                         stroke_width=10).move_to([0, -0.78, 0]),
                     Line([-0.12, -0.9, 0], [-0.12, -1.25, 0], color="#C9D1DE", stroke_width=3),
                     Line([0.12, -0.9, 0], [0.12, -1.25, 0], color="#C9D1DE", stroke_width=3))
        if robot:
            body.add(Circle(radius=0.22, fill_color=lk.trim, fill_opacity=0.9, stroke_width=0).move_to([0, -1.4, 0]),
                     Circle(radius=0.12, fill_color="#FFFFFF", fill_opacity=0.8, stroke_width=0).move_to([0, -1.4, 0]))

        # ---- arms (pointing arm is on screen-left, toward the content)
        arm_col = lk.outfit if not robot else "#7C879B"
        hand_col = lk.skin if not robot else lk.hair
        self.shoulder_l = np.array([-0.85, -0.95, 0])
        self.arm_l = VGroup(Line(self.shoulder_l, self.shoulder_l + DOWN * 0.95, color=arm_col, stroke_width=22),
                            Circle(radius=0.14, fill_color=hand_col, fill_opacity=1, stroke_width=0)
                            .move_to(self.shoulder_l + DOWN * 1.0))
        self.arm_l_angle = 0.0
        shoulder_r = np.array([0.85, -0.95, 0])
        self.shoulder_r = shoulder_r
        self.arm_r = VGroup(Line(shoulder_r, shoulder_r + DOWN * 0.95, color=arm_col, stroke_width=22),
                            Circle(radius=0.14, fill_color=hand_col, fill_opacity=1, stroke_width=0)
                            .move_to(shoulder_r + DOWN * 1.0))
        self.arm_r_angle = 0.0

        # ---- head
        head = VGroup()
        if lk.kind == "robot":
            head.add(RoundedRectangle(corner_radius=0.18, width=1.3, height=1.12, fill_color=lk.skin, fill_opacity=1,
                                      stroke_width=0),
                     RoundedRectangle(corner_radius=0.12, width=1.05, height=0.78, fill_color="#101522",
                                      fill_opacity=1, stroke_width=0).shift(DOWN * 0.02),
                     Rectangle(width=0.12, height=0.34, fill_color="#7C879B", fill_opacity=1, stroke_width=0)
                     .move_to([-0.71, 0, 0]),
                     Rectangle(width=0.12, height=0.34, fill_color="#7C879B", fill_opacity=1, stroke_width=0)
                     .move_to([0.71, 0, 0]))
        elif lk.kind == "dome":
            head.add(Circle(radius=0.62, fill_color=lk.skin, fill_opacity=1, stroke_width=0),
                     Ellipse(width=1.0, height=0.66, fill_color="#101522", fill_opacity=1, stroke_width=0)
                     .shift(DOWN * 0.03),
                     Arc(radius=0.7, start_angle=0.25, angle=math.pi - 0.5, color=lk.hair, stroke_width=6))
        elif lk.kind == "bear":
            for x in (-0.44, 0.44):  # ears
                head.add(Circle(radius=0.21, fill_color=lk.skin, fill_opacity=1, stroke_width=0).move_to([x, 0.44, 0]),
                         Circle(radius=0.11, fill_color=lk.hair, fill_opacity=1, stroke_width=0).move_to([x, 0.44, 0]))
            head.add(Circle(radius=0.58, fill_color=lk.skin, fill_opacity=1, stroke_width=0),
                     Ellipse(width=0.6, height=0.44, fill_color="#EBCFAE", fill_opacity=1, stroke_width=0)
                     .move_to([0, -0.2, 0]),
                     Ellipse(width=0.2, height=0.13, fill_color=INK, fill_opacity=1, stroke_width=0).move_to([0, -0.08, 0]),
                     Circle(radius=0.1, fill_color="#FF8A80", fill_opacity=0.45, stroke_width=0).move_to([-0.36, -0.14, 0]),
                     Circle(radius=0.1, fill_color="#FF8A80", fill_opacity=0.45, stroke_width=0).move_to([0.36, -0.14, 0]))
        else:
            head.add(Circle(radius=0.55, fill_color=lk.skin, fill_opacity=1, stroke_width=0),
                     Circle(radius=0.1, fill_color=lk.skin, fill_opacity=1, stroke_width=0).move_to([-0.55, -0.02, 0]),
                     Circle(radius=0.1, fill_color=lk.skin, fill_opacity=1, stroke_width=0).move_to([0.55, -0.02, 0]))
            # hair cap
            head.add(Polygon(*[[0.58 * math.cos(a), 0.58 * math.sin(a) + 0.02, 0] for a in np.linspace(0.05, math.pi - 0.05, 18)],
                             [-0.5, 0.18, 0], [0.5, 0.18, 0], fill_color=lk.hair, fill_opacity=1, stroke_width=0))
            if "bun" in lk.accessories:
                head.add(Circle(radius=0.24, fill_color=lk.hair, fill_opacity=1, stroke_width=0).move_to([0, 0.66, 0]))
            head.add(Circle(radius=0.09, fill_color="#FF8A80", fill_opacity=0.35, stroke_width=0).move_to([-0.33, -0.17, 0]),
                     Circle(radius=0.09, fill_color="#FF8A80", fill_opacity=0.35, stroke_width=0).move_to([0.33, -0.17, 0]))

        # ---- eyes, brows
        if robot:
            eye_col, ey = lk.hair, 0.08
            self.eyes = VGroup(*[RoundedRectangle(corner_radius=0.05, width=0.2, height=0.2, fill_color=eye_col,
                                                  fill_opacity=1, stroke_width=0).move_to([x, ey, 0]) for x in (-0.22, 0.22)])
            brows = VGroup()
        else:
            ew, eh, ey = (0.16, 0.22, 0.12) if lk.kind == "bear" else (0.12, 0.17, 0.03)
            self.eyes = VGroup(*[Ellipse(width=ew, height=eh, fill_color=INK, fill_opacity=1, stroke_width=0)
                                 .move_to([x, ey, 0]) for x in (-0.2, 0.2)])
            for e in self.eyes:
                e.add(Dot(e.get_center() + np.array([0.025, 0.035, 0]), radius=0.018, color="#FFFFFF"))
            brows = VGroup() if lk.kind == "bear" else VGroup(*[Arc(radius=0.12, start_angle=math.pi * 0.25, angle=math.pi * 0.5, color=lk.hair if lk.hair != "#C9CED6" else "#8A929E",
                                 stroke_width=5).move_to([x, 0.2, 0]) for x in (-0.2, 0.2)])
        self.eye_h = self.eyes[0].height

        acc = VGroup()
        if "glasses" in lk.accessories:
            acc.add(*[Circle(radius=0.13, stroke_color=INK, stroke_width=3.5).move_to([x, 0.03, 0]) for x in (-0.2, 0.2)],
                    Line([-0.07, 0.04, 0], [0.07, 0.04, 0], color=INK, stroke_width=3))
        if "goggles" in lk.accessories:
            acc.add(Rectangle(width=1.12, height=0.12, fill_color="#455A64", fill_opacity=1, stroke_width=0).move_to([0, 0.33, 0]),
                    *[Circle(radius=0.13, fill_color="#81D4FA", fill_opacity=0.9, stroke_color="#455A64", stroke_width=4)
                      .move_to([x, 0.35, 0]) for x in (-0.2, 0.2)])
        if "hat" in lk.accessories:
            acc.add(Ellipse(width=1.65, height=0.3, fill_color="#B08850", fill_opacity=1, stroke_width=0).move_to([0, 0.42, 0]),
                    RoundedRectangle(corner_radius=0.15, width=0.95, height=0.42, fill_color="#B08850", fill_opacity=1,
                                     stroke_width=0).move_to([0, 0.62, 0]),
                    Rectangle(width=0.95, height=0.08, fill_color="#5D4037", fill_opacity=1, stroke_width=0).move_to([0, 0.5, 0]))
        if "chefhat" in lk.accessories:
            acc.add(RoundedRectangle(corner_radius=0.06, width=0.95, height=0.42, fill_color="#FFFFFF", fill_opacity=1,
                                     stroke_color="#D9DCE3", stroke_width=2).move_to([0, 0.62, 0]),
                    *[Circle(radius=r, fill_color="#FFFFFF", fill_opacity=1, stroke_color="#D9DCE3", stroke_width=2)
                      .move_to([x, y, 0]) for x, y, r in ((-0.3, 0.95, 0.27), (0.3, 0.95, 0.27), (0, 1.07, 0.32))])
        if "headset" in lk.accessories:
            acc.add(Arc(radius=0.62, start_angle=0.15, angle=math.pi - 0.3, color="#263238", stroke_width=7),
                    RoundedRectangle(corner_radius=0.05, width=0.14, height=0.3, fill_color="#263238", fill_opacity=1,
                                     stroke_width=0).move_to([-0.6, 0, 0]),
                    Line([-0.6, -0.12, 0], [-0.22, -0.32, 0], color="#263238", stroke_width=4),
                    Dot([-0.2, -0.32, 0], radius=0.05, color=lk.trim))
        if "antenna" in lk.accessories:
            top = 0.56 if lk.kind == "robot" else 0.62
            self.antenna_tip = Dot([0, top + 0.32, 0], radius=0.08, color=lk.trim)
            acc.add(Line([0, top, 0], [0, top + 0.28, 0], color="#7C879B", stroke_width=5), self.antenna_tip)
        else:
            self.antenna_tip = None

        # ---- mouth (rebuilt every frame from the voice envelope)
        self.mouth = self._mouth(0.0)
        self.head = VGroup(head, self.eyes, brows, acc, self.mouth)
        self.add(self.arm_r, body, self.head, self.arm_l)

    # ------------------------------------------------------------------ drawing helpers
    def _mouth(self, level: float) -> VGroup:
        lk = self.look
        if lk.kind in ("robot", "dome"):
            col = lk.hair
            heights = [0.04 + level * h for h in (0.10, 0.18, 0.24, 0.18, 0.10)]
            y = -0.2 if lk.kind == "robot" else -0.18
            return VGroup(*[Rectangle(width=0.06, height=h, fill_color=col, fill_opacity=1, stroke_width=0)
                            .move_to([-0.2 + 0.1 * i, y, 0]) for i, h in enumerate(heights)])
        if level < 0.08:
            return VGroup(Arc(radius=0.14, start_angle=math.pi * 1.15, angle=math.pi * 0.7, color=INK, stroke_width=5)
                          .move_to([0, -0.24, 0]))
        h = 0.05 + 0.17 * level
        m = Ellipse(width=0.2 + 0.05 * level, height=h, fill_color="#5A1F24", fill_opacity=1, stroke_color=INK,
                    stroke_width=3).move_to([0, -0.25, 0])
        tongue = Ellipse(width=0.11, height=h * 0.35, fill_color="#E57373", fill_opacity=1, stroke_width=0) \
            .move_to(m.get_bottom() + UP * h * 0.22)
        return VGroup(m, tongue)

    def place(self, height: float, bottom_right: np.ndarray) -> "Presenter":
        h0 = self.height  # height in drawing units, before scaling
        self.scale_to_fit_height(height)
        self.move_to(bottom_right + LEFT * self.width / 2 + UP * self.height / 2)
        self.unit = height / 4.6  # drawing units -> scene units
        self.offset = 0.0
        self.mouth_c0 = self.mouth.get_center().copy()
        self.eye_h = self.eyes[0].height
        self.scale_factor = height / h0  # drawing units -> scene units (same for every character)
        return self

    @staticmethod
    def _bump(t: float, start: float, length: float = 1.3) -> float:
        if t < start or t > start + length:
            return 0.0
        x = (t - start) / length
        return math.sin(math.pi * x) ** 0.6

    def tick(self, t: float) -> None:
        # breathing: move the whole character by the change in offset (never measure the centre,
        # because raised arms change the bounding box)
        bob = 0.1 * self.unit * math.sin(t * 2.1)
        self.shift(UP * (bob - self.offset))
        self.offset = bob
        # mouth from voice loudness
        i = min(int(t * self.fps), len(self.env) - 1) if self.env else -1
        level = self.env[i] if i >= 0 else 0.0
        new = self._mouth(level).scale(self.scale_factor).move_to(self.mouth_c0 + UP * bob)
        self.mouth.become(new)
        # blinking (deterministic schedule)
        phase = (t + 0.7) % 3.7
        target_h = self.eye_h * (0.12 if phase < 0.12 else 1.0)
        for e in self.eyes:
            if abs(e.height - target_h) > 1e-4:
                e.stretch_to_fit_height(target_h)
        # point at the content (screen-left) whenever a new element appears
        g = max([self._bump(t, c - 0.1) for c in self.cues] or [0.0])
        angle_l = -g * 2.2
        self.arm_l.rotate(angle_l - self.arm_l_angle, about_point=self.arm_l[0].get_start())
        self.arm_l_angle = angle_l
        # wave hello with the other arm on the title scene
        if self.wave_hello:
            w = self._bump(t, 0.3, 2.6)
            angle_r = w * (2.4 + 0.35 * math.sin(t * 9))
            self.arm_r.rotate(angle_r - self.arm_r_angle, about_point=self.arm_r[0].get_start())
            self.arm_r_angle = angle_r
        if self.antenna_tip is not None:
            self.antenna_tip.set_opacity(0.55 + 0.45 * (0.5 + 0.5 * math.sin(t * 5)))
