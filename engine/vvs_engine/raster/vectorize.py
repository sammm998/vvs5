"""Raster -> stroke polylines.

Binary ink -> skeleton (one pixel wide) -> pixel graph (endpoints, junctions) -> branches -> simplified polylines
in page points, each with its measured stroke width (distance transform). Junction pixels are shared exactly by the
branches meeting there, so T-contacts and crossings become graph nodes downstream exactly as in vector PDFs.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from ..geometry.core import Seg


@dataclass
class Polyline:
    points: list[tuple[float, float]]     # page points (pt)
    width_pt: float
    closed: bool
    n_px: int


def binarize(gray: np.ndarray) -> np.ndarray:
    """Otsu threshold on a grayscale image (ink = True)."""
    import cv2
    _, b = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    return b > 0


def remove_specks(ink: np.ndarray, min_px: int = 4) -> np.ndarray:
    import cv2
    n, labels, stats, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    keep = stats[:, cv2.CC_STAT_AREA] >= min_px
    keep[0] = False
    return keep[labels]


def skeleton_and_width(ink: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Skeleton (bool) and local stroke width (px) at every pixel (2 x distance to background)."""
    import cv2
    from skimage.morphology import skeletonize
    dt = cv2.distanceTransform(ink.astype(np.uint8) * 255, cv2.DIST_L2, 3)
    sk = skeletonize(ink)
    return sk, 2.0 * dt


_NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def trace_branches(sk: np.ndarray, width: np.ndarray | None = None) -> list[tuple[list[tuple[float, float]], bool]]:
    """Split the skeleton into branches between endpoints / junction clusters (8-connected).

    Adjacent junction pixels form one cluster whose centroid is the shared node of every branch meeting there
    (so T-contacts and crossings become exact shared endpoints downstream). Skeleton spurs (free-ended stubs shorter
    than the local stroke width, e.g. at dash ends and corners) are dropped. Returns pixel chains (row, col) with
    junction ends snapped to their cluster centroid, and whether the chain closes on itself."""
    import cv2
    s = sk.astype(np.uint8)
    k = np.ones((3, 3), dtype=np.uint8)
    k[1, 1] = 0
    nb = cv2.filter2D(s, -1, k, borderType=cv2.BORDER_CONSTANT) * s
    junction = ((nb >= 3) & (s > 0)).astype(np.uint8)
    # junction pixels closer than 2 px belong to one junction cluster (skeleton crossings spread over a few pixels)
    grown = cv2.dilate(junction, np.ones((3, 3), dtype=np.uint8)) & s
    n_cl, cl_labels, _, cl_centroids = cv2.connectedComponentsWithStats(grown, connectivity=8)
    keep_cl = np.zeros(n_cl, dtype=bool)
    keep_cl[np.unique(cl_labels[junction > 0])] = True     # only grown regions that contain a real junction pixel
    keep_cl[0] = False
    junction = (keep_cl[cl_labels]).astype(np.uint8)
    ys, xs = np.nonzero(s)
    pixels = set(zip(ys.tolist(), xs.tolist()))
    jset = {(int(a), int(b)) for a, b in zip(*np.nonzero(junction))}
    cluster_of = {p: int(cl_labels[p[0], p[1]]) for p in jset}
    centroid = {c: (float(cl_centroids[c][1]), float(cl_centroids[c][0])) for c in range(1, n_cl)}   # (row, col)
    visited_edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    visited_px: set[tuple[int, int]] = set()
    branches: list[tuple[list[tuple[float, float]], bool]] = []

    def neighbours(p):
        r, c = p
        return [(r + dr, c + dc) for dr, dc in _NB if (r + dr, c + dc) in pixels]

    def walk(start, first):
        chain = [start, first]
        prev, cur = start, first
        while cur not in jset:
            visited_px.add(cur)
            nxt = [q for q in neighbours(cur) if q != prev and q not in chain[-2:]]
            if not nxt:
                break
            nxt.sort(key=lambda q: (abs(q[0] - cur[0]) + abs(q[1] - cur[1]), q))
            q = nxt[0]
            if q == start:
                chain.append(q)
                break
            prev, cur = cur, q
            chain.append(cur)
            if len(chain) > 5_000_000:
                break
        return chain

    def snapped(chain):
        pts = [(float(r), float(c)) for r, c in chain]
        if chain[0] in jset:
            pts[0] = centroid[cluster_of[chain[0]]]
        if chain[-1] in jset:
            pts[-1] = centroid[cluster_of[chain[-1]]]
        return pts

    def local_width(p):
        return float(width[p[0], p[1]]) if width is not None else 3.0

    seeds = sorted(jset) + sorted(p for p in pixels if p not in jset and len(neighbours(p)) == 1)
    for p in seeds:
        for q in neighbours(p):
            if p in jset and q in jset and cluster_of[p] == cluster_of[q]:
                continue            # connector inside one junction cluster
            e = (min(p, q), max(p, q))
            if e in visited_edges:
                continue
            chain = walk(p, q)
            for i2 in range(len(chain) - 1):
                visited_edges.add((min(chain[i2], chain[i2 + 1]), max(chain[i2], chain[i2 + 1])))
            for px in chain:
                visited_px.add(px)
            a_j, b_j = chain[0] in jset, chain[-1] in jset
            if a_j and b_j and cluster_of[chain[0]] == cluster_of[chain[-1]] and len(chain) <= 6:
                continue            # tiny loop inside a junction cluster
            n_px = len(chain)
            if a_j != b_j:
                tip, junc = (chain[-1], chain[0]) if a_j else (chain[0], chain[-1])
                # skeleton spur at a stroke end / corner: not longer than its own stroke is wide (width at the free
                # tip), or shorter than half the stroke it leaves (dash-end spurs of thick strokes); a thin tick half
                # next to a thick pipe is longer than both and survives
                if n_px <= max(2.0, 1.0 * local_width(tip)) or n_px <= 0.5 * local_width(junc):
                    continue
            closed = chain[0] == chain[-1] and len(chain) > 3
            branches.append((snapped(chain), closed))
    # isolated loops (no endpoints, no junctions)
    for p in sorted(pixels):
        if p in visited_px or p in jset:
            continue
        nbs = neighbours(p)
        if not nbs:
            visited_px.add(p)
            continue
        chain = walk(p, nbs[0])
        for px in chain:
            visited_px.add(px)
        branches.append((snapped(chain), True))
    return branches


def simplify(points: list[tuple[float, float]], tol: float) -> list[tuple[float, float]]:
    """Douglas-Peucker."""
    if len(points) <= 2:
        return points
    stack = [(0, len(points) - 1)]
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    pts = np.asarray(points, dtype=float)
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        pa, pb = pts[a], pts[b]
        d = pb - pa
        L = math.hypot(d[0], d[1])
        seg = pts[a + 1:b]
        if L < 1e-9:
            dist = np.hypot(seg[:, 0] - pa[0], seg[:, 1] - pa[1])
        else:
            dist = np.abs((seg[:, 0] - pa[0]) * d[1] - (seg[:, 1] - pa[1]) * d[0]) / L
        i = int(np.argmax(dist))
        if dist[i] > tol:
            keep[a + 1 + i] = True
            stack.append((a, a + 1 + i)); stack.append((a + 1 + i, b))
    return [points[i] for i in range(len(points)) if keep[i]]


def vectorize(ink: np.ndarray, px_per_pt: float, min_len_px: int = 2, tol_px: float = 0.9) -> list[Polyline]:
    sk, width = skeleton_and_width(ink)
    out: list[Polyline] = []
    for chain, closed in trace_branches(sk, width):
        if len(chain) < min_len_px and not closed:
            continue
        pts = [(c, r) for r, c in chain]                          # (x, y) in px
        interior = chain[1:-1] or chain
        ws = [width[int(round(r)), int(round(c))] for r, c in interior]
        w = float(np.median(ws)) if len(ws) >= 8 else float(min(ws))     # short branches: junction pixels inflate widths
        simp = simplify(pts, tol_px)
        # skeleton tips of a stroke end bend sideways over about half the stroke width (thinning artefact): an end
        # segment shorter than that is a hook, never drawn geometry
        simp = _trim_hooks(simp, max(2.0, 0.75 * w))
        if len(simp) < 2:
            continue
        out.append(Polyline(points=[(x / px_per_pt, y / px_per_pt) for x, y in simp], width_pt=max(w, 1.0) / px_per_pt, closed=closed, n_px=len(chain)))
    return out


def _trim_hooks(pts: list[tuple[float, float]], hook_px: float) -> list[tuple[float, float]]:
    """Fold an end segment shorter than hook_px into the adjacent segment (skeleton tips and junction offsets
    leave short hooks at a wrong angle that would otherwise become tiny primitives). The tip is projected onto
    the line of the adjacent segment so the run stays straight and keeps its extent."""
    pts = list(pts)
    changed = True
    while changed and len(pts) >= 3:
        changed = False
        if math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]) < hook_px:
            pts[0] = _project(pts[0], pts[1], pts[2]); del pts[1]; changed = True
        if len(pts) >= 3 and math.hypot(pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1]) < hook_px:
            pts[-1] = _project(pts[-1], pts[-2], pts[-3]); del pts[-2]; changed = True
    return pts


def _project(tip, a, b):
    """Projection of tip onto the line through a and b (a nearer the tip)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    if L2 < 1e-9:
        return tip
    t = ((tip[0] - a[0]) * dx + (tip[1] - a[1]) * dy) / L2
    if t > 0:                      # tip lies "inside" the run: keep the run end
        return a
    return (a[0] + t * dx, a[1] + t * dy)


def width_classes(polys: list[Polyline], px_per_pt: float) -> list[float]:
    """Drawing-local stroke width classes (pt): modes of the pixel-weighted width histogram (0.5 px bins,
    smoothed); peaks closer than 1.5 px merge. Every polyline is then assigned its nearest class."""
    if not polys:
        return []
    ws = np.array([p.width_pt * px_per_pt for p in polys])
    wt = np.array([max(p.n_px, 1) for p in polys], dtype=float)
    bins = np.arange(0.5, max(ws.max(), 2.0) + 1.0, 0.5)
    hist, edges = np.histogram(ws, bins=bins, weights=wt)
    sm = np.convolve(hist, [0.25, 0.5, 0.25], mode="same")
    total = sm.sum() or 1.0
    peaks = []
    for i in range(len(sm)):
        left = sm[i - 1] if i > 0 else 0.0
        right = sm[i + 1] if i + 1 < len(sm) else 0.0
        if sm[i] >= left and sm[i] >= right and sm[i] >= 0.02 * total:
            centre = (edges[i] + edges[i + 1]) / 2
            if peaks and centre - peaks[-1][0] < 1.5:
                if sm[i] > peaks[-1][1]:
                    peaks[-1] = (centre, sm[i])
                continue
            peaks.append((centre, sm[i]))
    if not peaks:
        peaks = [(float(np.median(ws)), 1.0)]
    return [round(c / px_per_pt, 2) for c, _ in peaks]


def assign_class(w: float, classes: list[float]) -> float:
    return min(classes, key=lambda c: abs(c - w))
