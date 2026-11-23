"""Fetch source material from Wikipedia. The script writer may only use facts found in this text."""
from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass

import requests

API = "https://{lang}.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "ai-video-factory/0.1 (local educational video generator)"}
SKIP_SECTIONS = {"see also", "references", "external links", "notes", "further reading",
                 "bibliography", "sources", "citations", "footnotes", "gallery"}


@dataclass
class Source:
    title: str
    url: str
    text: str  # cleaned, truncated plain text with "## Section" headings
    license: str = "CC BY-SA 4.0"

    def to_dict(self) -> dict:
        return asdict(self)


def _clean(extract: str, max_chars: int) -> str:
    out: list[str] = []
    skipping = False
    for line in extract.splitlines():
        m = re.match(r"^(=+)\s*(.*?)\s*=+$", line.strip())
        if m:
            name = m.group(2)
            level = len(m.group(1))
            if level == 2:  # top-level section decides skipping; subsections inherit it
                skipping = name.lower() in SKIP_SECTIONS
            if not skipping:
                out.append(f"\n## {name}")
            continue
        if skipping or not line.strip():
            continue
        out.append(line.strip())
    text = "\n".join(out).strip()
    text = re.sub(r"\{\\displaystyle[^}]*\}", "", text)  # leftover math markup
    text = re.sub(r"[ \t]+", " ", text)
    if len(text) > max_chars:  # cut at a paragraph boundary
        cut = text.rfind("\n", 0, max_chars)
        text = text[: cut if cut > max_chars // 2 else max_chars]
    return text


def _get(url: str, params: dict, attempts: int = 5) -> requests.Response:
    for i in range(attempts):
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if r.status_code in (429, 503) and i < attempts - 1:
            wait = float(r.headers.get("Retry-After", 0) or 0) or 5 * 2 ** i
            time.sleep(min(wait, 120))
            continue
        r.raise_for_status()
        return r
    raise RuntimeError("unreachable")


def exists(titles: list[str], lang: str = "en") -> dict[str, bool]:
    """Batch existence check (max 50 titles per request)."""
    result: dict[str, bool] = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        q = _get(API.format(lang=lang), {"action": "query", "format": "json", "redirects": 1,
                                         "titles": "|".join(chunk)}).json()["query"]
        alias = {}
        for key in ("normalized", "redirects"):
            for m in q.get(key, []):
                alias[m["from"]] = m["to"]
        found = {p["title"] for p in q["pages"].values() if "missing" not in p}
        for t in chunk:
            name = t
            while name in alias:
                name = alias[name]
            result[t] = name in found
    return result


def fetch(title: str, lang: str = "en", max_chars: int = 9000) -> Source:
    params = {
        "action": "query", "prop": "extracts|info", "inprop": "url", "explaintext": 1,
        "exsectionformat": "wiki", "redirects": 1, "format": "json", "titles": title,
    }
    r = _get(API.format(lang=lang), params)
    page = next(iter(r.json()["query"]["pages"].values()))
    if "missing" in page or not page.get("extract"):
        raise LookupError(f"Wikipedia article not found: {title!r}")
    text = _clean(page["extract"], max_chars)
    if len(text) < 1500:
        raise LookupError(f"Article {title!r} is too short to make a video from ({len(text)} chars)")
    return Source(title=page["title"], url=page["fullurl"], text=text)
