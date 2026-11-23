"""Turn a Wikibooks recipe into video scenes. English is taken verbatim; Hindi/Hinglish are translated line by line
by the local LLM, and any translated line whose numbers differ from the original is rejected (kept in English)."""
from __future__ import annotations

import re
from typing import Callable

from ..llm import LLMError, Ollama
from ..scriptwriter import numbers_in
from .icons import action_icon, dish_icon, ingredient_icon
from .source import Recipe

SENT = re.compile(r"(?<=[.!?])\s+")
MIN_RE = re.compile(r"(\d+)\s*(?:[-–]|to)?\s*(\d+)?\s*(?:minutes?|mins?)\b", re.I)
HOUR_RE = re.compile(r"(\d+)\s*(?:hours?|hrs?)\b", re.I)
FIXED = {
    "en": {"intro": "Today, let's make {name}!", "go": "Let's get cooking!", "need": "Here is what you need.",
           "more": "You will also need:", "step": "Step {n}.", "done": "And that's it!",
           "ready": "Your {name} is ready. Enjoy!", "bye": "Happy cooking!"},
    "hi": {"intro": "आज हम {name} बनाएँगे!", "go": "चलो, बनाना शुरू करते हैं!", "need": "इसके लिए हमें ये चीज़ें चाहिए।",
           "more": "और ये चीज़ें भी चाहिए।", "step": "स्टेप {n}।", "done": "बस, हो गया!",
           "ready": "आपका {name} तैयार है। मज़े से खाइए!", "bye": "हैप्पी कुकिंग!"},
}
FIXED["hinglish"] = FIXED["hi"]
LANG_NOTE = {
    "hi": "Translate into simple, natural spoken Hindi (Devanagari script).",
    "hinglish": ("Translate into conversational Hinglish: Hindi in Devanagari script, keeping common food and "
                 "kitchen words in English (Latin letters), e.g. 'Onion को golden होने तक fry करें'."),
}


def short_name(title: str) -> str:
    return re.split(r"\s*\(", title)[0].strip()


def minutes_in(text: str) -> int | None:
    m = MIN_RE.search(text)
    if m:
        return int(m.group(2) or m.group(1))
    h = HOUR_RE.search(text)
    return int(h.group(1)) * 60 if h else None


class Translator:
    def __init__(self, llm: Ollama, lang: str, log: Callable[[str], None] = print):
        self.llm, self.lang, self.log = llm, lang, log

    def lines(self, src: list[str]) -> list[str]:
        """Translate each line; a line is accepted only if it keeps exactly the same numbers."""
        if not src:
            return []
        schema = {"type": "object", "properties": {"lines": {"type": "array", "items": {"type": "string"},
                                                             "minItems": len(src), "maxItems": len(src)}},
                  "required": ["lines"]}
        prompt = (f"{LANG_NOTE[self.lang]} This is a cooking recipe for a YouTube video. Translate each line "
                  f"separately, keep the same order, and copy every number and fraction exactly using Western digits. "
                  "Do not add or remove information.\nLines:\n" + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(src)))
        out = list(src)
        todo = list(range(len(src)))
        for attempt in range(2):
            try:
                data = self.llm.chat_json([{"role": "user", "content": prompt}], schema,
                                          max_tokens=120 + 90 * len(src), temperature=0.2)
            except LLMError as e:
                self.log(f"    translation failed ({e}); retrying")
                continue
            got = [str(x).strip() for x in data.get("lines", [])]
            if len(got) != len(src):
                continue
            for i in list(todo):
                if got[i] and numbers_in(got[i]) == numbers_in(src[i]):
                    out[i] = got[i]
                    todo.remove(i)
            if not todo:
                break
        if todo:
            self.log(f"    kept {len(todo)} line(s) in English (numbers changed in translation)")
        return out


def build_script(recipe: Recipe, lang: str, llm: Ollama | None = None, log: Callable[[str], None] = print) -> dict:
    lang = lang if lang in ("hi", "hinglish") else "en"
    tr = Translator(llm, lang, log) if lang != "en" else None
    T = (lambda xs: tr.lines(xs)) if tr else (lambda xs: list(xs))
    fx = FIXED[lang]
    name = short_name(recipe.title)
    scenes = []

    intro_line = SENT.split(recipe.intro)[0] if recipe.intro else ""
    intro_line = intro_line if 20 < len(intro_line) < 230 else ""
    extra = T([intro_line]) if intro_line else []
    scenes.append({"type": "recipe_intro", "parts": [fx["intro"].format(name=name), *extra, fx["go"]],
                   "data": {"title": recipe.title, "name": name, "emoji": dish_icon(recipe.title),
                            "subtitle": "Easy recipe" if lang == "en" else "आसान रेसिपी"}})

    log("  ingredients...")
    ing_lines = T([i.text for i in recipe.ingredients])
    for page in range(0, len(recipe.ingredients), 6):
        chunk = list(range(page, min(page + 6, len(recipe.ingredients))))
        parts = [fx["need"] if page == 0 else fx["more"]] + [ing_lines[i] for i in chunk]
        items = [{"qty": recipe.ingredients[i].qty, "name": recipe.ingredients[i].name, "line": ing_lines[i],
                  "emoji": ingredient_icon(recipe.ingredients[i].name)} for i in chunk]
        scenes.append({"type": "ingredients", "parts": parts, "data": {"items": items, "lang": lang}})

    for n, step in enumerate(recipe.steps, 1):
        log(f"  step {n}/{len(recipe.steps)}")
        sentences = [s for s in SENT.split(step) if s.strip()]
        said = T(sentences)
        mentioned = next((ing for ing in recipe.ingredients if ing.name and len(ing.name) > 2
                          and ing.name.lower().split()[-1] in step.lower()), None)
        icons = [action_icon(step)]
        if mentioned and ingredient_icon(mentioned.name) not in icons:
            icons.append(ingredient_icon(mentioned.name))
        scenes.append({"type": "step", "parts": [fx["step"].format(n=n), *said],
                       "data": {"n": n, "total": len(recipe.steps), "text": " ".join(said), "icons": icons,
                                "minutes": minutes_in(step)}})

    scenes.append({"type": "recipe_final", "parts": [fx["done"], fx["ready"].format(name=name), fx["bye"]],
                   "data": {"name": name, "emoji": dish_icon(recipe.title)}})
    for i, s in enumerate(scenes):
        s["index"] = i
    return {"kind": "recipe", "title": recipe.title, "name": name, "lang": lang, "url": recipe.url,
            "ingredients": [i.text for i in recipe.ingredients], "scenes": scenes}
