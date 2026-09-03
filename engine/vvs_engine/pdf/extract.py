"""Raw PDF forensics: one extraction pass per page.

Everything derived later stays traceable to RawPath.pid / TextSpan.tid (content hashes)
and to the PDF drawing sequence number (`seqno`) which is stored for provenance ONLY —
it never participates in any semantic decision.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import pymupdf

from ..geometry.core import Seg, bbox_union, flatten_bezier, stable_id


@dataclass
class RawPath:
    pid: str
    seqno: int
    page: int
    layer: str
    layer_id: int
    kind: str  # 's' stroke, 'f' fill, 'fs' fill+stroke
    width: float
    color: tuple | None
    fill: tuple | None
    closed: bool
    segs: list[Seg]
    bbox: tuple[float, float, float, float]
    n_items: int
    n_curves: int
    n_subpaths: int
    xobject: str | None = None

    @property
    def length(self) -> float:
        return sum(s.length for s in self.segs)

    def as_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid, "seqno": self.seqno, "page": self.page, "layer": self.layer,
            "kind": self.kind, "width": round(self.width, 3), "color": self.color, "fill": self.fill,
            "closed": self.closed, "n_segments": len(self.segs), "n_items": self.n_items,
            "n_curves": self.n_curves, "n_subpaths": self.n_subpaths,
            "bbox": [round(v, 2) for v in self.bbox], "length": round(self.length, 2),
        }


@dataclass
class TextChar:
    c: str
    bbox: tuple[float, float, float, float]
    origin: tuple[float, float]


@dataclass
class TextSpan:
    tid: str
    seqno: int
    page: int
    text: str
    bbox: tuple[float, float, float, float]
    dir: tuple[float, float]
    font: str
    size: float
    chars: list[TextChar]
    layer: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"tid": self.tid, "page": self.page, "text": self.text, "bbox": [round(v, 2) for v in self.bbox],
                "dir": [round(self.dir[0], 3), round(self.dir[1], 3)], "font": self.font, "size": round(self.size, 2),
                "n_chars": len(self.chars)}


@dataclass
class PageInfo:
    index: int
    width: float
    height: float
    rotation: int
    mediabox: list[float]
    cropbox: list[float]
    n_images: int
    n_annots: int
    n_xobjects: int
    xobjects: list[dict]
    fonts: list[dict]
    annots: list[dict]


@dataclass
class RawPage:
    info: PageInfo
    paths: list[RawPath]
    spans: list[TextSpan]
    input_class: dict | None = None            # how the page was classified before it was accepted


class UnsupportedInputError(Exception):
    """The PDF carries no page the engine can read: every page is a scan, an image or empty."""

    def __init__(self, message: str, classifications: list[dict]):
        super().__init__(message)
        self.classifications = classifications


@dataclass
class RawDocument:
    path: str
    n_pages: int
    metadata: dict
    ocgs: dict[int, dict]
    pages: list[RawPage] = field(default_factory=list)
    skipped_pages: list[dict] = field(default_factory=list)   # scanned / image-only pages, with the reason

    def inventory(self) -> dict[str, Any]:
        out = {"source": self.path, "n_pages": self.n_pages, "metadata": self.metadata,
               "ocgs": [{"xref": k, **v} for k, v in sorted(self.ocgs.items())], "pages": []}
        for pg in self.pages:
            kinds: dict[str, int] = {}
            layers: dict[str, int] = {}
            widths: dict[str, int] = {}
            n_segs = 0
            n_curves = 0
            for p in pg.paths:
                kinds[p.kind] = kinds.get(p.kind, 0) + 1
                layers[p.layer] = layers.get(p.layer, 0) + 1
                w = f"{p.width:.2f}"
                widths[w] = widths.get(w, 0) + 1
                n_segs += len(p.segs)
                n_curves += p.n_curves
            out["pages"].append({
                "page": pg.info.index, "width": pg.info.width, "height": pg.info.height, "rotation": pg.info.rotation,
                "mediabox": pg.info.mediabox, "cropbox": pg.info.cropbox,
                "n_paths": len(pg.paths), "n_segments": n_segs, "n_curve_items": n_curves,
                "n_text_spans": len(pg.spans), "n_text_chars": sum(len(s.chars) for s in pg.spans),
                "n_images": pg.info.n_images, "n_annotations": pg.info.n_annots, "n_xobjects": pg.info.n_xobjects,
                "xobjects": pg.info.xobjects, "fonts": pg.info.fonts, "annotations": pg.info.annots,
                "path_kinds": kinds, "layers": dict(sorted(layers.items())), "stroke_widths": dict(sorted(widths.items())),
            })
        return out


def _pt(p) -> tuple[float, float]:
    return (float(p.x), float(p.y))


def _items_to_segs(items, closed: bool) -> tuple[list[Seg], int, int]:
    """Convert PyMuPDF path items into straight segments (curves flattened). Returns (segs, n_curves, n_subpaths)."""
    segs: list[Seg] = []
    n_curves = 0
    n_sub = 0
    first: tuple[float, float] | None = None
    last: tuple[float, float] | None = None
    for it in items:
        op = it[0]
        if op == "l":
            a, b = _pt(it[1]), _pt(it[2])
            if last is None or (abs(last[0] - a[0]) > 1e-6 or abs(last[1] - a[1]) > 1e-6):
                # new subpath
                if closed and first is not None and last is not None and (abs(first[0]-last[0]) > 1e-6 or abs(first[1]-last[1]) > 1e-6):
                    segs.append(Seg(last[0], last[1], first[0], first[1]))
                first = a
                n_sub += 1
            segs.append(Seg(a[0], a[1], b[0], b[1]))
            last = b
        elif op == "c":
            p0, p1, p2, p3 = _pt(it[1]), _pt(it[2]), _pt(it[3]), _pt(it[4])
            if last is None or (abs(last[0] - p0[0]) > 1e-6 or abs(last[1] - p0[1]) > 1e-6):
                if closed and first is not None and last is not None and (abs(first[0]-last[0]) > 1e-6 or abs(first[1]-last[1]) > 1e-6):
                    segs.append(Seg(last[0], last[1], first[0], first[1]))
                first = p0
                n_sub += 1
            chord = math.hypot(p3[0] - p0[0], p3[1] - p0[1])
            n = 4 if chord < 3 else (8 if chord < 30 else 16)
            pts = flatten_bezier(p0, p1, p2, p3, n)
            for i in range(len(pts) - 1):
                segs.append(Seg(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]))
            n_curves += 1
            last = p3
        elif op == "re":
            r = it[1]
            x0, y0, x1, y1 = float(r.x0), float(r.y0), float(r.x1), float(r.y1)
            segs += [Seg(x0, y0, x1, y0), Seg(x1, y0, x1, y1), Seg(x1, y1, x0, y1), Seg(x0, y1, x0, y0)]
            first = last = None
            n_sub += 1
        elif op == "qu":
            q = it[1]
            pts = [_pt(q.ul), _pt(q.ur), _pt(q.lr), _pt(q.ll)]
            for i in range(4):
                a, b = pts[i], pts[(i + 1) % 4]
                segs.append(Seg(a[0], a[1], b[0], b[1]))
            first = last = None
            n_sub += 1
    if closed and first is not None and last is not None and (abs(first[0]-last[0]) > 1e-6 or abs(first[1]-last[1]) > 1e-6):
        segs.append(Seg(last[0], last[1], first[0], first[1]))
    return segs, n_curves, max(n_sub, 1)


def _color(c) -> tuple | None:
    if c is None:
        return None
    return tuple(round(float(v), 4) for v in c)


def extract_document(pdf_path: str, pages: list[int] | None = None, progress=None) -> RawDocument:
    """Read the vector content of every page: paths with their segments, layers, stroke widths and text spans.

    Only vector pages are analysed. A page whose content is a scan or an image is classified as such and skipped,
    because reading it would mean guessing at pixels instead of the drawing's own geometry; a PDF with no vector
    page at all raises UnsupportedInputError."""
    doc = pymupdf.open(pdf_path)
    try:
        ocgs_raw = doc.get_ocgs() or {}
    except Exception:
        ocgs_raw = {}
    ocgs = {int(k): {"name": v.get("name", ""), "on": bool(v.get("on", True))} for k, v in ocgs_raw.items()}
    layer_ids: dict[str, int] = {}
    rd = RawDocument(path=pdf_path, n_pages=len(doc), metadata={k: v for k, v in (doc.metadata or {}).items() if v}, ocgs=ocgs)
    for pno in range(len(doc)):
        if pages is not None and pno not in pages:
            continue
        page = doc[pno]
        from .classify import classify_page
        klass = classify_page(page)
        if klass.mode in ("raster", "empty"):
            rd.skipped_pages.append({"page": pno, **klass.as_dict()})
            continue
        rot = page.rotation
        # Work in the displayed (rotated) page space: PyMuPDF get_drawings/get_text return unrotated
        # coordinates; map them with rotation_matrix so all downstream geometry matches the rendered page.
        M = page.rotation_matrix if rot else None
        rect = page.rect
        drawings = page.get_drawings()
        paths: list[RawPath] = []
        for seq, d in enumerate(drawings):
            items = d.get("items") or []
            if M is not None:
                items = _transform_items(items, M)
            closed = bool(d.get("closePath"))
            segs, n_curves, n_sub = _items_to_segs(items, closed)
            if not segs:
                continue
            layer = d.get("layer") or ""
            if layer not in layer_ids:
                layer_ids[layer] = len(layer_ids)
            kind = d.get("type") or "s"
            width = float(d.get("width") or 0.0)
            bbox = bbox_union([s.bbox() for s in segs])
            key = (layer, kind, f"{width:.3f}", ",".join(f"{s.x0:.2f},{s.y0:.2f},{s.x1:.2f},{s.y1:.2f}" for s in segs[:64]), len(segs))
            pid = stable_id("path", pno, *key)
            paths.append(RawPath(pid=pid, seqno=seq, page=pno, layer=layer, layer_id=layer_ids[layer], kind=kind,
                                 width=width, color=_color(d.get("color")), fill=_color(d.get("fill")), closed=closed,
                                 segs=segs, bbox=bbox, n_items=len(items), n_curves=n_curves, n_subpaths=n_sub))
        # duplicate pid disambiguation (identical geometry drawn twice): keep both, suffix by occurrence rank in
        # a content-sorted order so that the result does not depend on enumeration order.
        _dedupe_ids(paths)
        spans = _extract_text(page, pno, M)
        xobjs = []
        try:
            for xo in page.get_xobjects():
                xobjs.append({"xref": xo[0], "name": xo[1], "invoker": xo[2], "bbox": [round(v, 2) for v in xo[3]]})
        except Exception:
            pass
        fonts = []
        try:
            for f in page.get_fonts():
                fonts.append({"xref": f[0], "ext": f[1], "type": f[2], "basefont": f[3], "name": f[4], "encoding": f[5]})
        except Exception:
            pass
        annots = []
        try:
            for a in page.annots():
                annots.append({"type": a.type[1], "rect": [round(v, 2) for v in a.rect], "content": (a.info.get("content") or "")[:80]})
        except Exception:
            pass
        info = PageInfo(index=pno, width=float(rect.width), height=float(rect.height), rotation=rot,
                        mediabox=[round(v, 2) for v in page.mediabox], cropbox=[round(v, 2) for v in page.cropbox],
                        n_images=len(page.get_images()), n_annots=len(annots), n_xobjects=len(xobjs), xobjects=xobjs,
                        fonts=fonts, annots=annots)
        rp = RawPage(info=info, paths=paths, spans=spans)
        rp.input_class = klass.as_dict()
        rd.pages.append(rp)
    doc.close()
    if not rd.pages:
        which = ", ".join(f"page {c['page'] + 1}: {'; '.join(c['reasons'])}" for c in rd.skipped_pages) or "no pages"
        raise UnsupportedInputError(
            "The PDF carries no vector drawing. This engine reads the drawing's own vector geometry and never "
            f"guesses at pixels, so a scanned or image-only PDF cannot be measured ({which}).", rd.skipped_pages)
    return rd


def _transform_items(items, M):
    out = []
    for it in items:
        op = it[0]
        if op == "l":
            out.append(("l", it[1] * M, it[2] * M))
        elif op == "c":
            out.append(("c", it[1] * M, it[2] * M, it[3] * M, it[4] * M))
        elif op == "re":
            q = it[1].quad * M
            out.append(("qu", q))
        elif op == "qu":
            out.append(("qu", it[1] * M))
    return out


def _dedupe_ids(paths: list[RawPath]) -> None:
    groups: dict[str, list[RawPath]] = {}
    for p in paths:
        groups.setdefault(p.pid, []).append(p)
    for pid, lst in groups.items():
        if len(lst) > 1:
            # rank by full geometry string (identical) then by nothing else -> identical objects are interchangeable;
            # give them distinct suffixes in a content-sorted order (all equal -> order irrelevant for semantics).
            lst_sorted = sorted(lst, key=lambda p: (len(p.segs), p.length))
            for i, p in enumerate(lst_sorted):
                p.pid = f"{pid}_{i}"


def _extract_text(page, pno: int, M) -> list[TextSpan]:
    spans: list[TextSpan] = []
    try:
        raw = page.get_text("rawdict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_PRESERVE_LIGATURES)
    except Exception:
        return spans
    seq = 0
    for b in raw.get("blocks", []):
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            d = line.get("dir", (1.0, 0.0))
            for sp in line.get("spans", []):
                chars = []
                for ch in sp.get("chars", []):
                    bb = ch["bbox"]
                    org = ch.get("origin", (bb[0], bb[3]))
                    if M is not None:
                        r = pymupdf.Rect(bb) * M
                        bb = (r.x0, r.y0, r.x1, r.y1)
                        o = pymupdf.Point(org) * M
                        org = (o.x, o.y)
                    chars.append(TextChar(c=ch["c"], bbox=tuple(float(v) for v in bb), origin=(float(org[0]), float(org[1]))))
                text = "".join(c.c for c in chars)
                if not text.strip():
                    continue
                bbox = bbox_union([c.bbox for c in chars])
                dd = (float(d[0]), float(d[1]))
                if M is not None:
                    p = pymupdf.Point(dd) * pymupdf.Matrix(M.a, M.b, M.c, M.d, 0, 0)
                    dd = (p.x, p.y)
                tid = stable_id("text", pno, text, f"{bbox[0]:.1f}", f"{bbox[1]:.1f}", sp.get("font", ""))
                spans.append(TextSpan(tid=tid, seqno=seq, page=pno, text=text, bbox=bbox, dir=dd,
                                      font=sp.get("font", ""), size=float(sp.get("size", 0.0)), chars=chars))
                seq += 1
    # dedupe tids
    seen: dict[str, int] = {}
    for s in spans:
        if s.tid in seen:
            seen[s.tid] += 1
            s.tid = f"{s.tid}_{seen[s.tid]}"
        else:
            seen[s.tid] = 0
    return spans
