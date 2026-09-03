"""Leader endpoint -> physical pipe attachment and PipeCodeAnchors.

Attachment points are real geometry: the leader's far endpoint and the centers of crossing tick marks that sit on
the leader. Contacted primitives are grouped by vector family (layer|style). Designation rows of a block are mapped
to contacted groups either directly (single row, single group) or through drawing-local system-token / layer-token
compatibility, and the mapping must be a bijection; otherwise the attachment is AMBIGUOUS. Never nearest-distance.
"""
from __future__ import annotations

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


@dataclass
class Contact:
    point: tuple[float, float]
    kind: str            # 'end' | 'crossing_tick' | 'end_tick' | 'via_fitting'
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
                "system": self.system_token, "dn": self.dn, "multiplier": self.multiplier, "block_id": self.block_id,
                "leader_id": self.leader_id, "leader_source_paths": self.leader_paths,
                "leader_endpoint": [round(self.endpoint[0], 2), round(self.endpoint[1], 2)], "state": self.state, "reason": self.reason,
                "contacts": [c.as_dict() for c in self.contacts], "raw_pipe_source_paths": sorted({c.pid for c in self.contacts}),
                "raw_pipe_segments": [f"{p}#{k}" for p, k in self.pipe_prims], "candidate_families": self.candidate_families,
                "evidence": self.evidence}


# ---------------------------------------------------------------------------------------------------------------
# system token <-> layer token compatibility (drawing-derived; wildcard x/X in layer tokens matches digits)
# ---------------------------------------------------------------------------------------------------------------

def system_layer_match(system_token: str, layer: str) -> str | None:
    """Return the matching layer token if the layer name structurally carries the designation's system token."""
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
        for p in sorted(page.paths, key=lambda p: p.pid):
            if p.kind == "f" or family_of(p) in exclude_families or p.pid in exclude_pids:
                continue
            for k, s in enumerate(p.segs):
                self.items.append((p, k, s))
                self.idx.insert(len(self.items) - 1, s.bbox())

    def hits(self, x: float, y: float, tol: float = CONTACT_TOL, skip_pids: set[str] | None = None) -> list[tuple[RawPath, int, float]]:
        out = []
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


def leader_contacts(ld: Leader, gidx: GeometryIndex, pipe_families: set[str] | None, all_paths: dict[str, RawPath]) -> list[Contact]:
    """Contacts at each attachment point. When pipe_families is given, non-pipe hits that are small closed symbols
    are bridged to pipe primitives touching them (leader -> fitting -> pipe)."""
    out: list[Contact] = []
    skip = set(ld.path_ids)
    seen: set[tuple[str, int]] = set()
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
        for p, k, d in direct:
            if (p.pid, k) in seen:
                continue
            seen.add((p.pid, k))
            out.append(Contact(point=pt, kind=kind, family=family_of(p), pid=p.pid, seg_index=k, distance=d, mark_id=mid))
        if not direct and pipe_families and others:
            # marker bridge: a dot/tiny marker at the leader end sitting at a pipe END (micro gap <= 2.5 pt)
            for p, k, d in others:
                w = p.bbox[2] - p.bbox[0]; h = p.bbox[3] - p.bbox[1]
                if max(w, h) > 1.5:
                    continue
                mx, my = (p.bbox[0] + p.bbox[2]) / 2, (p.bbox[1] + p.bbox[3]) / 2
                ends = []
                for q, kk, dd in gidx.hits(mx, my, tol=2.5, skip_pids=skip | {p.pid}):
                    if family_of(q) not in pipe_families:
                        continue
                    sg = q.segs[kk]
                    de = min(dist((mx, my), (sg.x0, sg.y0)), dist((mx, my), (sg.x1, sg.y1)))
                    if de <= 2.5 and (q.pid, kk) not in seen:
                        ends.append((q, kk, de))
                for q, kk, de in ends:
                    seen.add((q.pid, kk))
                    out.append(Contact(point=pt, kind="via_marker", family=family_of(q), pid=q.pid, seg_index=kk, distance=de, mark_id=mid, via=p.pid))
            if any(c.kind == "via_marker" for c in out if c.point == pt):
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
                                out.append(Contact(point=pt, kind="via_fitting", family=family_of(q), pid=q.pid, seg_index=kk, distance=dd, mark_id=mid, via=p.pid))
    out.sort(key=lambda c: (c.pid, c.seg_index))
    return out


def resolve_block(block: AnnotationBlock, rows: list[Designation], ld: Leader, contacts: list[Contact],
                  system_tokens_in_drawing: set[str]) -> list[PipeCodeAnchor]:
    """Map designation rows of a block to contacted vector-family groups (bijection required)."""
    groups: dict[str, list[Contact]] = defaultdict(list)
    for c in contacts:
        groups[c.family].append(c)
    gkeys = sorted(groups)
    anchors: list[PipeCodeAnchor] = []

    def mk(d: Designation, state: str, reason: str, cs: list[Contact], extra: dict | None = None) -> PipeCodeAnchor:
        aid = stable_id("anc", d.page, d.did, ld.lid)
        return PipeCodeAnchor(anchor_id=aid, page=d.page, designation_id=d.did, designation=d.text, system_token=d.system_token,
                              dn=d.dn, multiplier=d.multiplier, block_id=block.bid, leader_id=ld.lid, leader_paths=ld.path_ids,
                              endpoint=ld.end, state=state, reason=reason, contacts=cs, candidate_families=gkeys,
                              evidence={"n_rows": len(rows), "n_groups": len(gkeys), "leader_family": ld.family, "row_index": d.row_index, **(extra or {})})

    if not gkeys:
        return [mk(d, "NO_PIPE_ATTACHMENT", "leader_endpoint_touches_no_pipe_geometry", []) for d in rows]
    # token matches
    match: dict[str, list[str]] = {}
    for d in rows:
        match[d.did] = [g for g in gkeys if system_layer_match(d.system_token, g.split("|s|")[0])]
    if len(rows) == 1:
        d = rows[0]
        if len(gkeys) == 1:
            g = gkeys[0]
            conflict = _system_conflict(d, g, system_tokens_in_drawing)
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


def _system_conflict(d: Designation, family: str, tokens: set[str]) -> str | None:
    """A conflict exists when the layer carries a system token matching ANOTHER designation family but not this one."""
    layer = family.split("|s|")[0]
    if system_layer_match(d.system_token, layer):
        return None
    for t in sorted(tokens):
        if t != d.system_token and system_layer_match(t, layer):
            m = re.match(r"([A-ZÅÄÖ]+)", t.upper()); m2 = re.match(r"([A-ZÅÄÖ]+)", d.system_token.upper())
            if m and m2 and m.group(1) != m2.group(1):
                return f"layer_matches_{t}_not_{d.system_token}"
    return None
