"""Post-validation generic rules: tick marks as drawn DN boundaries, DN rows with qualifiers, leader start
conflicts, bundle end-marker clusters. Synthetic PDFs only."""
import os

import pymupdf

from vvs_engine.measure.scale import discover_scale
from vvs_engine.pdf.extract import extract_document
from vvs_engine.pipeline import analyze_page
from vvs_engine.semantics.annotation import _row_role
from vvs_engine.text.vector_text import vector_text_rows
from tests.conftest import draw_hershey_text, make_dashed_line


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


def test_scale_bar_is_measured_from_its_own_drawn_extent(tmp_path):
    """The bar is drawn for a whole number of metres; the label glyph centres sit a fraction of a character off
    the graduations. The bar's own extent is the measurement, so the ratio comes out exact."""
    path = os.path.join(tmp_path, "bar.pdf")
    doc = pymupdf.open(); page = doc.new_page(width=842, height=595); shape = page.new_shape()
    span = 5 * 56.69                       # 5 m at 1:50
    for i in range(6):
        page.insert_text((300 + i * span / 5, 560), str(i), fontsize=8, fontname="helv")
    shape.draw_line((301.5, 566), (301.5 + span, 566)); shape.finish(width=1.0, color=(0, 0, 0), closePath=False)
    shape.commit(); doc.save(path); doc.close()
    pg = extract_document(path).pages[0]
    from vvs_engine.text.searchable import searchable_rows
    sc = discover_scale(pg, searchable_rows(pg))
    bar = [e for e in sc.evidence if e.kind == "scale_bar"]
    assert bar and bar[0].detail["measured_from"] == "bar_extent"
    assert abs(bar[0].detail["implied_ratio"] - 50.0) < 0.5


def test_scale_text_selected_by_sheet_format(tmp_path):
    """'SKALA A1 (A3)' over '1:50 (1:100)': the k-th format belongs to the k-th ratio, so an A1 sheet is 1:50.
    Without that pairing two ratios are a conflict and no scale may be assumed."""
    def build(fmt_row):
        path = os.path.join(tmp_path, f"fmt{abs(hash(fmt_row))}.pdf")
        doc = pymupdf.open()
        page = doc.new_page(width=2384, height=1684)          # A1
        page.insert_text((2048, 1600), fmt_row, fontsize=6, fontname="helv")
        page.insert_text((2050, 1612), "1:50 (1:100)", fontsize=9, fontname="helv")
        doc.save(path); doc.close()
        return extract_document(path).pages[0]
    from vvs_engine.text.searchable import searchable_rows
    pg = build("SKALA A1 (A3)")
    sc = discover_scale(pg, searchable_rows(pg))
    assert sc.state == "TEXT_ONLY" and abs(sc.meters_per_pt - 50 * 25.4 / 72 / 1000) < 1e-9
    assert "sheet_format_A1" in sc.reason
    pg = build("SKALA")
    assert discover_scale(pg, searchable_rows(pg)).meters_per_pt is None


def test_long_stroke_never_joins_a_text_row(tmp_path):
    """A frame edge or scale-bar end passing next to a label is drawing geometry: gluing it onto the label as a
    dash would destroy the label (here: the '0' of a scale bar)."""
    path = os.path.join(tmp_path, "stroke.pdf")
    doc = pymupdf.open(); page = doc.new_page(width=842, height=595); shape = page.new_shape()
    draw_hershey_text(shape, "0", 300, 300, 9.0)
    shape.draw_line((300.5, 302), (300.5, 319)); shape.finish(width=0.96, color=(0, 0, 0), closePath=False)
    draw_hershey_text(shape, "2", 340, 300, 9.0)
    draw_hershey_text(shape, "3", 380, 300, 9.0)
    shape.commit(); doc.save(path); doc.close()
    rows = vector_text_rows(extract_document(path).pages[0]).rows
    texts = {r.text for r in rows}
    assert "0" in texts, f"the digit must stay its own row, got {texts}"
    assert not any(len(t) > 1 and t[0] == "-" for t in texts)


def test_designation_clipped_by_a_drawing_boundary_is_completed_from_the_drawing(tmp_path):
    """A sheet-part boundary cuts a label in half: the last character's ink stops dead at the line. The reading
    is completed from what this drawing overwhelmingly writes, never invented, and only for truncated ink."""
    path = os.path.join(tmp_path, "clip.pdf")
    doc = pymupdf.open(); page = doc.new_page(width=842, height=595); shape = page.new_shape()
    for i in range(4):
        y = 120 + i * 40
        b = draw_hershey_text(shape, "KV01-X7-40", 100, y, 7.0)
        shape.draw_line((100, y + 2), (b[2], y + 2)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    y = 300
    b = draw_hershey_text(shape, "KV01-X7-4", 100, y, 7.0)
    cx = b[2]
    half = [(cx + 1.4, y - 7.0), (cx + 0.3, y - 5.6), (cx, y - 3.5), (cx + 0.3, y - 1.4), (cx + 1.4, y)]
    for k in range(len(half) - 1):
        shape.draw_line(half[k], half[k + 1]); shape.finish(width=0.5, color=(0, 0, 0), closePath=False)
    shape.draw_line((cx + 1.5, y - 9), (cx + 1.5, y + 2)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    shape.draw_line((100, y + 2), (cx + 1.5, y + 2)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    page.insert_text((100, 560), "SKALA 1:50", fontsize=10, fontname="helv")
    shape.commit(); doc.save(path); doc.close()
    pa = analyze_page(extract_document(path).pages[0])
    at_clip = [d for d in pa.designations if abs(d.bbox[1] - 293) < 6]
    assert at_clip, "the clipped label must still be read"
    assert at_clip[0].text == "KV01-X7-40" and at_clip[0].dn == 40
    assert sum(1 for d in pa.designations if d.text == "KV01-X7-40") == 5


def test_unlabeled_branch_takes_the_only_junction_identity(tmp_path):
    """A branch with no size label of its own, off a junction where every labelled arm carries the same identity,
    has no competing candidate: a size change is always drawn with its own label. Two candidates stay ambiguous."""
    def build(right_label):
        path = os.path.join(tmp_path, f"br{right_label}.pdf")
        doc = pymupdf.open(); page = doc.new_page(width=842, height=595); shape = page.new_shape()
        make_dashed_line(shape, (100, 300), (700, 300))          # main run through the tee at x = 400
        make_dashed_line(shape, (400, 300), (400, 480))          # branch with no label of its own
        _label(page, shape, 120, 200, "S3-R8-110", leader_to=(200, 300))
        _label(page, shape, 560, 200, right_label, leader_to=(640, 300))
        _scale(page)
        shape.commit(); doc.save(path); doc.close()
        return analyze_page(extract_document(path).pages[0])

    pa = build("S3-R8-110")
    reasons = {st.reason for sts in pa.ownership.prim_states.values() for st in sts.values()}
    assert "unlabeled_branch_takes_the_only_junction_identity" in reasons
    q = {(r["base"], r["dn"]): r for r in pa.quantities}
    assert abs(q[("S3-R8", 110)]["confirmed_horizontal_m"] - (600 + 180) / 56.69) < 0.4
    assert sum(r["ambiguous_m"] for r in pa.quantities) == 0

    # with a second size on the run the DN boundary is drawn at its tick, past the tee, so the tee still sees one
    # identity and the branch is still 110: what the branch may never do is take a size nobody drew on it
    pa = build("S3-R8-75")
    q = {(r["base"], r["dn"]): r for r in pa.quantities}
    assert abs(q[("S3-R8", 110)]["confirmed_horizontal_m"] - (600 - 60 + 180) / 56.69) < 0.25
    assert abs(q[("S3-R8", 75)]["confirmed_horizontal_m"] - 60 / 56.69) < 0.25


def test_dimension_on_the_row_below_is_a_vertical_pipe(tmp_path):
    """Two label forms mean two different things: the dimension inline names the horizontal run, the dimension on
    the row below names the vertical pipe at that point. A count prefix is the exception - it bundles parallel
    pipes along the run, and the reference takeoff gives such a label no vertical metres at all."""
    from vvs_engine.pipeline import _is_vertical_label

    class D:
        def __init__(self, src, dn, mult=1):
            self.dn_source, self.dn, self.multiplier = src, dn, mult

    assert _is_vertical_label(D("row", 75))
    assert not _is_vertical_label(D("inline", 75))
    assert not _is_vertical_label(D("row", 16, mult=2)), "2xKV1-X31 over 16 is a horizontal bundle"
    assert not _is_vertical_label(D("row", None))


def test_both_riser_sources_are_reported_side_by_side(tmp_path):
    """The drawn symbols and the row-below labels disagree, so the quantity carries both counts and the operator
    picks; neither is silently merged into the other."""
    path = os.path.join(tmp_path, "riser.pdf")
    doc = pymupdf.open(); page = doc.new_page(width=842, height=595); shape = page.new_shape()
    make_dashed_line(shape, (100, 300), (700, 300))
    _label(page, shape, 120, 200, "S3-R8-110", leader_to=(200, 300))
    _label(page, shape, 560, 200, "S3-R8", dn_row="75", leader_to=(640, 300))
    _scale(page)
    shape.commit(); doc.save(path); doc.close()
    pa = analyze_page(extract_document(path).pages[0])
    assert all("riser_count" in r and "riser_count_from_labels" in r for r in pa.quantities)
    assert sum(r["riser_count_from_labels"] for r in pa.quantities) >= 1


def test_dimension_row_is_folded_into_the_name():
    """A dimension written on the row below belongs to the code above it: one identity, named with the size."""
    from vvs_engine.semantics.annotation import Designation

    def des(text, dn, src, row_text):
        return Designation(did="d", page=0, block_id="b", row_index=0, text=text, raw_text=text, pattern="",
                           tokens=[], system_token=text.split("-")[0], dn=dn, dn_source=src, dn_row_index=1,
                           dn_row_text=row_text, multiplier=1, bbox=(0, 0, 1, 1), angle=0.0, layer="", source="",
                           glyph_scores=[], unknown_chars=0)
    assert des("KV01-X7", 16, "row", "16").display_text == "KV01-X7-16"
    assert des("KV01-X7", 50, "row", "50/W").display_text == "KV01-X7-50/W"
    assert des("KV01-X7-16", 16, "inline", None).display_text == "KV01-X7-16"
    assert des("KV01-X7", None, None, None).display_text == "KV01-X7"


def test_one_pipe_written_two_ways_is_one_identity():
    """The same pipe labelled inline and with the dimension on the row below must give one identity key, and a
    medium qualifier the recogniser reads badly must not split it in two."""
    from vvs_engine.pipes.ownership import identity_of
    from vvs_engine.semantics.attachment import PipeCodeAnchor

    def anc(designation, display, dn):
        return PipeCodeAnchor(anchor_id="a", page=0, designation_id="d", designation=designation,
                              designation_display=display, system_token=designation.split("-")[0], dn=dn,
                              multiplier=1, block_id="b", leader_id="l", leader_paths=[], endpoint=(0.0, 0.0),
                              state="VERIFIED_PIPE_ATTACHMENT", reason="")
    inline = identity_of(anc("KV01-X7-50/W", "KV01-X7-50/W", 50), 2)
    row = identity_of(anc("KV01-X7", "KV01-X7-50/W", 50), None)
    assert inline.key == row.key == "KV01-X7|DN50"
    assert inline.display == "KV01-X7-50/W"
    misread = identity_of(anc("KV01-X7", "KV01-X7-50ILI", 50), None)
    assert misread.key == "KV01-X7|DN50"


def test_a_word_that_starts_with_a_digit_is_not_a_code():
    """The leading letter separates a designation from a misread word or a date in the title block."""
    from vvs_engine.semantics.grammar import is_code_like
    assert is_code_like("KV01-X7-40") and is_code_like("2xKV01-X7")
    assert not is_code_like("53-R8-75") and not is_code_like("2024-O4-19") and not is_code_like("5PILLVAT")


def test_a_system_with_its_own_layer_is_not_an_abbreviation():
    """A layer token that a longer system name merely ends with is another system when the file names that
    system in full on a layer of its own."""
    from vvs_engine.semantics.attachment import system_layer_match
    assert system_layer_match("KV1", "V-52BB-FE--V1-") == "V1"
    assert system_layer_match("KV1", "V-52BB-FE--V1-", frozenset({"V1"})) == "V1"
    assert system_layer_match("KV1", "V-52BB-FE--V1-", frozenset({"V1", "KV1"})) is None
    assert system_layer_match("FJV1", "V-52BB-FE--V1-", frozenset({"V1", "FJV1"})) is None
    assert system_layer_match("FJV1", "V-56B--FE--FJV1-", frozenset({"V1", "FJV1"})) == "FJV1"
