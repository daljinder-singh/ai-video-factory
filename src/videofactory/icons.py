"""Pick a fitting Lucide icon for a piece of on-screen text, deterministically from icon names and tags.

Icons: Lucide (ISC license, see assets/icons/lucide/LICENSE)."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ICON_DIR = Path(__file__).resolve().parents[2] / "assets" / "icons" / "lucide"

CATEGORY_DEFAULT = {
    "mathematics": "sigma", "science": "flask-conical", "programming": "code-xml", "finance": "coins",
    "ai": "brain-circuit", "business": "briefcase-business", "history": "landmark", "psychology": "brain",
    "technology": "cpu",
}
# variants that look like UI states rather than concepts
VARIANT = re.compile(r"-(off|x|minus|plus|check|cog|dashed|slash|question|pen|search|up|down|left|right|"
                     r"\d+|lock|open|ellipsis|alert|heart|star|arrow.*|corner.*|fold.*)$")
BANNED = {"vegan", "skull", "bomb", "swords", "sword", "biohazard", "cigarette", "beer", "wine", "martini",
          "venetian-mask", "ghost", "angry", "frown", "squirrel", "rat", "bug", "dices", "dice-1", "bone"}
STOP = set("""a an the and or of to in on for with by is are was were be been it its this that these those as at
from into than then so such can will may also which who what when where how their there they them you your we
our not no but if about more most other some any each between over under very just only one two three use used
using make makes made""".split())
# extra hints for common educational words that Lucide tags don't cover well
HINTS = {
    "interest": "percent", "principal": "piggy-bank", "deposit": "piggy-bank", "saving": "piggy-bank",
    "loan": "hand-coins", "debt": "hand-coins", "bond": "file-text", "stock": "chart-candlestick",
    "inflation": "trending-up", "growth": "trending-up", "rate": "percent", "price": "tag", "tax": "receipt",
    "bank": "landmark", "mortgage": "house", "invest": "chart-line", "profit": "trending-up", "loss": "trending-down",
    "risk": "shield-alert", "market": "store", "year": "calendar", "time": "clock", "history": "scroll-text",
    "ancient": "scroll", "empire": "crown", "king": "crown", "war": "shield", "trade": "ship", "religion": "church",
    "circle": "circle", "diameter": "diameter", "radius": "radius", "formula": "sigma", "equation": "equal",
    "number": "hash", "prime": "hash", "ratio": "divide", "probability": "dices", "statistic": "chart-bar",
    "graph": "chart-line", "geometry": "triangle", "angle": "triangle-right", "infinite": "infinity",
    "decimal": "hash", "calculat": "calculator", "computer": "monitor", "algorithm": "workflow", "data": "database",
    "network": "network", "neuron": "brain-circuit", "learn": "graduation-cap", "train": "dumbbell",
    "model": "box", "predict": "telescope", "image": "image", "vision": "eye", "language": "languages",
    "text": "text", "word": "whole-word", "code": "code-xml", "function": "square-function", "loop": "repeat",
    "memory": "brain", "plant": "sprout", "leaf": "leaf", "sun": "sun", "light": "sun", "water": "droplet",
    "cloud": "cloud", "rain": "cloud-rain", "energy": "zap", "electric": "zap", "heat": "flame", "fire": "flame",
    "earth": "earth", "planet": "earth", "space": "rocket", "star": "sparkles", "gravity": "magnet",
    "atom": "atom", "cell": "microscope", "gene": "dna", "dna": "dna", "virus": "shield-plus", "vaccin": "syringe",
    "body": "person-standing", "heart": "heart-pulse", "health": "heart-pulse", "brain": "brain", "mind": "brain",
    "emotion": "smile", "behavio": "user-round", "habit": "repeat", "bias": "scale", "decision": "split",
    "think": "lightbulb", "idea": "lightbulb", "experiment": "flask-conical", "research": "microscope",
    "physic": "orbit", "chemic": "flask-conical", "oxygen": "wind", "carbon": "factory", "air": "wind",
    "ocean": "waves", "wave": "waves", "motion": "move-right", "speed": "gauge", "measure": "ruler",
    "distance": "ruler", "map": "map", "people": "users", "person": "user-round", "customer": "users",
    "brand": "badge-check", "product": "package", "cost": "receipt", "supply": "package", "demand": "shopping-cart",
    "company": "building-2", "business": "briefcase-business", "phone": "smartphone", "internet": "globe",
    "signal": "radio-tower", "battery": "battery-charging", "solar": "sun", "security": "shield-check",
    "encrypt": "lock", "key": "key-round", "money": "banknote", "coin": "coins", "wealth": "gem",
    "evapor": "thermometer-sun", "condens": "cloud", "precipit": "cloud-rain", "collect": "waves",
    "photosynth": "sprout", "orbit": "orbit", "quantum": "atom", "print": "printer", "press": "printer",
    "self": "user-round", "motivat": "rocket", "goal": "target", "need": "list-checks", "fear": "shield-alert",
    "tecton": "earth", "transistor": "cpu", "chip": "cpu", "franchis": "store", "volcan": "mountain",
    "universe": "orbit", "nature": "trees", "world": "earth", "everyday": "house", "rule": "book-open",
    "book": "book-open", "teach": "graduation-cap", "school": "school", "question": "circle-help",
}


def _stem(w: str) -> str:
    return w[:6]


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP and len(w) > 2]


@lru_cache(maxsize=1)
def _index() -> dict[str, tuple[set[str], set[str]]]:
    tags = json.loads((ICON_DIR / "tags.json").read_text())
    idx = {}
    for svg in ICON_DIR.glob("*.svg"):
        name = svg.stem
        if name in BANNED or VARIANT.search(name):
            continue
        name_words = {p for p in name.split("-") if len(p) > 2}
        tag_words = {w for t in tags.get(name, []) for w in re.findall(r"[a-z]+", t.lower()) if len(w) > 2}
        idx[name] = (name_words, tag_words)
    return idx


def icon_for(text: str, category: str = "", avoid: set[str] | None = None) -> str:
    """Best icon name for the text (never one in `avoid`); falls back to the category's icon."""
    avoid = avoid or set()
    words = _tokens(text)
    for w in words:  # curated hints first: they are the most reliable
        for key, icon in HINTS.items():
            if w.startswith(key) and icon not in avoid and (ICON_DIR / f"{icon}.svg").exists():
                return icon
    def hit(w: str, keys: set[str]) -> bool:  # 'orbits' ~ 'orbit', 'statistics' ~ 'statistic'
        for k in keys:
            short, long_ = sorted((w, k), key=len)
            if long_.startswith(short[:max(4, len(short) - 1)]) and len(short) >= 0.75 * len(long_):
                return True
        return False

    best, best_score = None, 0.0
    for name, (nw, tw) in _index().items():
        if name in avoid:
            continue
        score = sum(3.0 for w in words if hit(w, nw)) + sum(1.0 for w in words if hit(w, tw))
        if score == 0:
            continue
        score -= 0.05 * len(name)  # prefer simple, generic icons
        if score > best_score:
            best, best_score = name, score
    if best and best_score >= 0.9:
        return best
    default = CATEGORY_DEFAULT.get(category, "lightbulb")
    return default if default not in avoid else "circle-dot"


def icons_for(texts: list[str], category: str = "") -> list[str]:
    """One icon per text, avoiding repeats inside a scene."""
    used: set[str] = set()
    out = []
    for t in texts:
        name = icon_for(t, category, used)
        used.add(name)
        out.append(name)
    return out


def icon_path(name: str) -> Path:
    return ICON_DIR / f"{name}.svg"
