"""Scale discovery from the PDF itself: scale text (1:N with optional page-format qualifier) and vector scale bars
(a row of equally spaced numeric labels 0,1,2,... along a bar). No default scale is ever assumed."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

from ..geometry.core import GridIndex, Seg, bbox_expand, dist, point_seg_distance
from ..pdf.extract import RawPage
from ..text.model import TextRow, project, row_axes

MM_PER_PT = 25.4 / 72.0
SCALE_RE = re.compile(r"1\s*[:;]\s*([0-9Oo]{1,4})")
FORMAT_RE = re.compile(r"\bA([0-4])\b")


@dataclass
class ScaleEvidence:
    kind: str                       # 'scale_text' | 'scale_bar'
    text: str
    bbox: list[float]
    value: float                    # meters per pdf point implied
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScaleResult:
    meters_per_pt: float | None
    scope: str                      # 'page' | 'none'
    state: str                      # VERIFIED | TEXT_ONLY | BAR_ONLY | CONFLICT | NONE
    evidence: list[ScaleEvidence]
    reason: str

    def as_dict(self):
        return {"meters_per_pdf_point": self.meters_per_pt, "scope": self.scope, "state": self.state, "reason": self.reason,
                "evidence": [{"kind": e.kind, "text": e.text, "bbox": e.bbox, "meters_per_pt": e.value, "detail": e.detail} for e in self.evidence]}


def discover_scale(page: RawPage, lines: list[TextRow]) -> ScaleResult:
    ev: list[ScaleEvidence] = []
    # 1. scale text
    for ln in lines:
        t = ln.text.replace(" ", "")
        for m in SCALE_RE.finditer(t):
            digits = m.group(1).replace("O", "0").replace("o", "0")
            if not digits.isdigit():
                continue
            n = int(digits)
            if 5 <= n <= 5000:
                # ignore obvious non-scale ratios inside longer codes (e.g. 1:1 in notes) by requiring a 'scale-like' context:
                # the row is short or contains a scale keyword or a page-format qualifier
                ctx = ln.text.upper()
                if len(t) <= 14 or "SKALA" in ctx or "SCALE" in ctx or re.search(r"\(A[0-4]\)", ctx):
                    ev.append(ScaleEvidence(kind="scale_text", text=ln.text, bbox=[round(v, 1) for v in ln.bbox],
                                            value=n * MM_PER_PT / 1000.0, detail={"ratio": n, "qualifier": re.findall(r"\(A[0-4]\)", ctx)}))
    # 2. scale bar: >=3 numeric labels (integers) equally spaced along one axis with a long line/bar nearby
    bar = _find_scale_bar(page, lines)
    if bar is not None:
        ev.append(bar)
    texts = [e for e in ev if e.kind == "scale_text"]
    bars = [e for e in ev if e.kind == "scale_bar"]
    if bars and texts:
        # choose the text evidence consistent with the bar (page qualifier may differ from actual plot format)
        for b in bars:
            for t in texts:
                if abs(t.value - b.value) / b.value <= 0.03:
                    # the printed ratio is exact; the bar confirms it geometrically
                    return ScaleResult(t.value, "page", "VERIFIED", [t, b], "scale_text_and_scale_bar_agree")
        return ScaleResult(bars[0].value, "page", "CONFLICT", ev, "scale_bar_disagrees_with_scale_text; bar (geometric) used")
    if bars:
        return ScaleResult(bars[0].value, "page", "BAR_ONLY", ev, "vector_scale_bar_only")
    if texts:
        vals = sorted({round(t.value, 9) for t in texts})
        if len(vals) == 1:
            return ScaleResult(vals[0], "page", "TEXT_ONLY", ev, "scale_text_only (no vector scale bar found)")
        # several ratios (e.g. '1:50 (1:100)'): prefer the one whose qualifier matches the page format
        fmt = _page_format(page)
        for t in texts:
            if fmt and f"({fmt})" in "".join(t.detail.get("qualifier", [])):
                return ScaleResult(t.value, "page", "TEXT_ONLY", ev, f"scale_text_with_matching_page_format_{fmt}")
        # ratios listed in one row with the sheet formats listed in the same title-block cell, in the same order
        if fmt:
            rows: dict[tuple, list[ScaleEvidence]] = {}
            for t in texts:
                rows.setdefault(tuple(t.bbox), []).append(t)
            for bb, ts in sorted(rows.items()):
                if len(ts) < 2:
                    continue
                fmts = _cell_formats(lines, list(bb))
                if len(fmts) == len(ts) and fmt in fmts and len(set(fmts)) == len(fmts):
                    t = ts[fmts.index(fmt)]
                    return ScaleResult(t.value, "page", "TEXT_ONLY", ev,
                                       f"scale_text_selected_by_sheet_format_{fmt} (formats {'/'.join(fmts)})")
        return ScaleResult(None, "none", "CONFLICT", ev, "several_scale_texts_no_geometric_confirmation")
    return ScaleResult(None, "none", "NONE", ev, "no_scale_evidence_found")


def _cell_formats(lines: list[TextRow], bbox: list[float]) -> list[str]:
    """Sheet-format tokens (A0..A4) written in the same title-block cell as a scale row, in reading order.

    Drawings commonly state one ratio per print format ("SKALA A1 (A3)" over "1:50 (1:100)"): the k-th format
    belongs to the k-th ratio, so the sheet's own size selects the ratio that applies to it."""
    h = max(bbox[3] - bbox[1], 1.0)
    out: list[tuple[float, float, str]] = []
    for ln in lines:
        b = ln.bbox
        if abs((b[1] + b[3]) / 2 - (bbox[1] + bbox[3]) / 2) > 3.0 * h:
            continue
        if b[2] < bbox[0] - 6 * h or b[0] > bbox[2] + 6 * h:
            continue
        t = ln.text.upper()
        for m in FORMAT_RE.finditer(t):
            frac = m.start() / max(len(t), 1)
            out.append((round((b[1] + b[3]) / 2, 1), b[0] + frac * (b[2] - b[0]), f"A{m.group(1)}"))
    out.sort()
    return [f for _, _, f in out]


def _page_format(page: RawPage) -> str | None:
    w, h = sorted([page.info.width * MM_PER_PT, page.info.height * MM_PER_PT])
    fmts = {"A0": (841, 1189), "A1": (594, 841), "A2": (420, 594), "A3": (297, 420), "A4": (210, 297)}
    for k, (a, b) in fmts.items():
        if abs(w - a) <= 12 and abs(h - b) <= 12:
            return k
    return None


@dataclass
class _Label:
    text: str
    bbox: tuple
    angle: float
    height: float

    @property
    def cx(self):
        return (self.bbox[0] + self.bbox[2]) / 2

    @property
    def cy(self):
        return (self.bbox[1] + self.bbox[3]) / 2


def _numeric_words(lines: list[TextRow]) -> list[_Label]:
    out = []
    for ln in lines:
        cur = []
        for g in list(ln.glyphs) + [None]:
            if g is None or g.char == " ":
                if cur:
                    # twin shapes inside scale-bar labels: an O whose recognizer alternatives include 0 reads as 0
                    t = "".join("0" if (x.char == "O" and (any(a == "0" for a, _ in x.alternatives) or ln.source == "text")) else x.char for x in cur)
                    m = re.fullmatch(r"(\d{1,3})(m|M|cm|mm|CM|MM)?[:.,;]?", t)
                    if m:
                        t = m.group(1)
                        bb = (min(x.bbox[0] for x in cur), min(x.bbox[1] for x in cur), max(x.bbox[2] for x in cur), max(x.bbox[3] for x in cur))
                        out.append(_Label(t, bb, ln.angle, ln.height))
                cur = []
            else:
                cur.append(g)
    return out


def _find_scale_bar(page: RawPage, lines: list[TextRow]) -> ScaleEvidence | None:
    nums = _numeric_words(lines)
    if len(nums) < 3:
        return None
    idx = GridIndex(cell=60.0)
    for i, ln in enumerate(nums):
        idx.insert(i, ln.bbox)
    best = None
    for i, a in enumerate(nums):
        if a.text.strip() != "0":
            continue
        d, n = row_axes(a.angle)
        H = max(a.height, 1)
        # collect labels aligned with 'a' along d within 400 pt
        cands = []
        for j in idx.query(bbox_expand(a.bbox, 420)):
            b = nums[j]
            if abs(((b.angle - a.angle) + 180) % 360 - 180) > 3 or abs(b.height - a.height) > 0.3 * H:
                continue
            if abs(project((b.cx, b.cy), n) - project((a.cx, a.cy), n)) > 0.6 * H:
                continue
            cands.append((project((b.cx, b.cy), d) - project((a.cx, a.cy), d), int(b.text), b))
        cands = sorted((c for c in cands if c[0] >= -0.5), key=lambda c: (c[0], c[1]))
        if len(cands) < 3:
            continue
        # equal spacing check: value proportional to position
        vals = [c[1] for c in cands]; pos = [c[0] for c in cands]
        if vals != sorted(vals) or len(set(vals)) < 3:
            continue
        span_v = vals[-1] - vals[0]; span_p = pos[-1] - pos[0]
        if span_v <= 0 or span_p <= 20:
            continue
        k = span_p / span_v
        ok = all(abs(pos[m] - vals[m] * k) <= 0.35 * H + 0.03 * span_p for m in range(len(vals)))
        if not ok:
            continue
        # a bar/line must exist near the labels: strokes parallel to d within 3H whose extents cover >= 60 % of the
        # label span (one long stroke, or collinear pieces of a segmented / rasterised bar)
        bar_found = False
        covered: list[tuple[float, float]] = []
        extent: list[tuple[float, float]] = []       # unclipped, to measure the bar's own drawn length
        lo, hi = project((a.cx, a.cy), d), project((a.cx, a.cy), d) + span_p
        for p in page.paths:
            if p.kind == "f":
                continue
            for s in p.segs:
                if s.length < 4.0:
                    continue
                ang = s.angle
                if min(abs(ang - a.angle % 180), 180 - abs(ang - a.angle % 180)) > 3:
                    continue
                off = abs(project(s.mid, n) - project((a.cx, a.cy), n))
                if off > 3 * H:
                    continue
                p0, p1 = sorted((project((s.x0, s.y0), d), project((s.x1, s.y1), d)))
                if p1 < lo - 5 or p0 > hi + 5:
                    continue
                covered.append((max(p0, lo), min(p1, hi)))
                extent.append((p0, p1))
        covered.sort()
        total = 0.0
        cur_lo, cur_hi = None, None
        bar_lo, bar_hi = None, None
        for p0, p1 in covered:
            if cur_lo is None or p0 > cur_hi:
                if cur_lo is not None:
                    total += cur_hi - cur_lo
                cur_lo, cur_hi = p0, p1
            else:
                cur_hi = max(cur_hi, p1)
        for p0, p1 in extent:
            bar_lo = p0 if bar_lo is None else min(bar_lo, p0)
            bar_hi = p1 if bar_hi is None else max(bar_hi, p1)
        if cur_lo is not None:
            total += cur_hi - cur_lo
        bar_found = total >= 0.6 * span_p
        if not bar_found:
            continue
        # the bar's own drawn extent is the measurement; the label centres only say which values its ends carry
        # (a glyph centre sits a fraction of a character off the graduation it labels). Use the extent whenever
        # both ends of the bar coincide with the outer labels within half a graduation.
        span_used, ref = span_p, "label_centres"
        step = span_p / max(span_v, 1)
        if bar_lo is not None and abs(bar_lo - lo) <= 0.5 * step and abs(bar_hi - hi) <= 0.5 * step and bar_hi - bar_lo > 20:
            span_used, ref = bar_hi - bar_lo, "bar_extent"
        # unit: labels are meters when spacing implies a plausible drawing scale (1:10 .. 1:2000)
        mpp = span_v / span_used     # meters per pt if labels are meters
        ratio = mpp * 1000.0 / MM_PER_PT
        unit = "m"
        if ratio < 5:            # labels likely in cm or mm -> unrealistic; try mm
            mpp_mm = mpp / 1000.0
            if 5 <= mpp_mm * 1000.0 / MM_PER_PT <= 5000:
                mpp, unit, ratio = mpp_mm, "mm", mpp_mm * 1000.0 / MM_PER_PT
            else:
                continue
        if ratio > 5000:
            continue
        cand = ScaleEvidence(kind="scale_bar", text=" ".join(str(v) for v in vals), bbox=[round(v, 1) for v in (min(c[2].bbox[0] for c in cands), min(c[2].bbox[1] for c in cands), max(c[2].bbox[2] for c in cands), max(c[2].bbox[3] for c in cands))],
                             value=mpp, detail={"labels": vals, "span_pt": round(span_p, 2), "measured_from": ref, "bar_extent_pt": round(span_used, 2),
                                               "unit": unit, "implied_ratio": round(ratio, 1), "n_labels": len(vals)})
        if best is None or len(vals) > best.detail["n_labels"]:
            best = cand
    return best
