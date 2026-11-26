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
    from .series import SERIES as _SERIES

    p.add_argument("--series", choices=[*_SERIES, "random", "trending"],
                   help="make a video from a series (random topic inside it)")
    p.add_argument("--lang", dest="language", choices=["en"], help="English only")
    p.add_argument("--voice", help="Kokoro voice, e.g. af_heart, af_bella, am_michael, bf_emma, bm_george")
    p.add_argument("--quality", choices=list(QUALITY))
    p.add_argument("--speed", dest="speech_speed", type=float, help="speaking speed, e.g. 0.9 or 1.15")
    p.add_argument("--music", dest="music_path", help="optional background music file")
    p.add_argument("--burn-subs", dest="burn_subtitles", action="store_true", default=None)
    p.add_argument("--short", dest="short", action="store_true", default=None,
                   help="vertical 9:16 YouTube Short (30-45 seconds)")
    p.add_argument("--no-sfx", dest="sfx", action="store_false", default=None, help="no sound effects")
    p.add_argument("--no-music", dest="auto_music", action="store_false", default=None,
                   help="no automatic background music")
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
    p.add_argument("--upload", action="store_true", help="after making the video, upload it to YouTube as PRIVATE")
    p.add_argument("--upload-only", type=Path, metavar="FOLDER", help="upload an existing video folder (PRIVATE)")
    p.add_argument("--keep-video", action="store_true", help="keep the local video files after uploading")
    p.add_argument("--youtube-login", action="store_true", help="log in to YouTube once (opens your browser)")
    p.add_argument("--list-topics", action="store_true")
    a = p.parse_args()

    if a.youtube_login or a.upload_only:
        from .youtube import UploadError, login, upload_folder

        try:
            if a.youtube_login:
                print(f"Logged in. Uploads will go to the channel: {login()}")
            if a.upload_only:
                upload_folder(a.upload_only, delete_after=not a.keep_video)
        except UploadError as e:
            print(f"ERROR: {e}")
            return 1
        return 0
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
                                                            "presenter", "short", "sfx", "auto_music", "voice")})
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
    if a.upload:
        from .youtube import UploadError, upload_folder

        try:
            upload_folder(folder, delete_after=not a.keep_video)
        except UploadError as e:
            print(f"Video saved, but NOT uploaded: {e}")
            return 1
    if a.open:
        subprocess.Popen(["xdg-open", str(folder / "final.mp4")])
    return 0


if __name__ == "__main__":
    sys.exit(main())
