"""Extra reliable sources, combined with Wikipedia into one research text:

- Wikidata (CC0): exact dates and quantities for the topic's item
- OpenStax (CC BY 4.0): peer-reviewed textbook section that best matches the topic (per-series books)
- NASA (public domain): science.nasa.gov page for space topics

Every source is optional: if one fails or nothing relevant is found, the video still uses the others."""
from __future__ import annotations

import html
import re
from functools import lru_cache

from .research import _get

WIKIDATA = "https://www.wikidata.org/w/api.php"
OPENSTAX = "https://openstax.org"
STOP = set("""a an the and or of to in on for with by is are was were be how does do why what who which it its this that
from into about their your our we you they work works explained minutes""".split())
SKIP_PROPS = {"P8687", "P2397", "P1971", "P3744", "P4103", "P1833", "P1103"}  # follower counts etc.


def _clean_html(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript|svg|figure|nav|footer|header)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</h[1-6]>|</li>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def _keywords(s: str) -> set[str]:
    return {w[:6] for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP and len(w) > 2}


# ------------------------------------------------------------------ Wikidata
def _fmt_time(v: dict) -> str | None:
    t, prec = v.get("time", ""), v.get("precision", 9)
    m = re.match(r"([+-])(\d+)-(\d\d)-(\d\d)", t)
    if not m:
        return None
    sign, y, mo, d = m.groups()
    y = int(y)
    era = " BC" if sign == "-" else ""
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
              "November", "December"]
    if prec >= 11 and mo != "00" and d != "00":
        return f"{int(d)} {months[int(mo) - 1]} {y}{era}"
    if prec == 10 and mo != "00":
        return f"{months[int(mo) - 1]} {y}{era}"
    if prec == 9:
        return f"{y}{era}"
    if prec == 8:
        return f"{y}s{era}"
    if prec == 7:
        return f"{(y - 1) // 100 + 1}th century{era}"
    return None


def wikidata_facts(wikipedia_title: str, limit: int = 22) -> tuple[str, str] | None:
    r = _get("https://en.wikipedia.org/w/api.php", {"action": "query", "prop": "pageprops", "titles": wikipedia_title,
                                                    "redirects": 1, "format": "json"})
    page = next(iter(r.json()["query"]["pages"].values()))
    qid = page.get("pageprops", {}).get("wikibase_item")
    if not qid:
        return None
    ent = _get(WIKIDATA, {"action": "wbgetentities", "ids": qid, "props": "claims|labels", "languages": "en",
                          "format": "json"}).json()["entities"][qid]
    rows, ids = [], set()
    for pid, claims in ent.get("claims", {}).items():
        if pid in SKIP_PROPS:
            continue
        for c in claims[:2]:
            if c.get("rank") == "deprecated":
                continue
            snak = c.get("mainsnak", {})
            dv = snak.get("datavalue", {})
            if dv.get("type") == "time":
                val = _fmt_time(dv["value"])
                if val:
                    rows.append((pid, val, None))
            elif dv.get("type") == "quantity":
                amt = dv["value"]["amount"].lstrip("+")
                unit = dv["value"].get("unit", "1")
                uid = unit.rsplit("/", 1)[-1] if unit != "1" else None
                rows.append((pid, amt, uid))
                if uid:
                    ids.add(uid)
            ids.add(pid)
    if not rows:
        return None
    rows = rows[:limit]
    labels: dict[str, str] = {}
    idlist = sorted(ids)
    for i in range(0, len(idlist), 50):
        got = _get(WIKIDATA, {"action": "wbgetentities", "ids": "|".join(idlist[i:i + 50]), "props": "labels",
                              "languages": "en", "format": "json"}).json().get("entities", {})
        labels.update({k: v.get("labels", {}).get("en", {}).get("value", k) for k, v in got.items()})
    name = ent.get("labels", {}).get("en", {}).get("value", wikipedia_title)
    lines = [f"- {labels.get(p, p)}: {v}{(' ' + labels.get(u, '')) if u else ''}" for p, v, u in rows]
    text = f"Facts about {name} from Wikidata:\n" + "\n".join(lines)
    return text, f"https://www.wikidata.org/wiki/{qid}"


# ------------------------------------------------------------------ OpenStax
@lru_cache(maxsize=1)
def _openstax_catalog() -> dict[str, dict]:
    items = _get(f"{OPENSTAX}/apps/cms/api/v2/pages/", {"type": "books.Book", "fields": "title,cnx_id,book_state,slug",
                                                       "limit": 250}).json()["items"]
    return {b["title"]: b for b in items if b.get("book_state") == "live" and b.get("cnx_id")}


@lru_cache(maxsize=1)
def _openstax_release() -> dict:
    return _get(f"{OPENSTAX}/rex/release.json", {}).json()


@lru_cache(maxsize=8)
def _openstax_pages(book_title: str) -> tuple[str, str, str, list[tuple[str, str, str]]]:
    book = _openstax_catalog()[book_title]
    rel = _openstax_release()
    bid = book["cnx_id"]
    ver = rel["books"][bid]["defaultVersion"]
    bjson = _get(f"{OPENSTAX}{rel['archiveUrl']}/contents/{bid}@{ver}.json", {}).json()
    tree = bjson["tree"]
    book = {**book, "slug": bjson.get("slug") or book.get("slug") or ""}
    pages = []

    def walk(n):
        for c in n.get("contents", []):
            if "contents" in c:
                walk(c)
            else:
                pages.append((re.sub(r"<[^>]+>", "", c["title"]), c["id"].rstrip("@"), c.get("slug", "")))
    walk(tree)
    return bid, ver, book.get("slug", ""), pages


def openstax_section(query: str, books: tuple[str, ...], max_chars: int = 3000) -> tuple[str, str, str] | None:
    """Best-matching textbook section (title must share at least half of the topic's key words)."""
    want = _keywords(query)
    if not want or not books:
        return None
    best = None
    for title in books:
        if title not in _openstax_catalog():
            continue
        bid, ver, bslug, pages = _openstax_pages(title)
        for ptitle, pid, pslug in pages:
            if ptitle.lower().startswith(("introduction", "key terms", "summary", "review", "critical", "index",
                                          "preface", "chapter")):
                continue
            score = len(want & _keywords(ptitle)) / len(want)
            if score >= 0.5 and (best is None or score > best[0]):
                best = (score, title, bid, ver, bslug, ptitle, pid, pslug)
    if not best:
        return None
    _, btitle, bid, ver, bslug, ptitle, pid, pslug = best
    rel = _openstax_release()
    content = _get(f"{OPENSTAX}{rel['archiveUrl']}/contents/{bid}@{ver}:{pid}.json", {}).json()["content"]
    text = _clean_html(content)
    text = re.sub(r"(?i)^.*?learning objectives.*?(?=\n)", "", text, count=1)
    if len(text) > max_chars:
        cut = text.rfind("\n", 0, max_chars)
        text = text[: cut if cut > max_chars // 2 else max_chars]
    url = f"{OPENSTAX}/books/{bslug}/pages/{pslug}"
    return f"From the OpenStax textbook '{btitle}', section '{ptitle}':\n{text}", url, btitle


# ------------------------------------------------------------------ NASA
def nasa_page(query: str, max_chars: int = 2500) -> tuple[str, str] | None:
    want = _keywords(query)
    res = _get("https://science.nasa.gov/wp-json/wp/v2/search", {"search": query, "per_page": 10}).json()
    for r in res:
        url = r.get("url", "")
        if "/apod/" in url or not want & _keywords(r.get("title", "")):
            continue  # skip astronomy-picture-of-the-day posts and unrelated pages
        page = _get(url, {})
        m = re.search(r"(?is)<main[^>]*>(.*)</main>", page.text)
        text = _clean_html(m.group(1) if m else page.text)
        lines = []
        for ln in text.splitlines():  # keep the article's own sentences; stop at "related articles" teasers
            if re.search(r"\bMin Read\b|Skywatching|^\s*(Blog|Article|Related)\b", ln):
                if lines:
                    break
                continue
            if len(ln.split()) >= 8 and "…" not in ln:
                lines.append(ln.strip())
        text = "\n".join(lines)
        if len(text) < 400:
            continue
        if len(text) > max_chars:
            cut = text.rfind("\n", 0, max_chars)
            text = text[: cut if cut > max_chars // 2 else max_chars]
        return f"From NASA ({r.get('title', '')}):\n{text}", url
    return None


def gather(wikipedia_title: str, query: str, books: tuple[str, ...] = (), nasa: bool = False,
           log=print) -> tuple[str, list[dict]]:
    """Extra source text + credits. Failures are logged and skipped."""
    parts, credits = [], []
    try:
        wd = wikidata_facts(wikipedia_title)
        if wd:
            parts.append(wd[0])
            credits.append({"name": "Wikidata", "url": wd[1], "license": "CC0"})
    except Exception as e:  # noqa: BLE001
        log(f"  Wikidata skipped: {e}")
    try:
        ox = openstax_section(query, books)
        if ox:
            parts.append(ox[0])
            credits.append({"name": f"OpenStax, {ox[2]}", "url": ox[1], "license": "CC BY 4.0"})
    except Exception as e:  # noqa: BLE001
        log(f"  OpenStax skipped: {e}")
    if nasa:
        try:
            ns = nasa_page(query)
            if ns:
                parts.append(ns[0])
                credits.append({"name": "NASA", "url": ns[1], "license": "public domain"})
        except Exception as e:  # noqa: BLE001
            log(f"  NASA skipped: {e}")
    return "\n\n".join(f"## {p}" for p in parts), credits
