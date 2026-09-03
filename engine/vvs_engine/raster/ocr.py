"""OCR of a rasterised page into text spans (page points), tiled at a legible resolution.

The OCR engine (RapidOCR, ONNX, CPU) is used only on pages without usable vector content. Every recognised line
becomes a TextSpan with per-character boxes (uniform split along the reading direction) so that the searchable-text
row builder and the annotation grammar work unchanged. Confidence is kept for the validation report.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..geometry.core import stable_id
from ..pdf.extract import TextChar, TextSpan

TILE_PX = 1400
OVERLAP_PX = 120


@dataclass
class OcrLine:
    text: str
    conf: float
    quad: list[tuple[float, float]]     # 4 corners in page points, reading order: top-left, top-right, bottom-right, bottom-left


_engine = None


def _ocr():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _engine = RapidOCR()
    return _engine


def ocr_page(page, dpi: int = 300, progress=None) -> list[OcrLine]:
    """Run OCR over the page in overlapping tiles rendered at `dpi`; deduplicate lines found in overlaps."""
    import pymupdf
    s = dpi / 72.0
    W, H = page.rect.width, page.rect.height
    # rotated pages: render in displayed orientation (matches the vector extractor's display space)
    rot = page.rotation
    disp_w, disp_h = (H, W) if rot in (90, 270) else (W, H)
    tile_pt = TILE_PX / s
    ov_pt = OVERLAP_PX / s
    engine = _ocr()
    lines: list[OcrLine] = []
    inv = ~page.rotation_matrix
    y = 0.0
    n_tiles = 0
    while y < disp_h:
        x = 0.0
        while x < disp_w:
            clip_disp = pymupdf.Rect(x, y, min(x + tile_pt, disp_w), min(y + tile_pt, disp_h))
            clip = pymupdf.Rect(clip_disp) * inv
            clip.normalize()
            pix = page.get_pixmap(matrix=pymupdf.Matrix(s, s).prerotate(rot), clip=clip, colorspace=pymupdf.csRGB)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            res, _ = engine(img)
            for box, text, conf in (res or []):
                quad = [(clip_disp.x0 + float(px) / s, clip_disp.y0 + float(py) / s) for px, py in box]
                lines.append(OcrLine(text=str(text), conf=float(conf), quad=quad))
            n_tiles += 1
            x += tile_pt - ov_pt
        y += tile_pt - ov_pt
        if progress:
            progress(f"OCR {min(100, int(100 * y / disp_h))}%")
    return _dedupe(lines)


def _bbox(q):
    xs = [p[0] for p in q]; ys = [p[1] for p in q]
    return (min(xs), min(ys), max(xs), max(ys))


def _iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _dedupe(lines: list[OcrLine]) -> list[OcrLine]:
    lines = sorted(lines, key=lambda l: (-l.conf, l.text, _bbox(l.quad)))
    kept: list[OcrLine] = []
    for l in lines:
        b = _bbox(l.quad)
        if any(_iou(b, _bbox(k.quad)) > 0.4 for k in kept):
            continue
        kept.append(l)
    kept.sort(key=lambda l: (round(_bbox(l.quad)[1], 1), round(_bbox(l.quad)[0], 1), l.text))
    return kept


def lines_to_spans(lines: list[OcrLine], page_index: int) -> list[TextSpan]:
    spans: list[TextSpan] = []
    for i, l in enumerate(lines):
        text = l.text.strip().upper()       # drawing codes are upper case; OCR case is not evidence
        if not text:
            continue
        tl, tr, br, bl = l.quad
        dx, dy = tr[0] - tl[0], tr[1] - tl[1]
        L = math.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        hx, hy = bl[0] - tl[0], bl[1] - tl[1]
        h = math.hypot(hx, hy) or 1.0
        n = len(text)
        adv = L / n
        chars: list[TextChar] = []
        for k, ch in enumerate(text):
            x0, y0 = tl[0] + ux * adv * k, tl[1] + uy * adv * k
            x1, y1 = x0 + ux * adv + hx, y0 + uy * adv + hy
            bbox = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
            chars.append(TextChar(c=ch, bbox=bbox, origin=(x0 + hx, y0 + hy)))
        tid = stable_id("ocr", page_index, text, f"{tl[0]:.1f}", f"{tl[1]:.1f}")
        spans.append(TextSpan(tid=tid, seqno=i, page=page_index, text=text, bbox=_bbox(l.quad), dir=(ux, uy), font="ocr", size=h, chars=chars, layer="ocr"))
    return spans
