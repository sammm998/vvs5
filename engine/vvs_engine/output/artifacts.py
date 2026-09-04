"""Artifact writers: all per-drawing JSON / markdown outputs and the evidence graph."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from collections import Counter
from typing import Any

from .. import __version__
from ..profile.layers import layer_tokens
from ..semantics.leaders import leader_family_report


def _dump(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, sort_keys=False, default=str)


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def drawing_profile(pa, doc) -> dict[str, Any]:
    page = pa.page
    des_fams = Counter(d.family for d in pa.designations)
    anchors_by_des = {}
    for a in pa.anchors:
        anchors_by_des.setdefault(a.designation_id, []).append(a.state)
    def fam_stats(fam):
        ds = [d for d in pa.designations if d.family == fam]
        conf = sum(1 for d in ds if any(s == "VERIFIED_PIPE_ATTACHMENT" for s in anchors_by_des.get(d.did, [])))
        amb = sum(1 for d in ds if any(s == "AMBIGUOUS_PIPE_ATTACHMENT" for s in anchors_by_des.get(d.did, [])) and not any(s == "VERIFIED_PIPE_ATTACHMENT" for s in anchors_by_des.get(d.did, [])))
        return {"family": fam, "occurrences": len(ds), "processed": len(ds), "confirmed": conf, "ambiguous": amb, "unsupported": len(ds) - conf - amb,
                "examples": sorted({d.text for d in ds})[:6]}
    text_fams = Counter(r.family for r in pa.lines)
    leader_rep = leader_family_report(pa.leaders)
    ld_state = {}
    for a in pa.anchors:
        ld_state.setdefault(a.leader_id, set()).add(a.state)
    lfam_rows = []
    for f in leader_rep["families"]:
        fam = f["family"]
        lids = [l.lid for l in pa.leaders if l.family == fam]
        conf = sum(1 for l in lids if "VERIFIED_PIPE_ATTACHMENT" in ld_state.get(l, set()))
        amb = sum(1 for l in lids if "AMBIGUOUS_PIPE_ATTACHMENT" in ld_state.get(l, set()) and "VERIFIED_PIPE_ATTACHMENT" not in ld_state.get(l, set()))
        lfam_rows.append({"family": fam, "occurrences": len(lids), "processed": len(lids), "confirmed": conf, "ambiguous": amb, "unsupported": len(lids) - conf - amb})
    marker_fams = Counter()
    for l in pa.leaders:
        for m in l.end_marks:
            marker_fams[f"end-tick|{m.layer}|{m.style}"] += 1
        for m in l.crossing_marks:
            marker_fams[f"crossing-tick|{m.layer}|{m.style}"] += 1
    pipe_fams = []
    for fk, rf in pa.pipe_families.items():
        sts = pa.ownership.prim_states[fk]
        pipe_fams.append({**rf.as_dict(), "occurrences": rf.n_prims, "processed": rf.n_prims,
                          "confirmed": sum(1 for s in sts.values() if s.state == "CONFIRMED"),
                          "ambiguous": sum(1 for s in sts.values() if s.state == "AMBIGUOUS"),
                          "unsupported": 0, "unowned": sum(1 for s in sts.values() if s.state == "UNOWNED"),
                          "system_tokens": [t for t in layer_tokens(rf.layer) if len(t) >= 2]})
    unsupported = []
    for fam, n in des_fams.items():
        st = fam_stats(fam)
        if st["confirmed"] == 0 and st["ambiguous"] == 0 and n >= 3:
            unsupported.append({"family": fam, "kind": "code family without any verified pipe attachment (component tags / non-pipe codes)", "occurrences": n, "examples": st["examples"]})
    layers = []
    for name, st in sorted(pa.layer_stats.items()):
        role = "UNKNOWN"
        fams_here = [fk for fk in pa.pipe_families if fk.startswith(name + "|")]
        if fams_here:
            role = "PIPE_GEOMETRY"
        elif any(k.startswith(name + "|") for k in pa.ann_layers):
            role = "VVS_ANNOTATION"
        elif any(m.layer == name for l in pa.leaders for m in l.end_marks + l.crossing_marks):
            role = "CONNECTOR"
        layers.append({**st.as_dict(), "role": role})
    return {
        "engine_version": __version__,
        "page_structure": {"page": page.info.index, "width_pt": page.info.width, "height_pt": page.info.height, "rotation": page.info.rotation,
                           "mediabox": page.info.mediabox, "cropbox": page.info.cropbox, "n_pages": doc.n_pages, "format": _fmt(page)},
        "input": {"mode": "vector", "classification": getattr(page, "input_class", None)},
        "cad_structure": {"n_ocgs": len(doc.ocgs), "n_layers_with_geometry": len(pa.layer_stats), "n_xobjects": page.info.n_xobjects,
                          "layers": layers, "annotation_layers": pa.ann_layers},
        "text_structure": {"searchable_spans": len(page.spans), "searchable_rows": len(pa.srows), "vector_glyph_rows": len(pa.vtext.rows),
                           "glyph_components": pa.vtext.n_components, "glyphs": pa.vtext.n_glyphs, "glyph_families": len(pa.vtext.families),
                           "unknown_glyph_families": pa.vtext.stats.get("unknown_families"), "size_families_pt": pa.vtext.size_families,
                           "text_families": [{"family": k, "occurrences": v} for k, v in text_fams.most_common(20)],
                           "marks": len(pa.vtext.marks), "rejected_rows": len(pa.vtext.rejected_rows)},
        "annotation_structure": {"blocks": len(pa.blocks), "designation_grammar_families": [fam_stats(f) for f in sorted(des_fams, key=lambda f: -des_fams[f])],
                                 "grammar": pa.grammar.as_dict(), "leader_families": lfam_rows,
                                 "marker_families": [{"family": k, "occurrences": v} for k, v in marker_fams.most_common()],
                                 "dn_layouts": dict(Counter(d.dn_source or "none" for d in pa.designations))},
        "pipe_structure": {"representation_families": pipe_fams, "contact_votes": pa.contact_stats,
                           "junction_convention": "shared endpoints and endpoint-on-interior T contacts are nodes; crossings are never connections",
                           "hatched_areas": [h.as_dict() for h in pa.hatch_families]},
        "measurement": {"scale": pa.scale.as_dict(), "vertical_evidence": {"kind": "elevation annotations in label units", "anchors_with_elevation": len(pa.elevations)}},
        "unknown_structure": {"unsupported_families": unsupported,
                              "unresolved_anchor_reasons": dict(Counter(a.reason for a in pa.anchors if a.state != "VERIFIED_PIPE_ATTACHMENT"))},
    }


def _fmt(page):
    from ..measure.scale import _page_format
    return _page_format(page)


def profile_report_md(prof: dict, name: str) -> str:
    L = [f"# Drawing profile: {name}", "", f"Engine {prof['engine_version']}", "",
         "## Page structure", f"- size: {prof['page_structure']['width_pt']} x {prof['page_structure']['height_pt']} pt ({prof['page_structure']['format']}), rotation {prof['page_structure']['rotation']}, pages {prof['page_structure']['n_pages']}",
         "", "## CAD structure", f"- OCGs: {prof['cad_structure']['n_ocgs']}, layers with geometry: {prof['cad_structure']['n_layers_with_geometry']}, XObjects: {prof['cad_structure']['n_xobjects']}",
         f"- annotation layers (drawing-derived): {', '.join(sorted(prof['cad_structure']['annotation_layers'])) or 'none'}", "",
         "## Text structure", f"- searchable spans: {prof['text_structure']['searchable_spans']}, vector glyph rows: {prof['text_structure']['vector_glyph_rows']}, glyphs: {prof['text_structure']['glyphs']}, glyph families: {prof['text_structure']['glyph_families']} (unknown {prof['text_structure']['unknown_glyph_families']})",
         f"- glyph size families (pt): {prof['text_structure']['size_families_pt']}", "",
         "## Designation grammar families", "| pattern | occurrences | processed | confirmed | ambiguous | unsupported | examples |", "|---|---|---|---|---|---|---|"]
    for f in prof["annotation_structure"]["designation_grammar_families"]:
        L.append(f"| {f['family']} | {f['occurrences']} | {f['processed']} | {f['confirmed']} | {f['ambiguous']} | {f['unsupported']} | {', '.join(f['examples'])} |")
    L += ["", "## Leader families", "| family | occurrences | processed | confirmed | ambiguous | unsupported |", "|---|---|---|---|---|---|"]
    for f in prof["annotation_structure"]["leader_families"]:
        L.append(f"| {f['family']} | {f['occurrences']} | {f['processed']} | {f['confirmed']} | {f['ambiguous']} | {f['unsupported']} |")
    L += ["", "## Marker / connector families"] + [f"- {m['family']}: {m['occurrences']}" for m in prof["annotation_structure"]["marker_families"]]
    L += ["", "## Pipe representation families", "| family | kind | primitives | length pt | gap | confirmed | ambiguous | unowned |", "|---|---|---|---|---|---|---|---|"]
    for f in prof["pipe_structure"]["representation_families"]:
        L.append(f"| {f['family']} | {f['kind']} | {f['n_primitives']} | {f['total_length_pt']} | {f['gap_mode_pt']} | {f['confirmed']} | {f['ambiguous']} | {f['unowned']} |")
    sc = prof["measurement"]["scale"]
    L += ["", "## Scale", f"- state: {sc['state']} ({sc['reason']}), meters per PDF point: {sc['meters_per_pdf_point']}"]
    for e in sc["evidence"]:
        L.append(f"  - {e['kind']}: '{e['text']}' -> {e['meters_per_pt']} m/pt {e['detail']}")
    L += ["", "## Unsupported / unknown structure"]
    for u in prof["unknown_structure"]["unsupported_families"]:
        L.append(f"- {u['family']}: {u['kind']} ({u['occurrences']}; e.g. {', '.join(u['examples'])})")
    L.append(f"- unresolved anchor reasons: {prof['unknown_structure']['unresolved_anchor_reasons']}")
    return "\n".join(L) + "\n"


def evidence_graph(pa) -> dict[str, Any]:
    nodes = []
    edges = []
    def add(nid, kind, **attrs):
        nodes.append({"id": nid, "kind": kind, **attrs})
    des_by_id = {d.did: d for d in pa.designations}
    anc_by_id = {a.anchor_id: a for a in pa.anchors}
    ld_by_id = {l.lid: l for l in pa.leaders}
    for p in pa.ownership.pipes:
        add(p.physical_pipe_id, "PHYSICAL_PIPE", identity=p.identity.key, designation=p.identity.display, dn=p.identity.dn, length_pt=round(p.length_pt, 2), family=p.family)
        add(f"family:{p.family}", "DRAWING_FAMILY", family=p.family)
        edges.append({"from": f"family:{p.family}", "to": p.physical_pipe_id, "rel": "PIPE_GEOMETRY_OF"})
        for seg in p.source_segments[:50]:
            add(f"raw:{seg}", "RAW_PDF_OBJECT", segment=seg)
            edges.append({"from": f"raw:{seg}", "to": p.physical_pipe_id, "rel": "SOURCE_OF"})
        for aid in p.anchor_ids:
            a = anc_by_id.get(aid)
            if not a:
                continue
            add(aid, "PIPE_ATTACHMENT", state=a.state, endpoint=list(a.endpoint))
            edges.append({"from": aid, "to": p.physical_pipe_id, "rel": "OWNS"})
            d = des_by_id.get(a.designation_id)
            if d:
                add(d.did, "DESIGNATION", text=d.text, dn=d.dn, source=d.source, bbox=list(d.bbox))
                edges.append({"from": d.did, "to": aid, "rel": "LABELS"})
                for pid in d.tokens and []:
                    pass
                for prov in sorted(set(sum([g.path_ids for g in [] ], [])))[:0]:
                    pass
            ld = ld_by_id.get(a.leader_id)
            if ld:
                add(ld.lid, "ACTUAL_LEADER", family=ld.family, paths=ld.path_ids, endpoint=list(ld.end))
                edges.append({"from": d.did if d else aid, "to": ld.lid, "rel": "HAS_LEADER"})
                edges.append({"from": ld.lid, "to": aid, "rel": "ENDS_AT"})
                for pid in ld.path_ids:
                    add(f"raw:{pid}", "RAW_PDF_OBJECT", path=pid)
                    edges.append({"from": f"raw:{pid}", "to": ld.lid, "rel": "SOURCE_OF"})
        add("scale", "SCALE", **pa.scale.as_dict())
        edges.append({"from": "scale", "to": p.physical_pipe_id, "rel": "MEASURES"})
    # dedupe nodes
    seen = {}
    for n in nodes:
        seen.setdefault(n["id"], n)
    return {"nodes": list(seen.values()), "edges": edges}


def why(pa, pipe_id: str) -> dict[str, Any]:
    p = next((x for x in pa.ownership.pipes if x.physical_pipe_id == pipe_id), None)
    if p is None:
        return {"error": "unknown pipe id", "pipe_id": pipe_id}
    anc = [a for a in pa.anchors if a.anchor_id in p.anchor_ids]
    des = {d.did: d for d in pa.designations}
    lds = {l.lid: l for l in pa.leaders}
    chain = []
    for a in anc:
        d = des.get(a.designation_id)
        ld = lds.get(a.leader_id)
        b = next((b for b in pa.blocks if b.bid == a.block_id), None)
        chain.append({
            "designation": d.as_dict() if d else None,
            "glyph_or_text_evidence": {"source": d.source if d else None, "provenance_paths": (next((r.line.provenance for r in b.rows if r.line.rid and d and r.line.bbox == d.bbox), [])[:40] if b and d else [])},
            "dn": {"value": a.dn, "source": d.dn_source if d else None},
            "leader": ld.as_dict() if ld else None,
            "attachment": a.as_dict(),
        })
    m = next((m for m in pa.measures if m.pipe.physical_pipe_id == pipe_id), None)
    return {"pipe_id": pipe_id, "identity": p.identity.key, "designation": p.identity.display, "dn": p.identity.dn, "family": p.family,
            "evidence_chain": chain, "topology": {"nodes": p.nodes, "primitives": len(p.prim_ids), "evidence": p.evidence},
            "source_paths": p.source_paths, "source_segments": p.source_segments,
            "scale": pa.scale.as_dict(),
            "measurement": {"horizontal_pdf_units": round(p.length_pt, 3), "raw_pt": round(p.raw_length_pt, 3), "bridged_gap_pt": round(p.bridged_gap_pt, 3),
                            "horizontal_m": m.horizontal_m if m else None, "vertical_m": m.vertical_m if m else None,
                            "vertical_evidence": m.vertical_evidence if m else None, "state": m.state if m else None}}


def unresolved_issues(pa) -> list[dict]:
    issues = []
    # Unknown glyph shapes: hundreds of one-line entries drown the list, and most sit in legend text or notes that
    # never reach the takeoff. Report one entry for the shapes that break a designation and one for the rest.
    unknown_fams = [f for f in pa.vtext.families.values() if f.char == "?" and f.n_members >= 2]
    if unknown_fams:
        in_designation = sum(d.unknown_chars for d in pa.designations)
        total = sum(f.n_members for f in unknown_fams)
        if in_designation:
            first = next((d for d in pa.designations if d.unknown_chars), None)
            issues.append({"kind": "unknown_glyph_in_designation", "count": in_designation,
                           "families": len(unknown_fams), "bbox": list(first.bbox) if first else None,
                           "reason": "tecken som inte kunde namnges sitter i en beteckning och gör den oläsbar"})
        rest = total - in_designation
        if rest > 0:
            issues.append({"kind": "unknown_glyph_elsewhere", "count": rest, "families": len(unknown_fams),
                           "reason": "tecken som inte kunde namnges i legend, noter eller ramtext; påverkar inte mängden"})
    for d in pa.designations:
        if d.unknown_chars:
            issues.append({"kind": "uncertain_designation", "text": d.text, "bbox": list(d.bbox), "id": d.did})
        elif d.dn is None:
            issues.append({"kind": "missing_dn", "text": d.text, "bbox": list(d.bbox), "id": d.did})
    with_leader = {a.designation_id for a in pa.anchors}
    for d in pa.designations:
        if d.did not in with_leader:
            issues.append({"kind": "missing_leader", "text": d.text, "bbox": list(d.bbox), "id": d.did})
    for a in pa.anchors:
        if a.state == "AMBIGUOUS_PIPE_ATTACHMENT":
            issues.append({"kind": "ambiguous_pipe_attachment", "text": a.designation, "reason": a.reason, "bbox": [a.endpoint[0] - 5, a.endpoint[1] - 5, a.endpoint[0] + 5, a.endpoint[1] + 5], "id": a.anchor_id})
        elif a.state == "NO_PIPE_ATTACHMENT":
            issues.append({"kind": "missing_pipe_attachment", "text": a.designation, "reason": a.reason, "bbox": [a.endpoint[0] - 5, a.endpoint[1] - 5, a.endpoint[0] + 5, a.endpoint[1] + 5], "id": a.anchor_id})
    for r in pa.ownership.ambiguous_runs:
        g = pa.graphs[r["family"]]
        s = g.prims[r["from_prim"]].seg
        issues.append({"kind": "dn_conflict" if r["reason"] == "AMBIGUOUS_DN_BOUNDARY" else "topology_conflict", "reason": r["reason"], "identities": r["identities"],
                       "bbox": [s.x0 - 5, s.y0 - 5, s.x1 + 5, s.y1 + 5], "id": f"run:{r['family']}:{r['from_prim']}"})
    # branch conflicts + unowned geometry (aggregate per family chain)
    for fk, sts in pa.ownership.prim_states.items():
        g = pa.graphs[fk]
        branch = [pid for pid, st in sts.items() if st.state == "AMBIGUOUS" and st.reason == "AMBIGUOUS_BRANCH"]
        if branch:
            pid = branch[0]; s = g.prims[pid].seg
            issues.append({"kind": "branch_conflict", "family": fk, "count": len(branch), "bbox": [s.x0 - 5, s.y0 - 5, s.x1 + 5, s.y1 + 5], "id": f"branch:{fk}"})
        un = [pid for pid, st in sts.items() if st.state == "UNOWNED"]
        if un:
            L = sum(g.prims[p].seg.length for p in un)
            pid = un[0]; s = g.prims[pid].seg
            issues.append({"kind": "unowned_geometry", "family": fk, "count": len(un), "length_pt": round(L, 1), "bbox": [s.x0 - 5, s.y0 - 5, s.x1 + 5, s.y1 + 5], "id": f"unowned:{fk}"})
    if pa.scale.state in ("NONE", "CONFLICT"):
        issues.append({"kind": "unsupported_structural_family", "text": f"scale: {pa.scale.reason}", "id": "scale"})
    return issues


def write_all(pdf_path: str, doc, analyses: list, out_dir: str, name: str, timings: dict, determinism: dict | None,
              contamination: dict | None, overlays: dict, config: dict, review: dict | None = None) -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    pa = analyses[0]
    files: dict[str, str] = {}
    def W(fn, obj):
        path = os.path.join(out_dir, fn); _dump(path, obj); files[fn] = path
    prof = drawing_profile(pa, doc)
    W("drawing-profile.json", prof)
    with open(os.path.join(out_dir, "drawing-profile-report.md"), "w", encoding="utf-8") as fh:
        fh.write(profile_report_md(prof, name))
    files["drawing-profile-report.md"] = os.path.join(out_dir, "drawing-profile-report.md")
    W("raw-vector-inventory.json", doc.inventory())
    W("cad-layer-map.json", {"layers": [{"layer": k, **v.as_dict(), "role": next((l["role"] for l in prof["cad_structure"]["layers"] if l["layer"] == k), "UNKNOWN")} for k, v in sorted(pa.layer_stats.items())],
                              "annotation_layers": pa.ann_layers, "pipe_families": sorted(pa.pipe_families)})
    W("vector-designations.json", {"designations": [d.as_dict() for d in pa.designations], "text_rows": [r.as_dict() for r in pa.lines]})
    W("drawing-legend.json", pa.legend.as_dict())
    W("leader-forensics.json", {"leaders": [l.as_dict() for l in pa.leaders]})
    W("leader-family-report.json", leader_family_report(pa.leaders))
    W("pipe-code-anchors.json", {"anchors": [a.as_dict() for a in pa.anchors]})
    W("pipe-representation-families.json", {"families": [rf.as_dict() for rf in pa.pipe_families.values()]})
    inv = []
    from ..profile.hatch import inside_hatch
    for fk, g in pa.graphs.items():
        for pid, q in g.prims.items():
            st = pa.ownership.prim_states[fk][pid]
            inv.append({"family": fk, "prim": pid, "pid": q.pid, "seg": q.seg_index, "x0": round(q.seg.x0, 2), "y0": round(q.seg.y0, 2), "x1": round(q.seg.x1, 2), "y1": round(q.seg.y1, 2),
                        "length": round(q.seg.length, 3), "state": st.state, "identity": st.identity.key if st.identity else None,
                        "candidates": sorted(c.key for c in st.candidates), "reason": st.reason,
                        "in_hatch": bool(pa.hatch_families) and inside_hatch(pa.hatch_families, *q.seg.mid) is not None})
    W("pipe-geometry-inventory.json", {"primitives": inv})
    W("pipe-topology.json", {"families": [{"family": fk, "nodes": [{"id": n.nid, "x": round(n.x, 2), "y": round(n.y, 2), "degree": n.degree, "prims": n.prims} for n in g.nodes.values()],
                                            "edges": [{"prim": pid, "a": ab[0], "b": ab[1]} for pid, ab in g.prim_nodes.items()], "bridges": g.bridges, "junctions": g.junctions, "gap_mode": g.gap_mode}
                                           for fk, g in pa.graphs.items()]})
    W("physical-pipes.json", {"physical_pipes": [physical_pipe_dict(m) for m in pa.measures]})
    W("quantities.json", {"scale": pa.scale.as_dict(), "rows": pa.quantities,
                          "totals": {"physical_pipes": len(pa.measures),
                                     "confirmed_horizontal_m": round(sum(q["confirmed_horizontal_m"] for q in pa.quantities), 3),
                                     "confirmed_vertical_m": round(sum(q["confirmed_vertical_m"] for q in pa.quantities), 3),
                                     "confirmed_total_m": round(sum(q["confirmed_total_m"] for q in pa.quantities), 3),
                                     "ambiguous_m": round(sum(q["ambiguous_m"] for q in pa.quantities), 3),
                                     "in_hatched_area_m": round(sum(q.get("in_hatched_area_m", 0.0) for q in pa.quantities), 3),
                                     "riser_labels": sum(q.get("riser_count", 0) for q in pa.quantities)},
                          "hatched_areas": [h.as_dict() for h in pa.hatch_families],
                          "risers": pa.risers})
    W("unresolved-issues.json", {"issues": unresolved_issues(pa)})
    if review is not None:
        W("review-findings.json", review)
    if getattr(pa, "ocr_assist", None) is not None:
        W("ocr-assisted-characters.json", pa.ocr_assist)
    W("evidence-graph.json", evidence_graph(pa))
    from ..reconcile import reconcile
    W("reconciliation.json", reconcile(pa))
    W("route-crosscheck.json", pa.crosscheck)
    W("reading-review.json", pa.review_findings)
    if determinism is not None:
        W("determinism.json", determinism)
    if contamination is not None:
        W("contamination-report.json", contamination)
    W("performance-report.json", performance_report(pa, timings))
    for k, v in overlays.items():
        files[k] = v
    with open(os.path.join(out_dir, "analysis-report.md"), "w", encoding="utf-8") as fh:
        fh.write(analysis_report_md(pa, name, timings, determinism, contamination, files))
    files["analysis-report.md"] = os.path.join(out_dir, "analysis-report.md")
    # freeze manifest
    manifest = {"state": "BLIND_FROZEN", "drawing": name, "input_pdf_sha256": _sha(pdf_path), "source_revision": source_revision(),
                "engine_version": __version__, "configuration": config, "python": platform.python_version(), "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "artifacts": {fn: _sha(path) for fn, path in sorted(files.items())}}
    W("freeze-manifest.json", manifest)
    return files


def physical_pipe_dict(m) -> dict[str, Any]:
    p = m.pipe
    return {"physical_pipe_id": p.physical_pipe_id, "page": p.page, "system": p.identity.system, "designation": p.identity.display,
            "identity": p.identity.key, "dn": p.identity.dn, "supporting_anchors": p.anchor_ids, "representation_family": p.family,
            "geometry": [[[round(x, 2), round(y, 2)] for x, y in pl] for pl in p.points], "source_path_ids": p.source_paths,
            "source_segments": p.source_segments, "graph_nodes": p.nodes,
            "horizontal_pdf_units": round(m.horizontal_pdf_units, 3), "drawn_pdf_units": round(p.length_pt, 3), "raw_pt": round(p.raw_length_pt, 3), "bridged_gap_pt": round(p.bridged_gap_pt, 3),
            "horizontal_m": None if m.horizontal_m is None else round(m.horizontal_m, 3),
            "vertical_m": "UNKNOWN" if m.vertical_m is None else round(m.vertical_m, 3), "vertical_evidence": m.vertical_evidence,
            "total_m": None if m.total_m is None else round(m.total_m, 3), "evidence_state": m.state, "evidence": p.evidence,
            "in_hatched_area_m": None if m.hatched_m is None else round(m.hatched_m, 3),
            "ambiguity_reason": None, "reasons": m.reasons}


def performance_report(pa, timings: dict) -> dict[str, Any]:
    t = pa.timings
    text_ms = t.get("text_ms", 0.0)
    rep = {"pdf_extraction_ms": round(timings.get("extract_ms", 0.0)), "drawing_profile_ms": round(t.get("profile_ms", 0.0)),
           "glyph_text_reconstruction_ms": round(text_ms), "designation_dn_ms": round(t.get("designation_ms", 0.0)),
           "leader_discovery_and_pipe_attachment_ms": round(t.get("leader_attachment_ms", 0.0)),
           "topology_ms": round(t.get("representation_ms", 0.0) + t.get("topology_ms", 0.0)),
           "physical_pipe_reconstruction_ms": round(t.get("physical_pipes_ms", 0.0)), "measurement_ms": round(t.get("measurement_ms", 0.0)),
           "overlays_ms": round(timings.get("overlays_ms", 0.0)), "artifacts_ms": round(timings.get("artifacts_ms", 0.0)),
           "total_seconds": round(timings.get("total_s", 0.0), 2),
           "counts": {"raw_vector_objects": len(pa.page.paths), "raw_segments": sum(len(p.segs) for p in pa.page.paths),
                      "glyphs": pa.vtext.n_glyphs, "glyph_families": len(pa.vtext.families),
                      "pipe_primitives": sum(len(g.prims) for g in pa.graphs.values()),
                      "graph_nodes": sum(len(g.nodes) for g in pa.graphs.values()), "graph_edges": sum(len(g.prims) for g in pa.graphs.values())}}
    return rep


def source_revision() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=os.path.dirname(os.path.abspath(__file__)), stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def analysis_report_md(pa, name, timings, determinism, contamination, files) -> str:
    from ..reconcile import reconcile
    rec = reconcile(pa)
    st = Counter(a.state for a in pa.anchors)
    q = pa.quantities
    L = [f"# Analysis report: {name}", "", "## Status",
         f"- designations: {len(pa.designations)} (with DN {sum(1 for d in pa.designations if d.dn is not None)})",
         f"- actual CAD leaders: {len(pa.leaders)} (from designation blocks: {sum(1 for l in pa.leaders if any(d.block_id == l.block_id for d in pa.designations))})",
         f"- pipe attachments: verified {st.get('VERIFIED_PIPE_ATTACHMENT', 0)}, ambiguous {st.get('AMBIGUOUS_PIPE_ATTACHMENT', 0)}, none {st.get('NO_PIPE_ATTACHMENT', 0)}",
         f"- physical pipes: {len(pa.measures)}",
         f"- scale: {pa.scale.state} ({pa.scale.reason})",
         f"- reconciliation: {rec['state']} (raw {rec['raw_relevant_pipe_geometry_pt']} pt = confirmed {rec['confirmed_pt']} + ambiguous {rec['ambiguous_pt']} + unowned {rec['unowned_pt']})",
         f"- determinism: {determinism['state'] if determinism else 'not run'}",
         f"- contamination: {contamination['state'] if contamination else 'not run'}",
         f"- runtime: {timings.get('total_s', 0):.1f} s", "",
         "## Quantities (confirmed only; ambiguous reported separately)", "| Beteckning | DN | Antal | Horisontellt m | Vertikalt m | Totalt m | Tvetydigt m | Status |", "|---|---|---|---|---|---|---|---|"]
    for r in q:
        L.append(f"| {r['designation']} | {r['dn'] if r['dn'] is not None else '?'} | {r['physical_pipe_count']} | {r['confirmed_horizontal_m']:.2f} | {r['vertical_m'] if r['vertical_m']=='UNKNOWN' else f'{r[chr(118)+chr(101)+chr(114)+chr(116)+chr(105)+chr(99)+chr(97)+chr(108)+chr(95)+chr(109)]:.2f}'} | {r['confirmed_total_m']:.2f} | {r['ambiguous_m']:.2f} | {r['state']} |")
    L += ["", f"Totals: confirmed horizontal {sum(r['confirmed_horizontal_m'] for r in q):.2f} m, ambiguous {sum(r['ambiguous_m'] for r in q):.2f} m, unowned pipe geometry {rec['unowned_pt'] * (pa.scale.meters_per_pt or 0):.2f} m", "",
          "## Unresolved", ] + [f"- {k}: {v}" for k, v in Counter(i['kind'] for i in unresolved_issues(pa)).items()]
    L += ["", "## Artifacts"] + [f"- {fn}" for fn in sorted(files)]
    return "\n".join(L) + "\n"
