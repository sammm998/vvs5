"""Actual CAD leader discovery.

A leader is a chain of real PDF stroke segments that starts at an annotation block boundary (underline end,
box corner, block bbox corner) and leaves the block. Families (segment count, bends, start type, end marker,
crossing ticks) are discovered per drawing. No synthetic association rays are ever created.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..geometry.core import GridIndex, Seg, bbox_expand, dist, point_seg_distance, stable_id
from ..pdf.extract import RawPage
from ..pipes.representation import stroke_family
from ..text.vector_text import Mark
from .annotation import AnnotationBlock, FreeSeg

TOUCH_TOL = 0.15      # PDF export precision for shared endpoints
MAX_SEGMENTS = 8
START_PRIORITY = {"underline_end": 0, "box_corner": 0, "underline_touch": 1, "bbox_corner": 2, "bbox_edge": 3}


@dataclass
class Leader:
    lid: str
    page: int
    block_id: str
    segs: list[FreeSeg]                 # ordered from block to endpoint
    points: list[tuple[float, float]]    # polyline points from start to end
    start: tuple[float, float]
    end: tuple[float, float]
    start_type: str                     # underline_end | box_corner | bbox_corner | underline_touch
    layer: str
    width: float
    color: tuple | None = None
    end_marks: list[Mark] = field(default_factory=list)
    crossing_marks: list[Mark] = field(default_factory=list)
    family: str = ""
    truncated_reason: str | None = None   # branch | max_segments

    @property
    def length(self) -> float:
        return sum(s.seg.length for s in self.segs)

    @property
    def n_bends(self) -> int:
        b = 0
        for i in range(1, len(self.segs)):
            a1 = self.segs[i - 1].seg.angle; a2 = self.segs[i].seg.angle
            d = abs(a1 - a2) % 180
            if min(d, 180 - d) > 3:
                b += 1
        return b

    @property
    def path_ids(self) -> list[str]:
        return sorted({s.pid for s in self.segs})

    def as_dict(self) -> dict[str, Any]:
        return {"lid": self.lid, "page": self.page, "block_id": self.block_id, "family": self.family,
                "source_paths": self.path_ids, "segment_ids": [f"{s.pid}#{s.seg_index}" for s in self.segs],
                "points": [[round(x, 2), round(y, 2)] for x, y in self.points],
                "start": [round(self.start[0], 2), round(self.start[1], 2)], "end": [round(self.end[0], 2), round(self.end[1], 2)],
                "start_type": self.start_type, "layer": self.layer, "width": self.width, "n_segments": len(self.segs),
                "n_bends": self.n_bends, "length": round(self.length, 2),
                "end_marks": [m.mid for m in self.end_marks], "crossing_marks": [m.mid for m in self.crossing_marks],
                "truncated_reason": self.truncated_reason}


def _endpoints(f: FreeSeg):
    return ((f.seg.x0, f.seg.y0), (f.seg.x1, f.seg.y1))


def annotation_layers(blocks: list[AnnotationBlock]) -> dict[str, int]:
    """Drawing-derived annotation layer family: layers carrying underline/box frames of designation blocks
    plus the layers of vector-text designation glyphs."""
    c: Counter = Counter()
    for b in blocks:
        if not any(r.role == "designation" for r in b.rows):
            continue
        for r in b.rows:
            for u in r.underline:
                c[u.layer] += 1
            if r.role == "designation" and r.line.layer:
                c[r.line.layer] += 1
        for sgm in b.box_segs:
            c[sgm.layer] += 1
    return dict(c)


def discover_leaders(page: RawPage, blocks: list[AnnotationBlock], free: list[FreeSeg], marks: list[Mark],
                     ann_layers: dict[str, int] | None = None) -> list[Leader]:
    # ann_layers: annotation family keys (layer|s|width) discovered from verified attachments; None = unrestricted pass
    frame_ids: set[int] = set()
    for b in blocks:
        for r in b.rows:
            for u in r.underline:
                frame_ids.add(u.fid)
        for s in b.box_segs:
            frame_ids.add(s.fid)
    cands = [f for f in free if f.fid not in frame_ids
             and (not ann_layers or stroke_family(f.layer, f.width, f.color) in ann_layers)]
    fmap = {f.fid: f for f in cands}
    # endpoint index for chain growth
    ep_idx = GridIndex(cell=10.0)
    for f in cands:
        ep_idx.insert(f.fid, f.seg.bbox())
    mark_idx = GridIndex(cell=10.0)
    mmap = {m.mid: m for m in marks}
    mark_keys = sorted(mmap)
    for i, mid in enumerate(mark_keys):
        mark_idx.insert(i, mmap[mid].bbox)
    leaders: list[Leader] = []
    used_fids: set[int] = set()
    # 1. every block claims the free segments starting at its boundary; a segment claimed by several blocks goes to
    #    the strongest start evidence (frame end/corner > underline touch > bare bbox corner); equal claims of
    #    different blocks are ambiguous and produce no leader
    claims: dict[int, list[tuple[int, str, AnnotationBlock, FreeSeg, tuple[float, float], str]]] = defaultdict(list)
    for b in sorted(blocks, key=lambda b: b.bid):
        H = max(b.height, 1.0)
        tol_start = 0.35 * H
        has_frame = any(r.underline for r in b.rows) or bool(b.box_segs)
        bpts = [(pt, t) for (pt, t) in _boundary_points(b) if t != "bbox_corner" or not has_frame]
        starts: list[tuple[FreeSeg, tuple[float, float], str]] = []
        for (pt, ptype) in bpts:
            for fid in ep_idx.query_point(pt[0], pt[1], tol_start):
                f = fmap[fid]
                if f.fid in used_fids:
                    continue
                for ep in _endpoints(f):
                    if dist(ep, pt) <= tol_start:
                        # leader must leave the block: other endpoint outside the block bbox (expanded slightly)
                        other = _other(f, ep)
                        inside = b.bbox[0] - 0.3 * H <= other[0] <= b.bbox[2] + 0.3 * H and b.bbox[1] - 0.3 * H <= other[1] <= b.bbox[3] + 0.3 * H
                        if inside:
                            continue
                        starts.append((f, ep, ptype))
        # a leader may meet the label at the side of its box rather than at a corner or an underline end: the
        # draughtsman runs it to whichever edge faces the pipe. This is the weakest start there is, so it only
        # produces a leader where no stronger claim takes the segment.
        for fid in ep_idx.query(bbox_expand(b.bbox, tol_start)):
            f = fmap[fid]
            if f.fid in used_fids:
                continue
            for ep in _endpoints(f):
                if _box_outline_distance(ep, b.bbox) > tol_start:
                    continue
                other = _other(f, ep)
                if b.bbox[0] - 0.3 * H <= other[0] <= b.bbox[2] + 0.3 * H and \
                        b.bbox[1] - 0.3 * H <= other[1] <= b.bbox[3] + 0.3 * H:
                    continue
                starts.append((f, ep, "bbox_edge"))
        # also: leader touching an underline segment in its interior (T-start)
        for r in b.rows:
            for u in r.underline:
                for fid in ep_idx.query(bbox_expand(u.seg.bbox(), 0.2)):
                    f = fmap[fid]
                    if f.fid in used_fids:
                        continue
                    for ep in _endpoints(f):
                        dd, t = point_seg_distance(ep[0], ep[1], u.seg)
                        if dd <= TOUCH_TOL and 0.02 < t < 0.98:
                            other = _other(f, ep)
                            inside = b.bbox[0] - 0.3 * H <= other[0] <= b.bbox[2] + 0.3 * H and b.bbox[1] - 0.3 * H <= other[1] <= b.bbox[3] + 0.3 * H
                            if not inside:
                                starts.append((f, ep, "underline_touch"))
        # dedupe starts by fid within the block (strongest evidence first, then deterministic)
        seen: set[int] = set()
        for f, ep, ptype in sorted(starts, key=lambda t: (START_PRIORITY[t[2]], t[0].pid, t[0].seg_index, t[1])):
            if f.fid in seen:
                continue
            seen.add(f.fid)
            claims[f.fid].append((START_PRIORITY[ptype], b.bid, b, f, ep, ptype))
    chosen = []
    for fid in sorted(claims):
        lst = sorted(claims[fid], key=lambda t: (t[0], t[1]))
        best = lst[0][0]
        top = [t for t in lst if t[0] == best]
        if len({t[1] for t in top}) > 1:
            # equally strong claims of several blocks (shared frame line / corner): the leader leaves its own
            # block, so keep the blocks the segment points away from; then blocks that carry a designation
            out = [t for t in top if _leaves_block(t[2], t[3], t[4])]
            if len({t[1] for t in out}) > 1:
                out = [t for t in out if any(r.role == "designation" for r in t[2].rows)]
            if len({t[1] for t in out}) != 1:
                continue    # still ambiguous: no leader from this segment
            top = out
        chosen.append(top[0])
    # 2. grow chains, strongest starts first
    for prio, bid, b, f, ep, ptype in sorted(chosen, key=lambda t: (t[0], t[1], t[3].pid, t[3].seg_index)):
        if f.fid in used_fids:
            continue
        H = max(b.height, 1.0)
        chain, points, reason = _grow_chain(f, ep, fmap, ep_idx, used_fids)
        if not chain:
            continue
        L = sum(s.seg.length for s in chain)
        if L < 0.8 * H:
            continue
        for s in chain:
            used_fids.add(s.fid)
        end = points[-1]
        lid = stable_id("ldr", page.info.index, b.bid, *(f"{s.pid}#{s.seg_index}" for s in chain))
        ld = Leader(lid=lid, page=page.info.index, block_id=b.bid, segs=chain, points=points, start=points[0], end=end,
                    start_type=ptype, layer=chain[0].layer, width=chain[0].width, color=chain[0].color,
                    truncated_reason=reason)
        _attach_marks(ld, mark_idx, mark_keys, mmap)
        if not ld.end_marks:
            _attach_free_ticks(ld, ep_idx, fmap, H)
        leaders.append(ld)
    for ld in leaders:
        ld.family = leader_family(ld)
    leaders.sort(key=lambda l: l.lid)
    return leaders


def _box_outline_distance(pt, box) -> float:
    """Distance from a point to the outline of a box (zero on the edge, positive inside and outside)."""
    x, y = pt
    x0, y0, x1, y1 = box
    inside = x0 <= x <= x1 and y0 <= y <= y1
    dx = min(abs(x - x0), abs(x - x1))
    dy = min(abs(y - y0), abs(y - y1))
    if inside:
        return min(dx, dy)
    ox = 0.0 if x0 <= x <= x1 else dx
    oy = 0.0 if y0 <= y <= y1 else dy
    return math.hypot(ox, oy)


def _leaves_block(b: AnnotationBlock, f: FreeSeg, ep: tuple[float, float]) -> bool:
    """The segment's far end lies on the side of the start point facing away from the block's centre."""
    cx, cy = (b.bbox[0] + b.bbox[2]) / 2, (b.bbox[1] + b.bbox[3]) / 2
    other = _other(f, ep)
    return (ep[0] - cx) * (other[0] - ep[0]) + (ep[1] - cy) * (other[1] - ep[1]) > 0


def _boundary_points(b: AnnotationBlock) -> list[tuple[tuple[float, float], str]]:
    pts: list[tuple[tuple[float, float], str]] = []
    for r in b.rows:
        for u in r.underline:
            pts.append(((u.seg.x0, u.seg.y0), "underline_end")); pts.append(((u.seg.x1, u.seg.y1), "underline_end"))
    for s in b.box_segs:
        pts.append(((s.seg.x0, s.seg.y0), "box_corner")); pts.append(((s.seg.x1, s.seg.y1), "box_corner"))
    x0, y0, x1, y1 = b.bbox
    for p in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        pts.append((p, "bbox_corner"))
    return pts


def _other(f: FreeSeg, ep):
    a, c = _endpoints(f)
    return c if dist(a, ep) < dist(c, ep) else a


def _grow_chain(f: FreeSeg, start_ep, fmap, ep_idx: GridIndex, used: set[int]):
    chain = [f]
    points = [start_ep, _other(f, start_ep)]
    cur = points[-1]
    reason = None
    while len(chain) < MAX_SEGMENTS:
        nxt = []
        for fid in ep_idx.query_point(cur[0], cur[1], TOUCH_TOL):
            g = fmap[fid]
            if g.fid in used or any(g.fid == c.fid for c in chain):
                continue
            if g.layer != f.layer or abs(g.width - f.width) > 0.01:
                continue
            for ep in _endpoints(g):
                if dist(ep, cur) <= TOUCH_TOL:
                    nxt.append((g, ep))
                    break
        if not nxt:
            break
        if len(nxt) > 1:
            reason = "branch"
            break
        g, ep = nxt[0]
        chain.append(g)
        cur = _other(g, ep)
        points.append(cur)
    if len(chain) >= MAX_SEGMENTS:
        reason = "max_segments"
    return chain, points, reason


def _attach_marks(ld: Leader, mark_idx: GridIndex, mark_keys: list[str], mmap: dict[str, Mark]) -> None:
    end = ld.end
    for i in mark_idx.query_point(end[0], end[1], 2.5):
        m = mmap[mark_keys[i]]
        if _mark_near_point(m, end, 1.5):
            ld.end_marks.append(m)
    # crossing marks: marks whose center lies on the leader polyline (not at its end)
    x0 = min(p[0] for p in ld.points) - 2; y0 = min(p[1] for p in ld.points) - 2
    x1 = max(p[0] for p in ld.points) + 2; y1 = max(p[1] for p in ld.points) + 2
    for i in mark_idx.query((x0, y0, x1, y1)):
        m = mmap[mark_keys[i]]
        if any(m.mid == e.mid for e in ld.end_marks):
            continue
        cx, cy = (m.bbox[0] + m.bbox[2]) / 2, (m.bbox[1] + m.bbox[3]) / 2
        for s in ld.segs:
            d, t = point_seg_distance(cx, cy, s.seg)
            if d <= 0.6 and 0.0 <= t <= 1.0:
                ld.crossing_marks.append(m)
                break
    ld.end_marks.sort(key=lambda m: m.mid)
    ld.crossing_marks.sort(key=lambda m: m.mid)


def _attach_free_ticks(ld: Leader, ep_idx: GridIndex, fmap, H: float) -> None:
    """A tick at the leader end drawn as short strokes that share the end point (traced raster strokes meet at
    junctions exactly): two or more short free strokes leaving the end at an angle to the leader form the tick."""
    end = ld.end
    last = ld.segs[-1].seg.angle
    own = {s.fid for s in ld.segs}
    pieces = []
    for fid in ep_idx.query_point(end[0], end[1], 0.3):
        f = fmap[fid]
        if f.fid in own or f.seg.length > 0.9 * H or f.seg.length < 0.3:
            continue
        if min(dist((f.seg.x0, f.seg.y0), end), dist((f.seg.x1, f.seg.y1), end)) > TOUCH_TOL:
            continue
        d = abs(f.seg.angle - last) % 180
        if min(d, 180 - d) < 25:
            continue
        pieces.append(f)
    if len(pieces) < 2:
        return
    pieces.sort(key=lambda f: (f.pid, f.seg_index))
    bbox = (min(f.seg.bbox()[0] for f in pieces), min(f.seg.bbox()[1] for f in pieces), max(f.seg.bbox()[2] for f in pieces), max(f.seg.bbox()[3] for f in pieces))
    ld.end_marks.append(Mark(mid=stable_id("tick", ld.page, *(f"{f.pid}#{f.seg_index}" for f in pieces)), layer=pieces[0].layer,
                             style=f"w{pieces[0].width:.2f}", bbox=bbox, segs=[f.seg for f in pieces], path_ids=sorted({f.pid for f in pieces})))


def _mark_near_point(m: Mark, pt, tol: float) -> bool:
    for s in m.segs:
        d, _ = point_seg_distance(pt[0], pt[1], s)
        if d <= tol:
            return True
    return False


def leader_family(ld: Leader) -> str:
    n = len(ld.segs)
    shape = "straight" if n == 1 else ("bent" if ld.n_bends == 1 else ("multi-bend" if ld.n_bends > 1 else "split-path"))
    ang = ld.segs[-1].seg.angle
    orient = "horizontal" if min(ang, 180 - ang) < 5 else ("vertical" if abs(ang - 90) < 5 else "diagonal")
    marker = "end-tick" if ld.end_marks else "plain-end"
    cross = "crossing-ticks" if ld.crossing_marks else "no-crossing-ticks"
    return f"{shape}|{orient}|{ld.start_type}|{marker}|{cross}|w{ld.width:.2f}"


def leader_family_report(leaders: list[Leader]) -> dict[str, Any]:
    fams = Counter(l.family for l in leaders)
    return {"n_leaders": len(leaders), "families": [{"family": f, "occurrences": n} for f, n in sorted(fams.items(), key=lambda kv: (-kv[1], kv[0]))]}
