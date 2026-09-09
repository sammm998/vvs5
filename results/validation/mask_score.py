"""Mot en handmålad ritning: fick sträckan rätt namn, missades den, eller är den en vägg?

Facit i Excel säger hur många meter en beteckning skulle bli. Det är rätt fråga för en mängd och fel fråga för
en läsning: en summa som stämmer kan vara två fel som tar ut varandra, och en summa som fattas säger inte vilken
sträcka som fattas. Här finns något starkare - en människa har målat varje rör på bladet med vilken beteckning
det är, och målat väggarna `wall`. Det är ett svar per punkt på pappret.

Mätningen blir då fyra tal som var och ett svarar på en fråga någon faktiskt ställer:

  rätt      · av det motorn mätte, hur mycket bär det namn som människan satte på samma ställe
  fel namn  · motorn mätte, människan säger en annan beteckning - det dyraste felet, för det syns inte i en summa
  vägg      · motorn mätte, människan säger vägg - meter som inte finns
  missat    · människan säger rör, motorn gav det ingen identitet - täckningen, per beteckning

Läser en inspelad blindkörning och CVAT-annoteringarna. Motorn startas aldrig här, precis som i metrics.py
bredvid: det som kan se svaren får aldrig röra en mätning.

    python results/validation/mask_score.py /tmp/gate.json
"""
from __future__ import annotations

import glob
import json
import math
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

ROOT = os.environ.get("VVS_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
STEP_PT = 1.5           # how finely a run is sampled along its length, in PDF points
NEAR_PX = 4             # a stroke has width and a painted mask has a hand's edge: look this far around a sample


class Sheet:
    """One hand-painted sheet: every mask, and what label was painted where."""

    def __init__(self, path: str):
        root = ET.parse(path).getroot()
        img = next(root.iter("image"), None)
        if img is None:
            raise ValueError("no image in " + path)
        self.name = (img.get("name") or "").split("_page")[0]
        self.w, self.h = int(img.get("width")), int(img.get("height"))
        # label -> set of (x, y) pixels. Sheets are ~6600x4700 and the paint covers a small part of that, so a
        # set of the painted pixels is far smaller than an array of the page.
        self.px: dict[tuple[int, int], str] = {}
        self.labels: set[str] = set()
        for m in img.iter("mask"):
            lab = m.get("label") or "unknown"
            self.labels.add(lab)
            self._paint(m, lab)

    def _paint(self, m, lab: str) -> None:
        left, top = int(m.get("left")), int(m.get("top"))
        w, h = int(m.get("width")), int(m.get("height"))
        runs = [int(v) for v in (m.get("rle") or "").split(",") if v.strip()]
        i = 0                       # index into the box, row-major
        on = False                  # CVAT RLE starts with a run of "off"
        for n in runs:
            if on:
                for k in range(i, i + n):
                    y, x = divmod(k, w)
                    if y < h:
                        self.px[(left + x, top + y)] = lab
            i += n
            on = not on

    def at(self, x: float, y: float) -> str | None:
        """What was painted at a point, allowing for the width of a stroke and the edge of a hand-drawn mask."""
        xi, yi = int(round(x)), int(round(y))
        hit = self.px.get((xi, yi))
        if hit:
            return hit
        for r in range(1, NEAR_PX + 1):
            for dx in range(-r, r + 1):
                for dy in (-r, r):
                    hit = self.px.get((xi + dx, yi + dy)) or self.px.get((xi + dy, yi + dx))
                    if hit:
                        return hit
        return None


def sheets() -> dict[str, str]:
    """Every hand-painted sheet there is, by drawing name."""
    out = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "cvat", "**", "*.xml"), recursive=True)):
        out.setdefault(os.path.basename(p).split("_cvat_")[0], p)
    return out


def _same(a: str, b: str) -> bool:
    """Whether two designations name the same pipe, written the way two hands write them."""
    def norm(s: str) -> str:
        return "".join(c for c in (s or "").upper() if c.isalnum())
    na, nb = norm(a), norm(b)
    return bool(na) and na == nb


def score(rec_path: str) -> None:
    rec = json.load(open(rec_path))
    have = sheets()
    rows = []
    for tag, r in sorted(rec.items()):
        if r.get("state") != "OK":
            continue
        xml = have.get(tag)
        if not xml:
            continue
        sh = Sheet(xml)
        # the render was made at a whole number of dots per inch; take it from the page rather than assume 200
        page = r.get("page") or {}
        wpt = page.get("width_pt") or 0
        if not wpt:
            continue
        s = sh.w / wpt                      # pixels per PDF point

        right = wrong = wall = unpainted = 0.0
        wrong_pairs: dict[tuple[str, str], float] = defaultdict(float)
        for p in r.get("pipes") or []:
            ident = p.get("identity") or ""
            for pl in p.get("geometry") or []:
                for i in range(1, len(pl)):
                    (x0, y0), (x1, y1) = pl[i - 1], pl[i]
                    d = math.hypot(x1 - x0, y1 - y0)
                    n = max(1, int(d / STEP_PT))
                    for k in range(n):
                        t = (k + 0.5) / n
                        lab = sh.at((x0 + t * (x1 - x0)) * s, (y0 + t * (y1 - y0)) * s)
                        seg = d / n
                        if lab is None:
                            unpainted += seg
                        elif lab == "wall":
                            wall += seg
                        elif lab == "unknown":
                            unpainted += seg
                        elif _same(lab, ident):
                            right += seg
                        else:
                            wrong += seg
                            wrong_pairs[(ident, lab)] += seg

        # what the hand painted as pipe, and how much of it the reading gave a name
        painted: dict[str, int] = defaultdict(int)
        for lab in sh.px.values():
            if lab not in ("wall", "unknown"):
                painted[lab] += 1
        named = {q["designation"] for q in r.get("quantities") or []
                 if (q.get("confirmed_horizontal_m") or 0) > 0.005}
        missed = sorted(l for l in painted if not any(_same(l, n) for n in named))
        rows.append({"tag": tag, "right_pt": right, "wrong_pt": wrong, "wall_pt": wall, "unpainted_pt": unpainted,
                     "painted_labels": len(painted), "missed_labels": missed,
                     "worst": sorted(wrong_pairs.items(), key=lambda kv: -kv[1])[:3]})

    if not rows:
        print("inga handmålade blad matchade körningen")
        return
    W = max(len(r["tag"]) for r in rows)
    print(f"{'ritning':{W}s} {'rätt':>8s} {'fel namn':>9s} {'vägg':>8s} {'omålat':>8s} {'rätt%':>6s} "
          f"{'målade bet.':>12s} {'missade':>8s}")
    for r in rows:
        tot = r["right_pt"] + r["wrong_pt"] + r["wall_pt"] + r["unpainted_pt"]
        print(f"{r['tag']:{W}s} {r['right_pt']:8.0f} {r['wrong_pt']:9.0f} {r['wall_pt']:8.0f} "
              f"{r['unpainted_pt']:8.0f} {100 * r['right_pt'] / max(tot, 1):5.0f}% "
              f"{r['painted_labels']:12d} {len(r['missed_labels']):8d}")
    tr = sum(r["right_pt"] for r in rows); tw = sum(r["wrong_pt"] for r in rows)
    tl = sum(r["wall_pt"] for r in rows); tu = sum(r["unpainted_pt"] for r in rows)
    tot = tr + tw + tl + tu
    print(f"{'ALLA':{W}s} {tr:8.0f} {tw:9.0f} {tl:8.0f} {tu:8.0f} {100 * tr / max(tot, 1):5.0f}% "
          f"{sum(r['painted_labels'] for r in rows):12d} {sum(len(r['missed_labels']) for r in rows):8d}")
    print("\nTalen är ritade punkter, inte meter: de mäts på pappret och är jämförbara mellan blad oavsett skala.")
    print("'omålat' är sträckor människan inte målade alls - varken rör eller vägg - och är varken rätt eller fel.")

    bad = [(r["tag"], k, v) for r in rows for k, v in r["worst"]]
    bad.sort(key=lambda t: -t[2])
    if bad:
        print("\nde dyraste namnförväxlingarna (motorn sa / handen sa / hur långt):")
        for tag, (mine, theirs), v in bad[:12]:
            print(f"  {tag:{W}s} {mine or '(utan namn)':22s} -> {theirs:22s} {v:7.0f} pt")
    miss = [(r["tag"], l) for r in rows for l in r["missed_labels"]]
    if miss:
        print(f"\n{len(miss)} beteckningar handen målade som rör och läsningen aldrig gav meter:")
        for tag, l in miss[:20]:
            print(f"  {tag:{W}s} {l}")


if __name__ == "__main__":
    score(sys.argv[1])
