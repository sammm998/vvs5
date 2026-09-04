"""Vector glyph assembly: raw stroke/outline paths -> connected components -> row clusters -> glyphs.

Never assumes one path == one character. Characters may be split into several open-stroke paths,
multi-contour outlines or curve fragments. Reading order is derived from geometry only.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from ..geometry.core import EXPORT_EPS, GridIndex, Seg, bbox_union, stable_id
from ..pdf.extract import RawPage, RawPath


@dataclass
class StrokeComponent:
    cid: str
    layer: str
    style: str
    paths: list[RawPath]
    segs: list[Seg]
    bbox: tuple[float, float, float, float]
    kind: str  # 's' or 'f'

    @property
    def w(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def h(self) -> float:
        return self.bbox[3] - self.bbox[1]

    @property
    def cx(self) -> float:
        return (self.bbox[0] + self.bbox[2]) / 2

    @property
    def cy(self) -> float:
        return (self.bbox[1] + self.bbox[3]) / 2


@dataclass
class GlyphCandidate:
    gid: str
    comps: list[StrokeComponent]
    bbox: tuple[float, float, float, float]
    segs: list[Seg]
    layer: str
    style: str
    kind: str
    n_diacritics: int = 0

    @property
    def path_ids(self) -> list[str]:
        return sorted({p.pid for c in self.comps for p in c.paths})


@dataclass
class RowCluster:
    rcid: str
    glyphs: list[GlyphCandidate]      # ordered along reading axis
    angle: float
    height: float
    layer: str
    style: str
    kind: str


class _UF:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, a: int) -> int:
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if ra < rb:
                self.p[rb] = ra
            else:
                self.p[ra] = rb


def _path_endpoints(p: RawPath) -> list[tuple[float, float]]:
    pts = []
    for s in p.segs:
        pts.append((s.x0, s.y0))
        pts.append((s.x1, s.y1))
    return pts


def build_components(page: RawPage, max_diag: float = 40.0, tol: float = 0.12) -> list[StrokeComponent]:
    """Connected components of small stroke paths that touch at endpoints (same layer + style).

    max_diag: paths larger than this cannot be glyph strokes (glyph height is far below this on any drawing).
    """
    cands: list[RawPath] = []
    for p in page.paths:
        diag = math.hypot(p.bbox[2] - p.bbox[0], p.bbox[3] - p.bbox[1])
        if diag <= max_diag and diag > 0.05:
            cands.append(p)
    # deterministic order by content id
    cands.sort(key=lambda p: p.pid)
    # Vectorized endpoint hashing on a tol lattice: paths sharing a lattice cell (or neighbouring cell) with the
    # same layer/style touch. Connected components are computed with scipy (deterministic).
    style_ids: dict[tuple, int] = {}
    owner: list[int] = []
    xs: list[float] = []
    ys: list[float] = []
    for i, p in enumerate(cands):
        k = (p.layer, p.kind, f"{p.width:.2f}")
        sid = style_ids.setdefault(k, len(style_ids))
        for (x, y) in _path_endpoints(p):
            owner.append(i); xs.append(x); ys.append(y)
        # style id encoded into the key via a large offset
        for _ in p.segs:
            pass
    owner_a = np.array(owner, dtype=np.int64)
    sid_a = np.array([style_ids[(cands[i].layer, cands[i].kind, f"{cands[i].width:.2f}")] for i in owner], dtype=np.int64)
    cx = np.floor(np.array(xs) / tol).astype(np.int64)
    cy = np.floor(np.array(ys) / tol).astype(np.int64)
    rows_l: list[np.ndarray] = []
    cols_l: list[np.ndarray] = []
    base_key = (sid_a * 4_000_000_007 + cx) * 4_000_000_007 + cy
    order = np.argsort(base_key, kind="stable")
    sorted_key = base_key[order]
    # representative endpoint index per cell
    uniq, first_idx = np.unique(sorted_key, return_index=True)
    rep_by_key = dict(zip(uniq.tolist(), order[first_idx].tolist()))
    # same-cell links
    rows_l.append(owner_a[order]); cols_l.append(owner_a[order[first_idx[np.searchsorted(uniq, sorted_key)]]])
    # neighbouring cell links
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nk = (sid_a * 4_000_000_007 + (cx + dx)) * 4_000_000_007 + (cy + dy)
            pos = np.searchsorted(uniq, nk)
            pos_c = np.minimum(pos, len(uniq) - 1)
            hit = uniq[pos_c] == nk
            if hit.any():
                rows_l.append(owner_a[hit]); cols_l.append(owner_a[order[first_idx[pos_c[hit]]]])
    r = np.concatenate(rows_l); c = np.concatenate(cols_l)
    n = len(cands)
    m = coo_matrix((np.ones(len(r), dtype=np.int8), (r, c)), shape=(n, n))
    _, labels = connected_components(m, directed=False)
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[int(labels[i])].append(i)
    comps: list[StrokeComponent] = []
    for root, members in groups.items():
        paths = [cands[i] for i in members]
        paths.sort(key=lambda p: p.pid)
        segs = [s for p in paths for s in p.segs]
        bbox = bbox_union([p.bbox for p in paths])
        p0 = paths[0]
        cid = stable_id("comp", page.info.index, *(p.pid for p in paths))
        # the style carries colour as well as width, so that "layer|style" is the same family key the pipe and
        # leader families are keyed by: a tick mark and the line it marks must land in the same family
        comps.append(StrokeComponent(cid=cid, layer=p0.layer, style=f"{p0.kind}|w{p0.width:.2f}|c{p0.color if p0.color else '-'}",
                                     paths=paths, segs=segs, bbox=bbox, kind=p0.kind))
    comps.sort(key=lambda c: c.cid)
    return comps


def size_families(comps: list[StrokeComponent], min_count: int = 3) -> list[float]:
    """Dominant glyph heights (pt): clusters (within 12 %) of the component-height histogram (per drawing)."""
    hs = [c.h for c in comps if 1.5 <= c.h <= 40 and c.w <= 3.0 * c.h and (len(c.segs) >= 3 or any(p.n_curves > 0 for p in c.paths)) and c.w >= 0.15 * c.h]
    if len(hs) < min_count:
        return []
    bins = Counter(round(h / 0.25) * 0.25 for h in hs)
    total = sum(bins.values())
    # cluster adjacent bins (within 12 % of the running cluster height)
    clusters: list[list[tuple[float, int]]] = []
    for k in sorted(bins):
        # a bin joins the current cluster only while it stays within 12 % of the cluster's first bin
        if clusters and k - clusters[-1][0][0] <= 0.12 * clusters[-1][0][0] + 1e-9:
            clusters[-1].append((k, bins[k]))
        else:
            clusters.append([(k, bins[k])])
    out = []
    for cl in clusters:
        cnt = sum(v for _, v in cl)
        if cnt < max(min_count, 0.02 * total):
            continue
        peak = max(cl, key=lambda kv: (kv[1], -kv[0]))[0]
        out.append((peak, cnt))
    out.sort(key=lambda kv: (-kv[1], kv[0]))
    return [k for k, v in out[:6]]


def _bbox_gap(a, b) -> tuple[float, float]:
    dx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return dx, dy


def _glyph_like(c: StrokeComponent, H: float) -> bool:
    """A component can seed a text row only if it has 2-D ink (not a lone straight dash / tick)."""
    if len(c.segs) >= 3 or any(p.n_curves > 0 for p in c.paths):
        return True
    return c.w >= 0.15 * H and c.h >= 0.15 * H


def cluster_rows(page: RawPage, comps: list[StrokeComponent], H: float) -> list[RowCluster]:
    """Cluster glyph-sized components of one size family into rows and segment rows into glyphs.

    Lone straight strokes (dashes, ticks, hatch pieces) never seed a row; they may only join a row that already
    contains glyph-like ink. This keeps dashed line patterns from masquerading as text."""
    cands = [c for c in comps if c.h <= 1.3 * H and max(c.w, c.h) <= 2.4 * H and (c.h >= 0.02 * H or c.w >= 0.02 * H)]
    cands.sort(key=lambda c: c.cid)
    if not cands:
        return []
    seed = [_glyph_like(c, H) for c in cands]
    if not any(seed):
        return []
    idx = GridIndex(cell=max(8.0, 2 * H))
    for i, c in enumerate(cands):
        idx.insert(i, c.bbox)
    uf = _UF(len(cands))
    for i, c in enumerate(cands):
        r = 0.9 * H
        b = (c.bbox[0] - r, c.bbox[1] - r, c.bbox[2] + r, c.bbox[3] + r)
        for j in idx.query(b):
            if j <= i:
                continue
            d = cands[j]
            if d.layer != c.layer or d.style != c.style:
                continue
            if not (seed[i] or seed[j]):
                continue
            gx, gy = _bbox_gap(c.bbox, d.bbox)
            gap = math.hypot(gx, gy)
            if gap > 0.8 * H:
                continue
            # heights must be compatible unless one is a small mark (-, ., etc.)
            big = max(c.h, d.h)
            if big > 1.3 * H:
                continue
            cd = math.hypot(c.cx - d.cx, c.cy - d.cy)
            if cd > 1.9 * H:
                continue
            uf.union(i, j)
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(cands)):
        groups[uf.find(i)].append(i)
    clusters: list[tuple[list[StrokeComponent], float, int]] = []
    for root, members in groups.items():
        n_seed = sum(1 for i in members if seed[i])
        if n_seed == 0 or (n_seed == 1 and len(members) > 3):
            continue
        # a lone straight stroke that joined the row (hyphen, colon, 'I', '|') can never be taller than the row's
        # own glyphs: a longer one is drawing geometry passing by (a frame edge, a scale-bar end, a leader)
        gmax = max(max(cands[i].w, cands[i].h) for i in members if seed[i])
        members = [i for i in members if seed[i] or max(cands[i].w, cands[i].h) <= 1.15 * gmax]
        cs = [cands[i] for i in members]
        ang, strength = _principal_angle(cs), _angle_support(cs)
        clusters.append((cs, ang, strength))
    # drawing-local text orientations: clusters with >= 4 tall components estimate their axis robustly; weaker
    # clusters (2-3 glyphs, PCA of few centers) adopt the nearest robust orientation within 20 degrees
    robust: Counter = Counter()
    n_clusters: Counter = Counter()
    for cs, ang, strength in clusters:
        if strength >= 4:
            robust[round(ang) % 180] += len(cs)
            n_clusters[round(ang) % 180] += 1
    total = sum(robust.values()) or 1
    order = sorted(robust.items(), key=lambda kv: (-kv[1], kv[0]))
    prefs = [a for a, w in order if w >= 0.02 * total and n_clusters[a] >= 2] or [a for a, _ in order]
    rows: list[RowCluster] = []
    for cs, ang, strength in clusters:
        # A drawing writes its text along a few directions, and its own long rows establish them. A cluster
        # whose axis is near none of those is not text at a new angle: it is two short rows standing above each
        # other read as one column - a legend's codes, a stack of dimensions - so it is read along the
        # direction the drawing writes in, which splits it back into the rows it was.
        ang = _snap_angle(ang, prefs if prefs else [0.0, 90.0], 20.0)
        if prefs and not _near_any(ang, prefs, 20.0):
            ang = prefs[0]
        rows.extend(_split_and_order(page, cs, H, ang))
    rows.sort(key=lambda r: r.rcid)
    return rows


def _angle_support(cs: list[StrokeComponent]) -> int:
    if not cs:
        return 0
    hmax = max(max(c.h, c.w) for c in cs)
    return sum(1 for c in cs if max(c.h, c.w) >= 0.6 * hmax)


def _near_any(ang: float, prefs, tol: float) -> bool:
    return any(abs((ang - p + 90.0) % 180.0 - 90.0) <= tol for p in prefs)


def _snap_angle(ang: float, prefs, tol: float) -> float:
    best = None
    for p in prefs:
        d = abs((ang - p + 90.0) % 180.0 - 90.0)
        if d <= tol and (best is None or d < best[0]):
            best = (d, float(p))
    return best[1] % 180.0 if best else ang


def _principal_angle(cs: list[StrokeComponent]) -> float:
    if len(cs) < 2:
        return 0.0
    hmax = max(max(c.h, c.w) for c in cs)
    tall = [c for c in cs if max(c.h, c.w) >= 0.6 * hmax]
    if len(tall) >= 2:
        cs = tall
    pts = np.array([[c.cx, c.cy] for c in cs], dtype=float)
    pts -= pts.mean(axis=0)
    cov = pts.T @ pts
    w, v = np.linalg.eigh(cov)
    d = v[:, int(np.argmax(w))]
    ang = math.degrees(math.atan2(d[1], d[0])) % 180.0
    # snap near-axis angles
    for snap in (0.0, 90.0, 180.0):
        if abs(ang - snap) <= 8.0:
            ang = snap % 180.0
    if len(cs) == 2 and w[int(np.argmax(w))] < 1e-6:
        return 0.0
    return ang


def _split_and_order(page: RawPage, cs: list[StrokeComponent], H: float, angle: float | None = None) -> list[RowCluster]:
    cs = sorted(cs, key=lambda c: c.cid)
    ang = _principal_angle(cs) if angle is None else angle
    a = math.radians(ang)
    d = (math.cos(a), math.sin(a))
    n = (-d[1], d[0])
    # attach tiny marks (diacritics) to the tall component right below them before splitting rows
    cs, pre_dia = _attach_tiny_marks(cs, d, n, H)
    # perpendicular clustering into rows
    items = sorted(cs, key=lambda c: (c.cx * n[0] + c.cy * n[1], c.cid))
    rows_c: list[list[StrokeComponent]] = []
    cur: list[StrokeComponent] = []
    last_pos = None
    for c in items:
        pos = c.cx * n[0] + c.cy * n[1]
        if last_pos is not None and pos - last_pos > 0.55 * H:
            rows_c.append(cur)
            cur = []
        cur.append(c)
        last_pos = pos
    if cur:
        rows_c.append(cur)
    out: list[RowCluster] = []
    for rc in rows_c:
        # for text reading direction: angle in [0,180) -> choose direction so that reading goes left->right (or top->bottom for vertical)
        read_ang = ang
        if 90.0 < read_ang < 180.0:
            read_ang -= 180.0  # e.g. 135 -> -45 (reading up-right)
        ra = math.radians(read_ang)
        rd = (math.cos(ra), math.sin(ra))
        if abs(read_ang - 90.0) < 1e-6:
            rd = (0.0, -1.0)  # vertical text reads bottom-to-top (CAD convention: rotated 90 ccw)
            read_ang = -90.0
        # segment into glyphs by interval overlap along rd
        ivs = []
        for c in rc:
            ps = [s.x0 * rd[0] + s.y0 * rd[1] for s in c.segs] + [s.x1 * rd[0] + s.y1 * rd[1] for s in c.segs]
            ivs.append((min(ps), max(ps), c))
        ivs.sort(key=lambda t: (t[0], t[1], t[2].cid))
        glyph_groups: list[list[tuple[float, float, StrokeComponent]]] = []
        for iv in ivs:
            if glyph_groups:
                g = glyph_groups[-1]
                gend = max(t[1] for t in g)
                gstart = min(t[0] for t in g)
                if iv[0] < gend - 0.06 * H or (iv[0] - gend < 0.1 * H and iv[0] >= gstart - 0.02 * H and (iv[1] - iv[0] < 0.25 * H or gend - gstart < 0.25 * H)):
                    g.append(iv)
                    continue
            glyph_groups.append([iv])
        glyph_groups, ndia = _merge_diacritics(glyph_groups, rd, H)
        glyphs: list[GlyphCandidate] = []
        for g, nd in zip(glyph_groups, ndia):
            comps = sorted((t[2] for t in g), key=lambda c: c.cid)
            nd += sum(pre_dia.get(c.cid, 0) for c in comps)
            segs = [s for c in comps for s in c.segs]
            bbox = bbox_union([c.bbox for c in comps])
            gid = stable_id("vg", page.info.index, *(c.cid for c in comps))
            glyphs.append(GlyphCandidate(gid=gid, comps=comps, bbox=bbox, segs=segs, layer=comps[0].layer, style=comps[0].style, kind=comps[0].kind, n_diacritics=nd))
        hs = sorted(g.bbox[3] - g.bbox[1] if abs(read_ang) < 45 else g.bbox[2] - g.bbox[0] for g in glyphs)
        height = hs[len(hs) // 2] if hs else H
        rcid = stable_id("rc", page.info.index, *(g.gid for g in glyphs))
        out.append(RowCluster(rcid=rcid, glyphs=glyphs, angle=read_ang, height=max(height, 0.5 * H), layer=glyphs[0].layer, style=glyphs[0].style, kind=glyphs[0].kind))
    return out


def _merge_diacritics(groups, rd, H: float):
    """Attach tiny marks (dots / rings) sitting directly above a glyph to that glyph (generic Latin diacritics)."""
    nrm = (-rd[1], rd[0])  # perpendicular; text 'up' is -nrm for y-down coordinates when rd=(1,0)
    def span_along(g, axis):
        vals = []
        for t in g:
            c = t[2]
            corners = [(c.bbox[0], c.bbox[1]), (c.bbox[2], c.bbox[1]), (c.bbox[0], c.bbox[3]), (c.bbox[2], c.bbox[3])]
            vals += [x * axis[0] + y * axis[1] for x, y in corners]
        return min(vals), max(vals)
    info = []
    for g in groups:
        a0, a1 = span_along(g, rd)
        n0, n1 = span_along(g, nrm)
        size = max(a1 - a0, n1 - n0)
        info.append([a0, a1, n0, n1, size, g])
    tall_idx = [i for i, it in enumerate(info) if it[4] >= 0.5 * H]
    out = []
    ndia: list[int] = []
    dia_count = defaultdict(int)
    consumed = set()
    for i, it in enumerate(info):
        if it[4] >= 0.35 * H or i in consumed:
            continue
        # tiny mark: find a tall glyph overlapping along rd and located just below it (mark above glyph => smaller nrm)
        for j in tall_idx:
            jt = info[j]
            ov = min(it[1], jt[1]) - max(it[0], jt[0])
            if ov <= -0.05 * H:
                continue
            gap = jt[2] - it[3]  # glyph top minus mark bottom (mark above)
            if -0.15 * H <= gap <= 0.45 * H:
                jt[5].extend(it[5])
                dia_count[j] += 1
                consumed.add(i)
                break
    for i, it in enumerate(info):
        if i not in consumed:
            out.append(it[5])
            ndia.append(dia_count[i])
    return out, ndia


def _attach_tiny_marks(cs: list[StrokeComponent], d, n, H: float):
    """Merge tiny components (size < 0.35H) into the tall component directly below them (along -n).
    Returns (components, {cid: number of attached marks}). Merged components keep the tall component's cid."""
    tall = [c for c in cs if max(c.w, c.h) >= 0.5 * H]
    tiny = [c for c in cs if max(c.w, c.h) < 0.35 * H]
    if not tall or not tiny:
        return cs, {}
    def span(c, axis):
        corners = [(c.bbox[0], c.bbox[1]), (c.bbox[2], c.bbox[1]), (c.bbox[0], c.bbox[3]), (c.bbox[2], c.bbox[3])]
        ps = [x * axis[0] + y * axis[1] for x, y in corners]
        return min(ps), max(ps)
    tinfo = [(span(c, d), span(c, n), c) for c in tall]
    merged: dict[str, list[StrokeComponent]] = {}
    consumed: set[str] = set()
    for t in tiny:
        ta = span(t, d); tn = span(t, n)
        best = None
        for (aa, nn, c) in tinfo:
            ov = min(ta[1], aa[1]) - max(ta[0], aa[0])
            if ov <= -0.05 * H:
                continue
            gap = nn[0] - tn[1]   # tall top minus tiny bottom (tiny above => positive small gap)
            if -0.15 * H <= gap <= 0.45 * H:
                key = (gap, c.cid)
                if best is None or key < best[0]:
                    best = (key, c)
        if best is not None:
            merged.setdefault(best[1].cid, []).append(t)
            consumed.add(t.cid)
    if not consumed:
        return cs, {}
    out = []
    counts: dict[str, int] = {}
    for c in cs:
        if c.cid in consumed:
            continue
        if c.cid in merged:
            extra = merged[c.cid]
            paths = sorted(c.paths + [p for e in extra for p in e.paths], key=lambda p: p.pid)
            segs = c.segs + [s for e in extra for s in e.segs]
            bbox = bbox_union([c.bbox] + [e.bbox for e in extra])
            out.append(StrokeComponent(cid=c.cid, layer=c.layer, style=c.style, paths=paths, segs=segs, bbox=bbox, kind=c.kind))
            counts[c.cid] = len(extra)
        else:
            out.append(c)
    return out, counts
