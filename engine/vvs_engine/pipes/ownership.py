"""Physical pipe ownership.

VERIFIED PipeCodeAnchors seed identities on pipe graphs. Resolution is CHAIN based (a chain = maximal run of
primitives through degree-2 nodes): a chain carrying seeds of one identity is confirmed entirely; where seeds of
different identities sit on the same chain, the geometry between them is AMBIGUOUS (DN boundary / system
conflict) - never split at an invented midpoint. At junctions an identity continues only along a collinear arm
(straight run through a tee/cross) or an arm supported by agreeing anchors; other unlabeled arms are
AMBIGUOUS_BRANCH. Every primitive ends as CONFIRMED, AMBIGUOUS or UNOWNED.
"""
from __future__ import annotations

import re

import math
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from ..geometry.core import GridIndex, angle_diff, dist, point_seg_distance, stable_id
from ..semantics.attachment import PipeCodeAnchor, system_layer_match
from .representation import PipeGraph, Prim, chains as graph_chains


@dataclass(frozen=True)
class Identity:
    base: str                 # designation without its inline DN token (system + material tokens)
    dn: int | None
    system: str
    display: str              # designation as written (most common form)

    @property
    def key(self) -> str:
        return f"{self.base}|DN{self.dn if self.dn is not None else '?'}"

    def compatible(self, other: "Identity") -> bool:
        return self.base == other.base and (self.dn is None or other.dn is None or self.dn == other.dn)


@dataclass
class PrimState:
    state: str = "UNOWNED"                    # CONFIRMED | AMBIGUOUS | UNOWNED
    identity: Identity | None = None
    candidates: set[Identity] = field(default_factory=set)
    reason: str = ""
    anchors: set[str] = field(default_factory=set)
    evidence: list[str] = field(default_factory=list)


@dataclass
class PhysicalPipe:
    physical_pipe_id: str
    page: int
    family: str
    identity: Identity
    anchor_ids: list[str]
    prim_ids: list[int]
    points: list[list[tuple[float, float]]]
    source_paths: list[str]
    source_segments: list[str]
    nodes: list[int]
    raw_length_pt: float
    bridged_gap_pt: float
    frontier_reasons: list[str]
    evidence: list[str]
    state: str = "CONFIRMED"

    @property
    def length_pt(self) -> float:
        return self.raw_length_pt + self.bridged_gap_pt


@dataclass
class OwnershipResult:
    prim_states: dict[str, dict[int, PrimState]]
    pipes: list[PhysicalPipe]
    ambiguous_runs: list[dict]
    stats: dict[str, Any]
    riser_labels: dict[str, list[dict]] = field(default_factory=dict)   # identity key -> symbol-attached labels


def identity_of(a: PipeCodeAnchor, dn_token_index: int | None) -> Identity:
    """The identity a label names: its designation without the dimension token, plus the dimension.

    The name is read from the designation as the drawing states it - with a dimension row folded in - so that the
    two ways of writing one pipe, all on one line or the dimension on the row below, give the same identity and
    are not measured as two. The dimension token is the one the grammar points at, and otherwise the first token
    after the system token that spells the dimension itself.
    """
    from ..semantics.grammar import split_tokens
    text = a.designation_display or a.designation
    toks = split_tokens(text)
    idx = dn_token_index
    if not (idx is not None and 0 < idx < len(toks) and toks[idx].isdigit() and a.dn is not None and int(toks[idx]) == a.dn):
        idx = None
        if a.dn is not None:
            pat = re.compile(re.escape(str(a.dn)) + r"[A-Za-zÅÄÖÅäö]{0,3}")
            idx = next((i for i, t in enumerate(toks) if i > 0 and pat.fullmatch(t)), None)
    base_toks = list(toks)
    if idx is not None:
        # the dimension token goes, and with it a short qualifier written after it: the medium belongs to the
        # dimension, so a qualifier the recogniser reads badly cannot split one pipe into two
        end = idx + 1
        while end < len(toks) and len(toks[end]) <= 3 and toks[end].isalpha():
            end += 1
        base_toks = toks[:idx] + toks[end:]
    return Identity(base="-".join(base_toks), dn=a.dn, system=a.system_token, display=text)


TICK_KINDS = ("end_tick", "crossing_tick")
STRONG_KINDS = ("end", "end_tick", "crossing_tick")        # the leader meets the pipe line itself
BOUNDARY_TOL = 0.75


def _seed_prims(a: PipeCodeAnchor, graphs: dict[str, PipeGraph]) -> dict[str, list[tuple[int, str, tuple[float, float]]]]:
    """Graph primitives touched by an anchor's contacts: (prim id, contact kind, contact point) per family."""
    out: dict[str, list[tuple[int, str, tuple[float, float]]]] = defaultdict(list)
    for c in a.contacts:
        g = graphs.get(c.family)
        if g is None:
            continue
        best = None
        for pid, q in g.prims.items():
            if q.pid != c.pid or q.seg_index != c.seg_index:
                continue
            d, t = point_seg_distance(c.point[0], c.point[1], q.seg)
            if best is None or d < best[0] - 1e-9:
                best = (d, pid)
        if best is not None and best[0] <= 3.0 and all(p != best[1] for p, _, _ in out[c.family]):
            out[c.family].append((best[1], c.kind, c.point))
    return out


def propagate(graphs: dict[str, PipeGraph], anchors: list[PipeCodeAnchor], page: int,
              identities: dict[str, Identity], spelled_out: frozenset[str] = frozenset()) -> OwnershipResult:
    """identities: anchor_id -> Identity (only anchors that are verified AND belong to pipe-designation families)."""
    states: dict[str, dict[int, PrimState]] = {fk: {pid: PrimState() for pid in g.prims} for fk, g in graphs.items()}
    seeds: dict[str, dict[int, list[tuple[Identity, str, str, tuple[float, float]]]]] = {fk: defaultdict(list) for fk in graphs}
    for a in sorted(anchors, key=lambda a: a.anchor_id):
        if a.anchor_id not in identities:
            continue
        ident = identities[a.anchor_id]
        for fk, lst in _seed_prims(a, graphs).items():
            for pid, kind, pt in lst:
                seeds[fk][pid].append((ident, a.anchor_id, kind, pt))
    ambiguous_runs: list[dict] = []
    for fk, g in graphs.items():
        _resolve_family(g, states[fk], seeds[fk], ambiguous_runs, fk)
    for fk, g in graphs.items():
        _family_uniform_identity(fk, states[fk], anchors, identities, spelled_out)
    for fk, g in graphs.items():
        _demote_unbounded_flow(g, states[fk], fk, ambiguous_runs)
    pipes: list[PhysicalPipe] = []
    for fk, g in graphs.items():
        pipes.extend(_build_pipes(g, states[fk], fk, page))
    pipes.sort(key=lambda p: p.physical_pipe_id)
    stats = Counter()
    for fk in graphs:
        for st in states[fk].values():
            stats[st.state] += 1
    return OwnershipResult(prim_states=states, pipes=pipes, ambiguous_runs=ambiguous_runs, stats=dict(stats))


# the two rules that carry an identity into geometry no label touched and no drawn boundary delimits
FLOWED_REASONS = ("collinear_through_junction", "unlabeled_branch_takes_the_only_junction_identity")


def _demote_unbounded_flow(g: PipeGraph, st: dict[int, PrimState], fk: str, ambiguous_runs: list[dict]) -> None:
    """An identity may run on through a junction into geometry the drawing does not name - a straight run through
    a tee, an unnamed branch off a labelled one. On a pipe network that adds a little to what the labels say. On
    a mesh of geometry that only looks like a network it adds without end, and every metre of it is a guess.

    So the flow has to stay within what the drawing itself states: where a family's flowed length exceeds the
    length its labels delimit, the flow is not evidence and the geometry it took is AMBIGUOUS, not measured.
    """
    labelled = flowed = 0.0
    for pid, s in st.items():
        if s.state != "CONFIRMED":
            continue
        if s.reason in FLOWED_REASONS:
            flowed += g.prims[pid].seg.length
        else:
            labelled += g.prims[pid].seg.length
    if flowed <= labelled:
        return
    n = 0
    for pid in sorted(st):
        s = st[pid]
        if s.state != "CONFIRMED" or s.reason not in FLOWED_REASONS:
            continue
        ident = s.identity
        s.state, s.identity, s.reason = "AMBIGUOUS", None, "AMBIGUOUS_FLOW_BEYOND_THE_LABELLED_RUNS"
        s.candidates = {ident} if ident is not None else set()
        s.evidence.append("identity_flowed_further_than_the_labels_of_this_family_delimit")
        n += 1
    if n:
        ambiguous_runs.append({"family": fk, "chain": -1, "from_prim": -1, "to_prim": -1,
                               "reason": "AMBIGUOUS_FLOW_BEYOND_THE_LABELLED_RUNS",
                               "identities": sorted({c.key for s in st.values() for c in s.candidates}),
                               "n_primitives": n, "flowed_pt": round(flowed, 1), "labelled_pt": round(labelled, 1)})


def _family_uniform_identity(fk: str, st: dict[int, PrimState], anchors: list[PipeCodeAnchor], identities: dict[str, Identity],
                             spelled_out: frozenset[str] = frozenset()) -> None:
    """A vector family whose layer name structurally carries one system token (exact or abbreviated tail, never a
    wildcard) and whose verified anchors (>= 2) all agree on one designation AND DN is a single-system, single-size
    layer: its unlabeled runs carry that identity (evidence: layer token + every anchor of the family)."""
    aids = sorted({a.anchor_id for a in anchors if a.anchor_id in identities and any(c.family == fk for c in a.contacts)})
    if len(aids) < 2:
        return
    idents = [identities[aid] for aid in aids]
    if any(i.dn is None for i in idents):
        return
    uni = _merge_identity(idents)
    if uni is None or uni.dn is None:
        return
    layer = fk.split("|s|")[0]
    tok = system_layer_match(uni.system, layer, spelled_out)
    if not tok:
        return
    S, TU = uni.system.upper(), tok.upper()
    if not (TU == S or (len(S) > len(TU) and S.endswith(TU))):
        return      # alpha-only or wildcard layer tokens cover several systems: no family-level identity
    for pid in sorted(st):
        s = st[pid]
        if s.state == "UNOWNED" or (s.state == "AMBIGUOUS" and s.candidates and all(_merge_identity([uni, c]) is not None for c in s.candidates)):
            s.state, s.identity, s.reason, s.candidates = "CONFIRMED", uni, "family_uniform_identity", set()
            s.anchors |= set(aids)
            s.evidence.append(f"layer_token_{tok}_and_{len(aids)}_agreeing_anchors_{uni.key}")


def _merge_identity(ids: list[Identity]) -> Identity | None:
    """Merge compatible identities (same base; DN None adopts the unique known DN). None if incompatible."""
    if not ids:
        return None
    base = ids[0].base
    if any(i.base != base for i in ids):
        return None
    dns = {i.dn for i in ids if i.dn is not None}
    if len(dns) > 1:
        return None
    dn = next(iter(dns)) if dns else None
    display = Counter(i.display for i in ids if i.dn == dn).most_common(1)
    disp = display[0][0] if display else ids[0].display
    return Identity(base=base, dn=dn, system=ids[0].system, display=disp)


def _conflict_reason(ids: list[Identity]) -> str:
    return "AMBIGUOUS_DN_BOUNDARY" if len({i.base for i in ids}) == 1 or len({i.system for i in ids}) == 1 else "SYSTEM_CONFLICT"


@dataclass
class _SeedGroup:
    pos: float                    # chain position: k + 0.5 on primitive k, or integer k for a boundary at node k
    merged: Identity | None
    ids: list[Identity]
    anchors: set[str]
    boundary: bool                # tick mark sitting on a graph node = drawn DN boundary evidence
    strong: bool = True           # leader met the line itself (weak = label points at a symbol / marker / fitting)


def _chain_nodes(g: PipeGraph, c: list[int]) -> list[int]:
    """Ordered node ids along a chain: node i sits between primitives c[i-1] and c[i] (len == len(c) + 1)."""
    if len(c) == 1:
        a, b = g.prim_nodes[c[0]]
        return [a, b]
    inner = []
    for i in range(1, len(c)):
        shared = set(g.prim_nodes[c[i - 1]]) & set(g.prim_nodes[c[i]])
        inner.append(min(shared) if shared else g.prim_nodes[c[i]][0])
    first = [n for n in g.prim_nodes[c[0]] if n != inner[0]]
    last = [n for n in g.prim_nodes[c[-1]] if n != inner[-1]]
    return [first[0] if first else inner[0]] + inner + [last[0] if last else inner[-1]]


def _dead_end(g: PipeGraph, nid: int, chain_set: set[int], pidx: GridIndex) -> bool:
    """A chain end is a dead end when its node has degree 1 and no other primitive of the family has an endpoint
    ahead of it (within 2.5 gap modes, inside a 60 degree cone): the drawn line really stops here."""
    n = g.nodes[nid]
    if n.degree != 1:
        return False
    q = g.prims[n.prims[0]]
    far = q.b if dist(q.a, (n.x, n.y)) < dist(q.b, (n.x, n.y)) else q.a
    L = dist(far, (n.x, n.y))
    if L < 1e-9:
        return False
    ux, uy = (n.x - far[0]) / L, (n.y - far[1]) / L
    R = max(2.5 * (g.gap_mode or 0.0), 6.0)
    for pid2 in pidx.query((n.x - R, n.y - R, n.x + R, n.y + R)):
        if pid2 in chain_set:
            continue
        r = g.prims[pid2]
        for ep in (r.a, r.b):
            vx, vy = ep[0] - n.x, ep[1] - n.y
            dd = math.hypot(vx, vy)
            if dd <= R and (dd < 1e-9 or (vx * ux + vy * uy) >= 0.5 * dd):
                return False
    return True


def _chain_seed_groups(g: PipeGraph, c: list[int], nodes: list[int], seeds) -> list[_SeedGroup]:
    by_pos: dict[float, list[tuple[Identity, str, bool, bool]]] = defaultdict(list)
    for k, pid in enumerate(c):
        for ident, aid, kind, pt in seeds.get(pid, []):
            pos, boundary = k + 0.5, False
            strong = kind in STRONG_KINDS
            if kind in TICK_KINDS:
                n0, n1 = g.nodes[nodes[k]], g.nodes[nodes[k + 1]]
                d0 = dist(pt, (n0.x, n0.y)); d1 = dist(pt, (n1.x, n1.y))
                if min(d0, d1) <= BOUNDARY_TOL:
                    pos, boundary = (float(k) if d0 <= d1 else float(k + 1)), True
                else:
                    # tick beyond the primitive's end (in a dash gap): boundary at the node on that side
                    q = g.prims[pid]
                    _, t = point_seg_distance(pt[0], pt[1], q.seg)
                    a_is_k = dist(q.a, (n0.x, n0.y)) <= dist(q.a, (n1.x, n1.y))
                    if t <= 0.02:
                        pos, boundary = (float(k) if a_is_k else float(k + 1)), True
                    elif t >= 0.98:
                        pos, boundary = (float(k + 1) if a_is_k else float(k)), True
            by_pos[pos].append((ident, aid, boundary, strong))
    out: list[_SeedGroup] = []
    for pos in sorted(by_pos):
        lst = by_pos[pos]
        ids = [i for i, _, _, _ in lst]
        out.append(_SeedGroup(pos=pos, merged=_merge_identity(ids), ids=ids, anchors={a for _, a, _, _ in lst},
                              boundary=all(b for _, _, b, _ in lst), strong=any(s for _, _, _, s in lst)))
    return out


def _drop_overridden_symbol_labels(gs: list[_SeedGroup]) -> tuple[list[_SeedGroup], list[_SeedGroup]]:
    """Labels pointing at a symbol (riser mark, fitting) describe that object; where labels on the line itself
    carry the same system with another DN, the symbol labels do not seed the run."""
    strong_ids = [i for grp in gs if grp.strong for i in grp.ids]
    if not strong_ids:
        return gs, []
    smerge = _merge_identity(strong_ids)
    if smerge is None:
        return gs, []
    kept, dropped = [], []
    for grp in gs:
        if (not grp.strong and grp.merged is not None and grp.merged.base == smerge.base
                and _merge_identity([smerge, grp.merged]) is None):
            dropped.append(grp)
        else:
            kept.append(grp)
    return kept, dropped


def _outward_compatible(gs: list[_SeedGroup], i: int, side: int) -> bool:
    """All seed groups beyond group i (towards the chain end on `side`) agree with group i."""
    others = gs[:i] if side < 0 else gs[i + 1:]
    return _merge_identity([gs[i].merged] + [x for grp in others for x in grp.ids]) is not None


def _resolve_family(g: PipeGraph, st: dict[int, PrimState], seeds, ambiguous_runs, fk: str) -> None:
    ch = graph_chains(g)
    chain_of: dict[int, int] = {}
    for ci, c in enumerate(ch):
        for pid in c:
            chain_of[pid] = ci
    chain_nodes = [_chain_nodes(g, c) for c in ch]
    pidx = GridIndex(cell=12.0)
    for pid, q in g.prims.items():
        pidx.insert(pid, q.seg.bbox())
    dead_cache: dict[tuple[int, int], bool] = {}

    def dead(ci: int, nid: int) -> bool:
        key = (ci, nid)
        if key not in dead_cache:
            dead_cache[key] = _dead_end(g, nid, set(ch[ci]), pidx)
        return dead_cache[key]

    def confirm(pids, ident: Identity, reason: str, aids: set[str]) -> None:
        for pid in pids:
            s = st[pid]
            s.state, s.identity, s.reason, s.candidates = "CONFIRMED", ident, reason, set()
            s.anchors |= aids

    def ambiguous(pids, ids, aids: set[str], reason: str) -> None:
        cands = {i for i in ids if i is not None}
        for pid in pids:
            s = st[pid]
            s.state, s.identity, s.candidates, s.reason = "AMBIGUOUS", None, cands, reason
            s.anchors |= aids

    groups_of: dict[int, list[_SeedGroup]] = {}
    # 1. chains with seeds. A tick mark on a node is drawn boundary evidence: between two incompatible seed
    #    groups the DN changes at a tick, and the identity whose run ends at a dead end is delimited by its own tick.
    for ci, c in enumerate(ch):
        nodes = chain_nodes[ci]
        gs = _chain_seed_groups(g, c, nodes, seeds)
        if not gs:
            continue
        gs, dropped = _drop_overridden_symbol_labels(gs)
        for grp in dropped:
            for pid in c:
                st[pid].evidence.append(f"symbol_label_{grp.merged.key}_describes_riser_or_fitting_not_the_run")
        groups_of[ci] = gs
        all_ids = [i for grp in gs for i in grp.ids]
        anchors_all = set().union(*(grp.anchors for grp in gs))
        whole = _merge_identity(all_ids)
        if whole is not None:
            confirm(c, whole, "chain_with_agreeing_anchors" if len(gs) > 1 else "chain_from_anchor", anchors_all)
            continue

        def prims_between(lo: float, hi: float) -> list[int]:
            return [c[k] for k in range(len(c)) if lo < k + 0.5 < hi]

        for grp in gs:
            if grp.boundary:
                continue
            pid = c[int(grp.pos)]
            if grp.merged is not None:
                confirm([pid], grp.merged, "chain_from_anchor", grp.anchors)
            else:
                ambiguous([pid], grp.ids, grp.anchors, _conflict_reason(grp.ids))
        first, last = gs[0], gs[-1]
        if first.merged is not None:
            confirm(prims_between(-1.0, first.pos), first.merged, "chain_before_first_anchor", first.anchors)
        if last.merged is not None:
            confirm(prims_between(last.pos, len(c) + 1.0), last.merged, "chain_after_last_anchor", last.anchors)
        for gi in range(len(gs) - 1):
            A, B = gs[gi], gs[gi + 1]
            pids = prims_between(A.pos, B.pos)
            between = _merge_identity(A.ids + B.ids)
            if between is not None:
                confirm(pids, between, "chain_between_agreeing_anchors", A.anchors | B.anchors)
                continue
            owner = None
            aids: set[str] = set()
            reason = ""
            if A.merged is not None and B.merged is not None:
                if B.boundary and not A.boundary:
                    owner, aids, reason = A.merged, A.anchors, "dn_boundary_at_tick"
                elif A.boundary and not B.boundary:
                    owner, aids, reason = B.merged, B.anchors, "dn_boundary_at_tick"
                elif A.boundary and B.boundary:
                    term_a = _outward_compatible(gs, gi, -1) and dead(ci, nodes[0])
                    term_b = _outward_compatible(gs, gi + 1, +1) and dead(ci, nodes[-1])
                    if term_b and not term_a:
                        owner, aids, reason = A.merged, A.anchors, "dn_boundary_at_tick_before_dead_end"
                    elif term_a and not term_b:
                        owner, aids, reason = B.merged, B.anchors, "dn_boundary_at_tick_before_dead_end"
                    elif A.merged.dn is not None and B.merged.dn is not None and A.merged.dn != B.merged.dn and A.merged.base == B.merged.base:
                        # a reduction is drawn at the tick of the smaller size: the larger size runs up to it
                        big, small = (A, B) if A.merged.dn > B.merged.dn else (B, A)
                        owner, aids, reason = big.merged, big.anchors, "dn_boundary_at_smaller_dn_tick"
            if not pids:
                continue
            if owner is not None:
                confirm(pids, owner, reason, aids)
            else:
                reason = _conflict_reason(A.ids + B.ids)
                ambiguous(pids, A.ids + B.ids, A.anchors | B.anchors, reason)
                ambiguous_runs.append({"family": fk, "chain": ci, "from_prim": pids[0], "to_prim": pids[-1], "reason": reason,
                                       "identities": sorted({i.key for i in A.ids + B.ids})})

    def tick_delimited_stub(v: int, nid: int, ident: Identity) -> tuple[list[int], bool] | None:
        """Primitives of v's chain that the junction's identity may take over: up to the nearest tick boundary when
        the chain carries labels on the line; the whole chain when it carries only symbol labels (risers) or
        DN-less labels. All seeds must agree with ident. Also returns whether the far end is a dead end."""
        ci = chain_of[v]
        gs = groups_of.get(ci)
        if not gs or _merge_identity([ident] + [x for grp in gs for x in grp.ids]) is None:
            return None
        nodes = chain_nodes[ci]
        c = ch[ci]
        if nodes[0] == nodes[-1]:
            return None
        if nodes[0] == nid:
            side = 0
        elif nodes[-1] == nid:
            side = 1
        else:
            return None
        if not any(grp.strong for grp in gs) or ident.dn is None:
            return list(c), dead(ci, nodes[-1] if side == 0 else nodes[0])
        bpos = [grp.pos for grp in gs if grp.boundary]
        if not bpos:
            return None
        b = int(min(bpos) if side == 0 else max(bpos))
        pids = [c[k] for k in (range(0, b) if side == 0 else range(b, len(c)))]
        if not pids:
            return None
        return pids, dead(ci, nodes[-1] if side == 0 else nodes[0])

    # 2. junction resolution (iterative): the junction's identity flows into a labeled arm up to its tick boundary;
    #    collinear continuation into unowned arms; other unlabeled arms ambiguous
    changed = True
    rounds = 0
    while changed and rounds < 100:
        changed = False
        rounds += 1
        for nid in sorted(g.nodes):
            n = g.nodes[nid]
            if n.degree < 3:
                continue
            arms = sorted(n.prims)
            resolved = [p for p in arms if st[p].state == "CONFIRMED" and st[p].identity is not None]
            # arms whose far end is a dead end and which carry a tick / symbol / DN-less label are stubs; the arms
            # that continue into the network are the sources of the junction's DN. A stub takes the sources' DN
            # up to its drawn tick (a DN change is drawn as a tick; riser labels describe the riser, not the run).
            info = {}
            for v in resolved:
                res = tick_delimited_stub(v, nid, st[v].identity)
                if res:
                    info[v] = res
            def is_collinear(a: int, b: int) -> bool:
                return angle_diff(g.prims[a].seg.angle, g.prims[b].seg.angle) <= 3.0

            # a stub is a dead-end BRANCH (not part of a straight run through the junction)
            stubs = {v for v, (pids, dead_far) in info.items() if dead_far and not any(is_collinear(v, p) for p in arms if p != v)}
            sources = [p for p in resolved if p not in stubs]
            src_aids = set().union(*(st[p].anchors for p in sources)) if sources else set()

            X = _merge_identity([st[p].identity for p in sources]) if sources else None
            if X is not None and X.dn is not None:
                for v in sorted(stubs):
                    Y = st[v].identity
                    if X.base != Y.base:
                        continue
                    merged = _merge_identity([X, Y])
                    if merged is not None and Y.dn is not None:
                        continue
                    if any(is_collinear(p, v) for p in arms if p != v) and not any(is_collinear(p, v) for p in sources):
                        continue    # straight run through the junction: only its own run may flow into it
                    pids, _ = info[v]
                    todo = [p for p in pids if st[p].state == "CONFIRMED" and st[p].identity == Y]
                    if not todo:
                        continue
                    if merged is not None:
                        reason = "junction_dn_completes_dn_less_label"
                    elif any(grp.strong for grp in groups_of.get(chain_of[v], [])):
                        reason = "through_junction_up_to_tick_boundary"
                    else:
                        reason = "junction_dn_over_symbol_labels"
                    confirm(todo, merged if merged is not None else X, reason, src_aids)
                    for p in todo:
                        st[p].evidence.append(f"junction_{nid}_identity_flows_into_stub")
                    changed = True
            # continuing arms with a tick boundary: the identity of the OTHER sources flows up to the tick when the
            # arm is the straight continuation of one of them; otherwise undecidable
            flows = []
            for v in sorted(info):
                if v in stubs:
                    continue
                others = [p for p in sources if p != v]
                if not others:
                    continue
                Xv = _merge_identity([st[p].identity for p in others])
                Y = st[v].identity
                if Xv is None or Xv.dn is None or Xv.base != Y.base:
                    continue
                merged = _merge_identity([Xv, Y])
                if merged is not None and Y.dn is not None:
                    continue
                pids, _ = info[v]
                collinear = any(is_collinear(p, v) for p in others)
                if any(is_collinear(p, v) for p in arms if p != v) and not collinear:
                    continue
                flows.append((v, merged if merged is not None else Xv, Y, pids, collinear, set().union(*(st[p].anchors for p in others)), merged is not None))
            decidable = [f for f in flows if f[4]]
            undecidable = [f for f in flows if not f[4] and not f[6]]
            if len(decidable) >= 2:
                # competing tick boundaries on collinear arms: the run that ends at a dead end is delimited by its
                # own tick (the other identity flows up to it); with no or several dead ends it is undecidable
                dead_arms = [f for f in decidable if info[f[0]][1]]
                if len(dead_arms) == 1:
                    decidable = dead_arms
                else:
                    bigger = [f for f in decidable if f[1].dn is not None and f[2].dn is not None and f[1].dn > f[2].dn]
                    if len(bigger) == 1:
                        decidable = bigger      # the larger size runs up to the smaller size's tick
            if len(decidable) == 1:
                v, X, Y, pids, _, aids, completion = decidable[0]
                todo = [p for p in pids if st[p].state == "CONFIRMED" and st[p].identity == Y]
                if todo:
                    reason = "junction_dn_completes_dn_less_label" if completion else "through_junction_up_to_tick_boundary"
                    confirm(todo, X, reason, aids)
                    for p in todo:
                        st[p].evidence.append(f"junction_{nid}_identity_flows_into_arm")
                    changed = True
            elif len(decidable) >= 2:
                for v, X, Y, pids, _, aids, completion in decidable:
                    todo = [p for p in pids if st[p].state == "CONFIRMED" and st[p].identity == Y]
                    if todo:
                        ambiguous(todo, [X, Y], aids, "AMBIGUOUS_DN_BOUNDARY")
                        for p in todo:
                            st[p].evidence.append(f"competing_tick_boundaries_at_junction_{nid}")
                        ambiguous_runs.append({"family": fk, "chain": chain_of[v], "from_prim": todo[0], "to_prim": todo[-1],
                                               "reason": "AMBIGUOUS_DN_BOUNDARY", "identities": sorted({X.key, Y.key})})
                        changed = True
            for v, X, Y, pids, _, aids, completion in undecidable:
                # a tick in the middle of a branch that continues into the network: the label points at this
                # branch; the branch keeps its own label (the tick is the leader's pointer, not a DN change)
                for p in pids:
                    if f"tick_on_branch_at_junction_{nid}_taken_as_label_pointer" not in st[p].evidence:
                        st[p].evidence.append(f"tick_on_branch_at_junction_{nid}_taken_as_label_pointer")
            resolved = [p for p in arms if st[p].state == "CONFIRMED"]
            unresolved = [p for p in arms if st[p].state == "UNOWNED"]
            if not resolved or not unresolved:
                continue
            for u in unresolved:
                # collinear resolved partner?
                partners = [p for p in resolved if angle_diff(g.prims[p].seg.angle, g.prims[u].seg.angle) <= 3.0]
                idents = {st[p].identity for p in partners}
                if len(idents) == 1:
                    ident = next(iter(idents))
                    # extend along u's chain until a junction/terminal
                    ci = chain_of[u]
                    for pid in ch[ci]:
                        s = st[pid]
                        if s.state == "UNOWNED":
                            s.state, s.identity, s.reason = "CONFIRMED", ident, "collinear_through_junction"
                            s.anchors |= set().union(*(st[p].anchors for p in partners))
                            s.evidence.append(f"straight_through_node_{nid}")
                    changed = True
                else:
                    cands = {st[p].identity for p in resolved}
                    ci = chain_of[u]
                    # an unlabeled branch where every labeled arm of the junction carries the SAME identity has no
                    # competing candidate: a size change is drawn with its own label, so an unnamed branch is the
                    # identity that feeds it. Only a junction with two or more candidates is genuinely ambiguous.
                    only = next(iter(cands)) if len(cands) == 1 else None
                    if only is not None and only.dn is not None and not groups_of.get(ci):
                        aids = set().union(*(st[p].anchors for p in resolved))
                        for pid in ch[ci]:
                            s = st[pid]
                            if s.state == "UNOWNED":
                                s.state, s.identity, s.reason = "CONFIRMED", only, "unlabeled_branch_takes_the_only_junction_identity"
                                s.anchors |= aids
                                s.evidence.append(f"single_candidate_at_node_{nid}")
                    else:
                        for pid in ch[ci]:
                            s = st[pid]
                            if s.state == "UNOWNED":
                                s.state, s.candidates, s.reason = "AMBIGUOUS", set(cands), "AMBIGUOUS_BRANCH"
                                s.evidence.append(f"unlabeled_branch_at_node_{nid}")
                    changed = True


def _build_pipes(g: PipeGraph, st: dict[int, PrimState], fk: str, page: int) -> list[PhysicalPipe]:
    pipes: list[PhysicalPipe] = []
    visited: set[int] = set()
    node_gap = {b["from_node"]: b["gap_pt"] for b in g.bridges}
    for pid in sorted(g.prims):
        s = st[pid]
        if s.state != "CONFIRMED" or pid in visited:
            continue
        comp = []
        dq = deque([pid])
        visited.add(pid)
        while dq:
            p = dq.popleft()
            comp.append(p)
            for node in g.prim_nodes[p]:
                for q in g.nodes[node].prims:
                    if q != p and q not in visited and st[q].state == "CONFIRMED" and st[q].identity == s.identity:
                        visited.add(q)
                        dq.append(q)
        comp.sort()
        prims = [g.prims[p] for p in comp]
        raw = sum(q.seg.length for q in prims)
        nodes = sorted({n for p in comp for n in g.prim_nodes[p]})
        compset = set(comp)
        gap = sum(node_gap[n] for n in nodes if n in node_gap and all(q in compset for q in g.nodes[n].prims))
        polylines = _order_polylines(g, comp)
        anchors = sorted({a for p in comp for a in st[p].anchors})
        evidence = sorted({st[p].reason for p in comp})
        ppid = stable_id("pp", page, fk, s.identity.key, *(f"{g.prims[p].pid}#{g.prims[p].seg_index}" for p in comp[:8]), len(comp))
        pipes.append(PhysicalPipe(physical_pipe_id=ppid, page=page, family=fk, identity=s.identity, anchor_ids=anchors,
                                  prim_ids=comp, points=polylines, source_paths=sorted({q.pid for q in prims}),
                                  source_segments=[f"{q.pid}#{q.seg_index}" for q in prims], nodes=nodes,
                                  raw_length_pt=raw, bridged_gap_pt=gap, frontier_reasons=[], evidence=evidence))
    return pipes


def _order_polylines(g: PipeGraph, comp: list[int]) -> list[list[tuple[float, float]]]:
    compset = set(comp)
    used: set[int] = set()
    out: list[list[tuple[float, float]]] = []

    def comp_degree(n):
        return sum(1 for p in g.nodes[n].prims if p in compset)

    starts = sorted(p for p in comp if any(comp_degree(n) != 2 for n in g.prim_nodes[p]))
    for start in starts + sorted(comp):
        if start in used:
            continue
        a, b = g.prim_nodes[start]
        if comp_degree(a) != 2:
            cur_node, far = a, b
        else:
            cur_node, far = b, a
        pts = [(g.nodes[cur_node].x, g.nodes[cur_node].y)]
        p = start
        while True:
            used.add(p)
            pts.append((g.nodes[far].x, g.nodes[far].y))
            nxt = [r for r in g.nodes[far].prims if r in compset and r != p and r not in used]
            if comp_degree(far) != 2 or not nxt:
                break
            p = nxt[0]
            a2, b2 = g.prim_nodes[p]
            far = b2 if a2 == far else a2
        out.append(pts)
    return out
