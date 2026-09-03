"""Raster page -> RawPage.

1. The page is rendered in its displayed orientation (bounded resolution), binarised and de-speckled.
2. Text is read by OCR (tiled, higher resolution); its boxes become TextSpans and are masked out of the ink so
   that glyph strokes never become pipe or leader geometry.
3. The remaining ink is skeletonised and traced into polylines with measured stroke widths; drawing-local width
   classes become the vector families (layer 'raster', width = class) the vector engine reasons about.
4. A validation report records what was found and how reliable it is (OCR confidence, ink explained by strokes).
"""
from __future__ import annotations

import math
import time
from typing import Any

import numpy as np

from ..geometry.core import Seg, bbox_union, stable_id
from ..pdf.extract import PageInfo, RawPage, RawPath, TextSpan
from .ocr import lines_to_spans, ocr_page
from .vectorize import Polyline, assign_class, binarize, remove_specks, vectorize, width_classes

MAX_SIDE_PX = 7200


def render_dpi(page) -> int:
    long_side = max(page.rect.width, page.rect.height)
    dpi = int(min(300, max(150, MAX_SIDE_PX / long_side * 72)))
    return dpi


def raster_page(page, pno: int, progress=None) -> tuple[RawPage, dict[str, Any]]:
    import pymupdf
    t0 = time.perf_counter()
    rot = page.rotation
    dpi = render_dpi(page)
    s = dpi / 72.0
    pix = page.get_pixmap(matrix=pymupdf.Matrix(s, s).prerotate(rot), colorspace=pymupdf.csGRAY)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    disp_w, disp_h = pix.width / s, pix.height / s
    ink = remove_specks(binarize(img))
    ink_px = int(ink.sum())
    t_render = time.perf_counter()
    # ---- text (OCR) and its mask
    lines = ocr_page(page, dpi=300, progress=progress)
    lines = _tighten_to_ink(lines, ink, s)
    spans = lines_to_spans(lines, pno)
    boxes = np.zeros_like(ink)
    for l in lines:
        xs = [p[0] for p in l.quad]; ys = [p[1] for p in l.quad]
        pad = 0.1 * (max(ys) - min(ys))
        x0, y0 = int(max(0, (min(xs) - pad) * s)), int(max(0, (min(ys) - pad) * s))
        x1, y1 = int(min(ink.shape[1], (max(xs) + pad) * s)), int(min(ink.shape[0], (max(ys) + pad) * s))
        if x1 > x0 and y1 > y0:
            boxes[y0:y1, x0:x1] = True
    # glyph ink = connected components lying (>= 70 %) inside OCR boxes; underlines, frames and leaders that only
    # pass through a box keep their ink
    import cv2
    n, labels, stats, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    inside = np.bincount(labels[boxes], minlength=n).astype(float)
    area = np.maximum(stats[:, cv2.CC_STAT_AREA].astype(float), 1.0)
    glyph_comp = (inside / area) >= 0.7
    # elongated thin components (underlines, frame lines) inside a text box are drawing geometry, not glyphs
    w_c = stats[:, cv2.CC_STAT_WIDTH].astype(float); h_c = stats[:, cv2.CC_STAT_HEIGHT].astype(float)
    elongated = (np.maximum(w_c, h_c) >= 6.0 * np.maximum(np.minimum(w_c, h_c), 1.0)) & (np.maximum(w_c, h_c) >= 8.0)
    glyph_comp &= ~elongated
    glyph_comp[0] = False
    mask = glyph_comp[labels]
    text_px = int(mask.sum())
    ink_lines = ink & ~mask
    t_ocr = time.perf_counter()
    # ---- strokes
    polys = vectorize(ink_lines, s)
    classes = width_classes(polys, s)
    paths: list[RawPath] = []
    pieces: list[tuple[Polyline, list[tuple[float, float]]]] = []
    for pl in polys:
        # split at sharp corners: a bend becomes a shared endpoint (as in vector exports), a straight run stays one path
        for part in _split_at_corners(pl.points, 20.0) if not pl.closed else [pl.points]:
            pieces.append((pl, part))
    for i, (pl, pts) in enumerate(sorted(pieces, key=lambda t: (round(t[1][0][1], 2), round(t[1][0][0], 2), len(t[1])))):
        segs = [Seg(pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1]) for k in range(len(pts) - 1)]
        segs = [sg for sg in segs if sg.length > 1e-6]
        if not segs:
            continue
        w = assign_class(pl.width_pt, classes) if classes else pl.width_pt
        bbox = bbox_union([sg.bbox() for sg in segs])
        key = ("raster", f"{w:.3f}", ",".join(f"{sg.x0:.2f},{sg.y0:.2f},{sg.x1:.2f},{sg.y1:.2f}" for sg in segs[:64]), len(segs))
        paths.append(RawPath(pid=stable_id("rpath", pno, *key), seqno=i, page=pno, layer="raster", layer_id=0, kind="s", width=float(w),
                             color=(0.0, 0.0, 0.0), fill=None, closed=pl.closed, segs=segs, bbox=bbox, n_items=len(segs),
                             n_curves=1 if pl.closed else 0, n_subpaths=1))
    _dedupe(paths)
    t_vec = time.perf_counter()
    stroke_px = sum(pl.n_px for pl in polys)
    explained = min(1.0, stroke_px * max(1.0, float(np.median([pl.width_pt * s for pl in polys])) if polys else 1.0) / max(int(ink_lines.sum()), 1))
    confs = [l.conf for l in lines]
    report = {
        "mode": "raster", "render_dpi": dpi, "ocr_dpi": 300, "image_px": [pix.width, pix.height],
        "ink_px": ink_px, "text_ink_px": text_px, "line_ink_px": int(ink_lines.sum()),
        "ocr_lines": len(lines), "ocr_mean_confidence": round(float(np.mean(confs)), 3) if confs else None,
        "ocr_low_confidence_lines": sum(1 for c in confs if c < 0.8),
        "stroke_polylines": len(paths), "stroke_width_classes_pt": [round(c, 2) for c in classes],
        "ink_explained_by_strokes": round(float(explained), 3),
        "timings_ms": {"render_ms": round((t_render - t0) * 1000), "ocr_ms": round((t_ocr - t_render) * 1000), "vectorize_ms": round((t_vec - t_ocr) * 1000)},
    }
    info = PageInfo(index=pno, width=float(disp_w), height=float(disp_h), rotation=rot,
                    mediabox=[round(v, 2) for v in page.mediabox], cropbox=[round(v, 2) for v in page.cropbox],
                    n_images=len(page.get_images()), n_annots=0, n_xobjects=0, xobjects=[], fonts=[{"basefont": "ocr", "type": "raster"}], annots=[])
    return RawPage(info=info, paths=paths, spans=spans, input_mode="raster", raster_report=report), report


def _split_at_corners(pts: list[tuple[float, float]], deg: float) -> list[list[tuple[float, float]]]:
    if len(pts) < 3:
        return [pts]
    out: list[list[tuple[float, float]]] = []
    cur = [pts[0], pts[1]]
    for k in range(2, len(pts)):
        a = math.degrees(math.atan2(cur[-1][1] - cur[-2][1], cur[-1][0] - cur[-2][0]))
        b = math.degrees(math.atan2(pts[k][1] - cur[-1][1], pts[k][0] - cur[-1][0]))
        d = abs((b - a + 180) % 360 - 180)
        if d >= deg:
            out.append(cur)
            cur = [cur[-1], pts[k]]
        else:
            cur.append(pts[k])
    out.append(cur)
    return out


def _tighten_to_ink(lines, ink: np.ndarray, s: float):
    """OCR boxes carry padding; the glyph rows are the box rows that contain ink, excluding rows filled across the
    whole box width (an underline running inside the box). Only axis-aligned (horizontal) lines are tightened."""
    out = []
    H, W = ink.shape
    for l in lines:
        tl, tr, br, bl = l.quad
        if abs(tr[1] - tl[1]) > 0.05 * abs(tr[0] - tl[0]) + 0.5:
            out.append(l); continue
        x0, x1 = int(max(0, min(tl[0], bl[0]) * s)), int(min(W, max(tr[0], br[0]) * s))
        y0, y1 = int(max(0, min(tl[1], tr[1]) * s)), int(min(H, max(bl[1], br[1]) * s))
        if x1 - x0 < 3 or y1 - y0 < 3:
            out.append(l); continue
        sub = ink[y0:y1, x0:x1]
        rows = sub.sum(axis=1)
        width = x1 - x0
        glyph_rows = np.nonzero((rows > 0) & (rows < 0.8 * width))[0]
        if len(glyph_rows) < 2:
            out.append(l); continue
        ny0, ny1 = (y0 + glyph_rows.min()) / s, (y0 + glyph_rows.max() + 1) / s
        if ny1 - ny0 < 0.4 * (y1 - y0) / s:
            out.append(l); continue
        from .ocr import OcrLine
        out.append(OcrLine(text=l.text, conf=l.conf, quad=[(tl[0], ny0), (tr[0], ny0), (br[0], ny1), (bl[0], ny1)]))
    return out


def _dedupe(paths: list[RawPath]) -> None:
    seen: dict[str, int] = {}
    for p in paths:
        n = seen.get(p.pid, 0)
        if n:
            p.pid = f"{p.pid}_{n}"
        seen[p.pid.split('_')[0] if n else p.pid] = n + 1
