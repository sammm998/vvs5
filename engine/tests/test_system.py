import os

from vvs_engine.contamination import scan_source
from vvs_engine.determinism import run_determinism, semantic_signature, signature_hash
from vvs_engine.pdf.extract import extract_document
from vvs_engine.pipeline import analyze_page


def test_contamination_firewall_clean():
    root = os.path.join(os.path.dirname(__file__), "..", "vvs_engine")
    rep = scan_source(root)
    assert rep["state"] == "PASS", rep["findings"]


def test_no_validation_data_dependency():
    root = os.path.join(os.path.dirname(__file__), "..", "vvs_engine")
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if fn.endswith(".py") and fn != "contamination.py":
                src = open(os.path.join(dirpath, fn), encoding="utf-8").read()
                assert "facit" not in src.lower() and "validation/" not in src


def test_determinism_and_cross_job_isolation(synthetic_pdf):
    doc = extract_document(synthetic_pdf)
    det = run_determinism(doc, 0)
    assert det["state"] == "PASS", det
    # A -> B -> A isolation: analysing another document in between must not change A's result
    h1 = signature_hash(semantic_signature(analyze_page(doc.pages[0])))
    other = extract_document(synthetic_pdf)
    for pg in other.pages:
        pg.paths.reverse()
    analyze_page(other.pages[0])
    h2 = signature_hash(semantic_signature(analyze_page(extract_document(synthetic_pdf).pages[0])))
    assert h1 == h2


def test_an_odd_unresolved_record_never_costs_the_whole_reading(synthetic_pdf):
    """A production job died here: the flow bound filed its case under the primitive id -1, a placeholder that
    meant "this is about the family, not one run", and the issue writer looked -1 up as a real primitive.

    KeyError: -1, and the whole analysis was lost - every metre the sheet had given up, because a note about
    something the reading could NOT do was malformed. The listing of unresolved cases is the least important
    thing in a reading and must never be able to cost the reading itself.
    """
    from vvs_engine.output.artifacts import unresolved_issues

    pa = analyze_page(extract_document(synthetic_pdf).pages[0])
    n_before = len(unresolved_issues(pa))

    pa.ownership.ambiguous_runs.append({"family": "en-familj-som-inte-finns", "chain": -1, "from_prim": -1,
                                        "to_prim": -1, "reason": "AMBIGUOUS_FLOW_BEYOND_THE_LABELLED_RUNS",
                                        "identities": ["X|DN10"]})
    fk = sorted(pa.graphs)[0]
    pa.ownership.ambiguous_runs.append({"family": fk, "chain": -1, "from_prim": -1, "to_prim": -1,
                                        "reason": "AMBIGUOUS_DN_BOUNDARY", "identities": ["Y|DN20"]})

    issues = unresolved_issues(pa)
    assert len(issues) == n_before + 2, "both cases have to be reported, not dropped and not fatal"
    placed = [i for i in issues[n_before:] if i.get("bbox")]
    assert not placed, "a case with no primitive behind it has no place on the sheet, and says so"


def test_every_unresolved_run_names_a_primitive_that_exists(synthetic_pdf):
    """The invariant behind the crash above: a case about geometry has to name geometry that is there."""
    pa = analyze_page(extract_document(synthetic_pdf).pages[0])
    for r in pa.ownership.ambiguous_runs:
        g = pa.graphs.get(r["family"])
        assert g is not None, f"unresolved run names a family that is not in the reading: {r['family']}"
        assert r["from_prim"] in g.prims, f"unresolved run names primitive {r['from_prim']}, which does not exist"
        assert r["to_prim"] in g.prims, f"unresolved run names primitive {r['to_prim']}, which does not exist"
