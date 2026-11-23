"""Recipes from the Wikibooks Cookbook (CC BY-SA 4.0): ingredients and steps are taken verbatim from the source."""
from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass

from ..research import HEADERS, _get

API = "https://en.wikibooks.org/w/api.php"
CATEGORIES = ["Category:Indian recipes"]


@dataclass
class Ingredient:
    text: str  # full line from the source, e.g. "3 cups whole wheat flour"
    qty: str  # "3 cups" ("" if none)
    name: str  # "whole wheat flour"


@dataclass
class Recipe:
    title: str
    url: str
    intro: str
    ingredients: list[Ingredient]
    steps: list[str]
    license: str = "CC BY-SA 4.0 (Wikibooks Cookbook)"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Recipe":
        return cls(d["title"], d["url"], d["intro"], [Ingredient(**i) for i in d["ingredients"]], d["steps"], d["license"])


FRACTIONS = "½¼¾⅓⅔⅛"
UNITS = (r"cups?|c\.|tablespoons?|tbsp\.?|tbs\.?|teaspoons?|tsp\.?|grams?|g|kg|kilograms?|ml|millilit(?:re|er)s?|"
         r"lit(?:re|er)s?|l|pounds?|lbs?\.?|ounces?|oz\.?|pinch(?:es)?|dash(?:es)?|cloves?|inch(?:es)?|"
         r"pieces?|sprigs?|bunch(?:es)?|cans?|handfuls?|sticks?|slices?|pods?|leaves|stalks?|cm|mm")
QTY_RE = re.compile(rf"^\s*((?:\d+(?:[./]\d+)?|[{FRACTIONS}])(?:\s*[-–to]+\s*(?:\d+(?:[./]\d+)?|[{FRACTIONS}]))?"
                    rf"(?:\s*[{FRACTIONS}])?)\s*(?:({UNITS})\b\.?)?\s*(?:of\s+)?(.*)$", re.I)


def parse_ingredient(line: str) -> Ingredient:
    line = re.sub(r"\s+", " ", line).strip(" -•*")
    m = QTY_RE.match(line)
    if m and m.group(3):
        qty = " ".join(x for x in (m.group(1), m.group(2)) if x).strip()
        name = m.group(3)
    else:
        qty, name = "", line
    name = re.sub(r"\s*\(.*?\)", "", name).split(",")[0].strip() or line  # short display name
    return Ingredient(line, qty, name)


def _sections(extract: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"_intro": []}
    cur = "_intro"
    for line in extract.splitlines():
        m = re.match(r"^=+\s*(.*?)\s*=+$", line.strip())
        if m:
            cur = m.group(1).lower()
            out.setdefault(cur, [])
            continue
        if line.strip():
            out.setdefault(cur, []).append(line.strip())
    return out


def list_recipes() -> list[str]:
    titles: list[str] = []
    for cat in CATEGORIES:
        r = _get(API, {"action": "query", "list": "categorymembers", "cmtitle": cat, "cmlimit": 500,
                       "cmnamespace": 102, "format": "json"})
        titles += [m["title"] for m in r.json()["query"]["categorymembers"]]
    return titles


def fetch_recipe(title: str) -> Recipe:
    r = _get(API, {"action": "query", "prop": "extracts|info", "inprop": "url", "explaintext": 1,
                   "exsectionformat": "wiki", "redirects": 1, "format": "json", "titles": title})
    page = next(iter(r.json()["query"]["pages"].values()))
    if "missing" in page or not page.get("extract"):
        raise LookupError(f"Recipe not found: {title}")
    sec = _sections(page["extract"])
    ing_key = next((k for k in sec if k.startswith("ingredient")), None)
    step_key = next((k for k in sec if k.startswith(("procedure", "preparation", "method", "directions", "instructions"))), None)
    if not ing_key or not step_key:
        raise LookupError(f"{title}: no clear ingredients/procedure sections")
    ingredients = [parse_ingredient(x) for x in sec[ing_key] if len(x) < 140]
    steps = [s for s in sec[step_key] if 8 < len(s) < 400]
    intro = " ".join(x for x in sec["_intro"] if not x.startswith(("Cookbook |", "Category"))
                     and "|" not in x)[:600]
    name = page["title"].replace("Cookbook:", "").strip()
    if not 3 <= len(ingredients) <= 20 or not 2 <= len(steps) <= 14:
        raise LookupError(f"{name}: unsuitable recipe size ({len(ingredients)} ingredients, {len(steps)} steps)")
    return Recipe(name, page["fullurl"], intro, ingredients, steps)


def pick_recipe(rng: random.Random, title: str | None = None) -> Recipe:
    if title:
        return fetch_recipe(title if title.startswith("Cookbook:") else f"Cookbook:{title}")
    titles = list_recipes()
    rng.shuffle(titles)
    last = None
    for t in titles[:12]:
        try:
            return fetch_recipe(t)
        except LookupError as e:
            last = e
    raise LookupError(f"No suitable recipe found ({last})")
