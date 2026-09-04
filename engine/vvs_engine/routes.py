"""Reading the same drawing by more than one route, and saying where the routes disagree.

One reading can be wrong in a way it cannot see: a leader that lands on the wrong line names the wrong run, and
nothing inside that reading contradicts it. So the sheet is read again by a route that uses different evidence,
and the answers are put side by side. Where two routes name the same geometry the same way, the reading is
corroborated. Where they name it differently, the run is ambiguous and stays out of the quantity. Where only one
route reaches a run, that is said plainly rather than hidden inside a number.

There are two independent ways a drawing says which run a label names, and one way of carrying an identity
further than either of them said:

  pointing   the label's own leader, traced to the geometry it touches or the symbol it ends at
  writing    the label written along the run - parallel to it, beside it, spanning it, and alone on it
  closure    an identity continuing through a junction, or over a layer that names one system: not a second
             reading at all but the first one carried on, so metres reached only this way are counted as such

A route may add a run the others missed, and it may contradict one - which makes the run ambiguous. It may never
rename a run another route confirmed, because then the two readings would no longer be independent.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from .geometry.core import angle_diff
from .pipes.ownership import Identity, identity_from_text
from .text.model import project, row_axes

ROUTES = ("pointing", "writing", "closure")
INDEPENDENT = ("pointing", "writing")       # those that read the drawing rather than carry a reading on

_CLOSURE_REASONS = ("family_uniform_identity", "collinear_through_junction",
                    "unlabeled_branch_takes_the_only_junction_identity", "through_junction_up_to_tick_boundary",
                    "junction_dn_completes_dn_less_label", "junction_dn_over_symbol_labels")

ALONGSIDE_BAND = 2.2        # text heights: how far beside its run a label may be written
ALONGSIDE_ANGLE = 6.0       # degrees: the label reads along the run
ALONGSIDE_COVER = 0.6       # the run must span this much of the label's own length
ALONGSIDE_MIN_LABELS = 3    # and the sheet must label this way for more than one label, or it is not its way
ALONGSIDE_MIN_SHARE = 0.15

# A leader that stops short of every run is NOT read as pointing at the nearest one. Tried and measured: on the
# reference sheets it picks the wrong line out of a parallel bundle, because once the tip touches nothing, "which
# run" is decided by distance alone - which is the one thing this engine may never do. Such a leader is reported
# unplaced instead, with its reason, in the review.


@dataclass(frozen=True)
class Claim:
    """One route saying that one primitive belongs to one identity."""
    family: str
    prim_id: int
    identity: Identity
    route: str
    evidence: str


@dataclass
class RouteReport:
    route: str
    claims: list[Claim] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


def _first_reading(pa) -> dict[str, RouteReport]:
    """The reading already made, split into what the leaders said and what was carried on from it."""
    out = {r: RouteReport(route=r) for r in ROUTES}
    for fk, states in pa.ownership.prim_states.items():
        for pid, st in states.items():
            if st.state != "CONFIRMED" or st.identity is None:
                continue
            r = "closure" if st.reason in _CLOSURE_REASONS else "pointing"
            out[r].claims.append(Claim(family=fk, prim_id=pid, identity=st.identity, route=r, evidence=st.reason))
    return out


def _row_height(d) -> float:
    return max(min(d.bbox[3] - d.bbox[1], d.bbox[2] - d.bbox[0]), 1.0)


def _bbox_span(bbox, axis) -> tuple[float, float]:
    corners = [(bbox[0], bbox[1]), (bbox[2], bbox[1]), (bbox[0], bbox[3]), (bbox[2], bbox[3])]
    ps = [project(c, axis) for c in corners]
    return min(ps), max(ps)


def writing_route(pa) -> RouteReport:
    """Labels written along the run they name.

    A drawing may name a run by writing on it rather than by pointing at it. That is evidence when the writing
    reads along the run, sits in a narrow band beside it, spans it, and is the only label on it: then the sheet
    has said which run it means as plainly as a leader would. Anything less is nearness, and nearness names
    nothing - so a label whose own leader already reached a pipe is not read this way, and a sheet where only a
    label or two happens to lie along a run is not a sheet that labels by writing.
    """
    from .pipes.representation import chains as graph_chains
    rep = RouteReport(route="writing")
    if not pa.graphs:
        return rep
    lg = pa.legend
    anchored = {a.designation_id for a in pa.anchors if a.state == "VERIFIED_PIPE_ATTACHMENT"}
    pipe_labels = [d for d in pa.designations
                   if lg.names_a_pipe(d) and (d.text or "").upper() not in lg.components()]
    cand = [d for d in pipe_labels if d.dn is not None and d.did not in anchored]
    chain_of: dict[str, dict[int, int]] = {}
    chains: dict[str, list[list[int]]] = {}
    for fk, g in pa.graphs.items():
        ch = graph_chains(g)
        chains[fk] = ch
        chain_of[fk] = {pid: ci for ci, c in enumerate(ch) for pid in c}
    hits: dict[tuple[str, int], list] = defaultdict(list)
    for d in cand:
        d_dir, d_nrm = row_axes(d.angle)
        H = _row_height(d)
        s0, s1 = _bbox_span(d.bbox, d_dir)
        n0, n1 = _bbox_span(d.bbox, d_nrm)
        base = 0.5 * (n0 + n1)
        found: set[tuple[str, int]] = set()
        for fk, g in pa.graphs.items():
            for pid, q in g.prims.items():
                if angle_diff(q.seg.angle, d.angle % 180.0) > ALONGSIDE_ANGLE:
                    continue
                a0 = min(project(q.a, d_dir), project(q.b, d_dir))
                a1 = max(project(q.a, d_dir), project(q.b, d_dir))
                if min(a1, s1) - max(a0, s0) < ALONGSIDE_COVER * max(s1 - s0, 1e-6):
                    continue
                if abs(0.5 * (project(q.a, d_nrm) + project(q.b, d_nrm)) - base) > ALONGSIDE_BAND * H:
                    continue
                found.add((fk, chain_of[fk][pid]))
        if len(found) == 1:
            hits[next(iter(found))].append(d)
    named = {k: v[0] for k, v in hits.items() if len(v) == 1}
    rep.stats = {"labels_without_a_leader": len(cand), "runs_named": len(named),
                 "runs_with_several_labels": sum(1 for v in hits.values() if len(v) > 1),
                 "used": False}
    if len(named) < ALONGSIDE_MIN_LABELS or len(named) < ALONGSIDE_MIN_SHARE * max(len(pipe_labels), 1):
        return rep      # this sheet does not label by writing along its runs; a stray adjacency says nothing
    rep.stats["used"] = True
    for (fk, ci), d in sorted(named.items()):
        ident = identity_from_text(d.display_text, d.dn, d.system_token, None)
        for pid in chains[fk][ci]:
            rep.claims.append(Claim(family=fk, prim_id=pid, identity=ident, route="writing",
                                    evidence="label_written_along_the_run"))
    return rep


def run_routes(pa) -> dict[str, RouteReport]:
    reports = _first_reading(pa)
    reports["writing"] = writing_route(pa)
    return reports


def cross_check(pa, reports: dict[str, RouteReport]) -> dict[str, Any]:
    """Put the routes side by side, primitive by primitive, and say where they agree."""
    by_prim: dict[tuple[str, int], dict[str, Identity]] = defaultdict(dict)
    for rep in reports.values():
        for c in rep.claims:
            by_prim[(c.family, c.prim_id)][c.route] = c.identity
    mpp = (pa.scale.meters_per_pt or 0.0) if pa.scale else 0.0
    corroborated = pointed = closure_only = conflict = 0.0
    conflicts: list[dict] = []
    per_route: Counter = Counter()
    for (fk, pid), claims in by_prim.items():
        L = pa.graphs[fk].prims[pid].seg.length * mpp
        for r in claims:
            per_route[r] += L
        keys = {i.key for i in claims.values()}
        indep = [r for r in claims if r in INDEPENDENT]
        if len(keys) > 1:
            conflict += L
            conflicts.append({"family": fk, "prim": pid, "routes": {r: i.key for r, i in sorted(claims.items())}})
        elif len(indep) >= 2:
            corroborated += L
        elif indep:
            pointed += L
        else:
            closure_only += L
    return {
        "routes": {r: {"metres": round(per_route[r], 2), **reports[r].stats} for r in ROUTES},
        "corroborated_m": round(corroborated, 2),
        "one_reading_m": round(pointed, 2),
        "closure_only_m": round(closure_only, 2),
        "in_conflict_m": round(conflict, 2),
        "conflicts": conflicts[:200],
        "n_conflicts": len(conflicts),
    }


def apply_routes(pa, reports: dict[str, RouteReport]) -> dict[str, Any]:
    """Let a second route add what the first missed, and let a disagreement take a run out of the quantity."""
    from .pipes.ownership import _build_pipes
    own = pa.ownership
    added = made_ambiguous = 0.0
    mpp = (pa.scale.meters_per_pt or 0.0) if pa.scale else 0.0
    by_prim: dict[tuple[str, int], dict[str, Identity]] = defaultdict(dict)
    for rep in reports.values():
        if rep.route in ("pointing", "closure"):
            continue        # these are the reading already made
        for c in rep.claims:
            by_prim[(c.family, c.prim_id)][c.route] = c.identity
    touched: set[str] = set()
    for (fk, pid), claims in sorted(by_prim.items()):
        st = own.prim_states[fk][pid]
        keys = {i.key for i in claims.values()}
        L = pa.graphs[fk].prims[pid].seg.length * mpp
        if st.state == "CONFIRMED" and st.identity is not None:
            if len(keys) == 1 and next(iter(keys)) == st.identity.key:
                st.evidence.append("corroborated_by_" + "_and_".join(sorted(claims)))
            else:
                st.candidates = {st.identity} | set(claims.values())
                st.state, st.identity = "AMBIGUOUS", None
                st.reason = "AMBIGUOUS_ROUTES_DISAGREE"
                st.evidence.append("routes_disagree:" + ",".join(sorted(keys)))
                made_ambiguous += L
                touched.add(fk)
        elif st.state == "UNOWNED" and len(keys) == 1:
            st.state = "CONFIRMED"
            st.identity = next(iter(claims.values()))
            st.reason = "second_route_" + sorted(claims)[0]
            st.evidence.append("named_by_" + "_and_".join(sorted(claims)))
            added += L
            touched.add(fk)
    if touched:
        own.pipes = [p for p in own.pipes if p.family not in touched]
        for fk in sorted(touched):
            own.pipes.extend(_build_pipes(pa.graphs[fk], own.prim_states[fk], fk, pa.page.info.index))
        own.pipes.sort(key=lambda p: p.physical_pipe_id)
    return {"added_m": round(added, 2), "made_ambiguous_m": round(made_ambiguous, 2),
            "families_rebuilt": sorted(touched)}


def review(pa, cross: dict[str, Any]) -> dict[str, Any]:
    """What the reading did not reach, and why - so nothing is missing quietly.

    Two sweeps: the pipe geometry no route named, gathered into runs so a reader can find them on the sheet; and
    the pipe labels no route placed, with the reason the attachment gave.
    """
    from .pipes.representation import chains as graph_chains
    mpp = (pa.scale.meters_per_pt or 0.0) if pa.scale else 0.0
    unnamed: list[dict] = []
    unowned_m = ambiguous_m = confirmed_m = 0.0
    for fk, g in pa.graphs.items():
        states = pa.ownership.prim_states[fk]
        for c in graph_chains(g):
            L = sum(g.prims[p].seg.length for p in c) * mpp
            confirmed_m += sum(g.prims[p].seg.length for p in c if states[p].state == "CONFIRMED") * mpp
            ambiguous_m += sum(g.prims[p].seg.length for p in c if states[p].state == "AMBIGUOUS") * mpp
            unowned_m += sum(g.prims[p].seg.length for p in c if states[p].state == "UNOWNED") * mpp
            if all(states[p].state == "UNOWNED" for p in c) and L >= 0.5:
                q = g.prims[c[0]].seg
                unnamed.append({"family": fk, "n_primitives": len(c), "metres": round(L, 2),
                                "at": [round(q.x0, 1), round(q.y0, 1)], "reason": "no_route_named_this_run"})
    unnamed.sort(key=lambda r: -r["metres"])
    lg = pa.legend
    pipe_labels = [d for d in pa.designations
                   if lg.names_a_pipe(d) and (d.text or "").upper() not in lg.components()]
    placed = {a.designation_id for a in pa.anchors if a.state == "VERIFIED_PIPE_ATTACHMENT"}
    reasons: Counter = Counter()
    unplaced: list[dict] = []
    for d in pipe_labels:
        if d.did in placed:
            continue
        why = sorted({a.reason for a in pa.anchors if a.designation_id == d.did}) or ["no_leader_found"]
        reasons[why[0]] += 1
        unplaced.append({"designation": d.display_text, "at": [round(d.bbox[0], 1), round(d.bbox[1], 1)],
                         "reason": why[0], "unknown_characters": d.unknown_chars})
    total = confirmed_m + ambiguous_m + unowned_m
    return {
        "pipe_geometry_m": round(total, 2),
        "named_m": round(confirmed_m, 2),
        "ambiguous_m": round(ambiguous_m, 2),
        "unnamed_m": round(unowned_m, 2),
        "coverage_pct": round(100.0 * confirmed_m / total, 1) if total else None,
        "corroborated_m": cross["corroborated_m"],
        "one_reading_m": cross["one_reading_m"],
        "closure_only_m": cross["closure_only_m"],
        "in_conflict_m": cross["in_conflict_m"],
        "unnamed_runs": unnamed[:100],
        "n_unnamed_runs": len(unnamed),
        "pipe_labels": len(pipe_labels),
        "pipe_labels_placed": sum(1 for d in pipe_labels if d.did in placed),
        "unplaced_labels": unplaced[:200],
        "unplaced_reasons": dict(reasons.most_common()),
    }
