"""The review layer: independent agents that check a finished result instead of trusting it."""
import os

import pymupdf

from vvs_engine.pdf.extract import extract_document
from vvs_engine.pipeline import analyze_page
from vvs_engine.review import run_review


def test_review_reports_a_missing_scale_as_an_error(tmp_path):
    """Without a scale nothing can be measured, and the review must say so rather than pass the result on."""
    path = os.path.join(tmp_path, "noscale.pdf")
    doc = pymupdf.open(); page = doc.new_page(width=842, height=595); shape = page.new_shape()
    shape.draw_line((100, 300), (600, 300)); shape.finish(width=1.44, color=(0, 0, 0), closePath=False)
    shape.commit(); doc.save(path); doc.close()
    rev = run_review(analyze_page(extract_document(path).pages[0]), ocr=False)
    codes = {f["code"] for f in rev["findings"]}
    assert "no_scale" in codes and rev["state"] == "ERROR"


def test_review_passes_a_clean_drawing(synthetic_pdf):
    """A drawing the engine reads completely leaves no error, and the coverage agent reports what it accounted for."""
    rev = run_review(analyze_page(extract_document(synthetic_pdf).pages[0]), ocr=False)
    assert rev["state"] in ("OK", "WARN")
    assert not [f for f in rev["findings"] if f["severity"] == "ERROR"]
    cov = [f for f in rev["findings"] if f["code"] == "owned_share"]
    assert cov and cov[0]["detail"]["share"] > 0.5
    assert "designation_agent" in rev["agents"] and "coverage_agent" in rev["agents"]


def test_review_never_changes_the_measurement(synthetic_pdf):
    """The review states an opinion; it may not edit the numbers it is reviewing."""
    pa = analyze_page(extract_document(synthetic_pdf).pages[0])
    before = [dict(r) for r in pa.quantities]
    run_review(pa, ocr=False)
    assert [dict(r) for r in pa.quantities] == before
