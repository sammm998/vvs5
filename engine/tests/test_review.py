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


def test_ocr_assist_reports_when_it_cannot_run(synthetic_pdf, monkeypatch):
    """Without the OCR extra the resolver says so and leaves the reading untouched; it never invents a character."""
    import vvs_engine.text.ocr_assist as oa
    from vvs_engine.pdf.extract import extract_document as ed
    page = ed(synthetic_pdf).pages[0]

    class Row:
        def __init__(self):
            self.glyphs = [type("G", (), {"char": "?", "bbox": (0, 0, 5, 7), "source": "stroke", "score": 0.5})()]
            self.bbox = (0, 0, 5, 7)
            self.text = "?"
            self.unknown_chars = 1

    monkeypatch.setattr("vvs_engine.review.ocr_check.ocr_words", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no engine")))
    rows = [Row()]
    rep = oa.resolve_unknown_glyphs(page, rows)
    assert rep["state"] == "unavailable" and rep["resolved"] == 0
    assert rows[0].glyphs[0].char == "?", "an unreadable character stays unreadable"


def test_ocr_assist_only_fills_a_word_that_lines_up(synthetic_pdf, monkeypatch):
    """OCR may fill an unknown position only when the rest of the word agrees with the vector reading."""
    import vvs_engine.text.ocr_assist as oa
    from vvs_engine.pdf.extract import extract_document as ed
    page = ed(synthetic_pdf).pages[0]

    def row(chars):
        gs = [type("G", (), {"char": c, "bbox": (10.0 * i, 0.0, 10.0 * i + 8, 7.0), "source": "stroke", "score": 0.5})()
              for i, c in enumerate(chars)]
        r = type("R", (), {})()
        r.glyphs = gs
        r.bbox = (0.0, 0.0, 10.0 * len(chars), 7.0)
        r.text = "".join(chars)
        r.unknown_chars = sum(1 for c in chars if c == "?")
        return r

    monkeypatch.setattr("vvs_engine.review.ocr_check.ocr_words",
                        lambda *a, **k: [("VG+1.44", [0.0, 0.0, 70.0, 7.0], 0.95)])
    ok = row(list("VG+1.?4"))
    rep = oa.resolve_unknown_glyphs(page, [ok])
    assert rep["resolved"] == 1 and ok.text == "VG+1.44"

    monkeypatch.setattr("vvs_engine.review.ocr_check.ocr_words",
                        lambda *a, **k: [("XY+9.44", [0.0, 0.0, 70.0, 7.0], 0.95)])
    bad = row(list("VG+1.?4"))
    rep = oa.resolve_unknown_glyphs(page, [bad])
    assert rep["resolved"] == 0 and bad.text == "VG+1.?4", "a disagreeing OCR word may not fill anything"
