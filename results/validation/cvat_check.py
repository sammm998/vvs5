"""Score a reading against hand-drawn annotation masks.

The masks are painted by a person in CVAT, one label per designation, on a raster of the same sheet. They say
nothing about length - they say *where* each designation's pipe is. That makes them an independent answer to the
question the facit cannot ask on its own: did we find the right runs, in the right places, under the right names.

For every confirmed primitive we walk its length, convert each sample from page points to image pixels, and ask
the masks what is painted there:

  RÄTT      the mask under the sample carries the designation we gave it
  ANNAN     a mask is there, but under another designation - a naming error, the expensive kind
  OMÅLAT    nothing is painted there; either we measured something the annotator did not, or they stopped short

Reads annotations only from data/cvat, which is outside the engine and never imported by it.
"""
import glob
import math
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, "/home/user/vvs5/engine")
from vvs_engine.pdf.extract import extract_document
from vvs_engine.pipeline import analyze_page
from vvs_engine.profile.hatch import inside_hatch

CVAT = "/home/user/vvs5/data/cvat/CVAT"
STEP_PT = 1.0          # sample the geometry this often
GROW = 6               # px: the annotator's brush is wider than a hairline, but not by much


def decode(rle: str, w: int, h: int) -> bytearray:
    """CVAT run lengths, background first, row-major inside the mask's own box."""
    out = bytearray(w * h)
    i, val = 0, 0
    for run in rle.split(","):
        n = int(run)
        if val:
            out[i:i + n] = b"\x01" * n
        i += n
        val ^= 1
    return out


class Sheet:
    def __init__(self, xml: str):
        s = open(xml, encoding="utf-8").read()
        m = re.search(r'<image id="\d+" name="([^"]+)" width="(\d+)" height="(\d+)"', s)
        self.image, self.W, self.H = m.group(1), int(m.group(2)), int(m.group(3))
        self.masks = []
        for mm in re.finditer(
                r'<mask label="([^"]+)"[^>]*?rle="([^"]*)"\s*left="(\d+)"\s*top="(\d+)"\s*width="(\d+)"\s*height="(\d+)"', s):
            label, rle, left, top, w, h = mm.group(1), mm.group(2), int(mm.group(3)), int(mm.group(4)), int(mm.group(5)), int(mm.group(6))
            self.masks.append((label.upper(), left, top, w, h, decode(rle, w, h)))

    def at(self, px: float, py: float) -> set[str]:
        """Every designation painted at this pixel, allowing for the brush's width."""
        got = set()
        for label, left, top, w, h, bits in self.masks:
            if label in got:
                continue
            if not (left - GROW <= px <= left + w + GROW and top - GROW <= py <= top + h + GROW):
                continue
            x0, y0 = int(px) - left, int(py) - top
            for dx in range(-GROW, GROW + 1, 2):
                for dy in range(-GROW, GROW + 1, 2):
                    x, y = x0 + dx, y0 + dy
                    if 0 <= x < w and 0 <= y < h and bits[y * w + x]:
                        got.add(label)
                        break
                if label in got:
                    break
        return got


def run(job_dir: str, pdf: str) -> dict | None:
    xml = os.path.join(job_dir, "annotations.xml")
    if not os.path.exists(xml) or not os.path.exists(pdf):
        return None
    sheet = Sheet(xml)
    if not sheet.masks:
        return None
    page = extract_document(pdf).pages[0]
    pa = analyze_page(page)
    sx, sy = sheet.W / page.info.width, sheet.H / page.info.height
    mpp = pa.scale.meters_per_pt or 0.0
    own = {}
    for p in pa.ownership.pipes:
        for i in p.prim_ids:
            # the display form is what the drawing states, and what the annotator typed as the label
            own[(p.family, i)] = (p.identity.display or p.identity.key).upper()

    # the annotator painted a region of the sheet, not all of it, so geometry outside that region says nothing
    # about agreement: only what falls inside the painted area is scored
    xs = [m[1] for m in sheet.masks] + [m[1] + m[3] for m in sheet.masks]
    ys = [m[2] for m in sheet.masks] + [m[2] + m[4] for m in sheet.masks]
    PAD = 40
    region = (min(xs) - PAD, min(ys) - PAD, max(xs) + PAD, max(ys) + PAD)

    tally = defaultdict(float)
    per_des = defaultdict(lambda: defaultdict(float))
    for fk, states in pa.ownership.prim_states.items():
        for pid, st in states.items():
            if st.state != "CONFIRMED":
                continue
            name = own.get((fk, pid))
            if not name:
                continue
            s = pa.graphs[fk].prims[pid].seg
            n = max(1, int(s.length / STEP_PT))
            step_m = s.length / n * mpp
            for k in range(n):
                t = (k + 0.5) / n
                x, y = s.x0 + (s.x1 - s.x0) * t, s.y0 + (s.y1 - s.y0) * t
                px, py = x * sx, y * sy
                if not (region[0] <= px <= region[2] and region[1] <= py <= region[3]):
                    tally["UTANFÖR"] += step_m
                    continue
                labels = sheet.at(px, py)
                if name in labels:
                    verdict = "RÄTT"
                elif "WALL" in labels and len(labels) == 1:
                    # the wall mask also covers the pipes that cross it; where our own hatch detection already
                    # says this run is drawn inside a hatched area, the two readings agree rather than differ
                    verdict = "I SKRAFFERING" if inside_hatch(pa.hatch_families, x, y) is not None else "VÄGG"
                elif labels:
                    verdict = "ANNAN"
                else:
                    verdict = "OMÅLAT"
                tally[verdict] += step_m
                per_des[name][verdict] += step_m
    total = sum(v for k, v in tally.items() if k != "UTANFÖR")
    return {"sheet": os.path.basename(pdf), "labels": len({m[0] for m in sheet.masks if m[0] != "WALL"}),
            "masks": len(sheet.masks), "measured_m": total,
            "right": tally["RÄTT"], "other": tally["ANNAN"], "unpainted": tally["OMÅLAT"], "wall": tally["VÄGG"], "hatch": tally["I SKRAFFERING"], "outside": tally["UTANFÖR"],
            "per_designation": {k: dict(v) for k, v in per_des.items()}}


if __name__ == "__main__":
    jobs = sorted(glob.glob(os.path.join(CVAT, "*_cvat_job*")))
    want = sys.argv[1:]
    print(f"{'ark':26s} {'bet':>4s} {'mätt m':>9s} {'rätt':>9s} {'annan':>7s} {'vägg':>6s} {'skraff':>7s} {'omålat':>8s}   träff")
    tot = defaultdict(float)
    for j in jobs:
        base = os.path.basename(j).split("_cvat_job")[0]
        if want and base not in want:
            continue
        pdf = os.path.join(CVAT, base + ".pdf")
        try:
            r = run(j, pdf)
        except Exception as e:
            print(f"{base:26s} FEL {type(e).__name__}: {e}"[:110], flush=True)
            continue
        if r is None:
            continue
        hit = 100 * r["right"] / r["measured_m"] if r["measured_m"] else 0.0
        print(f"{base:26s} {r['labels']:4d} {r['measured_m']:9.1f} {r['right']:9.1f} {r['other']:7.1f} "
              f"{r['wall']:6.1f} {r['hatch']:7.1f} {r['unpainted']:8.1f}   {hit:5.1f} %", flush=True)
        for k in ("measured_m", "right", "other", "unpainted", "wall", "hatch"):
            tot[k] += r[k]
    if tot["measured_m"]:
        print(f"{'SUMMA':26s} {'':4s} {tot['measured_m']:9.1f} {tot['right']:9.1f} {tot['other']:7.1f} "
              f"{tot['wall']:6.1f} {tot['hatch']:7.1f} {tot['unpainted']:8.1f}   "
              f"{100 * tot['right'] / tot['measured_m']:5.1f} %")
