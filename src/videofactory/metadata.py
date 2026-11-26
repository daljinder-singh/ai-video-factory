"""YouTube metadata (title, description with chapters and source credit, tags) for manual upload."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .specs import VideoScript


def _stamp(t: float) -> str:
    t = int(t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def chapters(script: VideoScript, offsets: list[float], total: float) -> list[tuple[float, str]]:
    """YouTube rules: first chapter at 0:00, at least 3 chapters, each at least 10 seconds."""
    ends = offsets[1:] + [total]
    chs: list[tuple[float, str]] = []
    for sc, off, end in zip(script.scenes, offsets, ends):
        name = "Introduction" if sc.index == 0 else ("Summary" if sc.visual.template == "summary" else sc.heading)
        if chs and end - off < 10:
            continue  # scene shorter than 10s: it becomes part of the previous chapter
        chs.append((0.0 if not chs else off, name))
    return chs if len(chs) >= 3 else []


def build(script: VideoScript, offsets: list[float], total: float, lang_name: str) -> dict:
    chs = chapters(script, offsets, total)
    tags = []
    for t in [script.topic, script.category, *script.tags, "explained", "education"]:
        t = re.sub(r"[<>\"]", "", t).strip()
        if t and t.lower() not in {x.lower() for x in tags} and sum(len(x) + 1 for x in tags) + len(t) < 480:
            tags.append(t)
    hashtags = " ".join("#" + re.sub(r"\W", "", t.title()) for t in tags[:3])
    desc = [script.description.strip(), ""]
    if chs:
        desc += ["Chapters:", *[f"{_stamp(t)} {name}" for t, name in chs], ""]
    # licence-required credit, kept to one short line at the very bottom
    desc += [hashtags, "", f"Sources: Wikipedia \"{script.source_title}\" (CC BY-SA 4.0)"]
    return {
        "title": script.title[:100],
        "description": "\n".join(desc)[:4900],
        "tags": tags,
        "category": "Education",
        "language": lang_name,
        "chapters": [{"time": _stamp(t), "title": n} for t, n in chs],
        "privacy_recommendation": "Upload as Private first, review, then publish.",
        "made_for_kids": False,
    }


def write(meta: dict, folder: Path) -> None:
    (folder / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    text = (f"TITLE\n{meta['title']}\n\nDESCRIPTION\n{meta['description']}\n\nTAGS\n{', '.join(meta['tags'])}\n\n"
            f"CATEGORY: {meta['category']}   LANGUAGE: {meta['language']}   MADE FOR KIDS: No\n"
            "Upload thumbnail.png as the custom thumbnail and subtitles.srt under Subtitles.\n")
    if meta.get("title_options"):
        text += "\nOTHER TITLE IDEAS\n" + "\n".join(f"- {t}" for t in meta["title_options"]) + "\n"
    (folder / "youtube_upload.txt").write_text(text, encoding="utf-8")
