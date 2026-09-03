"""Optional OCR second opinion over the rendered page.

Used by the review layer to look for designations the vector reading may have missed, and by the OCR-assisted
resolver to name characters the stroke recogniser could not. It never reads the drawing on its own: the vector
geometry stays the source of the measurement.

The page is rendered at a legible resolution and read in overlapping tiles, because a whole A1 sheet scaled down
to one image leaves 6 pt CAD text too small for any recogniser. Lines found twice in an overlap are deduplicated.
"""
from __future__ import annotations

import math

import numpy as np

TILE_PX = 1400
OVERLAP_PX = 120
_ENGINE = None


def _engine():
    global _ENGINE
    if _ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR
        _ENGINE = RapidOCR()
    return _ENGINE


def ocr_words(page, dpi: int = 300, progress=None) -> list[tuple[str, list[float], float]]:
    """Read the page with OCR. Returns (word, bbox in page points, confidence) in the page's display space."""
    import pymupdf
    src = getattr(page, "source_path", None)
    if not src:
        raise RuntimeError("page carries no source path to render")
    doc = pymupdf.open(src)
    try:
        p = doc[page.info.index]
        s = dpi / 72.0
        rot = p.rotation
        W, H = p.rect.width, p.rect.height
        disp_w, disp_h = (H, W) if rot in (90, 270) else (W, H)
        tile_pt, ov_pt = TILE_PX / s, OVERLAP_PX / s
        engine = _engine()
        inv = ~p.rotation_matrix
        out: list[tuple[str, list[float], float]] = []
        y = 0.0
        while y < disp_h:
            x = 0.0
            while x < disp_w:
                clip_disp = pymupdf.Rect(x, y, min(x + tile_pt, disp_w), min(y + tile_pt, disp_h))
                clip = pymupdf.Rect(clip_disp) * inv
                clip.normalize()
                pix = p.get_pixmap(matrix=pymupdf.Matrix(s, s).prerotate(rot), clip=clip, colorspace=pymupdf.csRGB)
                if pix.width < 8 or pix.height < 8:
                    x += tile_pt - ov_pt
                    continue
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
                res, _ = engine(img)
                for box, text, conf in (res or []):
                    xs = [clip_disp.x0 + float(q[0]) / s for q in box]
                    ys = [clip_disp.y0 + float(q[1]) / s for q in box]
                    for w in str(text).split():
                        out.append((w, [min(xs), min(ys), max(xs), max(ys)], float(conf)))
                x += tile_pt - ov_pt
            y += tile_pt - ov_pt
            if progress:
                progress(f"OCR {min(100, int(100 * y / max(disp_h, 1)))}%")
        return _dedupe(out)
    finally:
        doc.close()


def _dedupe(words: list[tuple[str, list[float], float]]) -> list[tuple[str, list[float], float]]:
    """The same word read in two overlapping tiles: keep the more confident reading."""
    kept: list[tuple[str, list[float], float]] = []
    for w, b, c in sorted(words, key=lambda t: -t[2]):
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        h = max(b[3] - b[1], 1.0)
        if any(w2 == w and math.hypot(cx - (b2[0] + b2[2]) / 2, cy - (b2[1] + b2[3]) / 2) <= 0.6 * h for w2, b2, _ in kept):
            continue
        kept.append((w, b, c))
    return kept
