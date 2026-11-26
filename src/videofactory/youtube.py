"""Upload a finished video folder to YouTube with the official YouTube Data API v3.

Always uploads as PRIVATE. Never uploads the same folder twice (youtube.json records the upload).
Setup: secrets/client_secret.json (Google Cloud OAuth client, type "Desktop app"); first use opens a browser
login once (python -m videofactory --youtube-login), then secrets/token.json is reused."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from .config import ROOT

SECRETS = ROOT / "secrets"
CLIENT = SECRETS / "client_secret.json"
TOKEN = SECRETS / "token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
CATEGORY_IDS = {"Education": "27", "Howto & Style": "26", "Science & Technology": "28", "Entertainment": "24"}
LANG_CODES = {"English": "en", "Hindi": "hi", "Hindi (Hinglish)": "hi"}


class UploadError(RuntimeError):
    pass


BIG_FILES = ["final.mp4", "music.wav"]
BIG_DIRS = ["scenes", "assembly", "audio"]


def cleanup_local(folder: Path, log=print) -> None:
    """Delete the large media files of an uploaded video; keep youtube.json, thumbnail, script and metadata."""
    import shutil

    rec = folder / "youtube.json"
    if not rec.exists():
        return  # never delete anything that is not confirmed uploaded
    freed = 0
    for name in BIG_FILES:
        f = folder / name
        if f.exists():
            freed += f.stat().st_size
            f.unlink()
    for name in BIG_DIRS:
        d = folder / name
        if d.is_dir():
            freed += sum(p.stat().st_size for p in d.rglob("*") if p.is_file())
            shutil.rmtree(d)
    if freed:
        log(f"  deleted local video files ({freed / 1e6:.0f} MB freed); kept youtube.json, thumbnail and texts")


def _check_client() -> None:
    if not CLIENT.exists() or CLIENT.stat().st_size == 0:
        raise UploadError(f"{CLIENT} is missing or empty. Download the OAuth client JSON (type: Desktop app) from "
                          "Google Cloud Console > APIs & Services > Credentials and save it there.")
    try:
        data = json.loads(CLIENT.read_text())
    except json.JSONDecodeError as e:
        raise UploadError(f"{CLIENT} is not valid JSON ({e}). Re-download it from Google Cloud Console.") from e
    if "installed" not in data:
        raise UploadError(f"{CLIENT} is not a 'Desktop app' OAuth client (found: {list(data)}). Create an OAuth "
                          "client ID of type 'Desktop app' and download its JSON.")


def credentials(interactive: bool = True):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    _check_client()
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES) if TOKEN.exists() else None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:  # noqa: BLE001  (revoked / expired refresh token)
            creds = None
    if not creds or not creds.valid:
        if not interactive:
            raise UploadError("Not logged in to YouTube. Run once: ./run.sh --youtube-login")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True,
                                      authorization_prompt_message="Opening your browser to log in to YouTube: {url}",
                                      success_message="Login complete. You can close this tab.")
    TOKEN.write_text(creds.to_json())
    TOKEN.chmod(0o600)
    return creds


def service(interactive: bool = True):
    from googleapiclient.discovery import build

    return build("youtube", "v3", credentials=credentials(interactive), cache_discovery=False)


def login() -> str:
    yt = service(interactive=True)
    ch = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    if not ch:
        raise UploadError("Logged in, but this Google account has no YouTube channel yet. Create one on youtube.com.")
    return ch[0]["snippet"]["title"]


def upload_folder(folder: Path, log=print, delete_after: bool = True) -> dict:
    """Upload final.mp4 + metadata + thumbnail + subtitles from a run folder. Returns the youtube.json record."""
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    folder = Path(folder)
    record_file = folder / "youtube.json"
    if record_file.exists():
        rec = json.loads(record_file.read_text())
        log(f"Already uploaded: {rec['url']} (delete {record_file} to upload again)")
        if delete_after:
            cleanup_local(folder, log)
        return rec
    video, meta_file = folder / "final.mp4", folder / "metadata.json"
    qc_file = folder / "qc_report.json"
    if not video.exists() or not meta_file.exists():
        raise UploadError(f"{folder} has no final.mp4/metadata.json; make the video first")
    if qc_file.exists() and not json.loads(qc_file.read_text()).get("passed", False):
        raise UploadError(f"Quality checks FAILED for {folder}; fix the video before uploading (see qc_report.json)")
    meta = json.loads(meta_file.read_text())
    lang = LANG_CODES.get(meta.get("language", "English"), "en")
    body = {
        "snippet": {"title": meta["title"][:100], "description": meta["description"][:5000],
                    "tags": meta.get("tags", [])[:30], "categoryId": CATEGORY_IDS.get(meta.get("category"), "27"),
                    "defaultLanguage": lang, "defaultAudioLanguage": lang},
        "status": {"privacyStatus": "private",  # ALWAYS private; publish manually after reviewing
                   "selfDeclaredMadeForKids": bool(meta.get("made_for_kids", False)), "embeddable": True},
    }
    yt = service(interactive=False)
    log(f"Uploading {video.name} ({video.stat().st_size / 1e6:.0f} MB) as PRIVATE: {body['snippet']['title']!r}")
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    response, retries = None, 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                log(f"  {int(status.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and retries < 5:
                retries += 1
                time.sleep(2 ** retries)
                continue
            if e.resp.status == 403 and b"quota" in e.content.lower():
                raise UploadError("Daily YouTube API quota reached (about 6 uploads/day). Try again tomorrow.") from e
            raise UploadError(f"Upload failed: {e}") from e
    vid = response["id"]
    rec = {"id": vid, "url": f"https://youtu.be/{vid}", "studio": f"https://studio.youtube.com/video/{vid}/edit",
           "privacy": "private", "uploaded_at": datetime.now().isoformat(timespec="seconds"),
           "made_for_kids": body["status"]["selfDeclaredMadeForKids"], "warnings": []}
    record_file.write_text(json.dumps(rec, indent=2))  # write immediately so a later step can't cause a re-upload
    log(f"  uploaded: {rec['url']}")

    thumb = folder / "thumbnail.png"
    if thumb.exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/png")).execute()
            log("  thumbnail set")
        except HttpError as e:
            rec["warnings"].append("thumbnail not set (verify your channel's phone number to allow custom thumbnails)")
            log(f"  thumbnail NOT set: {e.resp.status} (channel probably needs phone verification)")
    srt = folder / "subtitles.srt"
    if srt.exists():
        try:
            yt.captions().insert(part="snippet", body={"snippet": {"videoId": vid, "language": lang, "name": "",
                                                                    "isDraft": False}},
                                 media_body=MediaFileUpload(str(srt), mimetype="application/octet-stream")).execute()
            log("  subtitles added")
        except HttpError as e:
            rec["warnings"].append(f"subtitles not added ({e.resp.status})")
            log(f"  subtitles NOT added: {e.resp.status}")
    record_file.write_text(json.dumps(rec, indent=2))
    if delete_after:
        check = yt.videos().list(part="status", id=vid).execute().get("items", [])
        if check and check[0]["status"].get("uploadStatus") in ("uploaded", "processed"):
            cleanup_local(folder, log)
        else:
            log("  kept local files: YouTube has not confirmed the upload yet")
    return rec
