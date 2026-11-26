"""Today's trending topics that make good educational videos.

Signals: Google Trends daily RSS for India + Wikipedia's most-viewed articles yesterday. Each candidate is mapped to
a Wikipedia article and filtered with Wikidata "instance of" classes: entertainment, sports, politics/elections,
crimes/tragedies and living people are skipped. Topics already made (any output/videos/*/topic.json) are skipped."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

from .research import _get

WIKI = "https://en.wikipedia.org/w/api.php"
SKIP_CLASSES = {
    "Q11424", "Q5398426", "Q3464665", "Q21191270", "Q482994", "Q7366", "Q134556", "Q7889", "Q15416", "Q526877",
    "Q63952888", "Q215380", "Q5741069", "Q24856", "Q1259759",  # films, TV, music, games, bands, film series
    "Q16466010", "Q27020041", "Q500834", "Q16510064", "Q18536594", "Q1366722", "Q47345468", "Q13406554",  # sports
    "Q40231", "Q858439", "Q1076105", "Q7278", "Q7210356",  # elections, referendums, political parties
    "Q2223653", "Q21480300", "Q132821", "Q744913", "Q3839081", "Q8065", "Q178561", "Q645883", "Q1931388",  # tragedies
    "Q12870", "Q728", "Q12140",  # explosives, weapons, medications (no how-to risk)
    "Q4167410", "Q13406463", "Q4504495", "Q58863414", "Q2178147", "Q11032",  # disambiguation, lists, awards
}
SKIP_TITLE = re.compile(r"^(Main_Page|Special:|Wikipedia:|File:|Portal:|Talk:|Help:|Category:|Template:|List_of|"
                        r"Deaths_in|\d{4}(_in|$))|_\(film\)|_\(TV_series\)|_season$|_cricket|_Premier_League|XXX", re.I)
BLOCK = re.compile(r"football|cricket|basketball|baseball|hockey|tennis|athlete|player|club\b|league|tournament|"
                   r"season|match|film|movie|novel|video game|game series|television|tv series|episode|sitcom|album|"
                   r"song|single|singer|rapper|actor|actress|musician|band\b|record producer|wrestl|youtuber|"
                   r"influencer|model\b|media personality|journalist|politician|election|political party|minister|"
                   r"disambiguation|shooting|attack|murder|killing|massacre|terror|suicide|crime|criminal|scandal|"
                   r"pornograph|adult|sex|erotic|casino|gambling|betting|lottery|warship|corvette|frigate|military|"
                   r"comic|manga|anime|fictional|character|beauty pageant|reality show|award|prize ceremony|explosive|"
                   r"weapon|firearm|gun\b|drug\b|narcotic|poison", re.I)
PEOPLE_ALLOW = re.compile(r"scientist|physicist|chemist|biologist|mathematician|astronomer|inventor|engineer|"
                          r"astronaut|explorer|philosopher|economist|physician|doctor|computer scientist|"
                          r"emperor|empress|king|queen|ruler|freedom fighter|reformer|painter|architect", re.I)
CATEGORY_HINTS = [
    (r"conjecture|theorem|mathemat|equation|number|geometry|statistic", "mathematics"),
    (r"philosoph|thought experiment|ethic", "psychology"),
    (r"satellite|orbit|solar|lunar", "mathematics"),
    (r"spacecraft|space mission|planet|star|galaxy|moon|comet|asteroid|telescope|rocket", "mathematics"),
    (r"artificial intelligence|machine learning|chatbot|language model", "ai"),
    (r"software|technology|computer|internet|smartphone|app|website|semiconductor|network", "technology"),
    (r"bank|economy|economic|market|stock|currency|tax|financial|company|inflation", "finance"),
    (r"disease|virus|bacteria|species|animal|plant|medicine|vaccine|human body|protein|gene|organ|fluid|"
     r"chemical|element|physics|energy|molecule", "science"),
    (r"festival|temple|empire|dynasty|history|historic|monument|river|mountain|country|island|desert|ocean|"
     r"volcano|earthquake|climate|weather|cyclone|forest", "history"),
    (r"psycholog|behaviour|behavior|mental|emotion", "psychology"),
]


def _google_trends_india() -> list[str]:
    try:
        r = _get("https://trends.google.com/trending/rss", {"geo": "IN"})
        root = ET.fromstring(r.content)
        return [i.findtext("title") for i in root.iter("item") if i.findtext("title")]
    except Exception:  # noqa: BLE001
        return []


def _wikipedia_top(day: date, n: int = 120) -> list[str]:
    try:
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia.org/all-access/{day:%Y/%m/%d}"
        arts = _get(url, {}).json()["items"][0]["articles"]
        return [a["article"] for a in arts if not SKIP_TITLE.search(a["article"])][:n]
    except Exception:  # noqa: BLE001
        return []


def _search_article(query: str) -> str | None:
    res = _get(WIKI, {"action": "query", "list": "search", "srsearch": query, "srlimit": 1, "format": "json"}).json()
    hits = res.get("query", {}).get("search", [])
    return hits[0]["title"] if hits else None


def _wikidata_info(titles: list[str]) -> dict[str, dict]:
    """title -> {"classes", "living_person", "description"} (titles must be canonical Wikipedia titles)."""
    out: dict[str, dict] = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        q = _get(WIKI, {"action": "query", "prop": "pageprops", "titles": "|".join(chunk), "redirects": 1,
                        "format": "json"}).json()["query"]
        alias = {m["from"]: m["to"] for k in ("normalized", "redirects") for m in q.get(k, [])}
        qids = {p["title"]: p.get("pageprops", {}).get("wikibase_item") for p in q["pages"].values()}
        ids = [x for x in qids.values() if x]
        ents = {}
        for k in range(0, len(ids), 50):
            ents.update(_get("https://www.wikidata.org/w/api.php", {
                "action": "wbgetentities", "ids": "|".join(ids[k:k + 50]), "props": "claims|descriptions",
                "languages": "en", "format": "json"}).json().get("entities", {}))
        for t in chunk:
            canon = t
            while canon in alias:
                canon = alias[canon]
            e = ents.get(qids.get(canon) or "", {})
            claims = e.get("claims", {})
            classes = {c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") for c in claims.get("P31", [])}
            human = "Q5" in classes
            out[t] = {"title": canon, "classes": classes, "living_person": human and "P570" not in claims,
                      "human": human, "description": e.get("descriptions", {}).get("en", {}).get("value", "")}
    return out


def _done_topics(output_dir: Path) -> set[str]:
    done = set()
    for f in Path(output_dir).glob("*/topic.json"):
        try:
            done.add(json.loads(f.read_text())["title"].lower())
        except Exception:  # noqa: BLE001
            pass
    return done


def category_for(description: str, human: bool) -> str:
    if human:
        return "mathematics"  # Professor Pi presents biographies
    for pattern, cat in CATEGORY_HINTS:
        if re.search(pattern, description, re.I):
            return cat
    return "science"


def candidates(output_dir: Path, log=print) -> list[dict]:
    trends = _google_trends_india()
    top = _wikipedia_top(date.today() - timedelta(days=1))
    log(f"  trending signals: {len(trends)} Google Trends (India), {len(top)} top Wikipedia articles")
    scored: dict[str, float] = {}
    for rank, q in enumerate(trends[:25]):
        try:
            art = _search_article(q)
        except Exception:  # noqa: BLE001
            art = None
        if art and not SKIP_TITLE.search(art.replace(" ", "_")):
            scored[art] = scored.get(art, 0) + 3.0 - rank * 0.08  # India trends count most
    for rank, a in enumerate(top):
        t = a.replace("_", " ")
        scored[t] = scored.get(t, 0) + 1.5 - rank * 0.01
    info = _wikidata_info(list(scored))
    done = _done_topics(output_dir)
    out = []
    for t, score in sorted(scored.items(), key=lambda x: -x[1]):
        i = info.get(t)
        if not i or i["classes"] & SKIP_CLASSES or i["living_person"] or i["title"].lower() in done:
            continue
        desc = i["description"]
        if not i["classes"] or not desc or BLOCK.search(desc) or BLOCK.search(i["title"]):
            continue
        if i["human"]:
            if not PEOPLE_ALLOW.search(desc):
                continue  # only deceased scientists, inventors, explorers, rulers, etc.
        elif not any(re.search(pat, desc, re.I) for pat, _ in CATEGORY_HINTS):
            continue  # allow-list: must clearly belong to an educational field
        out.append({"title": i["title"], "score": round(score, 2), "description": desc,
                    "category": category_for(desc, i["human"]), "human": i["human"]})
    return out
