"""Determinism: semantic results must not depend on PDF object enumeration order."""
from __future__ import annotations

import copy
import hashlib
import json
import random
from typing import Any

from .pdf.extract import RawDocument
from .pipeline import analyze_page


def semantic_signature(pa) -> dict[str, Any]:
    """Order-independent canonical description of the semantic result."""
    des = sorted((d.text, -1 if d.dn is None else d.dn, tuple(round(v, 1) for v in d.bbox)) for d in pa.designations)
    leaders = sorted((l.family, tuple(round(v, 1) for v in l.start), tuple(round(v, 1) for v in l.end)) for l in pa.leaders)
    anchors = sorted((a.designation, -1 if a.dn is None else a.dn, a.state, tuple(round(v, 1) for v in a.endpoint), tuple(sorted(f"{c.pid}#{c.seg_index}" for c in a.contacts))) for a in pa.anchors)
    fams = sorted(pa.pipe_families)
    pipes = sorted((p.identity.key, round(p.length_pt, 2), tuple(p.source_segments[:4])) for p in pa.ownership.pipes)
    quant = sorted((q["designation"], -1 if q["dn"] is None else q["dn"], q["physical_pipe_count"], round(q["confirmed_horizontal_m"], 2), round(q["ambiguous_m"], 2), q["state"]) for q in pa.quantities)
    topo = sorted((fk, len(g.nodes), len(g.prims), len(g.bridges), len(g.junctions)) for fk, g in pa.graphs.items())
    glyph_fams = sorted((f.char, f.n_members) for f in pa.vtext.families.values())
    sig = {"designations": des, "leaders": leaders, "anchors": anchors, "pipe_families": fams, "physical_pipes": pipes,
           "quantities": quant, "topology": topo, "glyph_families": glyph_fams, "scale": pa.scale.meters_per_pt}
    return sig


def signature_hash(sig: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(sig, sort_keys=True, default=str).encode()).hexdigest()


def _reordered(doc: RawDocument, mode: str, seed: int = 0) -> RawDocument:
    d2 = copy.deepcopy(doc)
    for pg in d2.pages:
        if mode == "reversed":
            pg.paths.reverse(); pg.spans.reverse()
        elif mode == "shuffled":
            rng = random.Random(seed)
            rng.shuffle(pg.paths); rng.shuffle(pg.spans)
    return d2


def run_determinism(doc: RawDocument, page_index: int = 0, base_pa=None) -> dict[str, Any]:
    results = {}
    base = base_pa if base_pa is not None else analyze_page(doc.pages[page_index])
    base_sig = semantic_signature(base)
    results["original"] = signature_hash(base_sig)
    for mode, seed in (("reversed", 0), ("shuffled", 11), ("shuffled", 23)):
        d2 = _reordered(doc, mode, seed)
        pa = analyze_page(d2.pages[page_index])
        sig = semantic_signature(pa)
        key = f"{mode}_seed{seed}" if mode == "shuffled" else mode
        results[key] = signature_hash(sig)
        if results[key] != results["original"]:
            results[f"{key}_diff"] = _diff(base_sig, sig)
    ok = all(v == results["original"] for k, v in results.items() if not k.endswith("_diff"))
    return {"state": "PASS" if ok else "FAIL", "hashes": {k: v for k, v in results.items() if not k.endswith("_diff")},
            "differences": {k: v for k, v in results.items() if k.endswith("_diff")}}


def _diff(a: dict, b: dict) -> dict:
    out = {}
    for k in a:
        if a[k] != b[k]:
            sa, sb = set(map(str, a[k])) if isinstance(a[k], list) else {str(a[k])}, set(map(str, b[k])) if isinstance(b[k], list) else {str(b[k])}
            out[k] = {"only_in_original": sorted(sa - sb)[:10], "only_in_variant": sorted(sb - sa)[:10]}
    return out
