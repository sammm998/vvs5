"""Physical pipe ownership.

VERIFIED PipeCodeAnchors seed identities on pipe graphs. Resolution is CHAIN based (a chain = maximal run of
primitives through degree-2 nodes): a chain carrying seeds of one identity is confirmed entirely; where seeds of
different identities sit on the same chain, the geometry between them is AMBIGUOUS (DN boundary / system
conflict) - never split at an invented midpoint. At junctions an identity continues only along a collinear arm
(straight run through a tee/cross) or an arm supported by agreeing anchors; other unlabeled arms are
AMBIGUOUS_BRANCH. Every primitive ends as CONFIRMED, AMBIGUOUS or UNOWNED.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from ..geometry.core import angle_diff, dist, point_seg_distance, stable_id
from ..semantics.attachment import PipeCodeAnchor
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


def identity_of(a: PipeCodeAnchor, dn_token_index: int | None) -> Identity:
    from ..semantics.grammar import split_tokens
    toks = split_tokens(a.designation)
    base_toks = list(toks)
    if dn_token_index is not None and dn_token_index < len(toks) and toks[dn_token_index].isdigit():
        base_toks = [t for i, t in enumerate(toks) if i != dn_token_index]
    return Identity(base="-".join(base_toks), dn=a.dn, system=a.system_token, display=a.designation)


def _seed_prims(a: PipeCodeAnchor, graphs: dict[str, PipeGraph]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = defaultdict(list)
    for c in a.contacts:
        g = graphs.get(c.family)
        if g is None:
            continue
        best = None
        for pid, q in g.prims.items():
            if q.pid != c.pid or q.seg_index != c.seg_index:
                continue
            d, t = point_seg_distance(c.point[0], c.point[1], q.seg)
            if best is None or d < best[0]:
                best = (d, pid)
        if best is not None and best[0] <= 3.0 and best[1] not in out[c.family]:
            out[c.family].append(best[1])
    return out


def propagate(graphs: dict[str, PipeGraph], anchors: list[PipeCodeAnchor], page: int,
              identities: dict[str, Identity]) -> OwnershipResult:
    """identities: anchor_id -> Identity (only anchors that are verified AND belong to pipe-designation families)."""
    states: dict[str, dict[int, PrimState]] = {fk: {pid: PrimState() for pid in g.prims} for fk, g in graphs.items()}
    seeds: dict[str, dict[int, list[tuple[Identity, str]]]] = {fk: defaultdict(list) for fk in graphs}
    for a in sorted(anchors, key=lambda a: a.anchor_id):
        if a.anchor_id not in identities:
            continue
        ident = identities[a.anchor_id]
        for fk, pids in _seed_prims(a, graphs).items():
            for pid in pids:
                seeds[fk][pid].append((ident, a.anchor_id))
    ambiguous_runs: list[dict] = []
    for fk, g in graphs.items():
        _resolve_family(g, states[fk], seeds[fk], ambiguous_runs, fk)
    pipes: list[PhysicalPipe] = []
    for fk, g in graphs.items():
        pipes.extend(_build_pipes(g, states[fk], fk, page))
    pipes.sort(key=lambda p: p.physical_pipe_id)
    stats = Counter()
    for fk in graphs:
        for st in states[fk].values():
            stats[st.state] += 1
    return OwnershipResult(prim_states=states, pipes=pipes, ambiguous_runs=ambiguous_runs, stats=dict(stats))


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


def _resolve_family(g: PipeGraph, st: dict[int, PrimState], seeds, ambiguous_runs, fk: str) -> None:
    ch = graph_chains(g)
    chain_of: dict[int, int] = {}
    for ci, c in enumerate(ch):
        for pid in c:
            chain_of[pid] = ci
    # 1. chains with seeds
    for ci, c in enumerate(ch):
        pos = [(k, seeds[pid]) for k, pid in enumerate(c) if pid in seeds]
        if not pos:
            continue
        # merge compatible identities per seed position
        groups = []
        for k, lst in pos:
            ids = [i for i, _ in lst]
            merged = _merge_identity(ids)
            groups.append((k, merged, ids, [aid for _, aid in lst]))
        # segment boundaries: consecutive seed groups
        first_k, first_id, _, _ = groups[0]
        last_k, last_id, _, _ = groups[-1]
        # overall merge attempt: if all seeds compatible -> whole chain one identity
        all_ids = [i for _, _, ids, _ in groups for i in ids]
        whole = _merge_identity(all_ids)
        anchors_all = {aid for _, _, _, aids in groups for aid in aids}
        if whole is not None:
            for pid in c:
                s = st[pid]
                s.state, s.identity, s.reason = "CONFIRMED", whole, "chain_with_agreeing_anchors" if len(groups) > 1 else "chain_from_anchor"
                s.anchors |= anchors_all
            continue
        # different identities along the chain: outer parts belong to the outer seeds; between differing seeds ambiguous
        for k, pid in enumerate(c):
            s = st[pid]
            if k <= first_k and first_id is not None:
                s.state, s.identity, s.reason = "CONFIRMED", first_id, "chain_before_first_anchor"
                s.anchors |= set(groups[0][3])
            elif k >= last_k and last_id is not None:
                s.state, s.identity, s.reason = "CONFIRMED", last_id, "chain_after_last_anchor"
                s.anchors |= set(groups[-1][3])
        for gi in range(len(groups) - 1):
            ka, ida, idsa, aidsa = groups[gi]
            kb, idb, idsb, aidsb = groups[gi + 1]
            between = _merge_identity(idsa + idsb)
            for k in range(ka, kb + 1):
                pid = c[k]
                s = st[pid]
                if between is not None:
                    s.state, s.identity, s.reason = "CONFIRMED", between, "chain_between_agreeing_anchors"
                    s.anchors |= set(aidsa) | set(aidsb)
                elif not (k == ka and s.state == "CONFIRMED" and gi == 0) and not (k == kb and s.state == "CONFIRMED" and gi == len(groups) - 2):
                    cands = set(i for i in idsa + idsb if i is not None)
                    reason = "AMBIGUOUS_DN_BOUNDARY" if len({i.base for i in cands}) == 1 or len({i.system for i in cands}) == 1 else "SYSTEM_CONFLICT"
                    s.state, s.identity, s.candidates, s.reason = "AMBIGUOUS", None, cands, reason
                    s.anchors |= set(aidsa) | set(aidsb)
            if between is None:
                cands = sorted({i.key for i in idsa + idsb if i is not None})
                ambiguous_runs.append({"family": fk, "chain": ci, "from_prim": c[ka], "to_prim": c[kb],
                                       "reason": "AMBIGUOUS_DN_BOUNDARY" if len({i.base for i in idsa + idsb}) == 1 else "SYSTEM_CONFLICT",
                                       "identities": cands})
    # 2. junction resolution (iterative): collinear straight-through continuation; other arms ambiguous
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
