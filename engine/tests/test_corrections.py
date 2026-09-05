"""What a person's correction is allowed to do - and, more importantly, what it is not."""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vvs_engine.corrections import apply
from vvs_engine.learning import lessons, settle, situation

MPP = 0.0176389        # 1:50


def _q(name, m):
    return {"designation": name, "base": name.rsplit("-", 1)[0], "dn": 110, "state": "CONFIRMED",
            "confirmed_horizontal_m": m, "confirmed_vertical_m": 0.0, "confirmed_total_m": m,
            "ambiguous_m": 0.0, "in_hatched_area_m": 0.0, "physical_pipe_count": 1, "label_count": 1,
            "risers_calc": 0, "riser_count": 0, "riser_count_from_labels": 0}


def test_a_correction_never_hides_what_the_engine_read():
    out = apply([_q("S3-R8-110", 10.0)],
                [{"id": "c1", "kind": "quantity", "designation": "S3-R8-110", "payload": {"meters": 12.0}}], MPP)
    row = out["quantities"][0]
    assert row["confirmed_total_m"] == 12.0
    assert row["engine_total_m"] == 10.0, "the engine's own figure has to survive the correction"
    assert row["corrected"] is True and out["applied"][0]["applied"] is True


def test_drawing_a_run_the_engine_missed_adds_its_own_length():
    pts = [[0.0, 0.0], [100.0, 0.0]]                      # 100 pt at 1:50 is 1.76 m
    out = apply([], [{"id": "c1", "kind": "draw", "designation": "KV1-X31-16", "payload": {"points": pts}}], MPP)
    row = out["quantities"][0]
    assert row["confirmed_total_m"] == round(100 * MPP, 3)   # metres are kept to the millimetre
    assert row["engine_total_m"] == 0.0 and row["from_correction"] is True


def test_retagging_moves_metres_rather_than_inventing_them():
    out = apply([_q("S3-R8-110", 10.0), _q("S3-R8-75", 4.0)],
                [{"id": "c1", "kind": "retag", "designation": "S3-R8-75",
                  "payload": {"from": "S3-R8-110", "meters": 3.0}}], MPP)
    rows = {r["designation"]: r for r in out["quantities"]}
    assert rows["S3-R8-110"]["confirmed_total_m"] == 7.0
    assert rows["S3-R8-75"]["confirmed_total_m"] == 7.0
    assert out["corrected_total_m"] == out["engine_total_m"], "retagging moves length, it does not create it"


def test_an_undone_correction_stops_counting():
    c = {"id": "c1", "kind": "quantity", "designation": "S3-R8-110", "payload": {"meters": 99.0}, "undone": True}
    out = apply([_q("S3-R8-110", 10.0)], [c], MPP)
    assert out["quantities"][0]["confirmed_total_m"] == 10.0


def test_a_lesson_only_forms_when_a_person_answered_the_same_way_twice_over():
    sit = situation(family="V-52|s|w1.44|c(0,0,0)", reason="multi_row_no_compatible_layer_group",
                    designation="KV1-X31-16")
    same = [{"kind": "retag", "designation": "KV1-X31-16", "situation": sit} for _ in range(2)]
    assert lessons(same) == [{**sit, "answer": "KV1-X31-16", "times": 2}]
    mixed = same + [{"kind": "retag", "designation": "VV1-X31-16", "situation": sit}]
    assert lessons(mixed) == [], "a situation answered two ways teaches nothing; the disagreement is the finding"


def test_the_shape_of_a_name_is_what_carries_between_drawings_not_its_numbers():
    a = situation(family="x|s|w1.44|c(0,0,0)", reason="r", designation="KV1-X31-16")
    b = situation(family="x|s|w1.44|c(0,0,0)", reason="r", designation="KV2-X31-25")
    c = situation(family="x|s|w1.44|c(0,0,0)", reason="r", designation="S3-R8-110")
    assert a == b, "two tap-water labels of the same shape are the same situation"
    assert a != c, "a differently shaped designation is a different situation"


def test_a_lesson_may_settle_an_ambiguous_case_but_never_name_geometry_on_its_own():
    sit = situation(family="V|s|w1.44|c(0,0,0)", reason="system_conflict:layer_matches_S3_not_B1",
                    designation="KV1-X31-16")
    taught = lessons([{"kind": "retag", "designation": "KV1-X31-16", "situation": sit}])
    keys = ("family_style", "reason", "designation_shape")
    case = {"id": "a1", "situation": sit, "candidates": ["KV1-X31-16", "VV1-X31-16"]}
    assert settle([case], taught) == [{"case": "a1", "answer": "KV1-X31-16", "times": 1,
                                       "situation": {k: sit[k] for k in keys},
                                       "why": "en person svarade så i samma situation på en tidigare ritning"}]
    assert settle([{"id": "a2", "situation": sit, "candidates": ["S1-P2-110"]}], taught) == [], \
        "the drawing does not offer this answer, so the lesson stays silent rather than naming the run"
    other = dict(sit, family_style="w0.24|c(0,0,0)")
    assert settle([{"id": "a3", "situation": other, "candidates": ["KV1-X31-16"]}], taught) == [], \
        "a different pen is a different situation, however similar the rest looks"


def test_a_case_with_no_situation_is_never_settled_by_a_lesson():
    taught = lessons([{"kind": "retag", "designation": "KV1-X31-16",
                       "situation": situation(family="f", reason="r", designation="KV1-X31-16")}])
    assert settle([{"id": "x", "candidates": ["KV1-X31-16"]}], taught) == []
