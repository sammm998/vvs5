"""Leader endpoint -> physical pipe attachment and PipeCodeAnchors.

Attachment points are real geometry: the leader's far endpoint and the centers of crossing tick marks that sit on
the leader. Contacted primitives are grouped by vector family (layer|style). Designation rows of a block are mapped
to contacted groups either directly (single row, single group) or through drawing-local system-token / layer-token
compatibility, and the mapping must be a bijection; otherwise the attachment is AMBIGUOUS. Never nearest-distance.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..geometry.core import GridIndex, Seg, dist, point_seg_distance, stable_id
from ..pdf.extract import RawPage, RawPath
from ..profile.layers import layer_tokens
from .annotation import AnnotationBlock, Designation
from .leaders import Leader

CONTACT_TOL = 0.6
MARKER_MAX = 3.0          # pt: closed end markers (dots, small circles) of pipes
DASH_GAP_MAX = 8.0        # pt: the widest drawn gap in a dashed run a leader end may land in


@dataclass
class Contact:
    point: tuple[float, float]
    kind: str            # 'end' | 'crossing_tick' | 'end_tick' | 'via_symbol' | 'via_marker' | 'via_fitting'
    family: str
    pid: str
    seg_index: int
    distance: float
    mark_id: str | None = None
    via: str | None = None

    def as_dict(self):
        return {"point": [round(self.point[0], 2), round(self.point[1], 2)], "kind": self.kind, "family": self.family,
                "pid": self.pid, "seg_index": self.seg_index, "distance": round(self.distance, 3), "mark_id": self.mark_id, "via": self.via}


@dataclass
class PipeCodeAnchor:
    anchor_id: str
    page: int
    designation_id: str
    designation: str
    designation_display: str        # with a dimension row folded in, the name the drawing states
    system_token: str
    dn: int | None
    multiplier: int
    block_id: str
    leader_id: str
    leader_paths: list[str]
    endpoint: tuple[float, float]
    state: str                      # VERIFIED_PIPE_ATTACHMENT | AMBIGUOUS_PIPE_ATTACHMENT | NO_PIPE_ATTACHMENT
    reason: str
    contacts: list[Contact] = field(default_factory=list)
    candidate_families: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def pipe_prims(self) -> list[tuple[str, int]]:
        return sorted({(c.pid, c.seg_index) for c in self.contacts})

    def as_dict(self):
        return {"anchor_id": self.anchor_id, "page": self.page, "designation_id": self.designation_id, "designation": self.designation,
                "designation_display": self.designation_display,
                "system": self.system_token, "dn": self.dn, "multiplier": self.multiplier, "block_id": self.block_id,
                "leader_id": self.leader_id, "leader_source_paths": self.leader_paths,
                "leader_endpoint": [round(self.endpoint[0], 2), round(self.endpoint[1], 2)], "state": self.state, "reason": self.reason,
                "contacts": [c.as_dict() for c in self.contacts], "raw_pipe_source_paths": sorted({c.pid for c in self.contacts}),
                "raw_pipe_segments": [f"{p}#{k}" for p, k in self.pipe_prims], "candidate_families": self.candidate_families,
                "evidence": self.evidence}


# ---------------------------------------------------------------------------------------------------------------
# system token <-> layer token compatibility (drawing-derived; wildcard x/X in layer tokens matches digits)
# ---------------------------------------------------------------------------------------------------------------

def layer_system_tokens(page) -> frozenset[str]:
    """Every layer-name token of the page shaped like a system code (letters then digits).

    These are the system names the file writes about itself, and they decide when a shorter token is an
    abbreviation of a designation and when it is a different system altogether."""
    out: set[str] = set()
    for p in page.paths:
        for t in layer_tokens(p.layer or ""):
            TU = t.upper()
            if re.fullmatch(r"[A-ZÅÄÖ]+\d+", TU):
                out.add(TU)
    return frozenset(out)


def system_layer_match(system_token: str, layer: str, spelled_out: frozenset[str] = frozenset()) -> str | None:
    """Return the matching layer token if the layer name structurally carries the designation's system token.

    spelled_out: the system names the drawing writes in full on some layer of its own. A designation whose system
    is among them is not read as an abbreviation of a shorter token, because the file already says where that
    system lives: a system with a layer of its own is not the shorter system whose name it happens to end with."""
    S = system_token.upper()
    m = re.match(r"([A-ZÅÄÖ]+)(\d*)", S)
    alpha = m.group(1) if m else S
    digits = m.group(2) if m else ""
    toks = layer_tokens(layer)
    # a layer carrying a fully specified token of the same alpha family with OTHER digits is specific to that system
    for T in toks:
        TU = T.upper()
        m2 = re.fullmatch(r"([A-ZÅÄÖ]+)(\d+)", TU)
        if m2 and m2.group(1) == alpha and digits and m2.group(2) != digits:
            return None
    for T in toks:
        TU = T.upper()
        if len(TU) < 2:
            continue
        if TU == S:
            return T
        if "X" in TU and re.fullmatch(r"[A-ZÅÄÖ0-9]+", TU):
            pat = "".join(r"\d" if c == "X" and i >= 1 else re.escape(c) for i, c in enumerate(TU))
            if re.fullmatch(pat, S):
                return T
        if TU == alpha and len(alpha) >= 2:
            return T
        # abbreviated system token: the layer token is the tail of the designation's system token with the same
        # digits (KV2 -> V2, VV1 -> V1); a token of another alpha family with other digits was excluded above
        if len(TU) >= 2 and len(S) > len(TU) and S.endswith(TU) and re.fullmatch(r"[A-ZÅÄÖ]+\d+", TU):
            if S in spelled_out:
                continue        # the drawing gives this system a layer of its own: a shorter token is another system
            return T
    return None


def contact_points(ld: Leader) -> list[tuple[tuple[float, float], str, str | None]]:
    pts: list[tuple[tuple[float, float], str, str | None]] = []
    if ld.end_marks:
        for m in ld.end_marks:
            pts.append((ld.end, "end_tick", m.mid))
    else:
        pts.append((ld.end, "end", None))
    for m in ld.crossing_marks:
        pts.append((((m.bbox[0] + m.bbox[2]) / 2, (m.bbox[1] + m.bbox[3]) / 2), "crossing_tick", m.mid))
    return pts


class GeometryIndex:
    """Index over stroke segments of candidate (non-annotation) families."""

    def __init__(self, page: RawPage, exclude_families: set[str], exclude_pids: set[str]):
        self.idx = GridIndex(cell=12.0)
        self.items: list[tuple[RawPath, int, Seg]] = []
        self.tol = CONTACT_TOL
        # closed small symbols (riser marks, end circles, fittings) are indexed from ALL stroke paths: a circle
        # read as a text glyph ('O', '0') is still the symbol a leader may point at
        self.symbols: list[RawPath] = []
        self.symbol_idx = GridIndex(cell=12.0)
        for p in sorted(page.paths, key=lambda p: p.pid):
            if p.kind == "s" and _is_closed_symbol(p):
                self.symbols.append(p)
                self.symbol_idx.insert(len(self.symbols) - 1, p.bbox)
            if p.kind == "f" or family_of(p) in exclude_families or p.pid in exclude_pids:
                continue
            for k, s in enumerate(p.segs):
                self.items.append((p, k, s))
                self.idx.insert(len(self.items) - 1, s.bbox())

    def symbols_near(self, x: float, y: float, r: float) -> list[RawPath]:
        return [self.symbols[i] for i in sorted(set(self.symbol_idx.query_point(x, y, r)))]

    def paths_near(self, x: float, y: float, r: float) -> list[RawPath]:
        seen: dict[str, RawPath] = {}
        for i in self.idx.query_point(x, y, r):
            p = self.items[i][0]
            seen.setdefault(p.pid, p)
        return [seen[k] for k in sorted(seen)]

    def hits(self, x: float, y: float, tol: float | None = None, skip_pids: set[str] | None = None) -> list[tuple[RawPath, int, float]]:
        out = []
        tol = self.tol if tol is None else tol
        for i in self.idx.query_point(x, y, tol + 3):
            p, k, s = self.items[i]
            if skip_pids and p.pid in skip_pids:
                continue
            d, t = point_seg_distance(x, y, s)
            if d <= tol + min(0.5 * p.width, 0.5):
                out.append((p, k, d))
        out.sort(key=lambda h: (h[0].pid, h[1]))
        return out


def family_of(p: RawPath) -> str:
    return f"{p.layer}|s|w{p.width:.2f}"


def _dash_gap_hits(pt: tuple[float, float], gidx: GeometryIndex, pipe_families: set[str] | None,
                   skip: set[str]) -> list[tuple[RawPath, int, float]]:
    """Segments of a dashed run whose drawn gap the point falls into.

    A dashed pipe is ink and gaps; where the leader lands is where the draughtsman aimed, not where the dash
    pattern happens to be. Two ends of the same family, a short gap apart, collinear with each other and with the
    point between them, are one run interrupted by its own pattern - so the point touches that run.
    """
    ends: list[tuple[RawPath, int, Seg, tuple[float, float]]] = []
    for i in gidx.idx.query_point(pt[0], pt[1], DASH_GAP_MAX + 2):
        p, k, sg = gidx.items[i]
        if p.pid in skip or (pipe_families is not None and family_of(p) not in pipe_families):
            continue
        if sg.length < 1e-6:
            continue
        for e in ((sg.x0, sg.y0), (sg.x1, sg.y1)):
            if dist(e, pt) <= DASH_GAP_MAX:
                ends.append((p, k, sg, e))
    best: dict[str, tuple[float, tuple, tuple]] = {}
    for i in range(len(ends)):
        for j in range(i + 1, len(ends)):
            a, b = ends[i], ends[j]
            if family_of(a[0]) != family_of(b[0]) or (a[0].pid == b[0].pid and a[1] == b[1]):
                continue
            gap = dist(a[3], b[3])
            if gap < 1e-6 or gap > DASH_GAP_MAX:
                continue
            ux, uy = (b[3][0] - a[3][0]) / gap, (b[3][1] - a[3][1]) / gap
            t = (pt[0] - a[3][0]) * ux + (pt[1] - a[3][1]) * uy
            if t < -0.5 or t > gap + 0.5:
                continue                                    # the point is not inside the gap
            if abs(-(pt[1] - a[3][1]) * ux + (pt[0] - a[3][0]) * uy) > CONTACT_TOL + 0.5 * max(a[0].width, b[0].width):
                continue                                    # the point is beside the run, not on it
            if _angle_to(a[2], ux, uy) > 5.0 or _angle_to(b[2], ux, uy) > 5.0:
                continue                                    # the two dashes do not continue one straight line
            fk = family_of(a[0])
            if fk not in best or gap < best[fk][0]:
                best[fk] = (gap, a, b)
    out: list[tuple[RawPath, int, float]] = []
    for fk in sorted(best):
        gap, a, b = best[fk]
        out.append((a[0], a[1], dist(a[3], pt)))
        out.append((b[0], b[1], dist(b[3], pt)))
    return out


def _angle_to(sg: Seg, ux: float, uy: float) -> float:
    """Angle in degrees between a segment's line and a direction, folded into [0, 90]."""
    a = math.degrees(math.atan2(sg.y1 - sg.y0, sg.x1 - sg.x0) - math.atan2(uy, ux)) % 180.0
    return min(a, 180.0 - a)


def leader_contacts(ld: Leader, gidx: GeometryIndex, pipe_families: set[str] | None, all_paths: dict[str, RawPath]) -> list[Contact]:
    """Contacts at each attachment point.

    A leader whose end lies inside a small closed symbol (riser mark, end circle, fitting) points at that symbol:
    pipe geometry through the symbol or ending at the symbol group is a 'via_symbol' contact (a weak seed - the
    label describes the symbol's object; DN ticks on the line outrank it). Otherwise the end / tick points give
    direct contacts; tiny markers at the end bridge to pipe ends (via_marker); small symbols touched by the leader
    bridge to pipes touching them (via_fitting)."""
    out: list[Contact] = []
    skip = set(ld.path_ids)
    seen: set[tuple[str, int]] = set()
    symbol = _enclosing_symbol(ld.end, gidx, pipe_families, skip)
    for (pt, kind, mid) in contact_points(ld):
        hits = gidx.hits(pt[0], pt[1], skip_pids=skip)
        direct = []
        others = []
        for p, k, d in hits:
            fk = family_of(p)
            if pipe_families is None or fk in pipe_families:
                direct.append((p, k, d))
            else:
                others.append((p, k, d))
        if symbol is not None and pt == ld.end:
            for p, k, d in direct:
                if (p.pid, k) in seen:
                    continue
                seen.add((p.pid, k))
                out.append(Contact(point=pt, kind="via_symbol", family=family_of(p), pid=p.pid, seg_index=k, distance=d, mark_id=mid, via=symbol.pid))
            if pipe_families:
                for p in _marker_cluster([symbol], gidx, pipe_families, skip):
                    for q, kk, de, ep in _pipe_ends_at_marker(p, gidx, pipe_families, skip):
                        if (q.pid, kk) not in seen:
                            seen.add((q.pid, kk))
                            out.append(Contact(point=ep, kind="via_symbol", family=family_of(q), pid=q.pid, seg_index=kk, distance=de, mark_id=mid, via=p.pid))
            continue
        for p, k, d in direct:
            if (p.pid, k) in seen:
                continue
            seen.add((p.pid, k))
            out.append(Contact(point=pt, kind=kind, family=family_of(p), pid=p.pid, seg_index=k, distance=d, mark_id=mid))
        if not direct and pipe_families and others:
            # marker bridge: a dot/tiny marker at the leader end sitting at a pipe END (micro gap). Touching tiny
            # markers form one cluster (stacked end markers of parallel pipes): every pipe end at any marker of
            # the cluster is a contact.
            n_before = len(out)
            for p in _marker_cluster([p for p, _, _ in others if max(p.bbox[2] - p.bbox[0], p.bbox[3] - p.bbox[1]) <= MARKER_MAX], gidx, pipe_families, skip):
                for q, kk, de, ep in _pipe_ends_at_marker(p, gidx, pipe_families, skip):
                    if (q.pid, kk) not in seen:
                        seen.add((q.pid, kk))
                        out.append(Contact(point=ep, kind="via_marker", family=family_of(q), pid=q.pid, seg_index=kk, distance=de, mark_id=mid, via=p.pid))
            if len(out) > n_before:
                continue
            # fitting bridge: small symbol touched by the leader; pipe primitives touching the symbol
            for p, k, d in others:
                w = p.bbox[2] - p.bbox[0]; h = p.bbox[3] - p.bbox[1]
                if max(w, h) > 20:
                    continue
                for s in p.segs:
                    for ep in ((s.x0, s.y0), (s.x1, s.y1), s.mid):
                        for q, kk, dd in gidx.hits(ep[0], ep[1], tol=1.5, skip_pids=skip | {p.pid}):
                            if family_of(q) in pipe_families and (q.pid, kk) not in seen:
                                seen.add((q.pid, kk))
                                out.append(Contact(point=(ep[0], ep[1]), kind="via_fitting", family=family_of(q), pid=q.pid, seg_index=kk, distance=dd, mark_id=mid, via=p.pid))
    if not out and pipe_families:
        # last resort - the leader touched nothing at all: it may have landed in the drawn gap of a dashed run
        # (see _dash_gap_hits). Only a leader with nothing else to point at is read this way, so a run that was
        # already touched keeps its contacts exactly as drawn.
        for (pt, kind, mid) in contact_points(ld):
            for q, kk, dd in _dash_gap_hits(pt, gidx, pipe_families, skip):
                if (q.pid, kk) in seen:
                    continue
                seen.add((q.pid, kk))
                out.append(Contact(point=pt, kind=kind, family=family_of(q), pid=q.pid, seg_index=kk, distance=dd, mark_id=mid))
    out.sort(key=lambda c: (c.pid, c.seg_index))
    return out


WEAK_KINDS = ("via_symbol", "via_marker", "via_fitting")
SYMBOL_MAX = 20.0         # pt: closed symbols a leader may point at (riser marks, end circles, fittings)


def _is_closed_symbol(p: RawPath) -> bool:
    if p.kind != "s" or len(p.segs) < 3:
        return False
    size = max(p.bbox[2] - p.bbox[0], p.bbox[3] - p.bbox[1])
    if size < 1.0 or size > SYMBOL_MAX:
        return False
    a = (p.segs[0].x0, p.segs[0].y0); b = (p.segs[-1].x1, p.segs[-1].y1)
    return dist(a, b) <= 0.25


def _enclosing_symbol(pt: tuple[float, float], gidx: GeometryIndex, pipe_families: set[str] | None, skip: set[str]) -> RawPath | None:
    """Smallest closed non-pipe symbol whose box strictly contains the point (the leader points at the symbol)."""
    best = None
    for p in gidx.symbols_near(pt[0], pt[1], 1.0):
        if p.pid in skip or (pipe_families and family_of(p) in pipe_families):
            continue
        w = p.bbox[2] - p.bbox[0]; h = p.bbox[3] - p.bbox[1]
        m = 0.1 * max(w, h)
        if p.bbox[0] + m <= pt[0] <= p.bbox[2] - m and p.bbox[1] + m <= pt[1] <= p.bbox[3] - m:
            size = max(w, h)
            if best is None or size < best[0] or (size == best[0] and p.pid < best[1].pid):
                best = (size, p)
    return best[1] if best else None


def _pipe_ends_at_marker(p: RawPath, gidx: GeometryIndex, pipe_families: set[str], skip: set[str]) -> list[tuple[RawPath, int, float, tuple[float, float]]]:
    """Pipe primitives whose END lies at the marker's edge (within half its size + 1 pt of its centre), with the
    end point (the contact point on the pipe)."""
    mx, my = (p.bbox[0] + p.bbox[2]) / 2, (p.bbox[1] + p.bbox[3]) / 2
    size = max(p.bbox[2] - p.bbox[0], p.bbox[3] - p.bbox[1])
    R = max(2.5, 0.5 * size + 1.0)
    ends = []
    for q, kk, dd in gidx.hits(mx, my, tol=R, skip_pids=skip | {p.pid}):
        if family_of(q) not in pipe_families:
            continue
        sg = q.segs[kk]
        cands = [((sg.x0, sg.y0), dist((mx, my), (sg.x0, sg.y0))), ((sg.x1, sg.y1), dist((mx, my), (sg.x1, sg.y1)))]
        ep, de = min(cands, key=lambda t: t[1])
        if de <= R:
            ends.append((q, kk, de, ep))
    ends.sort(key=lambda t: (t[0].pid, t[1]))
    return ends


def _marker_cluster(seeds: list[RawPath], gidx: GeometryIndex, pipe_families: set[str], skip: set[str], limit: int = 16) -> list[RawPath]:
    cluster: dict[str, RawPath] = {}
    frontier: list[RawPath] = []
    for p in sorted(seeds, key=lambda p: p.pid):
        if p.pid not in cluster:
            cluster[p.pid] = p
            frontier.append(p)
    while frontier and len(cluster) < limit:
        p = frontier.pop(0)
        mx, my = (p.bbox[0] + p.bbox[2]) / 2, (p.bbox[1] + p.bbox[3]) / 2
        size = max(p.bbox[2] - p.bbox[0], p.bbox[3] - p.bbox[1])
        neighbours = [q for q, _, _ in gidx.hits(mx, my, tol=2.5 + size, skip_pids=skip)] + gidx.symbols_near(mx, my, 2.5 + size)
        for q in sorted(neighbours, key=lambda q: q.pid):
            if q.pid in cluster or q.pid in skip or family_of(q) in pipe_families or q.kind == "f":
                continue
            qsize = max(q.bbox[2] - q.bbox[0], q.bbox[3] - q.bbox[1])
            if qsize > MARKER_MAX:
                continue
            gx = max(0.0, max(p.bbox[0], q.bbox[0]) - min(p.bbox[2], q.bbox[2]))
            gy = max(0.0, max(p.bbox[1], q.bbox[1]) - min(p.bbox[3], q.bbox[3]))
            if max(gx, gy) <= max(0.5, 0.35 * max(size, qsize)):
                cluster[q.pid] = q
                frontier.append(q)
    return [cluster[k] for k in sorted(cluster)]


def resolve_block(block: AnnotationBlock, rows: list[Designation], ld: Leader, contacts: list[Contact],
                  system_tokens_in_drawing: set[str], spelled_out: frozenset[str] = frozenset()) -> list[PipeCodeAnchor]:
    """Map designation rows of a block to contacted vector-family groups (bijection required)."""
    groups: dict[str, list[Contact]] = defaultdict(list)
    for c in contacts:
        groups[c.family].append(c)
    gkeys = sorted(groups)
    anchors: list[PipeCodeAnchor] = []

    def mk(d: Designation, state: str, reason: str, cs: list[Contact], extra: dict | None = None) -> PipeCodeAnchor:
        aid = stable_id("anc", d.page, d.did, ld.lid)
        return PipeCodeAnchor(anchor_id=aid, page=d.page, designation_id=d.did, designation=d.text,
                              designation_display=d.display_text, system_token=d.system_token,
                              dn=d.dn, multiplier=d.multiplier, block_id=block.bid, leader_id=ld.lid, leader_paths=ld.path_ids,
                              endpoint=ld.end, state=state, reason=reason, contacts=cs, candidate_families=gkeys,
                              evidence={"n_rows": len(rows), "n_groups": len(gkeys), "leader_family": ld.family, "row_index": d.row_index, **(extra or {})})

    if not gkeys:
        return [mk(d, "NO_PIPE_ATTACHMENT", "leader_endpoint_touches_no_pipe_geometry", []) for d in rows]
    # token matches
    match: dict[str, list[str]] = {}
    for d in rows:
        match[d.did] = [g for g in gkeys if system_layer_match(d.system_token, g.split("|s|")[0], spelled_out)]
    if len(rows) == 1:
        d = rows[0]
        if len(gkeys) == 1:
            g = gkeys[0]
            conflict = _system_conflict(d, g, system_tokens_in_drawing, spelled_out)
            if conflict:
                return [mk(d, "AMBIGUOUS_PIPE_ATTACHMENT", f"system_conflict:{conflict}", groups[g])]
            return [mk(d, "VERIFIED_PIPE_ATTACHMENT", "single_row_single_group", groups[g], {"layer_token": match[d.did][0].split('|s|')[0] if match[d.did] else None})]
        if len(match[d.did]) == 1:
            g = match[d.did][0]
            return [mk(d, "VERIFIED_PIPE_ATTACHMENT", "single_row_layer_token_match", groups[g], {"layer_token_match": g})]
        return [mk(d, "AMBIGUOUS_PIPE_ATTACHMENT", "several_vector_families_at_leader_no_token_discrimination", [c for g in gkeys for c in groups[g]])]
    # multi-row block: bijection through token matches; fallback: unique bijection by parallel-line count
    # (a 'k x' multiplier must equal the number of distinct parallel primitives of a group)
    owner: dict[str, list[str]] = defaultdict(list)
    for d in rows:
        for g in match[d.did]:
            owner[g].append(d.did)
    if all(not match[d.did] for d in rows) and len(gkeys) == len(rows):
        counts = {g: len({(c.pid, c.seg_index) for c in groups[g]}) for g in gkeys}
        by_count: dict[int, list[str]] = defaultdict(list)
        for g, n in counts.items():
            by_count[n].append(g)
        row_counts = Counter(d.multiplier for d in rows)
        if all(len(by_count.get(m, [])) == k for m, k in row_counts.items()) and sum(row_counts.values()) == len(gkeys):
            out = []
            for d in rows:
                if row_counts[d.multiplier] == 1:
                    g = by_count[d.multiplier][0]
                    out.append(mk(d, "VERIFIED_PIPE_ATTACHMENT", "multi_row_parallel_count_bijection", groups[g], {"count_match": d.multiplier}))
                else:
                    out.append(mk(d, "AMBIGUOUS_PIPE_ATTACHMENT", "multi_row_equal_counts_no_discrimination", [c for g in by_count[d.multiplier] for c in groups[g]]))
            return out
    for d in rows:
        ms = match[d.did]
        if len(ms) == 1 and len(owner[ms[0]]) == 1:
            anchors.append(mk(d, "VERIFIED_PIPE_ATTACHMENT", "multi_row_layer_token_bijection", groups[ms[0]], {"layer_token_match": ms[0]}))
        elif len(ms) == 0:
            anchors.append(mk(d, "NO_PIPE_ATTACHMENT", "multi_row_no_compatible_layer_group", []))
        else:
            anchors.append(mk(d, "AMBIGUOUS_PIPE_ATTACHMENT", "multi_row_token_match_not_unique", [c for g in ms for c in groups[g]]))
    return anchors


def _system_conflict(d: Designation, family: str, tokens: set[str], spelled_out: frozenset[str] = frozenset()) -> str | None:
    """A conflict exists when the layer carries a system token matching ANOTHER designation family but not this one."""
    layer = family.split("|s|")[0]
    if system_layer_match(d.system_token, layer, spelled_out):
        return None
    for t in sorted(tokens):
        if t != d.system_token and system_layer_match(t, layer, spelled_out):
            m = re.match(r"([A-ZÅÄÖ]+)", t.upper()); m2 = re.match(r"([A-ZÅÄÖ]+)", d.system_token.upper())
            if m and m2 and m.group(1) != m2.group(1):
                return f"layer_matches_{t}_not_{d.system_token}"
    return None
