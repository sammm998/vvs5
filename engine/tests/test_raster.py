"""Scanned / rasterised input: classification, vectorisation + OCR, same semantic pipeline."""
import os

import pymupdf
import pytest

from vvs_engine.pdf.classify import classify_page
from vvs_engine.pdf.extract import extract_document
from vvs_engine.pipeline import analyze_page


def _rasterise(src_pdf: str, dst_pdf: str, dpi: int = 300) -> None:
    src = pymupdf.open(src_pdf)
    page = src[0]
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    png = dst_pdf + ".png"
    pix.save(png)
    dst = pymupdf.open()
    p = dst.new_page(width=page.rect.width, height=page.rect.height)
    p.insert_image(p.rect, filename=png)
    dst.save(dst_pdf)
    dst.close(); src.close()


def test_classification_vector_vs_raster(synthetic_pdf, tmp_path):
    scan = os.path.join(tmp_path, "scan.pdf")
    _rasterise(synthetic_pdf, scan)
    assert classify_page(pymupdf.open(synthetic_pdf)[0]).mode == "vector"
    assert classify_page(pymupdf.open(scan)[0]).mode == "raster"


@pytest.mark.slow
def test_scanned_synthetic_drawing_through_raster_path(synthetic_pdf, tmp_path):
    scan = os.path.join(tmp_path, "scan.pdf")
    _rasterise(synthetic_pdf, scan)
    rd = extract_document(scan)
    pg = rd.pages[0]
    assert pg.input_mode == "raster" and pg.raster_report["ocr_lines"] >= 3
    pa = analyze_page(pg)
    texts = {d.text for d in pa.designations}
    assert "KV01-X7-40-W40" in texts
    assert pa.scale.state in ("VERIFIED", "TEXT_ONLY", "BAR_ONLY")
    q = {r["designation"]: r for r in pa.quantities}
    assert "KV01-X7-40-W40" in q
    # pipe 1 is 500 pt: traced dashes lose about half a stroke width at every dash end; accept 15 %
    assert abs(q["KV01-X7-40-W40"]["confirmed_horizontal_m"] - 500 / 56.69) < 0.15 * 500 / 56.69
