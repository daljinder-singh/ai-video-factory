"""Join scene videos and narration into the final MP4 (exact per-scene audio/video alignment)."""
from __future__ import annotations

from pathlib import Path

from .media import duration, run_ffmpeg


def assemble(scene_videos: list[Path], scene_wavs: list[Path], work: Path, out: Path, srt: Path | None = None,
             music: Path | None = None, music_volume: float = 0.10, burn_subtitles: bool = False) -> list[float]:
    """Returns the start offset (seconds) of each scene in the final video."""
    tmp = work / "assembly"
    tmp.mkdir(parents=True, exist_ok=True)
    offsets, t = [], 0.0
    padded = []
    for i, (v, a) in enumerate(zip(scene_videos, scene_wavs)):
        vd = duration(v, "video")
        offsets.append(t)
        t += vd
        p = tmp / f"audio_{i:02}.wav"
        # pad/trim each narration to its scene's exact video length, at 48 kHz stereo
        run_ffmpeg("-i", str(a), "-af", "aresample=48000,apad", "-ac", "2", "-t", f"{vd:.6f}",
                   "-c:a", "pcm_s16le", str(p))
        padded.append(p)

    vlist = tmp / "videos.txt"
    vlist.write_text("".join(f"file '{Path(v).resolve()}'\n" for v in scene_videos))
    video_only = tmp / "video.mp4"
    run_ffmpeg("-f", "concat", "-safe", "0", "-i", str(vlist), "-c", "copy", "-an", str(video_only))

    alist = tmp / "audios.txt"
    alist.write_text("".join(f"file '{p.resolve()}'\n" for p in padded))
    voice = tmp / "voice.wav"
    run_ffmpeg("-f", "concat", "-safe", "0", "-i", str(alist), "-c", "copy", str(voice))

    audio = voice
    if music:
        if not Path(music).exists():
            raise FileNotFoundError(f"music file not found: {music}")
        total = duration(voice)
        audio = tmp / "mixed.wav"
        fade_start = max(total - 3, 0)
        run_ffmpeg("-i", str(voice), "-stream_loop", "-1", "-i", str(music), "-filter_complex",
                   "[0:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit=2[v1][v2];"
                   f"[1:a]aresample=48000,aformat=sample_rates=48000:channel_layouts=stereo,volume={music_volume}[m];"
                   "[m][v1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=500[duck];"
                   f"[v2][duck]amix=inputs=2:duration=first:normalize=0,afade=t=out:st={fade_start:.2f}:d=3[out]",
                   "-map", "[out]", "-t", f"{total:.6f}", "-c:a", "pcm_s16le", str(audio))

    args = ["-i", str(video_only), "-i", str(audio)]
    if srt and not burn_subtitles:
        args += ["-i", str(srt)]
    args += ["-map", "0:v", "-map", "1:a"]
    if burn_subtitles and srt:
        style = "FontName=Noto Sans,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=3,MarginV=40"
        esc = str(srt.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        args += ["-vf", f"subtitles='{esc}':force_style='{style}'", "-c:v", "libx264", "-preset", "medium",
                 "-crf", "18", "-pix_fmt", "yuv420p"]
    else:
        args += ["-c:v", "copy"]
        if srt:
            args += ["-map", "2:s", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng"]
    args += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
             str(out)]
    run_ffmpeg(*args)
    return offsets
