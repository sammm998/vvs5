"""Post-validation generic rules: tick marks as drawn DN boundaries, DN rows with qualifiers, leader start
conflicts, bundle end-marker clusters. Synthetic PDFs only."""
import os

import pymupdf

from vvs_engine.pdf.extract import extract_document
from vvs_engine.pipeline import analyze_page
from vvs_engine.semantics.annotation import _row_role
from tests.conftest import make_dashed_line


def _label(page, shape, x, y, text, dn_row=None, leader_to=None, tick=True):
    page.insert_text((x, y), text, fontsize=10, fontname="helv")
    ul_y = y + 2
    if dn_row is not None:
        page.insert_text((x + 20, y + 12), dn_row, fontsize=10, fontname="helv")
        ul_y = y + 14
    shape.draw_line((x, ul_y), (x + 70, ul_y)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    if leader_to is not None:
        shape.draw_line((x + 70, ul_y), leader_to); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
        if tick:
            ex, ey = leader_to
            shape.draw_line((ex - 1, ey - 1), (ex + 1, ey + 1)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)


def _scale(page):
    page.insert_text((100, 560), "SKALA 1:50", fontsize=10, fontname="helv")


def test_tick_on_dead_end_stub_is_dn_boundary(tmp_path):
    """Main run S3-R8-110 (two labels). A stub branches off to a dead end; its S3-R8-75 label tick sits 60 pt
    down the stub. The junction's DN flows into the stub up to the tick; beyond the tick the stub is 75."""
    path = os.path.join(tmp_path, "stub.pdf")
    doc = pymupdf.open(); page = doc.new_page(width=842, height=595); shape = page.new_shape()
    make_dashed_line(shape, (100, 300), (700, 300))            # main run, y = 300
    make_dashed_line(shape, (400, 300), (400, 420))            # stub down to a dead end at y = 420
    _label(page, shape, 120, 200, "S3-R8-110", leader_to=(200, 300))
    _label(page, shape, 560, 200, "S3-R8-110", leader_to=(640, 300))
    _label(page, shape, 470, 380, "S3-R8", dn_row="75", leader_to=(400, 360))   # tick 60 pt below the junction
    _scale(page)
    shape.commit(); doc.save(path); doc.close()
    pa = analyze_page(extract_document(path).pages[0])
    q = {(r["base"], r["dn"]): r for r in pa.quantities}
    assert ("S3-R8", 110) in q and ("S3-R8", 75) in q
    # 600 pt main run + 60 pt of stub = 660 pt of DN110 (11.64 m); 60 pt of DN75 (1.06 m); dashes lose the last gap
    assert abs(q[("S3-R8", 110)]["confirmed_horizontal_m"] - 660 / 56.69) < 0.35
    assert abs(q[("S3-R8", 75)]["confirmed_horizontal_m"] - 60 / 56.69) < 0.3
    assert sum(r["ambiguous_m"] for r in pa.quantities) == 0
    reasons = {st.reason for sts in pa.ownership.prim_states.values() for st in sts.values()}
    assert "through_junction_up_to_tick_boundary" in reasons


def test_tick_mid_branch_that_continues_keeps_its_label(tmp_path):
    """Same as above but the branch continues past the tick to another junction: the tick is the label's pointer
    onto this branch, so the whole branch keeps the label's DN (never the main run's DN)."""
    path = os.path.join(tmp_path, "branch.pdf")
    doc = pymupdf.open(); page = doc.new_page(width=842, height=595); shape = page.new_shape()
    make_dashed_line(shape, (100, 300), (700, 300))
    make_dashed_line(shape, (400, 300), (400, 480))
    make_dashed_line(shape, (300, 480), (500, 480))            # the branch ends in a T (continues)
    _label(page, shape, 120, 200, "S3-R8-110", leader_to=(200, 300))
    _label(page, shape, 560, 200, "S3-R8-110", leader_to=(640, 300))
    _label(page, shape, 470, 380, "S3-R8", dn_row="75", leader_to=(400, 360))
    _scale(page)
    shape.commit(); doc.save(path); doc.close()
    pa = analyze_page(extract_document(path).pages[0])
    q = {(r["base"], r["dn"]): r for r in pa.quantities}
    assert abs(q[("S3-R8", 110)]["confirmed_horizontal_m"] - 600 / 56.69) < 0.35
    assert q[("S3-R8", 75)]["confirmed_horizontal_m"] > 180 / 56.69 - 0.4     # the whole branch (180 pt) stays DN75
    ev = [e for sts in pa.ownership.prim_states.values() for st in sts.values() for e in st.evidence]
    assert any("taken_as_label_pointer" in e for e in ev)


def test_dn_row_with_qualifier():
    class R:  # minimal stand-ins: _row_role only reads the text for these cases
        underline = []
    assert _row_role("75(L)", R(), None) == "dn"
    assert _row_role("110", R(), None) == "dn"
    assert _row_role("2ST", R(), None) != "dn"
    assert _row_role("S3-R8-75", R(), None) == "designation"


def test_leader_from_shared_frame_corner_goes_to_block_it_leaves(tmp_path):
    """A designation block and a note block have frame lines meeting at one point; the leader starting there
    belongs to the block it points away from, not to the first block by id."""
    path = os.path.join(tmp_path, "shared.pdf")
    doc = pymupdf.open(); page = doc.new_page(width=842, height=595); shape = page.new_shape()
    make_dashed_line(shape, (100, 400), (700, 400))
    page.insert_text((150, 300), "VS21-S13-15-F50", fontsize=10, fontname="helv")
    shape.draw_line((150, 302), (240, 302)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    page.insert_text((400, 300), "SE PLAN", fontsize=10, fontname="helv")
    shape.draw_line((240, 302), (480, 302)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    # leader from the shared point (240, 302) down-right to the pipe: it leaves the LEFT block only
    shape.draw_line((240, 302), (300, 400)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    shape.draw_line((299, 399), (301, 401)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    # a second label of the same designation elsewhere (tick votes for the pipe family)
    page.insert_text((500, 200), "VS21-S13-15-F50", fontsize=10, fontname="helv")
    shape.draw_line((500, 202), (590, 202)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    shape.draw_line((590, 202), (640, 400)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    shape.draw_line((639, 399), (641, 401)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    _scale(page)
    shape.commit(); doc.save(path); doc.close()
    pa = analyze_page(extract_document(path).pages[0])
    ver = [a for a in pa.anchors if a.state == "VERIFIED_PIPE_ATTACHMENT"]
    assert len(ver) == 2, [(a.designation, a.state, a.reason) for a in pa.anchors]
    assert {a.designation for a in ver} == {"VS21-S13-15-F50"}
    starts = sorted(tuple(round(v) for v in a.endpoint) for a in ver)
    assert starts == [(300, 400), (640, 400)]


def test_hatched_area_is_reported_separately(tmp_path):
    """A pipe whose east half runs through a hatched area (regularly spaced 45-degree strokes) is measured in
    full, and the part inside the hatch is reported separately."""
    path = os.path.join(tmp_path, "hatch.pdf")
    doc = pymupdf.open(); page = doc.new_page(width=842, height=595); shape = page.new_shape()
    make_dashed_line(shape, (100, 300), (700, 300))
    _label(page, shape, 120, 200, "S3-R8-110", leader_to=(200, 300))
    _label(page, shape, 300, 200, "S3-R8-110", leader_to=(380, 300))
    # hatch: 45-degree strokes every 9 pt covering x 400..700, y 150..450
    x = 400 - 300
    while x < 700 + 300:
        x0, y0 = max(400, x), 450 - (max(400, x) - x)
        x1, y1 = min(700, x + 300), 450 - (min(700, x + 300) - x)
        if x1 > x0:
            shape.draw_line((x0, y0), (x1, y1)); shape.finish(width=0.36, color=(0.5, 0.5, 0.5), closePath=False)
        x += 9
    _scale(page)
    shape.commit(); doc.save(path); doc.close()
    pa = analyze_page(extract_document(path).pages[0])
    assert len(pa.hatch_families) == 1 and abs(pa.hatch_families[0].spacing - 9.0 / 2 ** 0.5) < 1.0
    q = {(r["base"], r["dn"]): r for r in pa.quantities}
    row = q[("S3-R8", 110)]
    # horizontal quantity = drawn length outside the hatch (300 pt); the hatched half is reported separately
    assert abs(row["confirmed_horizontal_m"] - 300 / 56.69) < 0.5
    assert abs(row["in_hatched_area_m"] - 300 / 56.69) < 0.5
