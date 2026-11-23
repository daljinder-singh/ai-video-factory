"""Turn a researched source into a validated VideoScript (outline -> per-scene narration + visual spec)."""
from __future__ import annotations

import json
import re
from typing import Callable

from pydantic import BaseModel, ValidationError

from .llm import LLMError, Ollama
from .research import Source
from .specs import (CATEGORY_PREFERRED, TEMPLATE_GUIDE, TEMPLATE_MODELS, BulletList, Scene,
                    VideoScript, visual_text)

LANG_RULES = {
    "en": "Write narration in clear, simple, spoken English.",
    "hi": ("Write narration in simple spoken Hindi using Devanagari script. Write on-screen text in Hindi "
           "(Devanagari) too. Use Western digits (0-9) for numbers."),
    "hinglish": ("Write narration in conversational Hinglish: Hindi sentences in Devanagari script, keeping "
                 "technical terms in English (Latin letters), like 'Photosynthesis एक process है'. "
                 "Write on-screen text in English. Use Western digits (0-9) for numbers."),
}
WORDS = {"en": (35, 110), "hi": (30, 120), "hinglish": (30, 120)}

NUM_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")


def _norm_num(s: str) -> str:
    s = s.replace(",", "").rstrip(".")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


CENTURY_RE = re.compile(r"(\d+)\s*(?:st|nd|rd|th)[\s-]+(century|millennium)", re.I)


def numbers_in(text: str) -> set[str]:
    nums = {_norm_num(m) for m in NUM_RE.findall(text)}
    # centuries are tracked separately so "1st century" can't hide behind the small-number exemption
    nums |= {f"{n} {unit.lower()}" for n, unit in CENTURY_RE.findall(text)}
    return nums


def unsupported_numbers(text: str, source_numbers: set[str]) -> list[str]:
    """Numbers/centuries in text that do not appear in the source. Small integers (0-10) are allowed
    (counting words like 'two steps'), but never as part of a century."""
    bad = []
    for m in CENTURY_RE.finditer(text):
        if f"{m.group(1)} {m.group(2).lower()}" not in source_numbers and m.group(0) not in bad:
            bad.append(m.group(0))
    stripped = CENTURY_RE.sub(" ", text)
    for n in sorted({_norm_num(m) for m in NUM_RE.findall(stripped)}):
        if n in source_numbers:
            continue
        if n.isdigit() and int(n) <= 10:
            continue
        bad.append(n)
    return bad


def _year_key(when: str) -> float | None:
    """Sortable year for a timeline label: '250 BC' -> -250, '5th century AD' -> 450, '1494' -> 1494."""
    w = when.lower().replace("–", "-")
    bc = "bc" in w or "bce" in w
    m = CENTURY_RE.search(w)
    if m:
        c = int(m.group(1))
        year = (c - 1) * 100 + 50 if m.group(2).lower() == "century" else (c - 1) * 1000 + 500
    else:
        m = re.search(r"\d+", w.replace(",", ""))
        if not m:
            return None
        year = int(m.group(0))
    return -year if bc else year


def timeline_problems(events: list, source_text: str, source_numbers: set[str]) -> list[str]:
    """Every date must be in the source (no small-number exemption)."""
    low = source_text.lower()
    bad = []
    for e in events:
        when = e.when.strip()
        if when.lower() in low:
            continue
        cents = {f"{n} {u.lower()}" for n, u in CENTURY_RE.findall(when)}
        nums = {_norm_num(x) for x in NUM_RE.findall(CENTURY_RE.sub(" ", when))}
        if (cents or nums) and cents <= source_numbers and nums <= source_numbers:
            continue
        bad.append(when)
    return bad


def _clean_narration(text: str) -> str:
    text = re.sub(r"[*_#`>\[\]]", "", text)
    text = re.sub(r"^(scene|section)\s*\d+\s*[:\-.]\s*", "", text.strip(), flags=re.I)
    text = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", text)  # emoji
    return re.sub(r"\s+", " ", text).strip()


def _word_count(text: str) -> int:
    return len(text.split())


def _strip_max_length(node):
    """Remove maxLength so Ollama never cuts text mid-word; length is checked by pydantic instead."""
    if isinstance(node, dict):
        return {k: _strip_max_length(v) for k, v in node.items() if k != "maxLength"}
    if isinstance(node, list):
        return [_strip_max_length(v) for v in node]
    return node


def _schema_without_template(model: type[BaseModel]) -> dict:
    schema = model.model_json_schema()
    schema["properties"].pop("template", None)
    schema["required"] = [r for r in schema.get("required", []) if r != "template"]
    return _strip_max_length(schema)


def _limits_text(model: type[BaseModel]) -> str:
    """Human-readable character limits for the prompt, e.g. 'heading <= 40 chars; items: each <= 70 chars'."""
    schema = model.model_json_schema()
    defs = schema.get("$defs", {})
    out = []

    def walk(props: dict, prefix: str = ""):
        for name, spec in props.items():
            if name in ("template", "language"):
                continue
            spec = defs.get(spec.get("$ref", "").split("/")[-1], spec) if "$ref" in spec else spec
            if spec.get("type") == "array":
                item = spec.get("items", {})
                item = defs.get(item.get("$ref", "").split("/")[-1], item) if "$ref" in item else item
                if "maxLength" in item:
                    out.append(f"{prefix}{name}: each <= {item['maxLength']} chars")
                elif "properties" in item:
                    walk(item["properties"], f"{prefix}{name}[].")
            elif "maxLength" in spec:
                out.append(f"{prefix}{name} <= {spec['maxLength']} chars")

    walk(schema["properties"])
    return "; ".join(out)


DANGLING = {"a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "by", "as", "at", "from",
            "that", "which", "is", "are", "its", "their", "your"}


def smart_trim(text: str, limit: int) -> str:
    """Shorten at a word boundary without leaving a dangling word or open bracket/operator."""
    text = text.strip()
    if len(text) <= limit:
        return text
    words, out = text.split(), ""
    for w in words:
        if len(f"{out} {w}".strip()) > limit:
            break
        out = f"{out} {w}".strip()
    toks = out.split()
    while toks and (toks[-1].lower().strip(",;:") in DANGLING or re.search(r"[(\[=+\-/,;:]$", toks[-1])):
        toks.pop()
    out = " ".join(toks).rstrip(",;:")
    if out.count("(") > out.count(")"):
        out = out[: out.rfind("(")].rstrip()
    return out or text[:limit]


def _tidy_visual(raw: dict) -> dict:
    """Small deterministic clean-ups of model output before validation."""
    if isinstance(raw.get("steps"), list):  # boxes are already numbered on screen
        raw["steps"] = [re.sub(r"^\s*step\s*\d+\s*[:.\-–]\s*", "", str(x), flags=re.I) for x in raw["steps"]]
    for key in ("items", "points", "steps", "stages", "nodes"):
        if isinstance(raw.get(key), list):
            raw[key] = [str(x).strip().rstrip(".") for x in raw[key]]
    return raw


def _repair_lengths(raw: dict, err: ValidationError) -> dict:
    """Trim fields that are too long (at word boundaries) using pydantic's error locations."""
    for e in err.errors():
        if e["type"] != "string_too_long":
            continue
        loc = [x for x in e["loc"]]
        node = raw
        for key in loc[:-1]:
            node = node[key]
        node[loc[-1]] = smart_trim(str(node[loc[-1]]), e["ctx"]["max_length"])
    return raw


class ScriptWriter:
    def __init__(self, llm: Ollama, language: str = "en", min_scenes: int = 6, max_scenes: int = 9,
                 log: Callable[[str], None] = print):
        self.llm, self.language, self.log = llm, language, log
        self.min_scenes, self.max_scenes = min_scenes, max_scenes

    def _system(self, source: Source) -> str:
        # Identical for every call so Ollama can reuse the cached prompt prefix.
        return (
            "You are the writer of a high-quality educational YouTube explainer channel.\n"
            "STRICT RULES:\n"
            "- Use ONLY facts stated in the SOURCE below. Never invent statistics, dates, numbers, names or claims.\n"
            "- If the source does not state a number, do not use a number.\n"
            "- Explain simply for a curious general audience, with concrete examples from the source.\n"
            f"SOURCE (Wikipedia: {source.title}):\n\"\"\"\n{source.text}\n\"\"\""
        )

    # ---------- step 1: outline ----------
    def outline(self, source: Source, category: str, brief: str = "") -> dict:
        allowed = list(TEMPLATE_GUIDE)
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "hook": {"type": "string"},
                "description": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "heading": {"type": "string"},
                            "template": {"type": "string", "enum": allowed},
                            "key_points": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["heading", "template", "key_points"],
                    },
                },
            },
            "required": ["title", "hook", "description", "tags", "scenes"],
        }
        guide = "\n".join(f"- {k}: {v}" for k, v in TEMPLATE_GUIDE.items())
        prefer = ", ".join(CATEGORY_PREFERRED.get(category, []))
        user = (
            f"Plan a {self.min_scenes}-{self.max_scenes} scene explainer video about \"{source.title}\" "
            f"(category: {category}).\n"
            "Fields:\n"
            "- title: catchy but accurate YouTube title, max 70 characters, in English\n"
            + (f"SERIES BRIEF (follow it): {brief}\n" if brief else "") +
            "- hook: 2-4 word thumbnail text, in English\n"
            "- description: 2-3 sentence YouTube description of what viewers learn, in English\n"
            "- tags: 8-12 search keywords, in English\n"
            "- scenes: logical story order. Scene 1 template MUST be title_card. Last scene template MUST be summary. "
            "Each scene has a heading (a specific on-screen title of max 6 words, never a template name), "
            "a visual template, and 2-4 key_points taken from the source.\n"
            f"Visual templates:\n{guide}\n"
            f"For this category prefer: {prefer}. The video must be VISUAL: use graphic templates (graphs, charts, "
            "flows, cycles, diagrams) for most scenes, use each template at most twice, and use bullet_list at most once.\n"
            "Only choose bar_chart, big_number or timeline when the source gives the exact numbers/dates."
        )
        msgs = [{"role": "system", "content": self._system(source)}, {"role": "user", "content": user}]
        last_err = ""
        for attempt in range(3):
            try:
                data = self.llm.chat_json(msgs + ([{"role": "user", "content": last_err}] if last_err else []),
                                          schema, max_tokens=1400, temperature=0.5)
            except LLMError as e:
                last_err = f"Your previous answer was invalid: {e}. Answer again with valid, shorter JSON."
                continue
            scenes = [s for s in data.get("scenes", []) if s.get("heading") and s.get("template") in TEMPLATE_GUIDE]
            if len(scenes) < self.min_scenes - 1:
                last_err = f"You gave {len(scenes)} scenes; give {self.min_scenes}-{self.max_scenes}."
                continue
            scenes = scenes[: self.max_scenes]
            scenes[0]["template"] = "title_card"
            if scenes[-1]["template"] != "summary":
                if len(scenes) >= self.max_scenes:
                    scenes[-1]["template"] = "summary"
                else:
                    scenes.append({"heading": "Key takeaways", "template": "summary",
                                   "key_points": [p for s in scenes[1:] for p in s["key_points"][:1]][:4]})
            for sc in scenes:
                if sc["heading"].strip().lower().replace(" ", "_") in TEMPLATE_GUIDE or "title card" in sc["heading"].lower():
                    sc["heading"] = ((data.get("title") or source.title)[:40] if sc is scenes[0] else
                                     "Key takeaways" if sc["template"] == "summary" else sc["key_points"][0][:40])
            data["scenes"] = scenes
            data["title"] = (data.get("title") or source.title).strip()[:95]
            data["hook"] = " ".join((data.get("hook") or source.title).split()[:4])[:40]
            data["tags"] = [t.strip() for t in data.get("tags", []) if t.strip()][:15]
            return data
        raise LLMError(f"Could not produce a valid outline: {last_err}")

    # ---------- step 2: each scene ----------
    def scene(self, source: Source, outline: dict, i: int, source_numbers: set[str]) -> Scene:
        plan = outline["scenes"][i]
        tpl = plan["template"]
        model = TEMPLATE_MODELS[tpl]
        lo, hi = WORDS[self.language]
        n_min, n_max = (3, 5) if tpl == "title_card" else (4, 7)
        if tpl == "title_card":
            lo, hi = 22, 75
        flow = "\n".join(f"{n + 1}. {s['heading']} ({s['template']})" for n, s in enumerate(outline["scenes"]))
        schema = {
            "type": "object",
            "properties": {
                "sentences": {"type": "array", "minItems": n_min, "maxItems": n_max,
                              "items": {"type": "string", "minLength": 25, "maxLength": 240}},
                "visual": _schema_without_template(model),
            },
            "required": ["sentences", "visual"],
        }
        schema["$defs"] = schema["properties"]["visual"].pop("$defs", {})
        role = ("This is the OPENING scene: greet briefly, hook the viewer with why the topic matters, "
                "and say what the video covers." if i == 0 else
                "This is the CLOSING scene: recap the key ideas and end with a memorable final thought."
                if i == len(outline["scenes"]) - 1 else
                "Continue naturally from the previous scene; do not greet the viewer again.")
        user = (
            f"Video: \"{outline['title']}\". Scene plan:\n{flow}\n\n"
            f"Write scene {i + 1}: \"{plan['heading']}\". Key points: {plan['key_points']}\n"
            f"{role}\n{LANG_RULES[self.language]}\n"
            f"- sentences: the spoken narration as {n_min} to {n_max} complete, informative sentences "
            "(each 10-25 words), in a natural spoken style. No markdown, no scene labels.\n"
            f"- visual: content for the '{tpl}' template ({TEMPLATE_GUIDE[tpl]}). "
            f"On-screen text must be short, complete phrases (never cut off). Limits: {_limits_text(model)}. "
            "The visual must show exactly what the narration explains, in the same order."
        )
        msgs = [{"role": "system", "content": self._system(source)}, {"role": "user", "content": user}]
        feedback: list[dict] = []
        last: tuple[str, BaseModel | None] | None = None
        for attempt in range(3):
            try:
                data = self.llm.chat_json(msgs + feedback,
                                          schema, max_tokens=900, temperature=0.4 + 0.15 * attempt)
            except LLMError as e:
                feedback = [{"role": "user", "content": f"Previous answer was invalid ({e}). Reply again with valid JSON."}]
                continue
            sentences = data.get("sentences") or []
            if isinstance(sentences, str):
                sentences = [sentences]
            narration = _clean_narration(" ".join(str(x).strip() for x in sentences))
            problems = []
            visual = None
            raw = _tidy_visual({**(data.get("visual") or {}), "template": tpl})
            try:
                visual = model.model_validate(raw)
            except ValidationError as e:
                only_length = all(err["type"] == "string_too_long" for err in e.errors())
                if attempt == 2 and only_length:  # last try: trim at word boundaries instead of failing
                    try:
                        visual = model.model_validate(_repair_lengths(raw, e))
                    except (ValidationError, KeyError, IndexError, TypeError):
                        visual = None
                if visual is None:
                    problems += [f"visual.{'.'.join(map(str, err['loc']))}: {err['msg']} - rewrite it shorter as a complete phrase"
                                 if err["type"] == "string_too_long" else
                                 f"visual.{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()[:6]]
            if visual is not None and tpl == "timeline":
                wrong = timeline_problems(visual.events, source.text, source_numbers)
                if wrong:
                    problems.append(f"these timeline dates are NOT in the source: {wrong}; use only dates the source states")
                keys = [_year_key(e.when) for e in visual.events]
                if None not in keys and keys != sorted(keys):  # put events in chronological order
                    visual.events = [e for _, e in sorted(zip(keys, visual.events), key=lambda x: x[0])]
            wc = _word_count(narration)
            if wc < 20 or wc > hi + 30:  # hard limits; the prompt asks for the ideal range
                problems.append(f"narration has {wc} words; write {n_min} to {n_max} full sentences")
            bad = unsupported_numbers(narration + " " + (visual_text(visual) if visual else ""), source_numbers)
            if bad:
                problems.append(f"these numbers are NOT in the source, remove or correct them: {bad}")
            last = (narration, visual)
            if not problems:
                return Scene(index=i, heading=plan["heading"], narration=narration, visual=visual)
            self.log(f"    scene {i + 1} attempt {attempt + 1} rejected: {'; '.join(problems)[:300]}")
            feedback = [{"role": "assistant", "content": json.dumps(data, ensure_ascii=False)},
                        {"role": "user", "content": "Fix these problems and answer again:\n- " + "\n- ".join(problems)}]
        return self._fallback(i, plan, last, source_numbers)

    def _fallback(self, i: int, plan: dict, last, source_numbers: set[str]) -> Scene:
        """Deterministic repair: keep only verifiable sentences and use a safe visual."""
        narration, visual = last if last else ("", None)
        sentences = re.split(r"(?<=[.!?।])\s+", narration)
        kept = [s for s in sentences if s and not unsupported_numbers(s, source_numbers)]
        narration = " ".join(kept)
        if _word_count(narration) < 15:
            raise LLMError(f"Scene {i + 1} ({plan['heading']}) could not be written with verified facts")
        if visual is None or unsupported_numbers(visual_text(visual), source_numbers):
            pts = [smart_trim(p.rstrip("."), 70) for p in plan["key_points"]
                   if not unsupported_numbers(p, source_numbers)][:4]
            if len(pts) < 2:
                pts = [smart_trim(s.rstrip("."), 70) for s in kept[:3]]
            visual = BulletList(heading=smart_trim(plan["heading"], 40), items=pts[:4] if len(pts) >= 2 else pts * 2)
        self.log(f"    scene {i + 1}: used verified fallback ({visual.template})")
        return Scene(index=i, heading=plan["heading"], narration=narration, visual=visual)

    def write(self, source: Source, topic: str, category: str, brief: str = "") -> VideoScript:
        source_numbers = numbers_in(source.text)
        self.log("  outlining...")
        outline = self.outline(source, category, brief)
        self.log(f"  outline: {outline['title']!r}, {len(outline['scenes'])} scenes: "
                 + ", ".join(s["template"] for s in outline["scenes"]))
        scenes = []
        for i in range(len(outline["scenes"])):
            self.log(f"  writing scene {i + 1}/{len(outline['scenes'])}: {outline['scenes'][i]['heading']}")
            scenes.append(self.scene(source, outline, i, source_numbers))
        return VideoScript(
            topic=topic, category=category, language=self.language, title=outline["title"],
            hook=outline["hook"], description=outline["description"], tags=outline["tags"],
            source_title=source.title, source_url=source.url, scenes=scenes,
        )
