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
