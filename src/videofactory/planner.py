"""Scene planning rules: visual variety, staging (camera / transition / sound / music / presenter), title choice and a
pre-render quality score. Deterministic and cheap, so it works well with a small local LLM."""
from __future__ import annotations

import re
from collections import Counter

from .specs import CATEGORY_PREFERRED, TEMPLATE_GUIDE, ScenePlan

BANNED_OPENERS = re.compile(r"^\s*(hello|hi\b|hey\b|welcome|today,? we|in this video|in today'?s video|let'?s (talk|learn)|"
                            r"have you ever wondered|नमस्ते|हैलो|आज हम)", re.I)
CALL_TO_ACTION = re.compile(r"\b(subscribe|like (this|the) video|hit the bell|smash (that|the) like|comment below)\b", re.I)
CLICKBAIT = re.compile(r"\b(shocking|you won'?t believe|insane|gone wrong|must watch|100%)\b", re.I)
CURIOSITY = re.compile(r"\?|^(what|why|how|imagine|picture|your|you)\b|\b(secret|hidden|really|actually|never|"
                       r"invisible|mystery|surprising)\b", re.I)

NEEDS_NUMBERS = {"bar_chart", "big_number", "timeline", "line_chart", "pie_chart"}
WIDE = {"network", "function_graph", "line_chart", "timeline", "concept_map", "cycle", "comparison", "pie_chart",
        "venn", "pyramid", "bar_chart", "code", "process_flow"}  # these use the full width: presenter steps aside
RENDER_COST = {"network": 3, "concept_map": 2, "cycle": 2, "function_graph": 2, "code": 2}  # rough relative cost
GENERAL_POOL = ["process_flow", "comparison", "concept_map", "cycle", "definition", "function_graph", "bullet_list"]


def _has_digits(points: list[str]) -> bool:
    return any(re.search(r"\d", p) for p in points)


def enforce_variety(scenes: list[dict], category: str, short: bool = False) -> list[dict]:
    """No template twice in a row, none more than twice (once in Shorts); first/last scenes keep their roles.
    Replacements are scored by fit: category preference, numbers available, render cost, recent use."""
    limit = 1 if short else 2
    counts: Counter = Counter()
    prefer = CATEGORY_PREFERRED.get(category, [])
    for i, sc in enumerate(scenes):
        tpl = sc["template"]
        fixed = i == 0 or i == len(scenes) - 1
        prev = scenes[i - 1]["template"] if i else None
        bad = (tpl == prev) or counts[tpl] >= limit or (tpl in NEEDS_NUMBERS and not _has_digits(sc.get("key_points", [])))
        if not fixed and bad:
            best, best_score = tpl, -99.0
            for cand in dict.fromkeys(prefer + GENERAL_POOL):
                if cand not in TEMPLATE_GUIDE or cand in ("title_card", "summary") or cand == prev:
                    continue
                if counts[cand] >= limit or (cand in NEEDS_NUMBERS and not _has_digits(sc.get("key_points", []))):
                    continue
                score = (3 if cand in prefer else 0) - counts[cand] * 2 - RENDER_COST.get(cand, 1) * 0.3
                if cand == "bullet_list":
                    score -= 2  # text-heavy: last resort
                if score > best_score:
                    best, best_score = cand, score
            sc["template"] = best
        counts[sc["template"]] += 1
    return scenes


def assign_purposes(scenes: list[dict]) -> None:
    n = len(scenes)
    for i, sc in enumerate(scenes):
        p = sc.get("purpose")
        if i == 0:
            p = "hook"
        elif i == n - 1:
            p = "ending"
        elif p not in ("setup", "explain", "reveal", "payoff"):
            p = "setup" if i == 1 else ("payoff" if i == n - 2 else "explain")
        sc["purpose"] = p


def plan_scenes(templates: list[str], purposes: list[str], short: bool = False,
                presenter_enabled: bool = True) -> list[ScenePlan]:
    """Stage each scene. Camera moves are used selectively and never repeat back to back."""
    plans: list[ScenePlan] = []
    prev_camera = "none"
    for i, (tpl, purpose) in enumerate(zip(templates, purposes)):
        camera, transition, sfx, mood = "none", "fade", [], "curious"
        presenter = presenter_enabled and not short and tpl not in WIDE
        action = "point"
        if purpose == "hook":
            camera, transition, sfx, mood, action = "push_in", "cut", ["impact"], "mysterious", "wave"
        elif purpose == "reveal" or tpl == "big_number":
            camera, sfx, mood = "pull_out", ["impact"], "dramatic"
        elif purpose == "payoff":
            camera, sfx, mood = "push_in", ["shimmer"], "uplifting"
        elif purpose == "ending":
            camera, transition, sfx, mood, action = "pull_out", "fade", ["shimmer"], "calm", "wave"
            presenter = presenter_enabled and not short
        else:  # setup / explain: gentle motion on alternate scenes, pops for each new element
            camera = ["drift_left", "none", "push_in", "none", "drift_right"][i % 5]
            sfx = ["pop"]
            mood = "curious"
        if camera == prev_camera and camera != "none":
            camera = "none"
        if i > 0 and transition == "fade" and purpose in ("explain", "setup") and i % 3 == 0:
            transition = "slide"
        if i > 0:
            sfx = ["whoosh"] + sfx if transition in ("slide", "cut") else sfx
        plans.append(ScenePlan(camera=camera, transition=transition, sound_effects=sfx, music_mood=mood,
                               presenter=presenter, presenter_action=action))
        prev_camera = camera
    return plans


def pick_title(options: list[str], topic: str, fallback: str) -> str:
    """Curious but honest: prefer questions / 'you' framing, the topic's words, 30-70 chars; reject clickbait."""
    topic_words = {w for w in re.findall(r"[a-z]+", topic.lower()) if len(w) > 3}
    best, best_score = fallback, -99.0
    for t in options + [fallback]:
        t = t.strip().strip('"')
        if not 10 <= len(t) <= 95 or CLICKBAIT.search(t):
            continue
        score = 0.0
        score += 2 if CURIOSITY.search(t) else 0
        score += 2 if topic_words & set(re.findall(r"[a-z]+", t.lower())) else -3  # must be about the topic
        score += 1 if 30 <= len(t) <= 70 else -1
        score -= 1 if t.isupper() else 0
        if score > best_score:
            best, best_score = t, score
    return best[:95]


def _first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?।])\s+", text.strip())[0] if text.strip() else ""


def quality_score(scenes: list, short: bool = False) -> dict:
    """1-10 per category, rule-based. scenes: list of Scene (pydantic) objects."""
    def clamp(x):
        return max(1, min(10, round(x)))

    hook = _first_sentence(scenes[0].narration)
    hs = 6 + (2 if CURIOSITY.search(hook) else 0) + (1 if len(hook.split()) <= 18 else -2)
    hs -= 6 if BANNED_OPENERS.search(hook) else 0
    purposes = [s.purpose for s in scenes]
    story = 4 + 2 * (purposes[0] == "hook") + 2 * (purposes[-1] == "ending") + 2 * bool({"reveal", "payoff"} & set(purposes))
    tpls = [s.visual.template for s in scenes]
    repeats = sum(1 for a, b in zip(tpls, tpls[1:]) if a == b)
    variety = 10 * len(set(tpls)) / len(tpls) - 3 * repeats - 2 * tpls.count("bullet_list")
    sent = [s for sc in scenes for s in re.split(r"(?<=[.!?।])\s+", sc.narration) if s.strip()]
    avg = sum(len(s.split()) for s in sent) / max(len(sent), 1)
    clarity = 10 - max(0, avg - 20) * 0.6 - max(0, 7 - avg) * 0.8
    rel = []
    for sc in scenes:
        words = {w for w in re.findall(r"[a-z]+", sc.heading.lower()) if len(w) > 3}
        rel.append(1 if not words or words & set(re.findall(r"[a-z]+", sc.narration.lower())) else 0)
    relevance = 4 + 6 * sum(rel) / len(rel)
    words_per = [len(sc.narration.split()) for sc in scenes]
    lo, hi = (12, 45) if short else (25, 110)
    pacing = 10 - 2 * sum(1 for w in words_per if not lo <= w <= hi)
    last = scenes[-1].narration
    ending = 6 + (2 if _first_sentence(last[::-1][::-1]) and last.rstrip().endswith(("!", "?", ".")) else 0)
    ending -= 5 if CALL_TO_ACTION.search(last) else 0
    ending += 2 if CURIOSITY.search(re.split(r"(?<=[.!?])\s+", last.strip())[-1]) else 0
    scores = {"hook": clamp(hs), "story": clamp(story), "variety": clamp(variety), "clarity": clamp(clarity),
              "relevance": clamp(relevance), "pacing": clamp(pacing), "ending": clamp(ending)}
    scores["overall"] = round(sum(scores.values()) / len(scores), 1)
    return scores
