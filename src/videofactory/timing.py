"""Decide when each visual element appears so it matches the sentence that talks about it."""
from __future__ import annotations

import re

from .tts import Segment

STOP = set("""a an the and or of to in on for with by is are was were be been it its this that these those as at
from into than then so such can will may also which who what when where how their there they them you your
we our he she his her not no but if about more most other some any each between over under""".split())


def _tokens(s: str) -> set[str]:
    words = re.findall(r"[\wऀ-ॿ]+", s.lower())
    out = set()
    for w in words:
        if w in STOP or (len(w) < 3 and not w.isdigit()):
            continue
        out.add(w[:6])  # crude stemming: compare 6-char prefixes ("compounding" ~ "compound")
    return out


def cue_times(units: list[str], segments: list[Segment], duration: float, intro: float = 1.2,
              min_gap: float = 0.7) -> list[float]:
    """Return a start time for each unit (non-decreasing, inside the scene)."""
    n = len(units)
    if n == 0:
        return []
    seg_tok = [_tokens(s.text) for s in segments]
    best: list[int | None] = []
    for u in units:
        ut = _tokens(u)
        scores = [len(ut & st) / (len(ut) or 1) for st in seg_tok]
        m = max(scores) if scores else 0
        best.append(scores.index(m) if m >= 0.2 else None)

    # enforce order: a later unit never maps to an earlier sentence
    prev = 0
    for i, b in enumerate(best):
        if b is not None and b < prev:
            best[i] = None
        elif b is not None:
            prev = b
    # fill gaps by spreading unmatched units evenly between matched neighbours
    for i in range(n):
        if best[i] is None:
            left = next((best[j] for j in range(i - 1, -1, -1) if best[j] is not None), None)
            right = next((best[j] for j in range(i + 1, n) if best[j] is not None), None)
            if left is None and right is None:
                best[i] = min(int(i * len(segments) / n), len(segments) - 1)
            else:
                lo = left if left is not None else 0
                hi = right if right is not None else len(segments) - 1
                best[i] = max(lo, min(hi, round((lo + hi) / 2)))
    # monotonic again after filling
    for i in range(1, n):
        best[i] = max(best[i], best[i - 1])

    times = []
    for i, b in enumerate(best):
        seg = segments[b]
        same = [j for j in range(n) if best[j] == b]
        k = same.index(i)
        span = max(seg.end - seg.start, 0.1)
        times.append(seg.start + 0.1 + span * k / len(same))
    # spacing and bounds
    latest = duration - 1.2
    out = []
    t_prev = intro - min_gap
    for t in times:
        t = max(t, t_prev + min_gap, intro)
        out.append(round(min(t, latest), 3))
        t_prev = t
    return out
