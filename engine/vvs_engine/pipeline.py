"""Pipeline orchestration: RAW PDF -> DrawingProfile -> annotations -> designations -> leaders -> attachments
-> pipe families -> topology -> physical pipes -> measurement -> quantities -> artifacts."""
from __future__ import annotations

import json
import os
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

from .geometry.core import stable_id
from .pdf.extract import RawDocument, RawPage, extract_document
from .geometry.core import dist
from .pipes.representation import (Prim, RepresentationFamily, build_graph, chains, collect_prims, describe_family, family_key,
                                   split_prims_at_points)
from .profile.layers import compute_layer_stats
from .semantics.annotation import (AnnotationBlock, Designation, build_blocks, extract_designations, free_segments, merge_lines)
from .semantics.attachment import (GeometryIndex, PipeCodeAnchor, family_of, leader_contacts, resolve_block, system_layer_match)
from .semantics.leaders import Leader, annotation_layers, discover_leaders, leader_family_report
from .text.searchable import searchable_rows
from .text.vector_text import VectorTextResult, vector_text_rows
from .measure.scale import ScaleResult, discover_scale
from .measure.measure import PipeMeasure, aggregate, measure_pipes
from .pipes.ownership import Identity, OwnershipResult, identity_of, propagate

STAGES = ["READING_PDF", "DISCOVERING_DRAWING_GRAMMAR", "EXTRACTING_VECTORS", "RECONSTRUCTING_TEXT", "READING_DESIGNATIONS",
          "FINDING_LEADERS", "RESOLVING_PIPE_REPRESENTATION", "ATTACHING_PIPES", "BUILDING_TOPOLOGY", "BUILDING_PHYSICAL_PIPES",
          "MEASURING", "GENERATING_OVERLAYS", "COMPLETED"]


@dataclass
class PageAnalysis:
    page: RawPage
    layer_stats: dict
    vtext: VectorTextResult
    srows: list
    lines: list
    blocks: list[AnnotationBlock]
    designations: list[Designation]
    grammar: Any
    ann_layers: dict[str, int]
    leaders: list[Leader]
    pipe_families: dict[str, RepresentationFamily]
    prims: dict[str, list[Prim]]
    graphs: dict[str, Any]
    anchors: list[PipeCodeAnchor]
    contact_stats: dict[str, Any]
    ownership: OwnershipResult | None = None
    scale: ScaleResult | None = None
    measures: list[PipeMeasure] = field(default_factory=list)
    quantities: list[dict] = field(default_factory=list)
    elevations: dict[str, list[dict]] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)


def _t(timings: dict, key: str, t0: float) -> float:
    now = time.perf_counter()
    timings[key] = timings.get(key, 0.0) + (now - t0) * 1000.0
    return now


def analyze_page(page: RawPage, progress: Callable[[str], None] | None = None) -> PageAnalysis:
    timings: dict[str, float] = {}
    t0 = time.perf_counter()
    if progress:
        progress("DISCOVERING_DRAWING_GRAMMAR")
    layer_stats = compute_layer_stats(page)
    t0 = _t(timings, "profile_ms", t0)
    if progress:
        progress("RECONSTRUCTING_TEXT")
    vt_timing: dict = {}
    vtext = vector_text_rows(page, vt_timing)
    srows = searchable_rows(page)
    t0 = _t(timings, "text_ms", t0)
    if progress:
        progress("READING_DESIGNATIONS")
    lines = merge_lines(srows + vtext.rows, page.info.index)
    consumed = set(pid for r in vtext.rows for pid in r.provenance) | set(pid for m in vtext.marks for pid in m.path_ids)
    free = free_segments(page, consumed)
    blocks = build_blocks(page, lines, free)
    designations, grammar, _ = extract_designations(page, blocks)
    t0 = _t(timings, "designation_ms", t0)
    if progress:
        progress("FINDING_LEADERS")
    des_by_block: dict[str, list[Designation]] = defaultdict(list)
    for d in designations:
        des_by_block[d.block_id].append(d)
    paths = {p.pid: p for p in page.paths}
    glyph_pids = set(pid for r in vtext.rows for pid in r.provenance)
    block_by_id = {b.bid: b for b in blocks}
    # NOTE: consumed (for free segments) still excludes marks; the geometry index only excludes accepted text glyphs
    system_tokens = {d.system_token for d in designations}

    def run_pass(ann_layers: dict[str, int] | None):
        ann_marks = [m for m in vtext.marks if f"{m.layer}|{m.style}" in ann_layers] if ann_layers else vtext.marks
        leaders = discover_leaders(page, blocks, free, ann_marks, ann_layers)
        exclude = set(ann_layers) if ann_layers else set()
        gidx = GeometryIndex(page, exclude, glyph_pids)
        des_leaders = [ld for ld in leaders if ld.block_id in des_by_block]
        votes: Counter = Counter()
        token_votes: Counter = Counter()
        for ld in des_leaders:
            for c in leader_contacts(ld, gidx, None, paths):
                w = 1.0 if c.kind in ("end_tick", "crossing_tick") else 0.5
                votes[c.family] += w
                for d in des_by_block[ld.block_id]:
                    if system_layer_match(d.system_token, c.family.split("|s|")[0]):
                        token_votes[c.family] += 1
        total = sum(votes.values()) or 1.0
        tick_votes: Counter = Counter()
        for ld in des_leaders:
            for c in leader_contacts(ld, gidx, None, paths):
                if c.kind in ("end_tick", "crossing_tick"):
                    tick_votes[c.family] += 1
        # the vector families carrying the designation leaders themselves are annotation geometry, never pipes
        leader_fams = {f"{ld.layer}|s|w{ld.width:.2f}" for ld in des_leaders} | (set(ann_layers) if ann_layers else set())
        # evaluate the vector structure of every voted family first (kind: fragmented-dashed / continuous / sparse)
        voted = sorted(f for f in votes if f not in leader_fams)
        prims_all = collect_prims(page, set(voted))
        desc: dict[str, tuple] = {}
        for fk in voted:
            if not prims_all.get(fk):
                continue
            g = build_graph(prims_all[fk], fk)
            rf = describe_family(fk, prims_all[fk], g)
            desc[fk] = (rf, g)
        def chain_like(fk):
            return fk in desc and desc[fk][0].kind != "sparse" and desc[fk][0].longest_chain >= 25 and desc[fk][0].total_length >= 60
        token_fams = {f for f in voted if token_votes[f] >= 1 and chain_like(f)}
        total_votes = sum(votes.values()) or 1.0
        # styles that may vouch for name-less families: only strongly supported token families
        token_styles = {f.split("|s|")[1] for f in token_fams if votes[f] >= max(2.0, 0.05 * total_votes)}
        token_layers = [f.split("|s|")[0] for f in token_fams]
        total_ticks = sum(tick_votes.values()) or 1
        pipe_families: dict[str, RepresentationFamily] = {}
        graphs: dict[str, Any] = {}
        for f in voted:
            if not chain_like(f):
                continue
            layer, style = f.split("|s|")
            similar = any(_layer_template_similar(layer, tl) for tl in token_layers)
            accept = (token_votes[f] >= 1) or (tick_votes[f] >= 2 and similar) \
                or (tick_votes[f] >= 3 and style in token_styles) or (tick_votes[f] >= 5 and tick_votes[f] / total_ticks >= 0.15) \
                or (not token_fams and tick_votes[f] >= 2 and tick_votes[f] / total_ticks >= 0.25)   # no layer-name evidence at all
            if accept:
                pipe_families[f] = desc[f][0]
                graphs[f] = desc[f][1]
        pipe_families, graphs = _generalize_families(page, pipe_families, graphs)
        anchors: list[PipeCodeAnchor] = []
        pf = set(pipe_families)
        for ld in des_leaders:
            block = block_by_id[ld.block_id]
            unit = block.unit_for_point(ld.start)
            rows = sorted(des_by_block[ld.block_id], key=lambda d: d.row_index)
            if unit is not None:
                rows = [d for d in rows if d.row_index in unit]
                if not rows:
                    continue        # leader belongs to a non-designation label unit (component tag, note)
                rows = _rows_owning_leader(block, rows, ld)
            contacts = leader_contacts(ld, gidx, pf, paths)
            if not contacts and ld.length < 2.5 * max(block.height, 1.0) and not ld.end_marks:
                continue        # dangling frame stub, not a leader
            anchors.extend(resolve_block(block, rows, ld, contacts, system_tokens))
        anchors.sort(key=lambda a: a.anchor_id)
        stats = {"votes": dict(votes.most_common()), "token_votes": dict(token_votes.most_common()), "candidate_families": sorted(pipe_families), "tick_votes": dict(tick_votes.most_common())}
        return leaders, pipe_families, graphs, anchors, stats

    # pass 1: unrestricted leaders; pass 2: leaders/marks restricted to the annotation layers evidenced by
    # verified attachments of pass 1 (frames + leader layers + designation glyph layers)
    leaders, pipe_families, graphs, anchors, contact_stats = run_pass(None)
    ann_layers: Counter = Counter()
    ver_blocks = {a.block_id for a in anchors if a.state == "VERIFIED_PIPE_ATTACHMENT"}
    for a in anchors:
        if a.state != "VERIFIED_PIPE_ATTACHMENT":
            continue
        ld = next(l for l in leaders if l.lid == a.leader_id)
        ann_layers[f"{ld.layer}|s|w{ld.width:.2f}"] += 1
        b = block_by_id[a.block_id]
        for r in b.rows:
            for u in r.underline:
                ann_layers[f"{u.layer}|s|w{u.width:.2f}"] += 1
            if r.line.source != "text" and r.line.font.startswith("vector:"):
                ann_layers[f"{r.line.layer}|{r.line.font[len('vector:'):]}"] += 1
        for sgm in b.box_segs:
            ann_layers[f"{sgm.layer}|s|w{sgm.width:.2f}"] += 1
    if ann_layers:
        keep = {k: v for k, v in ann_layers.items() if v >= 2 or v >= 0.05 * max(ann_layers.values())}
        leaders, pipe_families, graphs, anchors, contact_stats = run_pass(keep)
        ann_layers = keep
    else:
        ann_layers = {}
    timings["leader_ms"] = 0.0
    t0 = _t(timings, "leader_attachment_ms", t0)
    if progress:
        progress("BUILDING_TOPOLOGY")
    graphs, pipe_families = _split_at_tick_contacts(page, graphs, pipe_families, anchors)
    prims = {fk: graphs[fk].prims for fk in graphs}
    t0 = _t(timings, "topology_ms", t0)
    if progress:
        progress("BUILDING_PHYSICAL_PIPES")
    identities = _pipe_identities(designations, anchors, grammar)
    ownership = propagate(graphs, anchors, page.info.index, identities)
    t0 = _t(timings, "physical_pipes_ms", t0)
    if progress:
        progress("MEASURING")
    scale = discover_scale(page, lines)
    elevations = _elevations(blocks, anchors)
    measures = measure_pipes(ownership, scale, elevations)
    amb_pt: Counter = Counter()
    for fk, g in graphs.items():
        for pid, st in ownership.prim_states[fk].items():
            if st.state == "AMBIGUOUS":
                for ident in st.candidates:
                    amb_pt[ident.key] += g.prims[pid].seg.length / max(len(st.candidates), 1)
    quantities = aggregate(measures, dict(amb_pt), scale.meters_per_pt, ownership.riser_labels)
    t0 = _t(timings, "measurement_ms", t0)
    timings.update({f"text_{k}": v for k, v in vt_timing.items()})
    return PageAnalysis(page=page, layer_stats=layer_stats, vtext=vtext, srows=srows, lines=lines, blocks=blocks,
                        designations=designations, grammar=grammar, ann_layers=ann_layers, leaders=leaders,
                        pipe_families=pipe_families, prims=prims, graphs=graphs, anchors=anchors, contact_stats=contact_stats,
                        ownership=ownership, scale=scale, measures=measures, quantities=quantities, elevations=elevations,
                        timings=timings)


def _rows_owning_leader(block: AnnotationBlock, rows: list[Designation], ld: Leader) -> list[Designation]:
    """Within a label unit of several designation rows each carrying its own underline (no box frame), a leader
    starting at the end of one row's underline belongs to that row alone."""
    if len(rows) <= 1 or block.box_segs or ld.start_type != "underline_end":
        return rows
    tol = 0.35 * max(block.height, 1.0)
    own = []
    for d in rows:
        br = block.rows[d.row_index]
        if any(dist(ld.start, ep) <= tol for u in br.underline for ep in ((u.seg.x0, u.seg.y0), (u.seg.x1, u.seg.y1))):
            own.append(d)
    return own if len(own) == 1 else rows


def _split_at_tick_contacts(page: RawPage, graphs: dict, pipe_families: dict, anchors: list[PipeCodeAnchor]):
    """Tick marks of verified leaders are drawn boundary evidence on the pipe: re-split the pipe primitives there
    so every tick contact becomes a graph node (ownership can then change identity exactly at the tick)."""
    pts: dict[str, set[tuple[float, float]]] = defaultdict(set)
    for a in anchors:
        if a.state != "VERIFIED_PIPE_ATTACHMENT":
            continue
        for c in a.contacts:
            if c.kind in ("end_tick", "crossing_tick") and c.family in graphs:
                pts[c.family].add((round(c.point[0], 3), round(c.point[1], 3)))
    if not pts:
        return graphs, pipe_families
    prims_all = collect_prims(page, set(pts))
    for fk in sorted(pts):
        if not prims_all.get(fk):
            continue
        ps = split_prims_at_points(prims_all[fk], sorted(pts[fk]))
        g = build_graph(ps, fk)
        graphs[fk] = g
        pipe_families[fk] = describe_family(fk, ps, g)
    return graphs, pipe_families


def _pipe_identities(designations, anchors, grammar) -> dict[str, Identity]:
    """Anchors of pipe-designation grammar families: a family qualifies when >= 50 % of its members carry a DN
    (inline or DN row) or >= 50 % of its verified attachments have layer-token support. Other code families
    (component tags) never seed pipe ownership."""
    des_by_id = {d.did: d for d in designations}
    fam_members: Counter = Counter()
    fam_dn: Counter = Counter()
    fam_ver: Counter = Counter()
    fam_tok: Counter = Counter()
    for d in designations:
        fam_members[d.family] += 1
        if d.dn is not None:
            fam_dn[d.family] += 1
    for a in anchors:
        if a.state != "VERIFIED_PIPE_ATTACHMENT":
            continue
        d = des_by_id.get(a.designation_id)
        if d is None:
            continue
        fam_ver[d.family] += 1
        if a.evidence.get("layer_token_match") or a.evidence.get("layer_token"):
            fam_tok[d.family] += 1
    pipe_fams = set()
    for f, n in fam_members.items():
        if fam_dn[f] >= 0.5 * n or (fam_ver[f] and fam_tok[f] >= 0.5 * fam_ver[f]):
            pipe_fams.add(f)
    out: dict[str, Identity] = {}
    for a in anchors:
        if a.state != "VERIFIED_PIPE_ATTACHMENT":
            continue
        d = des_by_id.get(a.designation_id)
        if d is None or d.family not in pipe_fams:
            continue
        gf = grammar.families.get(d.pattern)
        dn_idx = gf.dn_token_index if gf is not None else None
        if dn_idx is None and d.dn_source == "inline":
            toks = d.tokens
            cand = [i for i, t in enumerate(toks) if t.isdigit() and int(t) == d.dn]
            dn_idx = cand[0] if cand else None
        out[a.anchor_id] = identity_of(a, dn_idx)
    return out


ELEV_TAG_RE = __import__("re").compile(r"^([A-ZÅÄÖ]{1,4})\s*([+\-]?)\s*(\d+[.,]?\d*)$")


def _elevations(blocks, anchors) -> dict[str, list[dict]]:
    """Elevation annotations (e.g. VG+1.67, CL 4000) of the label unit of each anchor's designation row."""
    out: dict[str, list[dict]] = {}
    bmap = {b.bid: b for b in blocks}
    for a in anchors:
        b = bmap.get(a.block_id)
        if b is None:
            continue
        ri = a.evidence.get("row_index")
        if ri is None:
            continue
        unit = b.unit_of_row(ri)
        ev = []
        for k in unit:
            r = b.rows[k]
            if r.role != "elevation":
                continue
            m = ELEV_TAG_RE.match(r.text_norm.replace(" ", ""))
            if m:
                try:
                    v = float(m.group(3).replace(",", "."))
                except ValueError:
                    continue
                if m.group(2) == "-":
                    v = -v
                ev.append({"tag": m.group(1), "value": v, "text": r.text_norm, "row_id": r.line.rid})
        if ev:
            out[a.anchor_id] = ev
    return out


def _layer_template_similar(a: str, b: str) -> bool:
    """Two layer names follow the same template when their token counts differ by <= 1 and >= 60 % of the
    tokens (position-wise) are identical."""
    from .profile.layers import layer_tokens
    ta, tb = layer_tokens(a), layer_tokens(b)
    if not ta or not tb or abs(len(ta) - len(tb)) > 1:
        return False
    n = min(len(ta), len(tb))
    same = sum(1 for i in range(n) if ta[i].upper() == tb[i].upper())
    return same >= 0.6 * max(len(ta), len(tb))


def _generalize_families(page: RawPage, pipe_families: dict, graphs: dict):
    """Layers that follow the same name template as discovered pipe layers (same token count, same style)
    and carry chain-like geometry are pipe geometry as well (their pipes may remain UNNAMED)."""
    if not pipe_families:
        return pipe_families, graphs
    from .profile.layers import layer_tokens
    templates = set()
    styles = set()
    for fk in pipe_families:
        layer, _, style = fk.partition("|s|")
        toks = layer_tokens(layer)
        templates.add((len(toks), tuple(t if i != len(toks) - 1 else "*" for i, t in enumerate(toks))))
        styles.add(style)
    all_fams = Counter()
    for p in page.paths:
        if p.kind == "s":
            all_fams[family_key(p)] += 1
    add = set()
    for fk in all_fams:
        if fk in pipe_families:
            continue
        layer, _, style = fk.partition("|s|")
        if style not in styles:
            continue
        toks = layer_tokens(layer)
        for (n, tpl) in templates:
            if len(toks) == n and all(t == "*" or t == toks[i] for i, t in enumerate(tpl)):
                add.add(fk)
    if add:
        prims = collect_prims(page, add)
        for fk in sorted(add):
            if not prims.get(fk):
                continue
            g = build_graph(prims[fk], fk)
            rf = describe_family(fk, prims[fk], g)
            if rf.kind != "sparse" and rf.longest_chain >= 25 and rf.total_length >= 60:
                pipe_families[fk] = rf
                graphs[fk] = g
    return pipe_families, graphs


def summarize(pa: PageAnalysis) -> dict[str, Any]:
    st = Counter(a.state for a in pa.anchors)
    return {
        "designations": len(pa.designations), "with_dn": sum(1 for d in pa.designations if d.dn is not None),
        "blocks": len(pa.blocks), "leaders": len(pa.leaders), "designation_leaders": sum(1 for l in pa.leaders if any(d.block_id == l.block_id for d in pa.designations)),
        "anchors": dict(st), "pipe_families": {k: v.kind for k, v in pa.pipe_families.items()},
        "ownership": pa.ownership.stats if pa.ownership else {}, "physical_pipes": len(pa.ownership.pipes) if pa.ownership else 0,
        "scale": pa.scale.state if pa.scale else None,
        "confirmed_horizontal_m": round(sum(q["confirmed_horizontal_m"] for q in pa.quantities), 2),
        "ambiguous_m": round(sum(q["ambiguous_m"] for q in pa.quantities), 2),
        "timings_ms": {k: round(v) for k, v in pa.timings.items()},
    }
