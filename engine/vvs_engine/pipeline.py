"""Pipeline orchestration: RAW PDF -> DrawingProfile -> annotations -> designations -> leaders -> attachments
-> pipe families -> topology -> physical pipes -> measurement -> quantities -> artifacts."""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Callable

from .geometry.core import stable_id
from .pdf.extract import RawDocument, RawPage, extract_document
from .geometry.core import GridIndex, dist, point_seg_distance
from .pipes.representation import (Prim, RepresentationFamily, build_graph, chains, collect_prims, describe_family, family_key,
                                   stroke_family,
                                   graph_tolerances, split_prims_at_points)
from .profile.layers import compute_layer_stats
from .profile.hatch import HatchFamily, discover_hatch, inside_hatch
from .semantics.annotation import (AnnotationBlock, Designation, build_blocks, extract_designations, free_segments, merge_lines)
from .semantics.attachment import (GeometryIndex, PipeCodeAnchor, family_of, layer_system_tokens, leader_contacts,
                                   resolve_block, system_layer_match)
from .semantics.legend import DrawingLegend, assign_roles, read_legend
from .semantics.leaders import Leader, annotation_layers, discover_leaders, leader_family_report
from .text.searchable import searchable_rows
from .text.vector_text import VectorTextResult, vector_text_rows
from .measure.scale import ScaleResult, discover_scale
from .measure.measure import PipeMeasure, aggregate, measure_pipes
from .pipes.ownership import Identity, OwnershipResult, identity_of, propagate
from .film import Film
from .routes import apply_routes, cross_check, review, run_routes

# a drawing draws its leaders alike: a family carrying this share of the leaders is where it draws them
LEADER_MIN_SHARE = 0.25
# and with no layer name to vouch for it, this share of the sheet's own pipe labels must have reached it
LABELS_MUST_REACH = 0.15
LABELS_MIN = 20

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
    hatch_families: list[HatchFamily] = field(default_factory=list)
    risers: dict[str, list[dict]] = field(default_factory=dict)     # identity key -> riser symbols
    ocr_assist: dict | None = None                                  # report of the OCR-assisted glyph resolution
    crosscheck: dict = field(default_factory=dict)                  # the routes side by side, and where they differ
    review_findings: dict = field(default_factory=dict)             # what the reading did not reach, and why
    legend: DrawingLegend = field(default_factory=DrawingLegend)    # the sheet's own designation list


def _width_lengths(page: RawPage) -> dict[float, float]:
    """Drawn stroke length per pen width on the page."""
    out: dict[float, float] = {}
    for p in page.paths:
        if p.kind == "s":
            w = round(p.width, 2)
            out[w] = out.get(w, 0.0) + p.length
    return out


def _t(timings: dict, key: str, t0: float) -> float:
    now = time.perf_counter()
    timings[key] = timings.get(key, 0.0) + (now - t0) * 1000.0
    return now



# A leader that ends this close to a run is on it; the tolerance is the pen, not a search radius. Measured over
# the reference drawings, the endpoints that sit on geometry their own designation already owns are at 0.0-6.7 pt
# and the next one is at 13, so nothing is reached for.
CLOSE_ON_OWNED_TOL = 8.0


def _close_labels_on_owned_runs(anchors, ownership, graphs) -> None:
    """A label the drawing repeats over a run it already named is not an unresolved case.

    Runs after ownership, so it cannot add a metre: it only records that a label which failed to attach names
    the very identity that already owns the geometry under its leader. Where the nearest owned geometry belongs
    to a different identity - another system, another dimension - nothing is claimed and the case stays open.
    """
    owned: dict[str, list[tuple[str, int]]] = {}
    for p in ownership.pipes:
        owned.setdefault(p.identity.key, []).extend((p.family, i) for i in p.prim_ids)
    if not owned:
        return
    for a in anchors:
        if a.state == "VERIFIED_PIPE_ATTACHMENT" or not a.endpoint:
            continue
        stated = (a.designation_display or a.designation or "").upper()
        best = None
        for key, prims in owned.items():
            if key.replace("|DN", "-").upper() != stated:
                continue
            for fk, i in prims:
                d = point_seg_distance(a.endpoint[0], a.endpoint[1], graphs[fk].prims[i].seg)[0]
                if best is None or d < best:
                    best = d
        if best is not None and best <= CLOSE_ON_OWNED_TOL:
            a.evidence["closed_on_owned_run"] = {"identity": stated, "distance_pt": round(best, 2)}

def analyze_page(page: RawPage, progress: Callable[[str], None] | None = None, ocr_assist: bool = False,
                 film_sink: Callable[[str, dict], None] | None = None) -> PageAnalysis:
    film = Film(film_sink)
    film.page(page)
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
    film.text(vtext.rows)
    t0 = _t(timings, "text_ms", t0)
    ocr_report = None
    if ocr_assist:
        # characters the stroke recogniser could not name are filled from an OCR pass over the same page, and
        # only where the OCR word lines up character for character with what the vector reader already read
        if progress:
            progress("RESOLVING_UNREADABLE_TEXT")
        from .text.ocr_assist import resolve_unknown_glyphs
        ocr_report = resolve_unknown_glyphs(page, vtext.rows)
        t0 = _t(timings, "ocr_assist_ms", t0)
    if progress:
        progress("READING_DESIGNATIONS")
    lines = merge_lines(srows + vtext.rows, page.info.index)
    consumed = set(pid for r in vtext.rows for pid in r.provenance) | set(pid for m in vtext.marks for pid in m.path_ids)
    free = free_segments(page, consumed)
    blocks = build_blocks(page, lines, free)
    designations, grammar, _ = extract_designations(page, blocks)
    legend = read_legend(lines)                  # the sheet's own designation list
    assign_roles(legend, designations)
    film.designations(designations)
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
    # the sheet's own designation list says which labels name pipes; the rest describe objects and may sit
    # anywhere, so they say nothing about what pipe geometry looks like
    pipe_labels = {d.did for d in designations if legend.names_a_pipe(d) and (d.text or "").upper() not in legend.components()}
    spelled_out = layer_system_tokens(page)      # the system names the file writes on layers of its own

    def run_pass(ann_layers: dict[str, int] | None):
        ann_marks = [m for m in vtext.marks if f"{m.layer}|{m.style}" in ann_layers] if ann_layers else vtext.marks
        leaders = discover_leaders(page, blocks, free, ann_marks, ann_layers)
        exclude = set(ann_layers) if ann_layers else set()
        gidx = GeometryIndex(page, exclude, glyph_pids)
        des_leaders = [ld for ld in leaders if ld.block_id in des_by_block]
        votes: Counter = Counter()
        token_votes: Counter = Counter()
        # one leader meeting one drawn object is one vote for that object's family, however many segments the
        # object is exported as: a symbol drawn as sixteen little strokes is not sixteen pieces of evidence
        for ld in des_leaders:
            if not any(d.did in pipe_labels for d in des_by_block[ld.block_id]):
                continue
            seen_obj: dict[tuple[str, str], float] = {}
            for c in leader_contacts(ld, gidx, None, paths):
                w = 1.0 if c.kind in ("end_tick", "crossing_tick") else 0.5
                key = (c.family, c.pid)
                seen_obj[key] = max(seen_obj.get(key, 0.0), w)
            for (fam, _), w in seen_obj.items():
                votes[fam] += w
                for d in des_by_block[ld.block_id]:
                    if system_layer_match(d.system_token, fam.split("|s|")[0], spelled_out):
                        token_votes[fam] += 1
        total = sum(votes.values()) or 1.0
        tick_votes: Counter = Counter()
        for ld in des_leaders:
            seen_tick: set[tuple[str, str]] = set()
            for c in leader_contacts(ld, gidx, None, paths):
                if c.kind in ("end_tick", "crossing_tick") and (c.family, c.pid) not in seen_tick:
                    seen_tick.add((c.family, c.pid))
                    tick_votes[c.family] += 1
        # The leader lines themselves are annotation geometry, never pipes, and neither are the label frames: the
        # paths are dropped from whatever family they land in, so a leader drawn with the pipes' own pen is never
        # measured as pipe. Beyond that, a drawing draws its leaders alike - on one layer, or with one pen - and
        # those families are excluded whole, because they also carry the leaders the tracer missed. A family that
        # carries a handful of leaders while another carries most of them is not where this drawing draws them:
        # those few are strays, a label's bounding box touching a pipe, and excluding the family on their account
        # would drop the pipes with them. On a sheet exported without layers that is the difference between
        # reading the pipes and reading nothing.
        annotation_pids = {pid for ld in leaders for pid in ld.path_ids}
        for b in blocks:
            for r in b.rows:
                annotation_pids |= {u.pid for u in r.underline}
            annotation_pids |= {sg.pid for sg in b.box_segs}
        lead_count: Counter = Counter()
        for ld in des_leaders:
            lead_count[stroke_family(ld.layer, ld.width, ld.color)] += 1
        top = max(lead_count.values(), default=0)
        # a layer name is the drawing's own statement about what that geometry is for, so a named family carrying
        # leaders is a leader family however few it carries; a pen width says nothing, and there the count decides
        leader_fams = {f for f, c in lead_count.items() if f.split("|s|")[0] or c >= LEADER_MIN_SHARE * top} \
            | (set(ann_layers) if ann_layers else set())
        # evaluate the vector structure of every voted family first (kind: fragmented-dashed / continuous / sparse)
        voted = sorted(f for f in votes if f not in leader_fams)
        prims_all = collect_prims(page, set(voted), exclude_pids=annotation_pids)
        desc: dict[str, tuple] = {}
        for fk in voted:
            if not prims_all.get(fk):
                continue
            g = build_graph(prims_all[fk], fk, graph_tolerances(page))
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
        # the sheet's middle pen by drawn length: half the ink on the page is thinner than this
        by_width = sorted(_width_lengths(page).items())
        half = 0.5 * sum(L for _, L in by_width)
        median_width = 0.0
        run = 0.0
        for w, L in by_width:
            run += L
            if run >= half:
                median_width = w
                break
        pipe_families: dict[str, RepresentationFamily] = {}
        graphs: dict[str, Any] = {}
        for f in voted:
            if not chain_like(f):
                continue
            layer, style = f.split("|s|")
            if not layer and desc[f][0].width < median_width:
                # and with no layer name, a pen thinner than half the ink on the sheet draws its background -
                # construction lines, hatching, grids. The pipes are what the sheet is for; they are not its
                # faintest pen.
                continue
            similar = any(_layer_template_similar(layer, tl) for tl in token_layers)
            accept = (token_votes[f] >= 1) or (tick_votes[f] >= 2 and similar) \
                or (tick_votes[f] >= 3 and style in token_styles) or (tick_votes[f] >= 5 and tick_votes[f] / total_ticks >= 0.15) \
                or (not token_fams and tick_votes[f] >= 2 and tick_votes[f] / total_ticks >= 0.25) \
                or (not token_fams and votes[f] >= 5 and votes[f] / total_votes >= 0.4) \
                or (not token_fams and votes[f] >= 2 and votes[f] / total_votes >= 0.5)   # no layer names: leaders end mostly here
            if accept:
                pipe_families[f] = desc[f][0]
                graphs[f] = desc[f][1]
        pipe_families, graphs = _generalize_families(page, pipe_families, graphs)
        anchors: list[PipeCodeAnchor] = []
        pf = set(pipe_families)
        for ld in des_leaders:
            block = block_by_id[ld.block_id]
            # a leader that starts on one row's own line speaks for that row's label, whatever else the block holds
            unit = block.unit_of_row(ld.start_row) if ld.start_row is not None else block.unit_for_point(ld.start)
            rows = sorted(des_by_block[ld.block_id], key=lambda d: d.row_index)
            if unit is not None:
                rows = [d for d in rows if d.row_index in unit]
                if not rows:
                    continue        # leader belongs to a non-designation label unit (component tag, note)
                rows = _rows_owning_leader(block, rows, ld)
            contacts = leader_contacts(ld, gidx, pf, paths)
            if not contacts and ld.length < 2.5 * max(block.height, 1.0) and not ld.end_marks:
                continue        # dangling frame stub, not a leader
            anchors.extend(resolve_block(block, rows, ld, contacts, system_tokens, spelled_out))
        anchors.sort(key=lambda a: a.anchor_id)
        stats = {"votes": dict(votes.most_common()), "token_votes": dict(token_votes.most_common()), "candidate_families": sorted(pipe_families), "tick_votes": dict(tick_votes.most_common())}
        if os.environ.get("VVS_DEBUG_PASS"):
            print(f"[pass ann_layers={sorted(ann_layers) if ann_layers else None}] leaders={len(leaders)} des_leaders={len(des_leaders)} votes={dict(votes)} ticks={dict(tick_votes)} "
                  f"voted={voted} chain_like={[f for f in voted if chain_like(f)]} accepted={sorted(pipe_families)} anchors={Counter(a.state for a in anchors)}", file=sys.stderr)
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
        ann_layers[stroke_family(ld.layer, ld.width, ld.color)] += 1
        b = block_by_id[a.block_id]
        for r in b.rows:
            for u in r.underline:
                ann_layers[stroke_family(u.layer, u.width, u.color)] += 1
            if r.line.source != "text" and r.line.font.startswith("vector:"):
                ann_layers[f"{r.line.layer}|{r.line.font[len('vector:'):]}"] += 1
        for sgm in b.box_segs:
            ann_layers[stroke_family(sgm.layer, sgm.width, sgm.color)] += 1
    if ann_layers:
        # a vector family accepted as pipe geometry in pass 1 is never an annotation family (an underline bar that
        # happens to share the pipes' stroke class must not remove the pipes)
        keep = {k: v for k, v in ann_layers.items() if (v >= 2 or v >= 0.05 * max(ann_layers.values())) and k not in pipe_families}
        leaders, pipe_families, graphs, anchors, contact_stats = run_pass(keep)
        ann_layers = keep
    else:
        ann_layers = {}
    # A sheet labels the pipes it draws. Where the families accepted carry no layer name to vouch for them, and
    # the sheet's own pipe labels overwhelmingly failed to reach them, the wrong geometry was accepted: had it
    # been the pipes, the labels would have found it. Measured over the style library, a sheet reading its own
    # pipes places a quarter of its pipe labels or better; the one reading its building outline placed 6 %.
    if pipe_families and not any(f.split("|s|")[0] for f in pipe_families) and len(pipe_labels) >= LABELS_MIN:
        placed = {a.designation_id for a in anchors if a.state == "VERIFIED_PIPE_ATTACHMENT"} & pipe_labels
        if len(placed) < LABELS_MUST_REACH * len(pipe_labels):
            if os.environ.get("VVS_DEBUG_PASS"):
                print(f"[drop] only {len(placed)}/{len(pipe_labels)} pipe labels reached {sorted(pipe_families)}", file=sys.stderr)
            pipe_families, graphs, anchors, contact_stats = {}, {}, [], dict(contact_stats, dropped_by_label_reach=True)
    film.leaders(leaders)
    film.families(pipe_families, graphs)
    timings["leader_ms"] = 0.0
    t0 = _t(timings, "leader_attachment_ms", t0)
    if progress:
        progress("BUILDING_TOPOLOGY")
    graphs, pipe_families = _split_at_tick_contacts(page, graphs, pipe_families, anchors)
    prims = {fk: graphs[fk].prims for fk in graphs}
    t0 = _t(timings, "topology_ms", t0)
    if progress:
        progress("BUILDING_PHYSICAL_PIPES")
    identities = _pipe_identities(designations, anchors, grammar, legend=legend)
    ownership = propagate(graphs, anchors, page.info.index, identities, spelled_out)
    _close_labels_on_owned_runs(anchors, ownership, graphs)
    film.pipes(ownership.pipes)
    t0 = _t(timings, "physical_pipes_ms", t0)
    if progress:
        progress("MEASURING")
    scale = discover_scale(page, lines)
    elevations = _elevations(blocks, anchors)
    # read the sheet again by the other routes, put the answers side by side, and let a second route add what the
    # first missed or take out what it contradicts
    _read = SimpleNamespace(graphs=graphs, ownership=ownership, scale=scale, designations=designations,
                            anchors=anchors, legend=legend, pipe_families=pipe_families, page=page)
    route_reports = run_routes(_read)
    crosscheck = cross_check(_read, route_reports)
    crosscheck["applied"] = apply_routes(_read, route_reports)
    review_findings = review(_read, crosscheck)
    t0 = _t(timings, "routes_ms", t0)
    hatch = discover_hatch(page, set(pipe_families))
    hatched_pt: dict[str, float] = {}
    if hatch:
        for pp in ownership.pipes:
            g = graphs[pp.family]
            hatched_pt[pp.physical_pipe_id] = sum(g.prims[pid].seg.length for pid in pp.prim_ids if inside_hatch(hatch, *g.prims[pid].seg.mid) is not None)
    measures = measure_pipes(ownership, scale, elevations, hatched_pt)
    risers = _riser_symbols(page, ann_layers, glyph_pids, graphs, ownership, anchors, identities)
    label_risers = _risers_from_dn_rows(designations, anchors, leaders, identities)
    amb_pt: Counter = Counter()
    for fk, g in graphs.items():
        for pid, st in ownership.prim_states[fk].items():
            if st.state == "AMBIGUOUS":
                for ident in st.candidates:
                    amb_pt[ident.key] += g.prims[pid].seg.length / max(len(st.candidates), 1)
    # what a reader counts on the drawing: verified labels per identity (a run usually carries several)
    label_counts: Counter = Counter()
    for a in anchors:
        if a.state == "VERIFIED_PIPE_ATTACHMENT" and a.anchor_id in identities:
            label_counts[identities[a.anchor_id].key] += 1
    quantities = aggregate(measures, dict(amb_pt), scale.meters_per_pt, risers, dict(label_counts), label_risers)
    film.measured(quantities, scale)
    t0 = _t(timings, "measurement_ms", t0)
    timings.update({f"text_{k}": v for k, v in vt_timing.items()})
    return PageAnalysis(page=page, legend=legend, layer_stats=layer_stats, vtext=vtext, srows=srows, lines=lines, blocks=blocks,
                        designations=designations, grammar=grammar, ann_layers=ann_layers, leaders=leaders,
                        pipe_families=pipe_families, prims=prims, graphs=graphs, anchors=anchors, contact_stats=contact_stats,
                        ownership=ownership, scale=scale, measures=measures, quantities=quantities, elevations=elevations,
                        timings=timings, hatch_families=hatch, risers=risers, ocr_assist=ocr_report,
                        crosscheck=crosscheck, review_findings=review_findings)


SAME_RISER = 15.0        # pt: a label's leader ends at the riser symbol it names, not exactly on its centre


def _risers_from_dn_rows(designations, anchors, leaders, identities) -> dict[str, list[dict]]:
    """Risers the drawing names outright: a label whose dimension stands on the row below states the size of the
    VERTICAL pipe at that point (the drop to a drain, a stack), while a dimension inline names the horizontal run.

    Reported alongside the risers found from drawn symbols rather than merged into them. Against the reference
    takeoff of drawing A the two sources disagree - symbols 58, labels 41, reference 55 - and their union (68) is
    further off than either, so the operator chooses which one the quantity uses.
    """
    des = {d.did: d for d in designations}
    ends = {l.lid: l.end for l in leaders}
    labelled: dict[str, list[dict]] = {}
    for a in sorted(anchors, key=lambda x: x.anchor_id):
        if a.state != "VERIFIED_PIPE_ATTACHMENT":
            continue
        d = des.get(a.designation_id)
        if d is None or not _is_vertical_label(d):
            continue
        pt = ends.get(a.leader_id)
        ident = identities.get(a.anchor_id)
        if pt is None or ident is None:
            continue
        key = f"{ident.base}|DN{d.dn}"
        lst = labelled.setdefault(key, [])
        if any(dist(tuple(r["point"]), pt) <= 3.0 for r in lst):
            continue                      # two leaders of one label onto the same riser
        lst.append({"designation": d.text, "dn": d.dn, "point": [round(pt[0], 2), round(pt[1], 2)],
                    "evidence": "dimension_on_the_row_below_states_a_vertical_pipe", "designation_id": d.did})
    return labelled


def _riser_symbols(page: RawPage, ann_layers, glyph_pids, graphs, ownership, anchors, identities) -> dict[str, list[dict]]:
    """Risers (vertical pipes) are drawn as closed marks (circle / circle-cross) that a pipe run ends at or that
    a label points at. Concentric marks form one riser. The riser's designation is the label pointing at it
    (a DN-less label takes the DN of the pipe at the mark), otherwise the designation of the pipe ending there."""
    from .geometry.core import dist as _dist
    from .pipes.ownership import _merge_identity, _seed_prims
    gidx = GeometryIndex(page, set(ann_layers) if ann_layers else set(), glyph_pids)
    syms = [s for s in gidx.symbols if 1.5 <= max(s.bbox[2] - s.bbox[0], s.bbox[3] - s.bbox[1]) <= 14.0 and family_key(s) not in graphs]
    groups: list[dict] = []
    for s in sorted(syms, key=lambda s: s.pid):
        cx, cy = (s.bbox[0] + s.bbox[2]) / 2, (s.bbox[1] + s.bbox[3]) / 2
        size = max(s.bbox[2] - s.bbox[0], s.bbox[3] - s.bbox[1])
        for grp in groups:
            if _dist((cx, cy), grp["center"]) <= 1.0:
                grp["pids"].append(s.pid); grp["size"] = max(grp["size"], size)
                break
        else:
            groups.append({"center": (cx, cy), "size": size, "pids": [s.pid]})
    by_pid = {pid: i for i, grp in enumerate(groups) for pid in grp["pids"]}
    layer_of = {}
    for s in syms:
        layer_of[s.pid] = s.layer
    for grp in groups:
        grp["fam"] = (min(layer_of[p] for p in grp["pids"]), round(grp["size"]))
    gi_idx = GridIndex(cell=12.0)
    for i, grp in enumerate(groups):
        cx, cy = grp["center"]; r = grp["size"] / 2 + 1.5
        gi_idx.insert(i, (cx - r, cy - r, cx + r, cy + r))

    def stack_of(i: int) -> list[int]:
        """Marks of the same family touching / adjacent to mark i (a stack of end markers)."""
        grp = groups[i]
        out_ids, frontier = {i}, [i]
        while frontier:
            j = frontier.pop()
            cj = groups[j]["center"]; sz = groups[j]["size"]
            for k in gi_idx.query_point(cj[0], cj[1], 1.6 * sz):
                if k in out_ids or groups[k]["fam"] != grp["fam"]:
                    continue
                if _dist(cj, groups[k]["center"]) <= 1.5 * max(sz, groups[k]["size"]):
                    out_ids.add(k); frontier.append(k)
        return sorted(out_ids)

    out: dict[str, list[dict]] = defaultdict(list)
    counted: set[int] = set()
    riser_fams: set = set()
    # (a) labels pointing at a mark; a count prefix ("5x") names the number of risers of the mark's stack
    for a in sorted(anchors, key=lambda a: a.anchor_id):
        if a.anchor_id not in identities or not a.contacts or not all(c.kind == "via_symbol" for c in a.contacts):
            continue
        gi = next((by_pid[c.via] for c in a.contacts if c.via in by_pid), None)
        if gi is None or gi in counted:
            continue
        ident = identities[a.anchor_id]
        if ident.dn is None:
            for fk, lst in _seed_prims(a, graphs).items():
                for pid, _, _ in lst:
                    st = ownership.prim_states[fk][pid]
                    if st.state == "CONFIRMED" and st.identity is not None and _merge_identity([ident, st.identity]) is not None:
                        ident = _merge_identity([ident, st.identity])
                        break
        members = stack_of(gi) if a.multiplier > 1 else [gi]
        counted.update(members)
        riser_fams.add(groups[gi]["fam"])
        n = max(a.multiplier, 1)
        for k in range(n):
            grp = groups[members[min(k, len(members) - 1)]]
            out[ident.key].append({"designation": ident.display, "dn": ident.dn, "point": [round(v, 2) for v in grp["center"]],
                                   "symbol": grp["pids"][0], "source": "label", "anchor_id": a.anchor_id, "count_prefix": a.multiplier})
    # (b) unlabeled marks of a riser mark family (established by the labels above) sitting at the end of, or on,
    #     a confirmed pipe: risers of that pipe's designation. Tiny marks (< 4 pt: end dots, connection points)
    #     count only when a label points at them.
    from .geometry.core import point_seg_distance as _psd
    prim_idx: dict[str, GridIndex] = {}
    for fk, g in graphs.items():
        idx = GridIndex(cell=12.0)
        for pid, q in g.prims.items():
            idx.insert(pid, q.seg.bbox())
        prim_idx[fk] = idx
    for i, grp in enumerate(groups):
        if i in counted or grp["fam"] not in riser_fams or grp["size"] < 4.0:
            continue
        cx, cy = grp["center"]; R = grp["size"] / 2 + 1.5
        best = None
        for fk in sorted(graphs):
            g = graphs[fk]
            for pid in sorted(set(prim_idx[fk].query_point(cx, cy, R))):
                q = g.prims[pid]
                d, t = _psd(cx, cy, q.seg)
                if d > R:
                    continue
                st = ownership.prim_states[fk][pid]
                if st.state != "CONFIRMED" or st.identity is None:
                    continue
                at_end = any(_dist((n.x, n.y), (cx, cy)) <= R and n.degree == 1 for n in (g.nodes[k] for k in g.prim_nodes[pid]))
                if best is None or d < best[0]:
                    best = (d, st.identity, fk, "pipe_end" if at_end else "on_pipe")
        if best is None:
            continue
        counted.add(i)
        _, ident, fk, src = best
        out[ident.key].append({"designation": ident.display, "dn": ident.dn, "point": [round(cx, 2), round(cy, 2)],
                               "symbol": grp["pids"][0], "source": src, "family": fk})
    return dict(out)


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
        g = build_graph(ps, fk, graph_tolerances(page))
        graphs[fk] = g
        pipe_families[fk] = describe_family(fk, ps, g)
    return graphs, pipe_families


def _pipe_identities(designations, anchors, grammar, vertical_dn_rows: bool = True, legend=None) -> dict[str, Identity]:
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
        if d is None:
            continue
        # A pattern is a weak test of whether a code names a pipe: on a sheet where the component tags happen to
        # share the shape of the system codes, the whole shape fails the test and the systems go with it. The
        # sheet's own designation list settles it directly, so a code it lists as a system qualifies whatever the
        # pattern statistics say - and a code it lists as an object never does.
        by_legend = legend is not None and legend.systems() and legend.names_a_pipe(d)
        if d.family not in pipe_fams and not by_legend:
            continue
        if legend is not None and (d.text or "").upper() in legend.components():
            continue        # the legend says this code names an object, not a pipe
        gf = grammar.families.get(d.pattern)
        dn_idx = gf.dn_token_index if gf is not None else None
        if dn_idx is None and d.dn_source == "inline":
            toks = d.tokens
            cand = [i for i, t in enumerate(toks) if t.isdigit() and int(t) == d.dn]
            dn_idx = cand[0] if cand else None
        out[a.anchor_id] = identity_of(a, dn_idx)
    return out


def _is_vertical_label(d) -> bool:
    """A label whose dimension stands on the row below names a vertical pipe at that point: the drop to a drain,
    a stack. A label with the dimension inline names the horizontal run.

    The exception is a count prefix ("2xKV1-X31" over "16"): that counts parallel pipes running together, a
    bundle along the horizontal run, not a stack - and the reference takeoff of drawing A gives exactly that
    label 0 vertical metres.

    The vertical reading decides how many risers the identity has. It does not take the size away from the run
    the leader touches: measured against the reference, stripping it fragments the horizontal quantity (213.4 m
    of reference became 205.8 m), because a drain connection is usually drawn on a branch of its own size."""
    return d.dn_source == "row" and d.dn is not None and d.multiplier <= 1


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
    tokenised: list[list[str]] = []
    for fk in pipe_families:
        layer, _, style = fk.partition("|s|")
        toks = layer_tokens(layer)
        templates.add((len(toks), tuple(t if i != len(toks) - 1 else "*" for i, t in enumerate(toks))))
        styles.add(style)
        tokenised.append(toks)
    # A layer name may name its system in more than one place - a discipline code and the system code itself.
    # Every position that already varies among the accepted pipe layers is therefore a variable of the template
    # rather than part of it; the constant positions still have to carry the template, so a name with more
    # variables than constants is no template at all.
    by_len: dict[int, list[list[str]]] = defaultdict(list)
    for toks in tokenised:
        by_len[len(toks)].append(toks)
    for n, group in by_len.items():
        if len(group) < 2:
            continue
        tpl = tuple("*" if len({g[i].upper() for g in group}) > 1 else group[0][i] for i in range(n))
        if sum(1 for t in tpl if t == "*") <= n // 2:
            templates.add((n, tpl))
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
            g = build_graph(prims[fk], fk, graph_tolerances(page))
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
