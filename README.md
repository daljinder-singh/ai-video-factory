# AI Video Factory

Makes complete educational explainer videos on your own computer, with no input needed:
random topic → Wikipedia research → script → animated scenes (Manim) → voice (Piper) → subtitles →
final MP4 + thumbnail + YouTube title/description/tags. You upload the video to YouTube yourself.

## How to run

### 1. One-time setup (already done on this laptop)
```bash
sudo apt install -y ffmpeg libcairo2-dev libpango1.0-dev fonts-noto-core
cd ~/ai-video-factory
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ollama pull qwen3:4b
```
Piper voices go in `models/piper/` (English `en_US-lessac-medium`, Hindi `hi_IN-pratham-medium`).

### 2. Check everything is ready
```bash
cd ~/ai-video-factory
.venv/bin/python scripts/check_env.py      # should end with "All required checks passed."
```
Ollama must be running (it normally starts automatically; otherwise run `ollama serve` in another terminal).

### 3. Make a video
```bash
cd ~/ai-video-factory
./run.sh                                   # random topic, English, 1080p
```
More options:
```bash
./run.sh --category science                # random topic from one category
./run.sh --topic "Black hole"              # a specific Wikipedia topic
./run.sh --lang hinglish                   # en (default), hi, or hinglish
./run.sh --quality medium                  # low (480p), medium (720p), high (1080p, default)
./run.sh --speed 1.1                       # speaking speed (0.5 - 2.0)
./run.sh --music ~/Music/calm.mp3          # optional background music (auto-lowered under the voice)
./run.sh --burn-subs                       # also burn subtitles into the picture
./run.sh --no-presenter                  # turn off the animated cartoon presenter
./run.sh --list-topics                     # show all 92 topics
./run.sh --resume output/videos/<folder>   # continue a run that stopped halfway
```
A run takes roughly 15-40 minutes on this laptop (most of it is the local AI writing the script).
Progress is printed in the terminal and saved in the run folder's `log.txt`.

### Knowledge series
Each series has its own topic list (all verified Wikipedia articles), presenter, and writing style:
```bash
./run.sh --series how       # "How does it work?"  e.g. How does GPS / UPI / a fridge work?
./run.sh --series why       # "Why does it happen?" e.g. Why is the sky blue? Why do we dream?
./run.sh --series history   # History in 5 minutes  e.g. Maurya Empire, Apollo 11
./run.sh --series money     # Money basics (adds a "not financial advice" line)
./run.sh --series space     # Space & science       e.g. Chandrayaan-3, black holes
./run.sh --series mind      # Psychology & mind     e.g. procrastination, habits
./run.sh --series tech      # Tech explained        e.g. ChatGPT, 5G, blockchain
./run.sh --series india     # India GK              e.g. ISRO, Constitution of India
./run.sh --series random --lang hinglish   # any series, any language (en / hi / hinglish)
./run.sh --list-topics      # see every series topic
```

### Recipe videos
Real recipes from the Wikibooks Cookbook (148 Indian recipes, CC BY-SA). English ingredients and steps are read
exactly as written; Hindi/Hinglish are translated by the local AI and every number is checked against the original.
Chef Tara presents in a drawn kitchen, with ingredient cards, step-by-step action pictures and timers.
```bash
./run.sh --recipe                          # random Indian recipe, English
./run.sh --dish "Chapati"                  # a specific recipe
./run.sh --dish "Kheer (Rice Pudding)" --lang hi
```

### Kids videos (age 0-5)
A separate mode for toddlers: hand-written lessons (no AI, no internet), slow and clear voice, bright drawn
scenery, big colourful pictures, Bubbles the Bear as host, quizzes, and original background music.
```bash
./run.sh --kids                              # random kids topic, English
./run.sh --kids --lang hi                    # Hindi
./run.sh --kids-topic animals                # colours, shapes, numbers, abc, animals, fruits, vehicles
./run.sh --kids-topic colours --lang hi --seed 5   # same seed = same video
```
Each topic includes diagrams: colour mixing, counting sides of shapes, a "which has more?" graph,
"where do they go?" (road / sky / water) and sorting fruits by colour.
When uploading, set the audience to **"Yes, it's made for kids"** (YouTube requires this).
Pictures: Twemoji (CC-BY 4.0, credited automatically in the description). Font: Baloo 2 (SIL OFL).

### 4. Get your files
Each run creates a folder `output/videos/<date>_<topic>/` containing:

| File | What it is |
|---|---|
| `final.mp4` | the finished video |
| `thumbnail.png` | 1280×720 YouTube thumbnail |
| `youtube_upload.txt` | title, description (with chapters and source credit) and tags to copy-paste |
| `subtitles.srt` | subtitles to upload in YouTube Studio |
| `preview.jpg` | a grid of frames to check the video at a glance |
| `qc_report.json` | quality check results |

**Watch the video in VLC or the Videos app, not inside VS Code.** VS Code's video preview has no AAC
audio support, so videos play silently there:
```bash
vlc output/videos/<folder>/final.mp4      # or: xdg-open output/videos/<folder>/final.mp4
```

### 5. Upload to YouTube (manually)
In YouTube Studio: upload `final.mp4`, paste the title/description/tags from `youtube_upload.txt`,
set `thumbnail.png` as the thumbnail, add `subtitles.srt` under Subtitles. Keep it **Private** until you
have reviewed it.

### Settings
To change defaults permanently, create `config.json` in the project folder, for example:
```json
{"language": "en", "quality": "high", "speech_speed": 1.05, "min_scenes": 6, "max_scenes": 9}
```
All settings are listed in `src/videofactory/config.py`.

## System notes (checked 2026-11-20)
- i5-8265U CPU, 15 GB RAM, **no GPU**: everything runs on the CPU.
- Ollama `qwen3:4b`: about 5-8 tokens/s, so the script is the slowest stage.
- Piper voices: English (`lessac`) and Hindi (`pratham`). Whisper `base` is used for the quality check.
- LaTeX is not installed and not needed (formulas are drawn as plain text).

## Pipeline
1. **Topic**: random pick from a curated catalog of 92 Wikipedia topics in 9 categories (`topics.py`)
2. **Research**: Wikipedia article text (`research.py`)
3. **Script + scenes**: local LLM via Ollama, constrained to JSON schemas; every number must appear in the source (`scriptwriter.py`, `specs.py`)
4. **Narration**: Piper TTS, sentence by sentence for exact timings (`tts.py`)
5. **Sync**: each visual element appears at the sentence that mentions it (`timing.py`)
6. **Animation**: 19 Manim templates driven only by validated specs, Lucide icons, and an animated presenter (chosen by topic category) that lip-syncs to the voice and points at each new element (`render/`)
7. **Subtitles, assembly, optional music with ducking** (`subtitles.py`, `assemble.py`)
8. **Thumbnail + metadata** (`thumbnail.py`, `metadata.py`)
9. **QC**: A/V sync, scene order/timing, text size/layout, black frames, loudness, Whisper transcript vs script (`qc.py`)

Tests: `PYTHONPATH=src .venv/bin/python tests/test_templates.py low` renders every template.
