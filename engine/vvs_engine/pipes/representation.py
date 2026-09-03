"""Pipe representation discovery and fragment chaining.

Physical pipes are usually exported as many straight PDF fragments (dash pieces, dash-dot pieces, polyline
segments). For every (layer, style) family we discover the dominant micro-gap between collinear consecutive
fragments and bridge such gaps only when continuation is unique. Crossing is never connection.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..geometry.core import EXPORT_EPS, GridIndex, Seg, angle_diff, collinear, dist, point_seg_distance, seg_intersection, stable_id
from ..pdf.extract import RawPage, RawPath

TOUCH_TOL = 0.15


@dataclass(frozen=True)
class GraphTolerances:
    """Geometric precision the graph builder may assume of the source (exported vectors are exact)."""
    ang_tol: float = 1.5        # degrees, collinear continuation across a micro gap
    off_tol: float = 0.35       # pt, lateral offset of the continuation
    gap_slack: float = 0.5      # fraction of the gap mode accepted as deviation
    max_gap: float = 12.0       # pt, search window for a continuation


VECTOR_TOL = GraphTolerances()


def graph_tolerances(page) -> GraphTolerances:
    return VECTOR_TOL


@dataclass
class Prim:
    """A straight primitive of a pipe-candidate family (one segment of a raw path)."""
    prim_id: int
    pid: str
    seg_index: int
    seg: Seg
    family: str
    layer: str
    width: float

    @property
    def a(self):
        return (self.seg.x0, self.seg.y0)

    @property
    def b(self):
        return (self.seg.x1, self.seg.y1)


@dataclass
class Node:
    nid: int
    x: float
    y: float
    prims: list[int] = field(default_factory=list)   # prim ids incident here

    @property
    def degree(self) -> int:
        return len(self.prims)


@dataclass
class PipeGraph:
    family: str
    prims: dict[int, Prim]
    nodes: dict[int, Node]
    prim_nodes: dict[int, tuple[int, int]]           # prim id -> (node a, node b)
    bridges: list[dict]                               # micro-gap bridges (evidence)
    gap_mode: float | None
    junctions: list[dict] = field(default_factory=list)

    def neighbours(self, prim_id: int, node_id: int) -> list[int]:
        return [p for p in self.nodes[node_id].prims if p != prim_id]


@dataclass
class RepresentationFamily:
    family: str
    layer: str
    style: str
    width: float
    n_prims: int
    total_length: float
    gap_mode: float | None
    dash_mode: float | None
    n_chains: int
    longest_chain: float
    kind: str                       # 'fragmented-dashed' | 'continuous' | 'sparse'
    description: str

    def as_dict(self) -> dict[str, Any]:
        return {"family": self.family, "layer": self.layer, "style": self.style, "width": self.width, "n_primitives": self.n_prims,
                "total_length_pt": round(self.total_length, 1), "gap_mode_pt": self.gap_mode, "dash_mode_pt": self.dash_mode,
                "n_chains": self.n_chains, "longest_chain_pt": round(self.longest_chain, 1), "kind": self.kind, "description": self.description}


def family_key(p: RawPath) -> str:
    return f"{p.layer}|s|w{p.width:.2f}"


def collect_prims(page: RawPage, families: set[str]) -> dict[str, list[Prim]]:
    out: dict[str, list[Prim]] = defaultdict(list)
    pid_counter = 0
    for p in sorted(page.paths, key=lambda p: p.pid):
        if p.kind != "s":
            continue
        fk = family_key(p)
        if fk not in families:
            continue
        for k, s in enumerate(p.segs):
            if s.length < 1e-6:
                continue
            out[fk].append(Prim(prim_id=0, pid=p.pid, seg_index=k, seg=s, family=fk, layer=p.layer, width=p.width))
    # deterministic prim ids by content order
    for fk in out:
        out[fk].sort(key=lambda q: (q.pid, q.seg_index))
        for i, q in enumerate(out[fk]):
            q.prim_id = i
    return out


def split_t_junctions(prims: list[Prim]) -> tuple[list[Prim], list[dict]]:
    """An endpoint lying on the interior of another primitive of the same family is a proven T-contact
    (not a crossing): split that primitive there so the junction becomes a graph node."""
    idx = GridIndex(cell=12.0)
    for q in prims:
        idx.insert(q.prim_id, q.seg.bbox())
    pmap = {q.prim_id: q for q in prims}
    cuts: dict[int, list[float]] = defaultdict(list)
    junctions = []
    for q in prims:
        for ep in (q.a, q.b):
            for pid2 in idx.query_point(ep[0], ep[1], TOUCH_TOL + 0.05):
                if pid2 == q.prim_id:
                    continue
                r = pmap[pid2]
                d, t = point_seg_distance(ep[0], ep[1], r.seg)
                if d <= TOUCH_TOL and 0.02 < t < 0.98:
                    # not already an endpoint of r
                    if dist(ep, r.a) > TOUCH_TOL and dist(ep, r.b) > TOUCH_TOL:
                        cuts[pid2].append(t)
                        junctions.append({"prim": pid2, "t": round(t, 4), "from_prim": q.prim_id})
    return _apply_cuts(prims, cuts), junctions


def split_prims_at_points(prims: list[Prim], points: list[tuple[float, float]], tol: float = 1.0) -> list[Prim]:
    """Split primitives at drawn boundary points (tick marks of verified leaders) so that the boundary becomes a
    graph node; only interior hits (not already an endpoint) are cut."""
    if not points or not prims:
        return prims
    idx = GridIndex(cell=12.0)
    for q in prims:
        idx.insert(q.prim_id, q.seg.bbox())
    pmap = {q.prim_id: q for q in prims}
    cuts: dict[int, list[float]] = defaultdict(list)
    for (x, y) in sorted(points):
        for pid in idx.query_point(x, y, tol + 0.1):
            q = pmap[pid]
            d, t = point_seg_distance(x, y, q.seg)
            if d <= tol and 0.02 < t < 0.98 and dist((x, y), q.a) > tol and dist((x, y), q.b) > tol:
                cuts[pid].append(t)
    return _apply_cuts(prims, cuts)


def _apply_cuts(prims: list[Prim], cuts: dict[int, list[float]]) -> list[Prim]:
    if not cuts:
        return prims
    out: list[Prim] = []
    next_id = max(p.prim_id for p in prims) + 1
    for q in sorted(prims, key=lambda q: q.prim_id):
        ts = sorted(set(round(t, 5) for t in cuts.get(q.prim_id, [])))
        if not ts:
            out.append(q)
            continue
        pts = [q.a] + [(q.seg.x0 + t * (q.seg.x1 - q.seg.x0), q.seg.y0 + t * (q.seg.y1 - q.seg.y0)) for t in ts] + [q.b]
        for k in range(len(pts) - 1):
            a, b = pts[k], pts[k + 1]
            if dist(a, b) < 1e-6:
                continue
            nid = q.prim_id if k == 0 else next_id
            if k > 0:
                next_id += 1
            out.append(Prim(prim_id=nid, pid=q.pid, seg_index=q.seg_index, seg=Seg(a[0], a[1], b[0], b[1]), family=q.family, layer=q.layer, width=q.width))
    return out


def _merge_nodes(nodes, prim_nodes, nid: int, tn: int) -> None:
    for p in nodes[tn].prims:
        nodes[nid].prims.append(p)
        prim_nodes[p] = [nid if x == tn else x for x in prim_nodes[p]]
    nodes[tn].prims = []


def _outward(node, prim) -> tuple[float, float] | None:
    """Unit direction of the line leaving `node` along `prim`, pointing away from the primitive."""
    far = prim.b if dist(prim.a, (node.x, node.y)) < dist(prim.b, (node.x, node.y)) else prim.a
    dx, dy = node.x - far[0], node.y - far[1]
    L = math.hypot(dx, dy)
    return (dx / L, dy / L) if L > 1e-9 else None


def _corner_bridges(nodes, pmap, prim_nodes, idx, gap_mode: float, gtol: float, tol: GraphTolerances):
    """Pairs of free ends whose outward rays meet at a corner one gap away. Each end may take part in one
    corner only; a contested end is left open."""
    free = [n for n in nodes.values() if n.degree == 1]
    cands: dict[tuple[int, int], tuple[int, int, float, str]] = {}
    use: Counter = Counter()
    for n in free:
        u = _outward(n, pmap[n.prims[0]])
        if u is None:
            continue
        for m in free:
            if m.nid <= n.nid or not m.prims:
                continue
            if abs(m.x - n.x) > gap_mode + gtol or abs(m.y - n.y) > gap_mode + gtol:
                continue
            v = _outward(m, pmap[m.prims[0]])
            if v is None:
                continue
            turn = abs(((math.degrees(math.atan2(u[1], u[0]) - math.atan2(v[1], v[0])) + 180) % 360) - 180)
            if turn > 180 - 15.0:
                continue                      # the two ends face each other head-on: the collinear rule owns this
            den = u[0] * (-v[1]) - u[1] * (-v[0])
            if abs(den) < 1e-9:
                continue
            wx, wy = m.x - n.x, m.y - n.y
            t = (wx * (-v[1]) - wy * (-v[0])) / den      # along n's ray
            r = (u[0] * wy - u[1] * wx) / den            # along m's ray
            if t <= 0.2 or r <= 0.2 or t > tol.max_gap or r > tol.max_gap:
                continue
            if abs(t + r - gap_mode) > gtol:
                continue                      # the bend must span exactly one gap of this line style
            key = (min(n.nid, m.nid), max(n.nid, m.nid))
            if key not in cands or t + r < cands[key][2]:
                cands[key] = (n.nid, m.nid, t + r, "corner")
            use[n.nid] += 1; use[m.nid] += 1
    out = []
    for key in sorted(cands):
        a, b = key
        if use[a] > 1 or use[b] > 1:
            continue
        out.append(cands[key])
    return out


def build_graph(prims: list[Prim], family: str, tol: GraphTolerances | None = None) -> PipeGraph:
    """Nodes: shared endpoints (within TOUCH_TOL) incl. proven T-junctions. Then bridge collinear micro-gaps
    with unique continuation."""
    tol = tol or VECTOR_TOL
    prims, junctions = split_t_junctions(prims)
    # 1. endpoint clustering on a lattice
    pts = []
    for q in prims:
        pts.append((q.a, q.prim_id)); pts.append((q.b, q.prim_id))
    nodes: dict[int, Node] = {}
    lattice: dict[tuple[int, int], list[int]] = defaultdict(list)
    prim_nodes: dict[int, list[int]] = defaultdict(list)
    cell = TOUCH_TOL

    def find_node(x, y):
        cx, cy = int(math.floor(x / cell)), int(math.floor(y / cell))
        best = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for nid in lattice.get((cx + dx, cy + dy), []):
                    n = nodes[nid]
                    d = math.hypot(n.x - x, n.y - y)
                    if d <= TOUCH_TOL and (best is None or d < best[0]):
                        best = (d, nid)
        return best[1] if best else None

    for q in sorted(prims, key=lambda q: q.prim_id):
        for pt in (q.a, q.b):
            nid = find_node(pt[0], pt[1])
            if nid is None:
                nid = len(nodes)
                nodes[nid] = Node(nid=nid, x=pt[0], y=pt[1])
                lattice[(int(math.floor(pt[0] / cell)), int(math.floor(pt[1] / cell)))].append(nid)
            nodes[nid].prims.append(q.prim_id)
            prim_nodes[q.prim_id].append(nid)
    # 2. micro-gap statistics between collinear consecutive fragments at degree-1 nodes
    idx = GridIndex(cell=12.0)
    pmap = {q.prim_id: q for q in prims}
    for q in prims:
        idx.insert(q.prim_id, q.seg.bbox())
    gaps = []
    cand_bridges = []
    deg1 = [n for n in nodes.values() if n.degree == 1]
    for n in deg1:
        q = pmap[n.prims[0]]
        # direction pointing outward from the node
        far = q.b if dist(q.a, (n.x, n.y)) < dist(q.b, (n.x, n.y)) else q.a
        dx, dy = n.x - far[0], n.y - far[1]
        L = math.hypot(dx, dy)
        if L < 1e-9:
            continue
        ux, uy = dx / L, dy / L
        # search window ahead
        R = tol.max_gap
        box = (min(n.x, n.x + ux * R) - 1, min(n.y, n.y + uy * R) - 1, max(n.x, n.x + ux * R) + 1, max(n.y, n.y + uy * R) + 1)
        best = None
        for pid2 in idx.query(box):
            if pid2 == q.prim_id:
                continue
            r = pmap[pid2]
            if not collinear(q.seg, r.seg, ang_tol=tol.ang_tol, off_tol=tol.off_tol):
                continue
            # nearest endpoint of r ahead of the node
            for ep in (r.a, r.b):
                vx, vy = ep[0] - n.x, ep[1] - n.y
                along = vx * ux + vy * uy
                perp = abs(-vx * uy + vy * ux)
                if 0.2 < along <= R and perp <= tol.off_tol:
                    if best is None or along < best[0]:
                        best = (along, pid2, ep)
        if best is not None:
            gaps.append(best[0])
            cand_bridges.append((n.nid, best[1], best[2], best[0]))
    gap_mode = None
    if len(gaps) >= 6:
        hist = Counter(round(g * 4) / 4 for g in gaps)
        gap_mode, cnt = hist.most_common(1)[0]
        if cnt < 0.15 * len(gaps):
            gap_mode = None
    bridges = []
    if gap_mode is not None:
        gtol = max(0.6, tol.gap_slack * gap_mode)
        # unique continuation: the partner endpoint must itself be a degree-1 node and there must be no competing bridge
        by_target: dict[tuple[int, int], list] = defaultdict(list)
        for (nid, pid2, ep, g) in cand_bridges:
            if abs(g - gap_mode) > gtol:
                continue
            tn = find_node(ep[0], ep[1])
            if tn is None or tn == nid:
                continue
            # the partner endpoint may sit at a junction (a branch leaving exactly at a dash gap); uniqueness of the
            # collinear continuation is enforced below through node_use
            key = (min(nid, tn), max(nid, tn))
            by_target[key].append((nid, tn, pid2, g))
        node_use: Counter = Counter()
        for key, lst in by_target.items():
            node_use[key[0]] += 1; node_use[key[1]] += 1
        for key in sorted(by_target):
            a, b = key
            if node_use[a] > 1 or node_use[b] > 1:
                continue  # competing continuations -> no bridge (ambiguous)
            nid, tn, pid2, g = by_target[key][0]
            _merge_nodes(nodes, prim_nodes, nid, tn)
            bridges.append({"from_node": nid, "to_node": tn, "gap_pt": round(g, 2), "kind": "collinear",
                            "prims": sorted({pmap[n_p].pid for n_p in nodes[nid].prims})[:4]})
        # corner bridges: a dashed run that turns a corner inside a gap leaves two free ends that are not
        # collinear. Their outward rays meet at the corner, and the two legs together span exactly one gap of
        # this line style - the drawing's own evidence that the run continues around the bend.
        for nid, tn, g, kind in _corner_bridges(nodes, pmap, prim_nodes, idx, gap_mode, gtol, tol):
            _merge_nodes(nodes, prim_nodes, nid, tn)
            bridges.append({"from_node": nid, "to_node": tn, "gap_pt": round(g, 2), "kind": kind,
                            "prims": sorted({pmap[n_p].pid for n_p in nodes[nid].prims})[:4]})
    # remove emptied nodes
    nodes = {k: v for k, v in nodes.items() if v.prims}
    pn = {k: (v[0], v[1]) for k, v in prim_nodes.items()}
    return PipeGraph(family=family, prims=pmap, nodes=nodes, prim_nodes=pn, bridges=bridges, gap_mode=gap_mode, junctions=junctions)


def chains(graph: PipeGraph) -> list[list[int]]:
    """Maximal degree-2 chains of primitives (deterministic order)."""
    visited: set[int] = set()
    out: list[list[int]] = []
    for pid in sorted(graph.prims):
        if pid in visited:
            continue
        chain = [pid]
        visited.add(pid)
        for direction in (0, 1):
            cur = pid
            node = graph.prim_nodes[cur][direction]
            while True:
                nb = graph.neighbours(cur, node)
                if len(nb) != 1 or graph.nodes[node].degree != 2:
                    break
                nxt = nb[0]
                if nxt in visited:
                    break
                visited.add(nxt)
                if direction == 0:
                    chain.insert(0, nxt)
                else:
                    chain.append(nxt)
                a, b = graph.prim_nodes[nxt]
                node = b if a == node else a
                cur = nxt
        out.append(chain)
    return out


def describe_family(fk: str, prims: list[Prim], graph: PipeGraph) -> RepresentationFamily:
    layer, _, style = fk.partition("|s|")
    width = prims[0].width if prims else 0.0
    total = sum(q.seg.length for q in prims)
    lens = [q.seg.length for q in prims]
    dash_mode = None
    if lens:
        hist = Counter(round(l) for l in lens if l > 2)
        if hist:
            dash_mode = float(hist.most_common(1)[0][0])
    ch = chains(graph)
    clen = [sum(graph.prims[p].seg.length for p in c) for c in ch]
    longest = max(clen) if clen else 0.0
    if graph.gap_mode is not None and graph.bridges:
        kind = "fragmented-dashed"
        desc = f"dashed/fragmented line, dash~{dash_mode}pt gap~{graph.gap_mode}pt, width {width:.2f}"
    elif longest > 60:
        kind = "continuous"
        desc = f"continuous polyline, width {width:.2f}"
    else:
        kind = "sparse"
        desc = f"short/isolated strokes, width {width:.2f}"
    return RepresentationFamily(family=fk, layer=layer, style=style, width=width, n_prims=len(prims), total_length=total,
                                gap_mode=graph.gap_mode, dash_mode=dash_mode, n_chains=len(ch), longest_chain=longest, kind=kind, description=desc)
