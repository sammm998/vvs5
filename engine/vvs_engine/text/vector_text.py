"""Vector glyph text: components -> size families -> rows -> glyph families -> characters -> TextRows."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..geometry.core import stable_id
from ..pdf.extract import RawPage
from .model import Glyph, TextRow, make_row
from .recognize import (UNKNOWN_THRESHOLD, FamilyResult, classify, count_holes, decide, family_fingerprint,
                        rasterize_polygon_fill, rasterize_segments_oriented, skeleton_orientation)
from .postprocess import resolve_twins
from .strokes import GlyphCandidate, RowCluster, StrokeComponent, build_components, cluster_rows, size_families


@dataclass
class Mark:
    """An isolated straight stroke (1-2 segments) on a glyph-carrying layer: a tick/marker candidate, not text."""
    mid: str
    layer: str
    style: str
    bbox: tuple[float, float, float, float]
    segs: list
    path_ids: list[str]


@dataclass
class VectorTextResult:
    rows: list[TextRow]
    families: dict[str, FamilyResult]
    size_families: list[float]
    n_components: int
    n_glyphs: int
    marks: list[Mark] = field(default_factory=list)
    rejected_rows: list[TextRow] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


def _structural_char(g: GlyphCandidate, rc: RowCluster) -> str | None:
    """Generic typographic structure that pixel matching handles poorly at glyph scale:
    ':' = two tiny disconnected marks stacked across the reading axis; '(' / ')' = a single thin stroke whose
    bulge (sagitta) is significant, bulging left or right of its chord."""
    H = max(rc.height, 1e-6)
    a = math.radians(rc.angle)
    d = (math.cos(a), math.sin(a)); n = (-d[1], d[0])
    if len(g.comps) == 2 and all(max(c.w, c.h) < 0.2 * H for c in g.comps):
        c0, c1 = g.comps
        along = abs((c0.cx - c1.cx) * d[0] + (c0.cy - c1.cy) * d[1])
        across = abs((c0.cx - c1.cx) * n[0] + (c0.cy - c1.cy) * n[1])
        if across > 0.25 * H and along < 0.15 * H:
            return ":"
    if len(g.comps) == 1 and g.comps[0].kind == "s" and any(p.n_curves > 0 for p in g.comps[0].paths):
        segs = g.segs
        pts = [(s.x0, s.y0) for s in segs] + [(segs[-1].x1, segs[-1].y1)]
        # chord = farthest pair of endpoints of the stroke chain
        p0, p1 = pts[0], pts[-1]
        chord = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        width_along = max(x * d[0] + y * d[1] for x, y in pts) - min(x * d[0] + y * d[1] for x, y in pts)
        height_across = max(x * n[0] + y * n[1] for x, y in pts) - min(x * n[0] + y * n[1] for x, y in pts)
        if chord > 0.6 * H and height_across >= 0.6 * H and width_along <= 0.45 * H:
            # sagitta: max signed distance of points from the chord
            ux, uy = (p1[0] - p0[0]) / chord, (p1[1] - p0[1]) / chord
            sags = [(-(x - p0[0]) * uy + (y - p0[1]) * ux) for x, y in pts]
            smax, smin = max(sags), min(sags)
            sag = smax if abs(smax) > abs(smin) else smin
            if abs(sag) >= 0.12 * chord and (abs(smax) < 0.03 * chord or abs(smin) < 0.03 * chord):
                # bulge direction relative to reading axis: bulge toward -d (left) => '(' ; toward +d => ')'
                bulge_dir = (-uy * sag, ux * sag)     # normal * sag
                side = bulge_dir[0] * d[0] + bulge_dir[1] * d[1]
                # for chord oriented along -n (top-to-bottom in row frame) sign flips; normalise by chord direction
                orient = (ux * n[0] + uy * n[1])
                if orient < 0:
                    side = -side
                return "(" if side < 0 else ")"
    return None


BRACKETS = "()[]{}"
_PARTNER = {"(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{"}


def _drop_unpaired_brackets(rows) -> None:
    """A bracket comes in pairs. A single curved stroke that reads as one, with no partner anywhere in its row,
    is not a bracket - in these drawings it is a digit of the stroke font ('5' and ')' share an arc). Such a glyph
    is re-read as its best non-bracket candidate, and left unknown when none is close enough."""
    for row in rows:
        chars = [g.char for g in row.glyphs]
        for i, g in enumerate(row.glyphs):
            if g.char not in BRACKETS:
                continue
            partner = _PARTNER[g.char]
            if partner in chars[i + 1:] or partner in chars[:i]:
                continue                        # a real pair: leave it
            alt = next(((c, sc) for c, sc in g.alternatives if c not in BRACKETS), None)
            if alt is not None and alt[1] <= UNKNOWN_THRESHOLD:
                g.char, g.score = alt[0], alt[1]
            else:
                g.char, g.score = "?", 99.0
        row.text = "".join(g.char for g in row.glyphs)
        row.unknown_chars = sum(1 for g in row.glyphs if g.char == "?")


_LAYER_SEP = re.compile(r"[^A-Za-z0-9]+")
_WORD = re.compile(r"[A-Za-z0-9?]+")


def layer_vocabulary(page: RawPage) -> set[str]:
    """The code-like words the file writes about itself.

    A CAD file names its layers, and a layer name is machine-written text, not drawn geometry: it carries the very
    system codes the drawn labels repeat. Only tokens that mix letters and digits are kept, because those are the
    system codes; plain words would match too easily."""
    words: set[str] = set()
    for p in page.paths:
        for t in _LAYER_SEP.split(p.layer or ""):
            if len(t) >= 3 and any(c.isalpha() for c in t) and any(c.isdigit() for c in t):
                words.add(t.upper())
    return words


def _name_unknown_from_layers(page: RawPage, rows: list[TextRow]) -> list[dict[str, Any]]:
    """Name glyph shapes the reference alphabet cannot, from the file's own layer names.

    A drawing may write its labels in a typeface no reference alphabet holds - and embed only the handful of
    glyphs its remaining real text used - so a character can be drawn plainly and still match nothing. Where a
    word is unknown in exactly one place and exactly one layer name of the file spells it out, that name says
    what the shape is. The reading is adopted for the whole glyph family, since one shape is one character
    throughout a drawing, and every character taken this way is recorded with the name it came from.
    """
    vocab = layer_vocabulary(page)
    if not vocab:
        return []
    votes: dict[str, Counter] = defaultdict(Counter)
    evidence: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        text = row.text
        for m in _WORD.finditer(text):
            word = m.group(0).upper()
            if word.count("?") != 1 or len(word) - 1 < 3:
                continue
            k = word.index("?")
            found = {t[k] for t in vocab
                     if len(t) == len(word) and all(t[j] == word[j] for j in range(len(word)) if j != k)}
            if len(found) != 1:
                continue                        # ambiguous, or the file never spells this word: say nothing
            g = row.glyphs[m.start() + k]
            if g.char != "?":
                continue
            ch = found.pop()
            votes[g.family_id][ch] = votes[g.family_id][ch] + 1
            evidence[g.family_id].add(word.replace("?", ch))
    adopted: list[dict[str, Any]] = []
    named: dict[str, str] = {}
    for fid, counter in votes.items():
        if len(counter) != 1:
            continue                            # the same shape read two ways: no reading
        named[fid] = next(iter(counter))
    if not named:
        return []
    for row in rows:
        changed = False
        for g in row.glyphs:
            ch = named.get(g.family_id)
            if ch is None or g.char != "?":
                continue
            g.char, g.score, g.source = ch, 0.0, f"{g.source}+layer"
            changed = True
        if changed:
            row.text = "".join(g.char for g in row.glyphs)
            row.unknown_chars = sum(1 for g in row.glyphs if g.char == "?")
    for fid, ch in sorted(named.items()):
        adopted.append({"family_id": fid, "char": ch, "from_layer_names": sorted(evidence[fid])})
    return adopted


def _is_junk_row(row: TextRow) -> bool:
    """Rows that are not text: mostly unknown shapes, or periodic dash/dot line patterns."""
    chars = [g.char for g in row.glyphs if g.char != " "]
    if not chars:
        return True
    n = len(chars)
    unknown = sum(1 for c in chars if c == "?")
    dashes = sum(1 for c in chars if c in "-.|")
    alnum = sum(1 for c in chars if c.isalnum())
    if unknown > 0.5 * n:
        return True
    if alnum == 0:
        return True          # punctuation-only "rows" (pipe dashes, dots, ticks) are geometry, not text
    if n >= 4 and dashes >= 0.5 * n:
        return True
    if n >= 6 and alnum < 0.4 * n:
        return True
    return False


def _is_mark(rc: RowCluster) -> bool:
    if len(rc.glyphs) != 1:
        return False
    g = rc.glyphs[0]
    if len(g.comps) != 1:
        return False
    c = g.comps[0]
    return len(c.segs) <= 2 and all(p.n_curves == 0 for p in c.paths)


def _glyph_image(g: GlyphCandidate, angle: float):
    if g.kind == "s":
        return rasterize_segments_oriented(g.segs, angle)
    img, ar = rasterize_polygon_fill(g.segs, angle)
    return img, ar, skeleton_orientation(img)


def _size_class(g: GlyphCandidate, rc: RowCluster) -> str:
    gh = g.bbox[3] - g.bbox[1] if abs(rc.angle) < 45 else g.bbox[2] - g.bbox[0]
    gs = max(g.bbox[3] - g.bbox[1], g.bbox[2] - g.bbox[0])
    rel_h = gh / rc.height if rc.height else 1.0
    rel_s = gs / rc.height if rc.height else 1.0
    if rel_s < 0.18 and rel_h < 0.18:
        return "dot"
    if rel_h < 0.35:
        return "small"
    if rel_h < 0.55:
        return "mid"
    if rel_h < 0.85:
        return "x"
    return "cap"


def vector_text_rows(page: RawPage, timing: dict | None = None) -> VectorTextResult:
    import time
    t0 = time.perf_counter()
    comps = build_components(page)
    t1 = time.perf_counter()
    sizes = size_families(comps)
    clusters: list[RowCluster] = []
    marks: list[Mark] = []
    used_comp: set[str] = set()
    # process size families from largest count first; a component belongs to one family only
    for H in sizes:
        avail = [c for c in comps if c.cid not in used_comp]
        rows = cluster_rows(page, avail, H)
        for r in rows:
            if _is_mark(r):
                c = r.glyphs[0].comps[0]
                marks.append(Mark(mid=stable_id("mark", page.info.index, c.cid), layer=c.layer, style=c.style, bbox=c.bbox,
                                  segs=c.segs, path_ids=[p.pid for p in c.paths]))
                used_comp.add(c.cid)
                continue
            # keep only rows that look like text: >=2 glyphs or a single glyph with plausible size
            if len(r.glyphs) >= 2 or (len(r.glyphs) == 1 and max(r.glyphs[0].bbox[3] - r.glyphs[0].bbox[1], r.glyphs[0].bbox[2] - r.glyphs[0].bbox[0]) >= 0.5 * H):
                clusters.append(r)
                for g in r.glyphs:
                    for c in g.comps:
                        used_comp.add(c.cid)
    for c in comps:
        if c.cid in used_comp:
            continue
        if len(c.segs) <= 2 and all(p.n_curves == 0 for p in c.paths) and max(c.w, c.h) <= 12.0:
            marks.append(Mark(mid=stable_id("mark", page.info.index, c.cid), layer=c.layer, style=c.style, bbox=c.bbox,
                              segs=c.segs, path_ids=[p.pid for p in c.paths]))
            used_comp.add(c.cid)
    marks.sort(key=lambda m: m.mid)
    t2 = time.perf_counter()
    # glyph families
    fam_members: dict[str, list[tuple[GlyphCandidate, RowCluster, np.ndarray, float, np.ndarray]]] = defaultdict(list)
    glyph_family: dict[str, str] = {}
    for rc in clusters:
        for g in rc.glyphs:
            img, ar, omap = _glyph_image(g, rc.angle)
            fid = family_fingerprint(img, ar, _size_class(g, rc), g.n_diacritics > 0)
            fam_members[fid].append((g, rc, img, ar, omap))
            glyph_family[g.gid] = fid
    t3 = time.perf_counter()
    n_relaxed = 0
    families: dict[str, FamilyResult] = {}
    for fid in sorted(fam_members):
        members = fam_members[fid]
        # representative = member with median stroke count, deterministic by gid
        members_sorted = sorted(members, key=lambda m: (len(m[0].segs), m[0].gid))
        g, rc, img, ar, omap = members_sorted[len(members_sorted) // 2]
        holes = count_holes(img)
        # lowercase allowed only when the glyph is clearly shorter than its row (x-height)
        gh = g.bbox[3] - g.bbox[1] if abs(rc.angle) < 45 else g.bbox[2] - g.bbox[0]
        rel = gh / rc.height if rc.height > 0 else 1.0
        gsize = max(g.bbox[3] - g.bbox[1], g.bbox[2] - g.bbox[0])
        rel_size = gsize / rc.height if rc.height > 0 else 1.0
        allow_lower = rel < 0.85
        ch, score, alts = classify(img, ar, holes, allow_lower=allow_lower, rel_height=rel,
                                   has_diacritic=g.n_diacritics > 0, rel_size=rel_size, omap=omap,
                                   embedded=getattr(page, "embedded_fonts", ()))
        structural = _structural_char(g, rc)
        if structural is not None:
            ch, score, alts = structural, 0.0, [(structural, 0.0)] + alts[:3]
        ch, relaxed = decide(ch, score, alts)
        if relaxed:
            n_relaxed += 1
        families[fid] = FamilyResult(family_id=fid, char=ch, score=score, alternatives=alts, holes=holes, aspect=ar, n_members=len(members))
    t4 = time.perf_counter()
    rows: list[TextRow] = []
    rejected: list[TextRow] = []
    for rc in clusters:
        glyphs: list[Glyph] = []
        for g in rc.glyphs:
            fr = families[glyph_family[g.gid]]
            glyphs.append(Glyph(gid=g.gid, char=fr.char, bbox=g.bbox, source="stroke" if g.kind == "s" else "outline",
                                layer=g.layer, family_id=fr.family_id, score=fr.score, alternatives=fr.alternatives,
                                path_ids=g.path_ids))
        # inject spaces for large gaps along reading axis
        glyphs = _inject_spaces(glyphs, rc)
        resolve_twins(glyphs)
        row = make_row(page.info.index, glyphs, rc.angle, "stroke" if rc.kind == "s" else "outline", layer=rc.layer,
                       font=f"vector:{rc.style}", family=f"vector:{rc.layer}:{rc.style}:{rc.height:.1f}")
        if _is_junk_row(row):
            rejected.append(row)
            # its components are geometry after all: small straight ones are marker candidates (ticks, dots)
            for g in rc.glyphs:
                for c in g.comps:
                    if len(c.segs) <= 2 and all(p.n_curves == 0 for p in c.paths) and max(c.w, c.h) <= 12.0:
                        marks.append(Mark(mid=stable_id("mark", page.info.index, c.cid), layer=c.layer, style=c.style, bbox=c.bbox,
                                          segs=c.segs, path_ids=[p.pid for p in c.paths]))
            continue
        rows.append(row)
    rows.sort(key=lambda r: r.rid)
    marks.sort(key=lambda m: m.mid)
    t5 = time.perf_counter()
    if timing is not None:
        timing.update({"components_ms": (t1 - t0) * 1000, "rows_ms": (t2 - t1) * 1000, "raster_ms": (t3 - t2) * 1000,
                       "classify_ms": (t4 - t3) * 1000, "assemble_ms": (t5 - t4) * 1000})
    _drop_unpaired_brackets(rows)
    named = _name_unknown_from_layers(page, rows)
    return VectorTextResult(rows=rows, families=families, size_families=sizes, n_components=len(comps),
                            n_glyphs=sum(len(rc.glyphs) for rc in clusters), marks=marks, rejected_rows=rejected,
                            stats={"n_clusters": len(clusters), "n_families": len(families),
                                   "unknown_families": sum(1 for f in families.values() if f.char == "?"),
                                   "named_from_layer_names": named})


def _inject_spaces(glyphs: list[Glyph], rc: RowCluster) -> list[Glyph]:
    a = math.radians(rc.angle)
    d = (math.cos(a), math.sin(a))
    out: list[Glyph] = []
    prev_end = None
    H = rc.height
    for g in glyphs:
        corners = [(g.bbox[0], g.bbox[1]), (g.bbox[2], g.bbox[1]), (g.bbox[0], g.bbox[3]), (g.bbox[2], g.bbox[3])]
        ps = [x * d[0] + y * d[1] for x, y in corners]
        start, end = min(ps), max(ps)
        if prev_end is not None and start - prev_end > 0.55 * H:
            out.append(Glyph(gid=g.gid + "_sp", char=" ", bbox=(g.bbox[0], g.bbox[1], g.bbox[0], g.bbox[3]), source=g.source, layer=g.layer))
        out.append(g)
        prev_end = end
    return out
