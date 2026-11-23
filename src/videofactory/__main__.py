"""CLI:  python -m videofactory [options]

Examples:
  python -m videofactory                              # random topic, English
  python -m videofactory --category science --lang hinglish
  python -m videofactory --topic "Black hole" --quality medium
  python -m videofactory --resume output/videos/20261120-2300_black-hole
"""
import argparse
import subprocess
import sys
from pathlib import Path

from .config import QUALITY, Settings
from .topics import CATALOG


def main() -> int:
    p = argparse.ArgumentParser(prog="videofactory", description="Make an educational explainer video automatically.")
    p.add_argument("--topic", help="Wikipedia article title (default: random)")
    p.add_argument("--category", choices=list(CATALOG), help="random topic from this category")
    p.add_argument("--series", choices=["how", "why", "history", "money", "space", "mind", "tech", "india", "random"],
                   help="make a video from a series (random topic inside it)")
    p.add_argument("--lang", dest="language", choices=["en", "hi", "hinglish"])
    p.add_argument("--quality", choices=list(QUALITY))
    p.add_argument("--speed", dest="speech_speed", type=float, help="speaking speed, e.g. 0.9 or 1.15")
    p.add_argument("--music", dest="music_path", help="optional background music file")
    p.add_argument("--burn-subs", dest="burn_subtitles", action="store_true", default=None)
    p.add_argument("--no-presenter", dest="presenter", action="store_false", default=None,
                   help="turn off the animated cartoon presenter")
    p.add_argument("--model", dest="llm_model", help="Ollama model (default qwen3:4b)")
    p.add_argument("--workers", dest="render_workers", type=int)
    p.add_argument("--recipe", action="store_true", help="make a cooking video from a Wikibooks recipe")
    p.add_argument("--dish", help='recipe name, e.g. "Chapati" (default: random Indian recipe)')
    p.add_argument("--kids", action="store_true", help="make a video for children aged 0-5 (no AI, no internet)")
    p.add_argument("--kids-topic", choices=["colours", "shapes", "numbers", "abc", "animals", "fruits", "vehicles"],
                   help="kids topic (default: random)")
    p.add_argument("--resume", type=Path, help="continue an unfinished run folder")
    p.add_argument("--seed", type=int, help="seed for reproducible random topic choice")
    p.add_argument("--open", action="store_true", help="open the finished video")
    p.add_argument("--list-topics", action="store_true")
    a = p.parse_args()

    if a.list_topics:
        from .series import SERIES

        for cat, ts in CATALOG.items():
            print(f"{cat}: {', '.join(ts)}")
        print("\nSERIES (use --series KEY):")
        for s in SERIES.values():
            print(f"{s.key} - {s.name}: {', '.join(q for q, _ in s.topics)}")
        return 0
    settings = Settings.load(**{k: getattr(a, k) for k in ("language", "quality", "speech_speed", "music_path",
                                                            "burn_subtitles", "llm_model", "render_workers",
                                                            "presenter")})
    if a.recipe or a.dish:
        from .recipes.pipeline import make_recipe_video

        folder = make_recipe_video(settings, dish=a.dish, seed=a.seed, resume=a.resume)
    elif a.kids or a.kids_topic:
        from .kids.pipeline import make_kids_video

        folder = make_kids_video(settings, topic=a.kids_topic, lang=a.language or "en", seed=a.seed, resume=a.resume)
    else:
        from .pipeline import make_video

        folder = make_video(settings, topic=a.topic, category=a.category, resume=a.resume, seed=a.seed,
                            series=a.series)
    if a.open:
        subprocess.Popen(["xdg-open", str(folder / "final.mp4")])
    return 0


if __name__ == "__main__":
    sys.exit(main())
