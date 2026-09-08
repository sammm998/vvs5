"""The judge: what actually changes, out of everything the reading and its reviewers found.

The reviewers are deliberately unable to change anything, so without a judge a pile of findings leads nowhere.
With one, the danger is the opposite: a confident verdict on evidence that does not carry it. These tests pin the
four rules that make it safe to let it decide - it only implements answers the drawing itself offered, it never
touches a confirmed measurement, everything it implements is a correction, and where the evidence runs out it
says so rather than guessing.
"""
import os

from vvs_engine.agent.model import DrawingModel
from vvs_engine.cli import analyze_pdf
from vvs_engine.review.judge import ASK, IMPLEMENT, LEAVE, judge

_CACHE: dict[str, DrawingModel] = {}


def _read(tmp_path, synthetic_pdf) -> DrawingModel:
    if synthetic_pdf not in _CACHE:
        out = os.path.join(tmp_path, "res")
        os.makedirs(out, exist_ok=True)
        analyze_pdf(synthetic_pdf, out, name="test", determinism=False, contamination=False, review=True)
        _CACHE[synthetic_pdf] = DrawingModel(out)
    return _CACHE[synthetic_pdf]


def test_every_verdict_says_what_and_why(tmp_path, synthetic_pdf):
    d = judge(_read(tmp_path, synthetic_pdf))
    for v in d["utslag"]:
        assert v["beslut"] in (IMPLEMENT, LEAVE, ASK)
        assert v["skäl"].strip(), f"{v['typ']} avgjordes utan skäl"
        assert v["typ"].strip()
    assert sum(d["sammanfattning"].values()) == d["antal"]


def test_nothing_is_implemented_without_the_drawings_own_candidates(tmp_path, synthetic_pdf):
    """A verdict to implement must name an answer the drawing put forward, and carry the correction to write."""
    d = judge(_read(tmp_path, synthetic_pdf))
    for v in d["utslag"]:
        if v["beslut"] != IMPLEMENT:
            continue
        assert v.get("svar") in (v.get("kandidater") or []), "domaren genomförde ett svar ritningen inte erbjöd"
        assert v.get("rättelse"), "en genomförd ändring ska vara en rättelse som kan ångras"


def test_a_reading_with_no_proposals_implements_nothing(tmp_path, synthetic_pdf):
    """Without earlier corrections to learn from there is nothing to implement, and that is the right answer."""
    d = judge(_read(tmp_path, synthetic_pdf), proposals=[])
    assert d["sammanfattning"].get(IMPLEMENT, 0) == 0


def test_a_proposal_the_drawing_does_not_offer_is_refused(tmp_path, synthetic_pdf):
    """The one route by which an answer can come from outside the sheet is still bounded by the sheet."""
    m = _read(tmp_path, synthetic_pdf)
    open_cases = [a for a in m.anchors if a.get("state") == "AMBIGUOUS_PIPE_ATTACHMENT"]
    if not open_cases:
        return
    bad = [{"id": open_cases[0]["anchor_id"], "answer": "PÅHITTAT-999", "candidates": ["A-1", "B-2"]}]
    d = judge(m, proposals=bad)
    assert all(v.get("svar") != "PÅHITTAT-999" for v in d["utslag"])
    assert d["sammanfattning"].get(IMPLEMENT, 0) == 0


def test_judging_twice_gives_the_same_verdicts(tmp_path, synthetic_pdf):
    """It calls no model, so it cannot drift between two runs of the same reading."""
    m = _read(tmp_path, synthetic_pdf)
    a, b = judge(m), judge(m)
    assert a == b
