"""Render every visual template with sample specs; fail on any render error or layout issue.

Usage: PYTHONPATH=src .venv/bin/python tests/test_templates.py [low|medium|high]
Writes output/dev/templates/<name>.mp4 and a contact sheet output/dev/templates/sheet.png
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from videofactory.config import QUALITY, ROOT
from videofactory.specs import TEMPLATE_MODELS

SAMPLES = {
    "title_card": {"title": "Compound Interest", "subtitle": "Why your money grows faster over time"},
    "definition": {"term": "Compound interest", "definition": "Interest calculated on the initial principal "
                   "and also on the interest accumulated from previous periods."},
    "bullet_list": {"heading": "Why it matters", "items": ["Savings grow faster over long periods",
                    "Debts can grow quickly too", "Frequency of compounding changes the result"]},
    "process_flow": {"heading": "How it works", "steps": ["Deposit principal", "Earn interest",
                     "Interest added to balance", "Earn interest on interest", "Balance snowballs"]},
    "cycle": {"heading": "The water cycle", "center": "Water", "stages": ["Evaporation", "Condensation",
              "Precipitation", "Collection"]},
    "comparison": {"heading": "Simple vs compound", "left_title": "Simple interest",
                   "left_items": ["Only on principal", "Grows linearly"], "right_title": "Compound interest",
                   "right_items": ["On principal and interest", "Grows exponentially", "Rewards patience"]},
    "timeline": {"heading": "A short history", "events": [{"when": "2000 BC", "label": "Babylonian loans"},
                 {"when": "1613", "label": "Witt's interest tables"}, {"when": "1683", "label": "Bernoulli studies e"},
                 {"when": "Today", "label": "Savings accounts"}]},
    "bar_chart": {"heading": "Growth of 100 at 10%", "unit": "", "bars": [{"label": "Year 0", "value": 100},
                  {"label": "Year 5", "value": 161}, {"label": "Year 10", "value": 259},
                  {"label": "Year 20", "value": 673}]},
    "big_number": {"value": "1,000,000", "caption": "Approximate value after decades of steady compounding"},
    "formula": {"heading": "The formula", "formula": "A = P(1 + r/n)^(nt)", "terms": [
                {"symbol": "P", "meaning": "principal (starting amount)"}, {"symbol": "r", "meaning": "annual rate"},
                {"symbol": "n", "meaning": "compounds per year"}, {"symbol": "t", "meaning": "years"}]},
    "code": {"heading": "In Python", "language": "python", "code": "def grow(p, r, years):\n    for _ in range(years):\n"
             "        p = p * (1 + r)\n    return p\n\nprint(grow(100, 0.1, 10))", "caption": "Each loop adds interest on the current balance"},
    "concept_map": {"center": "Interest", "nodes": ["Principal", "Rate", "Time", "Frequency", "Inflation"]},
    "function_graph": {"heading": "Simple vs compound growth", "x_label": "Time", "y_label": "Money",
                       "curves": [{"shape": "linear", "label": "Simple"}, {"shape": "exponential", "label": "Compound"}]},
    "line_chart": {"heading": "Balance over time", "y_label": "Balance", "points": [{"label": "Year 0", "value": 100},
                   {"label": "Year 5", "value": 161}, {"label": "Year 10", "value": 259}, {"label": "Year 15", "value": 418},
                   {"label": "Year 20", "value": 673}]},
    "pie_chart": {"heading": "Where returns come from", "unit": "%", "slices": [{"label": "Original deposit", "value": 40},
                  {"label": "Simple interest", "value": 25}, {"label": "Interest on interest", "value": 35}]},
    "pyramid": {"heading": "Maslow's hierarchy", "levels": ["Physiological", "Safety", "Love and belonging",
                "Esteem", "Self-actualization"]},
    "venn": {"heading": "Saving vs investing", "left": "Saving", "right": "Investing", "overlap": "Compounding"},
    "network": {"heading": "A neural network", "layers": [{"label": "Input layer", "nodes": 4},
                {"label": "Hidden layer", "nodes": 5}, {"label": "Hidden layer", "nodes": 5}, {"label": "Output", "nodes": 2}]},
    "summary": {"heading": "Key takeaways", "points": ["Interest earns interest", "Start early to benefit most",
                "Compounding frequency matters"]},
}
HEADINGS = {"concept_map": "Key factors", "big_number": "The power of time", "definition": "What is it?"}


def main(quality: str = "low") -> int:
    w, h, fps = QUALITY[quality]
    out = ROOT / "output" / "dev" / "templates"
    out.mkdir(parents=True, exist_ok=True)
    assert set(SAMPLES) == set(TEMPLATE_MODELS), "every template needs a sample"
    jobs = []
    for i, (name, spec) in enumerate(SAMPLES.items()):
        v = TEMPLATE_MODELS[name].model_validate({**spec, "template": name}).model_dump()
        units = 1 if name in ("title_card", "definition", "big_number", "code") else \
            len(v.get("items") or v.get("steps") or v.get("stages") or v.get("events") or v.get("bars")
                or v.get("terms") or v.get("nodes") or v.get("points") or v.get("curves") or v.get("slices")
                or v.get("levels") or v.get("layers") or ([0, 0, 0] if name == "venn" else [0, 0]))
        dur = 4.0 + 1.2 * units
        cues = [round(1.6 + k * (dur - 3.0) / max(units, 1), 2) for k in range(units)]
        job = {"visual": v, "heading": spec.get("heading") or HEADINGS.get(name, ""), "category": "finance",
               "index": i, "total": len(SAMPLES), "duration": dur, "cues": cues, "width": w, "height": h,
               "fps": fps, "out": str(out / f"{name}.mp4"), "presenter": "--no-presenter" not in sys.argv,
               "wav": str(ROOT / "output" / "tests" / "smoke.wav")}
        jp = out / f"{name}.job.json"
        jp.write_text(json.dumps(job))
        jobs.append((name, jp, dur))

    def run(item):
        name, jp, dur = item
        r = subprocess.run([sys.executable, "-m", "videofactory.render.render_scene", str(jp)],
                           capture_output=True, text=True, env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"})
        return name, dur, r

    failed = 0
    with ThreadPoolExecutor(3) as ex:
        for name, dur, r in ex.map(run, jobs):
            if r.returncode != 0:
                failed += 1
                print(f"FAIL {name}\n{r.stderr[-1500:]}")
                continue
            rep = json.loads(r.stdout.strip().splitlines()[-1])
            flag = "WARN" if rep["issues"] else "OK  "
            failed += bool(rep["issues"])
            print(f"{flag} {name:<13} target {dur:5.2f}s rendered {rep['rendered_seconds']:5.2f}s "
                  f"min text {rep['min_text_size']}  {rep['issues']}")
    # contact sheet: one frame from 75% through each clip
    frames = []
    for name, _, dur in jobs:
        png = out / f"{name}.png"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{dur * 0.8:.2f}", "-i", str(out / f"{name}.mp4"),
                        "-frames:v", "1", "-vf", "scale=640:-2", str(png)])
        frames.append(png)
    from PIL import Image
    imgs = [Image.open(f) for f in frames if f.exists()]
    if imgs:
        fw, fh = imgs[0].size
        cols = 4
        sheet = Image.new("RGB", (fw * cols, fh * ((len(imgs) + cols - 1) // cols)))
        for k, im in enumerate(imgs):
            sheet.paste(im, ((k % cols) * fw, (k // cols) * fh))
        sheet.save(out / "sheet.png")
    print(f"\n{len(jobs) - failed}/{len(jobs)} templates clean. Contact sheet: {out / 'sheet.png'}")
    return 1 if failed else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sys.exit(main(args[0] if args else "low"))
