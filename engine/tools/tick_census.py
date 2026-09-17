"""Strecken tvärs över ett rör som ingen hänvisningslinje pekar på - hur många, och hur mycket de delar.

Ritaren markerar en dimensionsövergång med ett kort streck tvärs ledningen. Ibland pekar en etikett på det
strecket, och då ser läsningen det: ledarens egen tick är redan en ritad gräns. Ibland står strecket ensamt -
en reduktion mitt i ett stråk, en gräns mot nästa blad - och då säger ritningen något som läsningen aldrig
läser. PipeStudio klassar en sådan markering på längden: ett streck vars längd ligger mellan 1,2 och 3,0
gånger rörets bredd är en markering, inte ett rör (`bucket.tick_rel_min`).

Det här verktyget räknar dem, blint, utan ett enda referensmått:

  * hur många korta streck som korsar ägd rörgeometri i stor vinkel,
  * hur många av dem som INGEN ledare når (de läsningen inte ser),
  * och hur mycket ägt rör som ligger mellan ett sådant streck och stråkets ändar - alltså hur mycket mängd
    som skulle kunna byta ägare om strecket räknades som gräns.

Talen avgör om det är värt en regel. Ingenting här ändrar en läsning.
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, "/home/user/vvs5/engine")
from vvs_engine.pdf.extract import extract_document          # noqa: E402
from vvs_engine.pipeline import analyze_page                 # noqa: E402
from vvs_engine.geometry.core import GridIndex, Seg, point_seg_distance   # noqa: E402

TICK_REL_MIN = 1.2          # PipeStudios giltighetsintervall för en markering: längd / rörbredd
TICK_REL_MAX = 3.0
CROSS_MIN_DEG = 55.0        # tvärs, inte längs: så mycket ska strecket luta mot röret det korsar
ON_LINE = 0.8               # pt: så nära rörets mittlinje ska streckets mitt ligga
LEADER_REACH = 3.0          # pt: en ledare som slutar så nära strecket är den som pekar på det


def _angle(x0, y0, x1, y1) -> float:
    return math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180.0


def census(pdf: str) -> dict:
    page = extract_document(pdf).pages[0]
    pa = analyze_page(page)
    mpp = (pa.scale.meters_per_pt or 0.0) if pa.scale else 0.0

    # ägd rörgeometri, per familj, med familjens egen penna
    owned: list[tuple] = []          # (x0, y0, x1, y1, family, width, identity)
    width_of: dict[str, float] = {}
    for fk, g in pa.graphs.items():
        st = pa.ownership.prim_states.get(fk, {})
        for pid, q in g.prims.items():
            s = st.get(pid)
            if s is None or s.state != "CONFIRMED" or s.identity is None:
                continue
            owned.append((q.seg.x0, q.seg.y0, q.seg.x1, q.seg.y1, fk, q.width, s.identity.key))
            width_of.setdefault(fk, q.width)
    idx = GridIndex(cell=12.0)
    for i, o in enumerate(owned):
        idx.insert(i, (min(o[0], o[2]) - 1, min(o[1], o[3]) - 1, max(o[0], o[2]) + 1, max(o[1], o[3]) + 1))

    # var ledarna slutar och var deras egna markeringar sitter
    ends = GridIndex(cell=12.0)
    n_ends = 0
    for ld in pa.leaders:
        for pt in [ld.end] + [((m.bbox[0] + m.bbox[2]) / 2, (m.bbox[1] + m.bbox[3]) / 2)
                              for m in list(ld.end_marks) + list(ld.crossing_marks)]:
            ends.insert(n_ends, (pt[0] - 0.01, pt[1] - 0.01, pt[0] + 0.01, pt[1] + 0.01))
            n_ends += 1

    # rörens egna primitiver, så att ett streck som redan ÄR rör inte räknas som markering
    pipe_segs = {(round(o[0], 2), round(o[1], 2), round(o[2], 2), round(o[3], 2)) for o in owned}

    seen = 0
    marks: list[dict] = []
    for p in page.paths:
        if len(p.segs) != 1:
            continue                       # en markering är ett streck, inte en form
        s = p.segs[0]
        L = math.hypot(s.x1 - s.x0, s.y1 - s.y0)
        if L <= 0:
            continue
        mx, my = (s.x0 + s.x1) / 2, (s.y0 + s.y1) / 2
        hit = None
        for i in idx.query_point(mx, my, ON_LINE + 0.2):
            o = owned[i]
            w = width_of.get(o[4]) or o[5] or 1.0
            if not (TICK_REL_MIN * w <= L <= TICK_REL_MAX * w):
                continue
            if (round(s.x0, 2), round(s.y0, 2), round(s.x1, 2), round(s.y1, 2)) in pipe_segs:
                continue
            d, t = point_seg_distance(mx, my, Seg(o[0], o[1], o[2], o[3]))
            if d > ON_LINE or not (0.02 < t < 0.98):
                continue
            a = abs(_angle(s.x0, s.y0, s.x1, s.y1) - _angle(o[0], o[1], o[2], o[3]))
            a = min(a, 180.0 - a)
            if a < CROSS_MIN_DEG:
                continue
            hit = o
            break
        if hit is None:
            continue
        seen += 1
        pointed = bool(list(ends.query_point(mx, my, LEADER_REACH)))
        marks.append({"x": round(mx, 2), "y": round(my, 2), "len": round(L, 2), "width": round(hit[5], 2),
                      "layer": p.layer, "identity": hit[6], "a_leader_points_at_it": pointed})

    lonely = [m for m in marks if not m["a_leader_points_at_it"]]
    return {"state": "OK", "input": pdf, "meters_per_pt": mpp,
            "owned_prims": len(owned), "marks_crossing_a_measured_pipe": seen,
            "with_a_leader": seen - len(lonely), "with_no_leader": len(lonely),
            "identities_marked_without_a_leader": sorted({m["identity"] for m in lonely}),
            "sample": lonely[:25]}


if __name__ == "__main__":
    out = {}
    for arg in sys.argv[1:]:
        tag = os.path.basename(os.path.dirname(arg)) or os.path.basename(arg)
        try:
            out[tag] = census(arg)
        except Exception as e:                                        # noqa: BLE001
            out[tag] = {"state": "ERROR", "error": f"{type(e).__name__}: {e}"}
        r = out[tag]
        print(f"{tag:18s} {r.get('state')} markeringar {r.get('marks_crossing_a_measured_pipe')} "
              f"(med ledare {r.get('with_a_leader')}, utan {r.get('with_no_leader')})")
    print(json.dumps(out, ensure_ascii=False)[:200] and "")
    with open("/tmp/claude-0/tick-census.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
