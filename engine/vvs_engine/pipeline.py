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
from .pipes.representation import (Prim, RepresentationFamily, build_graph, chains, collect_prims, describe_family,
                                   duplicate_overlaps, family_key,
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
LEADER_INK_SHARE = 0.5     # a nameless pen is the leader pen when its leaders are most of what it draws
PEER_SHARE = 0.15          # a drawn family carrying this much of the best family's label ends is a peer of it
PEER_LABELS_MIN = 2        # and two of the sheet's own labels pointing at it is the least that can say so
# and with no layer name to vouch for it, this share of the sheet's own pipe labels must have reached it
LABELS_MUST_REACH = 0.15
OCR_ASSIST_BUDGET_S = 90.0  # naming a handful of glyphs may not hold a reading that is otherwise finished
LABELS_MIN = 20
DECLINED_SEGMENT_BUDGET = 8000        # strokes of declined families a reading carries, so they can be looked at
DECLINED_SEGMENTS_PER_FAMILY = 3000   # and no single family may spend the whole budget
UNCONSIDERED_SEGMENT_BUDGET = 4000    # and a smaller one for the ink no label ever pointed at
UNCONSIDERED_SEGMENTS_PER_FAMILY = 1500
UNCONSIDERED_PATHS_PER_FAMILY = 400

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
    second_reader: dict | None = None       # bounded cases put to a second reader, and what it did with them
    vision: dict | None = None              # what a look at the rendered page said the reading may have missed


def reached_labels(anchors, pipe_labels: set[str]) -> set[str]:
    """The sheet's own pipe labels that ended up verified on a pipe."""
    return {a.designation_id for a in anchors if a.state == "VERIFIED_PIPE_ATTACHMENT"} & pipe_labels


def label_reach_fails(families, anchors, pipe_labels: set[str]) -> bool:
    """A sheet labels the pipes it draws, so its own labels say whether the right geometry was taken.

    The test only applies where no layer name vouches for the families taken, and only on a sheet carrying enough
    labels to say anything. Measured over the style library, a sheet reading its own pipes places a sixth of its
    pipe labels or better; the one reading its building outline placed 6 %.
    """
    if not families or any(f.split("|s|")[0] for f in families) or len(pipe_labels) < LABELS_MIN:
        return False
    return len(reached_labels(anchors, pipe_labels)) < LABELS_MUST_REACH * len(pipe_labels)


def _unconsidered(page: RawPage, pipe_families: dict, contact_stats: dict, ann_layers: dict, glyph_pids: set,
                  leaders: list) -> dict:
    """Every drawn stroke the reading did not weigh as a candidate for pipe, and which of two things it was.

    Ink lands here for one of two reasons. Either no label's leader ever came near it, or it sits on a layer this
    drawing uses for its labels and frames - and on a sheet whose text is drawn as strokes that second group is
    large. Neither can become pipe: identity comes from a designation and its real leader, and there is none
    here. But together they are most of what a reader sees, and a line that is simply absent from the reading
    looks the same whether it was judged and set aside or never looked at. Saying which is the whole point. No
    graph is built for any of it - that is what the reading does for a family a label reached, and doing it for
    the title block would cost the reading its time for nothing.
    """
    seen_fams = set(pipe_families) | set(contact_stats.get("declined_families") or {})
    ann = set(ann_layers or {}) | (set(contact_stats.get("votes") or {}) - seen_fams)
    lead_pids = {pid for ld in leaders for pid in ld.path_ids}
    fams: dict[str, dict] = {}
    for pth in page.paths:
        if pth.kind != "s" or pth.pid in glyph_pids or pth.pid in lead_pids:
            continue
        fk = stroke_family(pth.layer, pth.width, pth.color)
        if fk in seen_fams:
            continue
        why = "ON_A_LAYER_THE_READING_TREATS_AS_ANNOTATION" if fk in ann else "NO_LEADER_EVER_CAME_NEAR_IT"
        r = fams.setdefault(fk, {"family": fk, "why": why, "width": round(pth.width, 2),
                                 "total_length_pt": 0.0, "n_segments": 0, "paths": []})
        r["total_length_pt"] += pth.length
        r["n_segments"] += len(pth.segs)
        if len(r["paths"]) < UNCONSIDERED_PATHS_PER_FAMILY:
            r["paths"].append(pth)
    # A family drawn on a layer named the way this drawing names its pipe layers is the one worth a second look:
    # it is where the sheet puts pipes, and nothing pointed at it. It still cannot be measured - a run with no
    # label has no identity - but "this looks like a pipe layer and no leader reached it" is a different sentence
    # from "this is the title block", and a reader deserves to be told which one it is. So it is also the ink the
    # stroke budget is spent on first; a vector logo must not crowd it out by being long.
    for fk, r in fams.items():
        lay = fk.partition("|s|")[0]
        r["on_a_pipe_like_layer"] = bool(lay) and any(_layer_template_similar(lay, pf.partition("|s|")[0])
                                                      for pf in pipe_families if pf.partition("|s|")[0])
    budget = UNCONSIDERED_SEGMENT_BUDGET
    for fk in sorted(fams, key=lambda k: (not fams[k]["on_a_pipe_like_layer"], -fams[k]["total_length_pt"])):
        r = fams[fk]
        segs = []
        for pth in r["paths"]:
            for sg in pth.segs:
                if len(segs) >= min(budget, UNCONSIDERED_SEGMENTS_PER_FAMILY):
                    break
                segs.append([round(sg.x0, 2), round(sg.y0, 2), round(sg.x1, 2), round(sg.y1, 2)])
        r["segments"] = segs
        r["segments_truncated"] = len(segs) < r["n_segments"]
        r["total_length_pt"] = round(r["total_length_pt"], 1)
        del r["paths"]
        budget -= len(segs)
    return fams



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


CLAIM_WALK_LIMIT = 600      # a line, not a network: a claim that runs away is not worth drawing


def claimed_runs(anchors, ownership, graphs) -> dict[str, dict[int, list[str]]]:
    """The lines a label points at that no identity could take, and which labels point at them.

    A designation whose case the reading could not settle still reached geometry - the leader touched a drawn
    line, and that line is on the sheet whether or not anyone can say what it is called. Left as plain unowned
    ink it is indistinguishable from the ink nothing points at, so it is drawn as neither: it is not measured,
    because nothing here settles anything, and it is not hidden, because the drawing plainly has a pipe there.

    The walk follows the line and stops where the drawing does something: at a junction, and at the point the
    run becomes owned. Following the whole network instead would light up half a sheet from one open label.
    """
    from collections import defaultdict
    out: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    prim_of: dict[tuple[str, str, int], int] = {}
    for fk, g in graphs.items():
        for pid, prim in g.prims.items():
            prim_of[(fk, prim.pid, prim.seg_index)] = pid
    for a in sorted(anchors, key=lambda x: x.anchor_id):
        if a.state == "VERIFIED_PIPE_ATTACHMENT" or not a.contacts:
            continue
        code = a.designation_display or a.designation
        if not code:
            continue
        for c in a.contacts:
            fk = c.family
            g = graphs.get(fk)
            if g is None:
                continue
            start = prim_of.get((fk, c.pid, c.seg_index))
            if start is None:
                continue
            states = ownership.prim_states.get(fk) or {}
            seen: set[int] = set()
            stack = [start]
            while stack and len(seen) < CLAIM_WALK_LIMIT:
                cur = stack.pop()
                if cur in seen:
                    continue
                st = states.get(cur)
                if st is not None and st.state != "UNOWNED":
                    continue                  # the run is spoken for from here on; the claim stops
                seen.add(cur)
                for nid in g.prim_nodes.get(cur, ()):
                    node = g.nodes.get(nid)
                    if node is None or node.degree > 2:
                        continue              # a junction: the drawing changes something here
                    stack.extend(x for x in node.prims if x not in seen)
            for pid in seen:
                if code not in out[fk][pid]:
                    out[fk][pid].append(code)
    return {fk: dict(v) for fk, v in out.items()}


def _settle_bundles_by_elimination(anchors, ownership, graphs) -> int:
    """A bundle of parallel runs named by one stacked label, settled by what the rest of the sheet already says.

    The label lists its codes in order and the runs lie side by side, but nothing in the label says which code is
    which line - and guessing by a drawing convention swaps identities between systems on the sheet where the
    convention does not hold. What does say it is the drawing: a run of the bundle usually carries on and is
    named on its own somewhere else. Every run the sheet has already named pins its code, and where that leaves
    one code and one run over, the last one is determined rather than chosen.

    Runs before ownership is recomputed, so what it settles is seeded like any other reading. A bundle the sheet
    does not name enough of stays ambiguous.
    """
    owner: dict[tuple[str, int], str] = {}
    prim_of: dict[tuple[str, str, int], int] = {}
    for fk, g in graphs.items():
        for pid, prim in g.prims.items():
            prim_of[(fk, prim.pid, prim.seg_index)] = pid
    # What a run is already called has to be spelled the way the label spells it. The identity's key is a
    # normalised form - it drops the suffix the sheet writes, so `KV1-X7-16/W` becomes `KV1-X7-16` - and it was
    # being compared against the label's own text. The two alphabets never met, so every run the sheet had
    # already named looked unnamed and no bundle was ever settled. The display form is the label's own.
    for p in ownership.pipes:
        name = (p.identity.display or p.identity.key.replace("|DN", "-")).upper()
        for i in p.prim_ids:
            owner[(p.family, i)] = name

    by_block: dict[str, list] = defaultdict(list)
    for a in anchors:
        if a.reason == "multi_row_bundle_awaiting_elimination" and a.evidence.get("bundle"):
            by_block[(a.block_id, a.leader_id)].append(a)
    settled = 0
    for key, group in sorted(by_block.items(), key=lambda kv: str(kv[0])):
        b = group[0].evidence["bundle"]
        runs = b["runs"]
        if len(group) != b["n"] or len(runs) != b["n"]:
            continue
        group.sort(key=lambda a: a.evidence["bundle"]["pos"])
        codes = [(a.designation_display or a.designation or "").upper() for a in group]
        if len(set(codes)) != len(codes):
            continue                      # the same code twice: order says nothing about which line is which
        # what the sheet already calls each run of the bundle
        named: list[str | None] = []
        for run in runs:
            got = set()
            for fam_pid, seg in run:
                for fk in graphs:
                    pid = prim_of.get((fk, fam_pid, seg))
                    if pid is not None and (fk, pid) in owner:
                        got.add(owner[(fk, pid)])
            named.append(got.pop() if len(got) == 1 else None)
        fixed = {n for n in named if n is not None}
        free_codes = [c for c in codes if c not in fixed]
        free_slots = [i for i, n in enumerate(named) if n is None]
        if len(free_codes) != len(free_slots) or len(free_slots) > 1:
            continue                      # more than one left over: the sheet has not said enough
        if free_slots:
            named[free_slots[0]] = free_codes[0]
        if sorted(x for x in named if x) != sorted(codes):
            continue
        # Elimination says which code is left over; it must not be what makes the identity. Each label of the
        # bundle keeps its own contact with the run it is being given, so what settles the case is a leader
        # touching that line plus the constraint - never the arithmetic on its own.
        assign = []
        for a in group:
            code = (a.designation_display or a.designation or "").upper()
            idx = named.index(code)
            touching = [c for c in a.contacts if [c.pid, c.seg_index] in runs[idx]]
            if not touching:
                break
            assign.append((a, idx, touching))
        if len(assign) != len(group):
            continue                      # a code with no line of its own under it: not settled, still ambiguous
        for a, idx, touching in assign:
            a.state = "VERIFIED_PIPE_ATTACHMENT"
            a.reason = "multi_row_bundle_settled_by_elimination"
            a.contacts = touching
            a.evidence["settled_against"] = {"run": idx, "named_by_the_sheet": [n for n in named]}
            settled += 1
    return settled

SYSTEM_FAMILY_SHARE = 0.8   # the sheet places a system on one family this consistently
SYSTEM_FAMILY_MIN = 3       # and has said so this many times before its habit counts as evidence


def _settle_by_system_usage(anchors) -> int:
    """Where a leader ends on several families at once, the sheet's own habit for that system decides.

    A drawing draws a system with one pen. Where other labels of the same system have already been placed on
    this sheet - each by its own leader, each verified on its own evidence - and they agree overwhelmingly on
    one of the families THIS leader actually touched, that is the family this label means too.

    It is the same kind of evidence as the designation list and the grammar: not a rule about VVS drawings, but
    a reading of what this drawing does. Nothing is chosen that the leader did not touch, so no geometry is
    claimed that the label never reached, and a sheet that has not said the same thing several times over
    settles nothing.
    """
    habit: dict[str, Counter] = defaultdict(Counter)
    for a in anchors:
        if a.state != "VERIFIED_PIPE_ATTACHMENT" or not a.system_token:
            continue
        for fk in {c.family for c in a.contacts}:
            habit[a.system_token.upper()][fk] += 1
    settled = 0
    for a in sorted(anchors, key=lambda a: a.anchor_id):
        if a.state != "AMBIGUOUS_PIPE_ATTACHMENT" or not a.system_token:
            continue
        if not a.reason.startswith("several_vector_families_at_leader_no_token_discrimination"):
            continue
        touched = {c.family for c in a.contacts}
        if len(touched) < 2:
            continue
        used = habit.get(a.system_token.upper())
        if not used:
            continue
        among = {f: used.get(f, 0) for f in touched}
        total = sum(among.values())
        if total < SYSTEM_FAMILY_MIN:
            continue
        best, n = max(sorted(among.items()), key=lambda kv: kv[1])
        if n < SYSTEM_FAMILY_SHARE * total:
            continue                    # the sheet uses more than one family for this system: no habit to read
        a.contacts = [c for c in a.contacts if c.family == best]
        a.candidate_families = [best]
        a.state = "VERIFIED_PIPE_ATTACHMENT"
        a.reason = "family_this_sheet_uses_for_this_system"
        a.evidence = dict(a.evidence or {}, system_usage={"family": best, "of": n, "seen": total})
        settled += 1
    return settled


def analyze_page(page: RawPage, progress: Callable[[str], None] | None = None, ocr_assist: bool = False,
                 film_sink: Callable[[str, dict], None] | None = None,
                 second_reader: Callable[[Any], str] | None = None) -> PageAnalysis:
    """second_reader: an optional transport for putting the reading's own open cases to a language model.

    Without it - the default, and what every test and every reference run uses - nothing is asked, the analysis
    is deterministic and needs no network, and every ambiguous case stays ambiguous. With it, only cases the
    engine itself gave up on are asked, only among candidates the drawing offers, and every answer is verified
    against those candidates twice before it can move a metre.
    """
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
        # bounded, and it says where it is: an assist that holds a finished reading is worse than no assist
        ocr_report = resolve_unknown_glyphs(page, vtext.rows, budget_s=OCR_ASSIST_BUDGET_S,
                                            progress=(lambda t: progress(f"RESOLVING_UNREADABLE_TEXT {t}"))
                                            if progress else None,
                                            seen=film.seeing if film else None)
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

    def run_pass(ann_layers: dict[str, int] | None, admit_leader_pens: bool = False):
        ann_marks = [m for m in vtext.marks if f"{m.layer}|{m.style}" in ann_layers] if ann_layers else vtext.marks
        leaderless: dict[str, list[str]] = {}
        leaders = discover_leaders(page, blocks, free, ann_marks, ann_layers, report=leaderless)
        exclude = set(ann_layers) if ann_layers else set()
        gidx = GeometryIndex(page, exclude, glyph_pids)
        des_leaders = [ld for ld in leaders if ld.block_id in des_by_block]
        votes: Counter = Counter()
        token_votes: Counter = Counter()
        leader_votes: Counter = Counter()
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
            # how many of the sheet's own pipe labels point at this family, counted once per label however many
            # of its objects that label's leader happens to run along. This is the quantity a reader would count
            # off the drawing, and unlike a sum of contact weights it does not grow with how a family is exported.
            for fam in {f for f, _ in seen_obj}:
                leader_votes[fam] += 1
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
        # leaders is a leader family however few it carries. A pen width says nothing, and counting leaders is not
        # enough there either: a sheet exported without layer names draws its leaders with the same pens as its
        # pipes, and refusing every pen that carries a quarter of the leaders left such a sheet with no pipes at
        # all. What separates them is how much of the pen's own ink the leaders are. Where a pen draws leaders and
        # little else, it is the leader pen; where the leaders are a fraction of what it draws, the rest of that
        # ink is the drawing, and the pen stays a candidate.
        lead_ink: Counter = Counter()
        for ld in des_leaders:
            fk = stroke_family(ld.layer, ld.width, ld.color)
            for sgm in ld.segs:
                lead_ink[fk] += sgm.seg.length
        fam_ink: Counter = Counter()
        for pth in page.paths:
            if pth.pid in annotation_pids:
                continue
            fk = stroke_family(pth.layer, pth.width, pth.color)
            for sgm in pth.segs:
                fam_ink[fk] += sgm.length
        leader_fams = {f for f, c in lead_count.items()
                       if f.split("|s|")[0]
                       or c >= LEADER_MIN_SHARE * top
                       and not (admit_leader_pens and lead_ink[f] < LEADER_INK_SHARE * fam_ink.get(f, 0.0))} \
            | (set(ann_layers) if ann_layers else set())
        if os.environ.get("VVS_DEBUG_INK"):
            for f, c in lead_count.most_common():
                fi = fam_ink.get(f, 0.0) or 1.0
                print(f"[ink] n={c:4d} andel={lead_ink[f]/fi:7.3f} röster={votes.get(f,0):7.1f} ticks={tick_votes.get(f,0):4d} "
                      f"ledarfamilj={f in leader_fams}  {f}", file=sys.stderr)
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
        # the strongest evidence any single drawn family carries, which is what the others are compared with
        chain_voted = [f for f in voted if chain_like(f)]
        best_ticks = max((tick_votes[f] for f in chain_voted), default=0)
        best_votes = max((votes[f] for f in chain_voted), default=0.0)
        best_leaders = max((leader_votes[f] for f in chain_voted), default=0)
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
                or (not token_fams and tick_votes[f] >= 2 and tick_votes[f] >= PEER_SHARE * best_ticks) \
                or (not token_fams and votes[f] >= 5 and votes[f] >= PEER_SHARE * best_votes) \
                or (not token_fams and leader_votes[f] >= PEER_LABELS_MIN and leader_votes[f] >= PEER_SHARE * best_leaders)
            # A leader that ends on a valve or a floor drain and only then reaches the pipe leaves no tick on the
            # pipe itself, and a sum of contact weights counts one label several times when its leader runs along
            # several pieces of the same family. Neither says what a reader would say, which is simply: how many
            # of this sheet's labels point here. Counted that way, a third pipe size on a layer-less sheet that
            # carried more labels than either family taken - and was refused for holding fewer than five contact
            # weights, on a sheet whose best family held four - is a peer of them.
            #
            # A sheet with no layer names to vouch for anything used to need one family to carry a large share of
            # every leader on the page. But a drawing that runs tap water, waste and heating draws them with
            # their own pens, and then no single family holds a large share of the total - the votes are split
            # between them and every one of them falls short. So a family is measured against the best family
            # rather than against the sum: several pens carrying comparable numbers of label ends are several
            # systems, while the sheet's background carries almost none however the rest is divided.
            if accept:
                pipe_families[f] = desc[f][0]
                graphs[f] = desc[f][1]
        pipe_families, graphs = _generalize_families(page, pipe_families, graphs)
        # Every drawn family the reading looked at and did not take, with the reason it did not. A family that is
        # declined is drawn on the sheet and simply absent from the reading afterwards, and geometry that is
        # absent without a word is indistinguishable from geometry that was never seen. Declining is often
        # right - walls and grids share a pen with pipes - so the point is not to take these, it is to say them.
        declined: dict[str, dict] = {}
        for f in voted:
            if f in pipe_families or f not in desc:
                continue
            rf = desc[f][0]
            layer, style = f.split("|s|")
            if not chain_like(f):
                why = "NO_CONTINUOUS_RUN"
            elif not layer and rf.width < median_width:
                why = "FAINTEST_PEN_ON_THE_SHEET"
            else:
                why = "NO_LABEL_REACHED_IT"
            declined[f] = {"family": f, "kind": rf.kind, "why": why, "width": round(rf.width, 2),
                           "longest_chain": round(rf.longest_chain, 1), "total_length_pt": round(rf.total_length, 1),
                           "votes": round(votes.get(f, 0.0), 2), "tick_votes": tick_votes.get(f, 0),
                           "leader_votes": leader_votes.get(f, 0),
                           "n_segments": len(prims_all.get(f) or ())}
        # Keep the drawn strokes of the declined families so a reader can see them, spending the budget on the
        # ones a label came closest to: a wall layer holds tens of thousands of strokes and would drown both the
        # payload and the eye, while the family that nearly became pipe is the one worth looking at.
        budget = DECLINED_SEGMENT_BUDGET
        for f in sorted(declined, key=lambda k: (-declined[k]["tick_votes"], -declined[k]["votes"], -declined[k]["total_length_pt"])):
            take = min(budget, DECLINED_SEGMENTS_PER_FAMILY, declined[f]["n_segments"])
            qs = (prims_all.get(f) or [])[:take]
            declined[f]["segments"] = [[round(q.seg.x0, 2), round(q.seg.y0, 2), round(q.seg.x1, 2), round(q.seg.y1, 2)] for q in qs]
            declined[f]["segments_truncated"] = take < declined[f]["n_segments"]
            budget -= take
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
            anchors.extend(resolve_block(block, rows, ld, contacts, system_tokens, spelled_out, paths))
        anchors.sort(key=lambda a: a.anchor_id)
        stats = {"votes": dict(votes.most_common()), "token_votes": dict(token_votes.most_common()), "candidate_families": sorted(pipe_families), "tick_votes": dict(tick_votes.most_common()),
                 "leader_votes": dict(leader_votes.most_common()), "declined_families": declined,
                 "labels_without_a_leader": {b: sorted(set(v)) for b, v in leaderless.items()},
                 "leader_pens_admitted": admit_leader_pens}
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
    # A sheet labels the pipes it draws. Where the families accepted carry no layer name to vouch for them, and
    # the sheet's own pipe labels overwhelmingly failed to reach them, the wrong geometry was accepted: had it
    # been the pipes, the labels would have found it. Measured over the style library, a sheet reading its own
    # pipes places a quarter of its pipe labels or better; the one reading its building outline placed 6 %.
    def _reached(anchors) -> set[str]:
        return reached_labels(anchors, pipe_labels)

    def _label_reach_fails(fams, anchors) -> bool:
        return label_reach_fails(fams, anchors, pipe_labels)

    # A pen that carries the sheet's leaders is normally not one that draws its pipes, and where a layer name
    # vouches for the geometry that always holds. Without layer names it is the only rule there is, and on a sheet
    # whose export collapsed leaders and pipes onto one pen it refuses the pipes as well: the page then measures
    # nothing at all. So the refusal stands unless it leaves the sheet unread, and only then are the pens whose
    # leaders are a small part of what they draw let back in - a rescue, not a default, because admitting them
    # everywhere also admits the pen a sheet hatches its building with, and the drawing fills with pipe that no
    # label owns.
    if not pipe_families or _label_reach_fails(pipe_families, anchors):
        rescue = run_pass(None, admit_leader_pens=True)
        if rescue[1] and not _label_reach_fails(rescue[1], rescue[3]) and len(_reached(rescue[3])) > len(_reached(anchors)):
            if os.environ.get("VVS_DEBUG_PASS"):
                print(f"[rescue] leader pens admitted: {len(_reached(anchors))} -> {len(_reached(rescue[3]))} "
                      f"of {len(pipe_labels)} labels placed", file=sys.stderr)
            leaders, pipe_families, graphs, anchors, contact_stats = rescue
    pass1 = (leaders, pipe_families, graphs, anchors, contact_stats)
    if os.environ.get("VVS_DEBUG_PASS"):
        print(f"[reach] pass1 placed {len(_reached(anchors))}/{len(pipe_labels)} pipe labels, fams={sorted(pipe_families)}", file=sys.stderr)
    if ann_layers:
        # a vector family accepted as pipe geometry in pass 1 is never an annotation family (an underline bar that
        # happens to share the pipes' stroke class must not remove the pipes)
        keep = {k: v for k, v in ann_layers.items() if (v >= 2 or v >= 0.05 * max(ann_layers.values())) and k not in pipe_families}
        pass2 = run_pass(keep)
        # The restriction is a hypothesis about which of the sheet's pens write rather than draw, learned from
        # the attachments the first reading verified. It is the sheet's own labels that test it: a sheet labels
        # the pipes it draws, so the reading that puts more of its labels on pipes is the one that read it. Where
        # the restriction withdraws the very pens the leaders were drawn with, it places fewer of them - or none
        # at all - and then the unrestricted reading stands. Without this a sheet the first pass read well ended
        # with a worse answer, and on some sheets with no answer at all.
        # Where a layer name vouches for the geometry, the restriction is checked only against collapse: the name
        # is the drawing's own statement and outweighs a count. Where nothing vouches for anything, the count is
        # all there is, and a restriction that costs the sheet more than half its placed labels has withdrawn the
        # pens the drawing was read with rather than the pens it was written with.
        nameless = not any(f.split("|s|")[0] for f in (pass2[1] or pass1[1] or {"x|s|"}))
        collapsed = not pass2[1] or _label_reach_fails(pass2[1], pass2[3])
        halved = nameless and 2 * len(_reached(pass2[3])) < len(_reached(pass1[3]))
        take1 = (collapsed or halved) and pass1[1] and not _label_reach_fails(pass1[1], pass1[3])
        if take1:
            if os.environ.get("VVS_DEBUG_PASS"):
                print(f"[withdraw] restricted pass left {len(_reached(pass2[3]))}/{len(pipe_labels)} labels placed, "
                      f"unrestricted placed {len(_reached(pass1[3]))}; keeping the unrestricted reading", file=sys.stderr)
            leaders, pipe_families, graphs, anchors, contact_stats = pass1
            contact_stats = dict(contact_stats, annotation_restriction_withdrawn=True)
            ann_layers = {}
        else:
            leaders, pipe_families, graphs, anchors, contact_stats = pass2
            ann_layers = keep
    else:
        ann_layers = {}
    if _label_reach_fails(pipe_families, anchors):
        if os.environ.get("VVS_DEBUG_PASS"):
            print(f"[drop] only {len(_reached(anchors))}/{len(pipe_labels)} pipe labels reached {sorted(pipe_families)}", file=sys.stderr)
        pipe_families, graphs, anchors, contact_stats = {}, {}, [], dict(contact_stats, dropped_by_label_reach=True)
    film.leaders(leaders)
    film.families(pipe_families, graphs)
    timings["leader_ms"] = 0.0
    t0 = _t(timings, "leader_attachment_ms", t0)
    if progress:
        progress("BUILDING_TOPOLOGY")
    graphs, pipe_families = _split_at_tick_contacts(page, graphs, pipe_families, anchors)
    prims = {fk: graphs[fk].prims for fk in graphs}
    # a family taken after the passes ran is not a declined one, whatever the pass that looked at it decided
    if contact_stats.get("declined_families"):
        contact_stats["declined_families"] = {k: v for k, v in contact_stats["declined_families"].items() if k not in pipe_families}
    contact_stats["unconsidered_families"] = _unconsidered(page, pipe_families, contact_stats, ann_layers, glyph_pids, leaders)
    # where the drawing drew the same line twice. Said, not subtracted: see duplicate_overlaps for the measurement
    # that settles which of the two is the smaller error.
    dup_pt, dup_places = 0.0, []
    for fk, g in graphs.items():
        t, places = duplicate_overlaps(list(g.prims.values()))
        dup_pt += t
        dup_places.extend(places)
    dup_places.sort(key=lambda d: (-d["pt"], d["source_path"]))
    contact_stats["drawn_twice"] = {"total_pt": round(dup_pt, 2), "places": dup_places[:200],
                                    "n_places": len(dup_places)}
    # filled shapes are counted but never drawn as candidates: a pipe is a stroked line, and a filled outline of
    # a room or a piece of furniture is not one however much of the sheet it covers
    contact_stats["filled_shapes"] = {"paths": sum(1 for p in page.paths if p.kind != "s"),
                                      "length_pt": round(sum(p.length for p in page.paths if p.kind != "s"), 1)}
    t0 = _t(timings, "topology_ms", t0)
    if progress:
        progress("BUILDING_PHYSICAL_PIPES")
    # what the rest of the sheet already says about where this system is drawn, before anyone is asked anything
    _settle_by_system_usage(anchors)

    # A second reader, where one is offered, sees the open cases before ownership is built - so anything it
    # settles is seeded like any other reading and carried by the same rules, rather than pasted on afterwards.
    second: dict | None = None
    if second_reader is not None:
        from .semantics.astra import Settlement, apply_answers, questions_for, settle as ask_settle
        qs = questions_for(anchors)
        st = Settlement(answers=ask_settle(qs, ask=second_reader))
        second = dict(st.as_dict(), applied=apply_answers(anchors, st.answers))
        anchors.sort(key=lambda a: a.anchor_id)

    identities = _pipe_identities(designations, anchors, grammar, legend=legend)
    ownership = propagate(graphs, anchors, page.info.index, identities, spelled_out)
    if _settle_bundles_by_elimination(anchors, ownership, graphs):
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
                            anchors=anchors, legend=legend, pipe_families=pipe_families, page=page,
                            lines=lines, contact_stats=contact_stats)
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
    return PageAnalysis(page=page, legend=legend, second_reader=second, layer_stats=layer_stats, vtext=vtext, srows=srows, lines=lines, blocks=blocks,
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
                # The unit is what the drawing wrote, not what the number looks like. A decimal separator is a
                # level in metres ("VG+1,67"); a whole number of a thousand or more is millimetres ("CL 4000").
                # A bare small integer says neither, and guessing there turns 100 and 150 into fifty metres of
                # pipe. Such a value is carried with no unit and no vertical length is claimed from it.
                digits = m.group(3)
                unit = "m" if ("." in digits or "," in digits) else ("mm" if abs(v) >= 1000 else None)
                ev.append({"tag": m.group(1), "value": v, "unit": unit,
                           "text": r.text_norm, "row_id": r.line.rid})
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
