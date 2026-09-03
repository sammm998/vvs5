"""Optional OCR second opinion over the rendered page.

Only used by the review layer to look for designations the vector reading may have missed; it never feeds the
measurement. Requires rapidocr-onnxruntime, which is an optional extra - without it the review agent reports that
the cross-check did not run rather than failing the analysis.
"""
from __future__ import annotations

import numpy as np

_ENGINE = None


def _engine():
    global _ENGINE
    if _ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR
        _ENGINE = RapidOCR()
    return _ENGINE


def ocr_words(page, dpi: int = 300, max_side: int = 6000) -> list[tuple[str, list[float], float]]:
    """Render the page and OCR it. Returns (text, bbox in page points, confidence)."""
    import pymupdf
    doc = pymupdf.open(page.source_path) if getattr(page, "source_path", None) else None
    if doc is None:
        raise RuntimeError("page carries no source path to render")
    p = doc[page.info.index]
    scale = min(dpi / 72.0, max_side / max(p.rect.width, p.rect.height))
    m = pymupdf.Matrix(scale, scale).prerotate(p.rotation)
    pix = p.get_pixmap(matrix=m, colorspace=pymupdf.csGRAY)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    res, _ = _engine()(np.stack([img] * 3, axis=-1))
    doc.close()
    out: list[tuple[str, list[float], float]] = []
    for item in res or []:
        quad, text, conf = item[0], item[1], float(item[2])
        xs = [q[0] / scale for q in quad]
        ys = [q[1] / scale for q in quad]
        for w in str(text).split():
            out.append((w, [min(xs), min(ys), max(xs), max(ys)], conf))
    return out
