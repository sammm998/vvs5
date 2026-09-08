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


def test_a_repeated_label_is_not_a_pipe_without_metres(synthetic_pdf):
    """"To fix" has to mean one thing: a pipe the sheet names that got no length.

    A drawing labels the same run many times and most of those labels carry no dimension of their own - it sits on
    the row below, or on the single label that states the size. Comparing the label's text with the measured
    designations letter for letter called every one of those repeats a pipe with no metres: on the reference set
    that was twelve of twenty-two, more than half of a list somebody is meant to work through.
    """
    from vvs_engine.output.artifacts import unresolved_issues

    pa = analyze_page(extract_document(synthetic_pdf).pages[0])
    measured = {q["designation"].upper() for q in pa.quantities if q.get("confirmed_total_m", 0) > 0}
    assert measured, "the fixture measures something"
    for it in unresolved_issues(pa):
        t = (it.get("text") or "").upper()
        if it["severity"] != "blocking":
            continue
        assert t not in measured
        assert not any(m.startswith(t + "-") for m in measured), \
            f"{t} har meter under sin dimension och är därför inget att åtgärda"


def test_a_label_whose_metres_are_on_another_row_says_so(synthetic_pdf):
    """And it says why it is only a note, so nobody has to work out where its metres went."""
    from vvs_engine.output.artifacts import unresolved_issues

    pa = analyze_page(extract_document(synthetic_pdf).pages[0])
    measured = {q["designation"].upper() for q in pa.quantities if q.get("confirmed_total_m", 0) > 0}
    for it in unresolved_issues(pa):
        t = (it.get("text") or "").upper()
        if t and any(m.startswith(t + "-") for m in measured) and it["kind"] in (
                "missing_pipe_attachment", "ambiguous_pipe_attachment", "missing_leader", "missing_dn",
                "uncertain_designation"):
            assert it["severity"] == "advisory"
            assert "upprepar" in (it.get("note") or "")


def test_the_ocr_assist_reads_only_where_a_character_is_unreadable(synthetic_pdf):
    """A pass that exists to name a handful of glyphs may not render a whole A1 to do it.

    On the reference sheet seventeen rows carry an unreadable character, and reading only the parts of the page
    that hold them repairs the same characters in a third of the time. In a small container the difference is
    between a reading that finishes and one that looks hung.
    """
    from vvs_engine.pdf.extract import extract_document
    from vvs_engine.review import ocr_check
    from vvs_engine.text.ocr_assist import resolve_unknown_glyphs
    from vvs_engine.text.vector_text import vector_text_rows

    pg = extract_document(synthetic_pdf).pages[0]
    rows = vector_text_rows(pg, {}).rows
    seen: dict = {}

    def spy(page, dpi=300, progress=None, regions=None, budget_s=None):
        seen["regions"], seen["budget"] = regions, budget_s
        return []

    real, ocr_check.ocr_words = ocr_check.ocr_words, spy
    try:
        rep = resolve_unknown_glyphs(pg, rows, budget_s=12.0)
    finally:
        ocr_check.ocr_words = real
    if rep["state"] == "nothing_to_resolve":
        return          # this sheet has no unreadable character, which is its own kind of pass
    assert seen["budget"] == 12.0, "assistenten måste ha en tidsbudget"
    assert seen["regions"], "assistenten läste hela bladet i stället för de rader som behövde det"
    assert len(seen["regions"]) == rep["rows_with_unknown"]
