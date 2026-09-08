"""The agent's tools, which are the only place its numbers can come from.

The division the whole thing rests on: the model decides what to ask, these functions decide what the answer is.
So the contract is tested like any other measurement - a tool that quietly disagrees with the takeoff table would
put a number on screen that no artifact backs.
"""
import os

from vvs_engine.agent import tools as T
from vvs_engine.agent.model import DrawingModel
from vvs_engine.cli import analyze_pdf

_CACHE: dict[str, DrawingModel] = {}


def _read(tmp_path, synthetic_pdf) -> DrawingModel:
    """A whole reading, written out as the service writes it - the tools read artifacts, not objects."""
    if synthetic_pdf not in _CACHE:
        out = os.path.join(tmp_path, "res")
        os.makedirs(out, exist_ok=True)
        analyze_pdf(synthetic_pdf, out, name="test", determinism=False, contamination=False, review=False)
        _CACHE[synthetic_pdf] = DrawingModel(out)
    return _CACHE[synthetic_pdf]


def test_the_contract_is_a_contract(tmp_path, synthetic_pdf):
    """Every tool carries a name, a description and a parameter schema a model can call it by."""
    for name, t in T.TOOLS.items():
        assert t["description"].strip(), f"{name} says nothing about what it does"
        p = t["parameters"]
        assert p["type"] == "object" and isinstance(p["properties"], dict)
        assert p["additionalProperties"] is False, f"{name} would accept arguments it does not have"
    assert len(T.schemas()) == len(T.TOOLS)


def test_the_agent_and_the_table_cannot_disagree(tmp_path, synthetic_pdf):
    """What the agent says a designation measures is what the takeoff says it measures."""
    m = _read(tmp_path, synthetic_pdf)
    rows = m.quantities.get("rows") or []
    if not rows:
        return
    row = max(rows, key=lambda r: r.get("confirmed_total_m") or 0)
    out = T.run("visa_hur_mangden_raknades", m, {"beteckning": row["designation"]})
    assert abs(out["summa_m"] - row["confirmed_total_m"]) < 1e-6
    per_run = sum(s["horizontal_m"] for s in out["stracker"])
    assert abs(per_run - out["summa_m"]) < 0.02, "sträckorna ska summera till det tabellen visar"


def test_a_quantity_grouped_any_way_is_the_same_total(tmp_path, synthetic_pdf):
    m = _read(tmp_path, synthetic_pdf)
    a = T.run("mangda", m, {"gruppera_pa": "beteckning"})["summa_m"]
    b = T.run("mangda", m, {"gruppera_pa": "system"})["summa_m"]
    c = T.run("mangda", m, {"gruppera_pa": "dimension"})["summa_m"]
    assert abs(a - b) < 1e-6 and abs(a - c) < 1e-6


def test_an_unknown_tool_is_an_answer_not_a_crash(tmp_path, synthetic_pdf):
    m = _read(tmp_path, synthetic_pdf)
    out = T.run("finns_inte", m, {})
    assert "fel" in out and out["tillgangliga"]
    bad = T.run("hamta_ror", m, {"ror_id": "pp_saknas"})
    assert "fel" in bad


def test_the_agent_never_measures_anything_itself(tmp_path, synthetic_pdf):
    """A tool may only report what the artifacts hold: no tool may invent a run the reading did not produce."""
    m = _read(tmp_path, synthetic_pdf)
    known = {p["physical_pipe_id"] for p in m.pipes}
    for name in ("hitta_ror", "hitta_fria_rorandar", "hitta_dimensionsbyten"):
        out = T.run(name, m, {})
        for key in ("ror", "andar", "granser"):
            for row in out.get(key) or []:
                if isinstance(row, dict) and row.get("pipe_id"):
                    assert row["pipe_id"] in known, f"{name} hittade på ett rör-id"


def test_the_graph_answers_what_connects_to_what(tmp_path, synthetic_pdf):
    m = _read(tmp_path, synthetic_pdf)
    if not m.pipes:
        return
    pid = max(m.pipes, key=lambda p: len(m.adjacency.get(p["physical_pipe_id"], [])))["physical_pipe_id"]
    net = T.run("folj_natet", m, {"ror_id": pid})
    assert any(r["pipe_id"] == pid for r in net["ror"]), "ett rör hänger alltid ihop med sig självt"
    for nb in T.run("grannar", m, {"ror_id": pid})["ror"]:
        assert nb["pipe_id"] in {r["pipe_id"] for r in net["ror"]}, "en granne ligger i samma nät"
