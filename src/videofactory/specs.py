"""Validated scene specifications. The LLM only fills these schemas; it never writes animation code.

Each visual template has hard limits on item counts and text lengths so everything stays readable on screen.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, StringConstraints

Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=28)]
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=48)]
Line = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=70)]
Heading = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class TitleCard(BaseModel):
    template: Literal["title_card"] = "title_card"
    title: Heading
    subtitle: Line


class BulletList(BaseModel):
    template: Literal["bullet_list"] = "bullet_list"
    heading: Heading
    items: list[Line] = Field(min_length=2, max_length=4)


class ProcessFlow(BaseModel):
    template: Literal["process_flow"] = "process_flow"
    heading: Heading
    steps: list[Short] = Field(min_length=2, max_length=5)


class Cycle(BaseModel):
    template: Literal["cycle"] = "cycle"
    heading: Heading
    center: Short
    stages: list[Short] = Field(min_length=3, max_length=6)


class Comparison(BaseModel):
    template: Literal["comparison"] = "comparison"
    heading: Heading
    left_title: Short
    left_items: list[Label] = Field(min_length=1, max_length=4)
    right_title: Short
    right_items: list[Label] = Field(min_length=1, max_length=4)


class TimelineEvent(BaseModel):
    when: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=14)]
    label: Short


class Timeline(BaseModel):
    template: Literal["timeline"] = "timeline"
    heading: Heading
    events: list[TimelineEvent] = Field(min_length=2, max_length=5)


class Bar(BaseModel):
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=18)]
    value: float = Field(ge=0)


class BarChart(BaseModel):
    template: Literal["bar_chart"] = "bar_chart"
    heading: Heading
    unit: Annotated[str, StringConstraints(strip_whitespace=True, max_length=16)] = ""
    bars: list[Bar] = Field(min_length=2, max_length=6)


class BigNumber(BaseModel):
    template: Literal["big_number"] = "big_number"
    value: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=14)]
    caption: Line


class Definition(BaseModel):
    template: Literal["definition"] = "definition"
    term: Heading
    definition: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=170)]


class FormulaTerm(BaseModel):
    symbol: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8)]
    meaning: Label


class Formula(BaseModel):
    template: Literal["formula"] = "formula"
    heading: Heading
    formula: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=40)]
    terms: list[FormulaTerm] = Field(default_factory=list, max_length=4)


class CodeSnippet(BaseModel):
    template: Literal["code"] = "code"
    heading: Heading
    language: Literal["python", "javascript", "java", "c", "cpp", "pseudocode"] = "python"
    code: Annotated[str, StringConstraints(min_length=5, max_length=600)]
    caption: Line


class ConceptMap(BaseModel):
    template: Literal["concept_map"] = "concept_map"
    center: Short
    nodes: list[Short] = Field(min_length=3, max_length=6)


class Summary(BaseModel):
    template: Literal["summary"] = "summary"
    heading: Heading
    points: list[Line] = Field(min_length=2, max_length=4)


class Curve(BaseModel):
    shape: Literal["linear", "exponential", "logarithmic", "quadratic", "s_curve", "bell", "decay", "sine", "flat"]
    label: Short


class FunctionGraph(BaseModel):
    template: Literal["function_graph"] = "function_graph"
    heading: Heading
    x_label: Short
    y_label: Short
    curves: list[Curve] = Field(min_length=1, max_length=3)


class ChartPoint(BaseModel):
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=12)]
    value: float


class LineChart(BaseModel):
    template: Literal["line_chart"] = "line_chart"
    heading: Heading
    y_label: Annotated[str, StringConstraints(strip_whitespace=True, max_length=28)] = ""
    points: list[ChartPoint] = Field(min_length=3, max_length=8)


class Slice(BaseModel):
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=24)]
    value: float = Field(gt=0)


class PieChart(BaseModel):
    template: Literal["pie_chart"] = "pie_chart"
    heading: Heading
    unit: Annotated[str, StringConstraints(strip_whitespace=True, max_length=8)] = ""
    slices: list[Slice] = Field(min_length=2, max_length=6)


class Pyramid(BaseModel):
    template: Literal["pyramid"] = "pyramid"
    heading: Heading
    levels: list[Short] = Field(min_length=3, max_length=6)


class Venn(BaseModel):
    template: Literal["venn"] = "venn"
    heading: Heading
    left: Short
    right: Short
    overlap: Short


class Layer(BaseModel):
    label: Short
    nodes: int = Field(ge=1, le=6)


class Network(BaseModel):
    template: Literal["network"] = "network"
    heading: Heading
    layers: list[Layer] = Field(min_length=2, max_length=5)


Visual = Annotated[
    Union[TitleCard, BulletList, ProcessFlow, Cycle, Comparison, Timeline, BarChart, BigNumber,
          Definition, Formula, CodeSnippet, ConceptMap, Summary,
          FunctionGraph, LineChart, PieChart, Pyramid, Venn, Network],
    Field(discriminator="template"),
]

TEMPLATE_MODELS: dict[str, type[BaseModel]] = {
    m.model_fields["template"].default: m
    for m in (TitleCard, BulletList, ProcessFlow, Cycle, Comparison, Timeline, BarChart, BigNumber,
              Definition, Formula, CodeSnippet, ConceptMap, Summary, FunctionGraph, LineChart, PieChart,
              Pyramid, Venn, Network)
}

TEMPLATE_GUIDE = {
    "title_card": "opening scene: video title and a one-line hook",
    "definition": "define the core term in one sentence",
    "bullet_list": "2-4 key points or characteristics",
    "process_flow": "an ordered sequence of 2-5 steps (A then B then C)",
    "cycle": "a repeating loop of 3-6 stages around a central idea",
    "comparison": "two things contrasted side by side",
    "timeline": "2-5 dated historical events in order",
    "bar_chart": "2-6 numeric quantities compared; every number MUST appear in the source",
    "big_number": "one striking number or statistic from the source",
    "formula": "a formula written in plain text (e.g. A = P(1 + r/n)^(nt)) with its symbols explained",
    "code": "a short code example (max 12 lines) for programming topics",
    "concept_map": "a central idea connected to 3-6 related ideas or types",
    "summary": "closing recap of 2-4 takeaways",
    "function_graph": ("the SHAPE of a relationship drawn as 1-3 curves (linear, exponential, logarithmic, quadratic, "
                       "s_curve, bell, decay, sine, flat), e.g. simple vs compound growth, a bell curve, decay; no numbers"),
    "line_chart": "a quantity changing over time: 3-8 points whose values MUST all appear in the source",
    "pie_chart": "parts of a whole: 2-6 slices whose values MUST all appear in the source",
    "pyramid": "a hierarchy of 3-6 levels, BOTTOM level first (e.g. Maslow's needs, a food chain)",
    "venn": "two ideas and what they have in common (left, right, overlap)",
    "network": "2-5 layers of connected nodes that information flows through (neural networks, the internet)",
}

CATEGORY_PREFERRED = {
    "mathematics": ["function_graph", "formula", "process_flow", "line_chart", "big_number"],
    "science": ["process_flow", "cycle", "function_graph", "concept_map", "pie_chart"],
    "programming": ["code", "process_flow", "network", "comparison", "concept_map"],
    "finance": ["function_graph", "formula", "line_chart", "pie_chart", "comparison"],
    "ai": ["network", "process_flow", "function_graph", "concept_map", "timeline"],
    "business": ["function_graph", "venn", "pyramid", "pie_chart", "process_flow"],
    "history": ["timeline", "line_chart", "concept_map", "big_number", "comparison"],
    "psychology": ["pyramid", "venn", "function_graph", "concept_map", "cycle"],
    "technology": ["network", "process_flow", "timeline", "comparison", "function_graph"],
}


PURPOSES = ("hook", "setup", "explain", "reveal", "payoff", "ending")


class ScenePlan(BaseModel):
    """How a scene is staged. Filled by the planner (rules), not by the LLM; every field has a safe default."""
    camera: Literal["none", "push_in", "pull_out", "drift_left", "drift_right"] = "none"
    transition: Literal["fade", "slide", "flash", "cut"] = "fade"
    sound_effects: list[str] = Field(default_factory=list)  # e.g. ["whoosh", "pop", "impact"]
    music_mood: Literal["curious", "mysterious", "dramatic", "calm", "uplifting"] = "curious"
    presenter: bool = True
    presenter_action: Literal["idle", "point", "wave"] = "point"


class Scene(BaseModel):
    index: int
    heading: str
    narration: str
    visual: Visual
    purpose: str = "explain"  # hook | setup | explain | reveal | payoff | ending
    highlight: list[str] = Field(default_factory=list)  # key words to emphasise in captions
    plan: ScenePlan = Field(default_factory=ScenePlan)


class VideoScript(BaseModel):
    topic: str
    category: str
    language: str
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=95)]
    hook: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)]
    description: str
    tags: list[str]
    source_title: str
    source_url: str
    scenes: list[Scene] = Field(min_length=3)
    title_options: list[str] = Field(default_factory=list)
    short: bool = False  # vertical YouTube Shorts format
    quality: dict = Field(default_factory=dict)  # pre-render quality scores


def reveal_units(v: BaseModel) -> list[str]:
    """Text of each element revealed one by one (in order), used to sync reveals with narration."""
    t = v.template
    if t == "title_card":
        return [v.subtitle]
    if t == "bullet_list":
        return list(v.items)
    if t == "process_flow":
        return list(v.steps)
    if t == "cycle":
        return list(v.stages)
    if t == "comparison":
        return [v.left_title + " " + " ".join(v.left_items), v.right_title + " " + " ".join(v.right_items)]
    if t == "timeline":
        return [f"{e.when} {e.label}" for e in v.events]
    if t == "bar_chart":
        return [f"{b.label} {b.value:g}" for b in v.bars]
    if t == "big_number":
        return [v.caption]
    if t == "definition":
        return [v.definition]
    if t == "formula":
        return [f"{x.symbol} {x.meaning}" for x in v.terms] or [v.formula]
    if t == "code":
        return [v.caption]
    if t == "concept_map":
        return list(v.nodes)
    if t == "summary":
        return list(v.points)
    if t == "function_graph":
        return [c.label for c in v.curves]
    if t == "line_chart":
        return [f"{p.label} {p.value:g}" for p in v.points]
    if t == "pie_chart":
        return [f"{x.label} {x.value:g}" for x in v.slices]
    if t == "pyramid":
        return list(v.levels)
    if t == "venn":
        return [v.left, v.right, v.overlap]
    if t == "network":
        return [x.label for x in v.layers]
    return []


def visual_text(v: BaseModel) -> str:
    """All human-readable text in a visual (for fact checking)."""
    out: list[str] = []

    def walk(x):
        if isinstance(x, BaseModel):
            for k, val in x:
                if k not in ("template", "language"):
                    walk(val)
        elif isinstance(x, list):
            for i in x:
                walk(i)
        elif isinstance(x, (str, int, float)):
            out.append(str(x))

    walk(v)
    return " ".join(out)
