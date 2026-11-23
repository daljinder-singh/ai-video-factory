from manim import *

class Smoke(Scene):
    def construct(self):
        title = Text("Photosynthesis", font_size=64)
        hi = Text("प्रकाश संश्लेषण", font="Noto Sans Devanagari", font_size=48).next_to(title, DOWN)
        sun = Circle(radius=0.6, color=YELLOW, fill_opacity=1).to_corner(UL)
        leaf = Ellipse(width=2.5, height=1.2, color=GREEN, fill_opacity=0.8).to_edge(DOWN)
        arrow = Arrow(sun.get_center(), leaf.get_top(), color=YELLOW)
        self.play(Write(title), FadeIn(hi))
        self.play(FadeIn(sun), GrowFromCenter(leaf))
        self.play(GrowArrow(arrow))
        self.wait(0.5)
