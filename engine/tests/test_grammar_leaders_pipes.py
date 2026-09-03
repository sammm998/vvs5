import os

import pymupdf

from vvs_engine.pdf.extract import extract_document
from vvs_engine.pipeline import analyze_page
from vvs_engine.semantics.grammar import DesignationGrammar, compress_pattern, is_code_like, strip_count_prefix
from vvs_engine.semantics.attachment import system_layer_match
from vvs_engine.pipes.representation import Prim, build_graph, chains
from vvs_engine.geometry.core import Seg
from tests.conftest import make_dashed_line


def test_pattern_and_count_prefix():
    assert compress_pattern("KV01-X7-40-W40") == "A9-A9-9-A9"
    assert compress_pattern("S3-R8-110") == "A9-A9-9"
    assert strip_count_prefix("5xVV1-X31") == (5, "VV1-X31")
    assert is_code_like("KV01-X7-40") and not is_code_like("2024-04-19") and not is_code_like("MATRUM")


def test_non_pipe_text_rejected_by_structure():
    for t in ("2024-04-19", "A01-038", "ENL. PM-1", "RITNINGSNUMMER", "1:50"):
        assert compress_pattern(t) != "A9-A9-9"


def test_layer_token_matching():
    assert system_layer_match("KV01", "V-52B--FE-_Vxx-KV")
    assert system_layer_match("VS31", "V-56B--FE-_VS3x-")
    assert system_layer_match("VVC01", "V-52B--FE-_Vxx-VVCXX")
    assert system_layer_match("S3", "XX|V-53BB-FE--S3-")
    assert not system_layer_match("KV01", "V-52BB-FE-_KV02-KV"), "layer specific to KV02 must not match KV01"
    assert not system_layer_match("S3", "HUS A - GRUNDPLAN|K-15S---EI_")


def _prims(segs, fam="L|s|w1.44"):
    return [Prim(prim_id=i, pid=f"p{i}", seg_index=0, seg=s, family=fam, layer="L", width=1.44) for i, s in enumerate(segs)]


def test_fragmented_dashes_bridged_with_unique_continuation():
    segs = [Seg(x, 0, x + 12, 0) for x in range(0, 120, 15)]      # dash 12, gap 3
    g = build_graph(_prims(segs), "L|s|w1.44")
    assert g.gap_mode == 3.0 and len(g.bridges) == len(segs) - 1
    assert len(chains(g)) == 1


def test_crossing_is_not_connection_but_t_contact_is():
    segs = [Seg(0, 50, 100, 50), Seg(50, 0, 50, 100)]              # X crossing, no shared endpoint
    g = build_graph(_prims(segs), "f")
    assert max(n.degree for n in g.nodes.values()) == 1
    segs = [Seg(0, 50, 100, 50), Seg(50, 50, 50, 100)]             # T: endpoint on interior -> junction node
    g = build_graph(_prims(segs), "f")
    assert max(n.degree for n in g.nodes.values()) == 3


def test_micro_gap_not_bridged_without_repeated_structure():
    segs = [Seg(0, 0, 40, 0), Seg(43, 0, 80, 0)]                    # only 2 fragments: no gap family evidence
    g = build_graph(_prims(segs), "f")
    assert g.gap_mode is None and not g.bridges


def test_full_pipeline_on_synthetic_drawing(synthetic_pdf):
    rd = extract_document(synthetic_pdf)
    pa = analyze_page(rd.pages[0])
    texts = {d.text for d in pa.designations}
    assert "KV01-X7-40-W40" in texts and "VS21-S13" in texts
    dn = {d.text: d.dn for d in pa.designations}
    assert dn["KV01-X7-40-W40"] == 40 and dn["VS21-S13"] == 15
    assert any(l.end_marks for l in pa.leaders), "end tick marker must be discovered as real geometry"
    ver = [a for a in pa.anchors if a.state == "VERIFIED_PIPE_ATTACHMENT"]
    assert {a.designation for a in ver} >= {"KV01-X7-40-W40", "VS21-S13"}
    assert pa.scale.state == "VERIFIED" and abs(pa.scale.meters_per_pt - 1 / 56.69) / (1 / 56.69) < 0.03
    q = {r["designation"]: r for r in pa.quantities}
    # pipe 1 is 500 pt long -> 8.82 m ; pipe 2 is 200 pt -> 3.53 m (T-junction: pipe 2 becomes AMBIGUOUS_BRANCH? no: it has its own anchor)
    assert abs(q["KV01-X7-40-W40"]["confirmed_horizontal_m"] - 500 / 56.69) < 0.3
    assert abs(q["VS21-S13"]["confirmed_horizontal_m"] - 200 / 56.69) < 0.3
    assert q["VS21-S13"]["vertical_m"] == "UNKNOWN"
    from vvs_engine.reconcile import reconcile
    assert reconcile(pa)["state"] == "VALID"


def test_dn_boundary_at_smaller_dn_tick_not_midpoint(tmp_path):
    """Two tick-labelled DN on one straight run with dead ends both sides: the reduction is drawn at the tick of
    the smaller size, so DN40 runs up to the DN25 tick; nothing is split at an invented midpoint."""
    path = os.path.join(tmp_path, "dn.pdf")
    doc = pymupdf.open(); page = doc.new_page(width=842, height=595); shape = page.new_shape()
    make_dashed_line(shape, (100, 300), (700, 300))
    for x, txt in ((150, "KV01-X7-40-W40"), (550, "KV01-X7-25-W40")):
        page.insert_text((x, 200), txt, fontsize=10, fontname="helv")
        shape.draw_line((x, 202), (x + 80, 202)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
        shape.draw_line((x + 80, 202), (x + 100, 300)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
        shape.draw_line((x + 99, 299), (x + 101, 301)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    page.insert_text((100, 560), "SKALA 1:50", fontsize=10, fontname="helv")
    shape.commit(); doc.save(path); doc.close()
    pa = analyze_page(extract_document(path).pages[0])
    reasons = {st.reason for sts in pa.ownership.prim_states.values() for st in sts.values()}
    assert "dn_boundary_at_smaller_dn_tick" in reasons
    q = {r["dn"]: r for r in pa.quantities}
    # DN40 tick at x=250, DN25 tick at x=650 on a 100..700 run: 40 owns 100..650 (550 pt), 25 owns 650..700 (50 pt)
    assert abs(q[40]["confirmed_horizontal_m"] - 550 / 56.69) < 0.35
    assert abs(q[25]["confirmed_horizontal_m"] - 50 / 56.69) < 0.35
    assert sum(r["ambiguous_m"] for r in pa.quantities) == 0


def test_vertical_from_two_elevations(tmp_path):
    path = os.path.join(tmp_path, "vg.pdf")
    doc = pymupdf.open(); page = doc.new_page(width=842, height=595); shape = page.new_shape()
    make_dashed_line(shape, (100, 300), (700, 300))
    for x, txt, vg in ((150, "S3-R8-110", "VG+1.50"), (550, "S3-R8-110", "VG+1.90")):
        page.insert_text((x, 200), txt, fontsize=10, fontname="helv")
        page.insert_text((x, 212), vg, fontsize=10, fontname="helv")
        shape.draw_line((x, 214), (x + 60, 214)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
        shape.draw_line((x + 60, 214), (x + 100, 300)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
        shape.draw_line((x + 99, 299), (x + 101, 301)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    page.insert_text((100, 560), "SKALA 1:50", fontsize=10, fontname="helv")
    shape.commit(); doc.save(path); doc.close()
    pa = analyze_page(extract_document(path).pages[0])
    q = pa.quantities
    assert len(q) == 1 and q[0]["physical_pipe_count"] == 1
    assert abs(float(q[0]["vertical_m"]) - 0.4) < 1e-6
