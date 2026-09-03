"""Overlay PDFs drawn on top of the original drawing (actual geometry only; no synthetic rays)."""
from __future__ import annotations

import os

import pymupdf

COLORS = {
    "confirmed": (0.0, 0.55, 0.0), "ambiguous": (1.0, 0.55, 0.0), "unowned": (0.6, 0.6, 0.6), "designation": (0.0, 0.3, 1.0),
    "leader": (0.8, 0.0, 0.8), "endpoint": (1.0, 0.0, 0.0), "no_attach": (1.0, 0.0, 0.0), "unsupported": (0.5, 0.0, 0.0),
    "node": (0.0, 0.6, 0.6),
}


def _rot_shape(page):
    """Shapes are drawn in page (rotated display) coordinates; PyMuPDF's Shape expects unrotated coordinates."""
    return page.derotation_matrix if page.rotation else None


def _pt(page, x, y):
    M = _rot_shape(page)
    if M is None:
        return pymupdf.Point(x, y)
    return pymupdf.Point(x, y) * M


def _rect(page, b):
    p0 = _pt(page, b[0], b[1]); p1 = _pt(page, b[2], b[3])
    return pymupdf.Rect(min(p0.x, p1.x), min(p0.y, p1.y), max(p0.x, p1.x), max(p0.y, p1.y))


def write_overlays(pdf_path: str, analyses: list, out_dir: str) -> dict[str, str]:
    """analyses: list of PageAnalysis (one per analyzed page). Returns {name: path}."""
    out: dict[str, str] = {}
    specs = {
        "production-overlay.pdf": _draw_production,
        "designation-overlay.pdf": _draw_designations,
        "leader-overlay.pdf": _draw_leaders,
        "endpoint-pipe-attachment-overlay.pdf": _draw_attachments,
        "topology-overlay.pdf": _draw_topology,
        "ambiguous-overlay.pdf": _draw_ambiguous,
        "unsupported-style-overlay.pdf": _draw_unsupported,
    }
    for name, fn in specs.items():
        doc = pymupdf.open(pdf_path)
        for pa in analyses:
            page = doc[pa.page.info.index]
            shape = page.new_shape()
            fn(page, shape, pa)
            shape.commit()
        path = os.path.join(out_dir, name)
        doc.save(path, garbage=3, deflate=True)
        doc.close()
        out[name] = path
    return out


def _draw_polylines(page, shape, polylines, color, width):
    for pts in polylines:
        if len(pts) < 2:
            continue
        shape.draw_polyline([_pt(page, x, y) for x, y in pts])
        shape.finish(color=color, width=width, lineCap=1, lineJoin=1, closePath=False)


def _pipe_polylines(pa, state):
    out = []
    own = pa.ownership
    for fk, g in pa.graphs.items():
        for pid, st in own.prim_states[fk].items():
            if st.state == state:
                s = g.prims[pid].seg
                out.append([(s.x0, s.y0), (s.x1, s.y1)])
    return out


def _draw_production(page, shape, pa):
    for m in pa.measures:
        _draw_polylines(page, shape, m.pipe.points, COLORS["confirmed"], 2.6)
    _draw_polylines(page, shape, _pipe_polylines(pa, "AMBIGUOUS"), COLORS["ambiguous"], 2.0)
    for d in pa.designations:
        if any(a.designation_id == d.did and a.state == "VERIFIED_PIPE_ATTACHMENT" for a in pa.anchors):
            shape.draw_rect(_rect(page, d.bbox)); shape.finish(color=COLORS["designation"], width=0.5)
    for a in pa.anchors:
        if a.state == "VERIFIED_PIPE_ATTACHMENT":
            shape.draw_circle(_pt(page, a.endpoint[0], a.endpoint[1]), 1.6); shape.finish(color=COLORS["endpoint"], width=0.6)


def _draw_designations(page, shape, pa):
    for d in pa.designations:
        shape.draw_rect(_rect(page, d.bbox)); shape.finish(color=COLORS["designation"], width=0.6)
        shape.insert_text(_pt(page, d.bbox[0], d.bbox[1] - 1), f"{d.text} DN{d.dn if d.dn is not None else '?'}", fontsize=3, color=COLORS["designation"])


def _draw_leaders(page, shape, pa):
    for ld in pa.leaders:
        _draw_polylines(page, shape, [ld.points], COLORS["leader"], 1.0)
        shape.draw_circle(_pt(page, ld.end[0], ld.end[1]), 1.2); shape.finish(color=COLORS["endpoint"], width=0.5)
        for m in ld.crossing_marks:
            shape.draw_rect(_rect(page, m.bbox)); shape.finish(color=COLORS["endpoint"], width=0.4)


def _draw_attachments(page, shape, pa):
    for a in pa.anchors:
        col = COLORS["confirmed"] if a.state == "VERIFIED_PIPE_ATTACHMENT" else (COLORS["ambiguous"] if a.state.startswith("AMBIGUOUS") else COLORS["no_attach"])
        shape.draw_circle(_pt(page, a.endpoint[0], a.endpoint[1]), 2.2); shape.finish(color=col, width=0.8)
        for c in a.contacts:
            p = pa.page.paths[0] if False else None
            shape.draw_circle(_pt(page, c.point[0], c.point[1]), 1.0); shape.finish(color=col, width=0.5)
        shape.insert_text(_pt(page, a.endpoint[0] + 2.5, a.endpoint[1] - 1), a.designation, fontsize=2.6, color=col)


def _draw_topology(page, shape, pa):
    for fk, g in pa.graphs.items():
        for n in g.nodes.values():
            if n.degree >= 3:
                shape.draw_circle(_pt(page, n.x, n.y), 1.5); shape.finish(color=COLORS["node"], width=0.6)
            elif n.degree == 1:
                shape.draw_rect(_rect(page, (n.x - 0.8, n.y - 0.8, n.x + 0.8, n.y + 0.8))); shape.finish(color=COLORS["node"], width=0.4)
        for b in g.bridges:
            n = g.nodes.get(b["from_node"])
            if n:
                shape.draw_circle(_pt(page, n.x, n.y), 0.9); shape.finish(color=COLORS["leader"], width=0.4)


def _draw_ambiguous(page, shape, pa):
    _draw_polylines(page, shape, _pipe_polylines(pa, "AMBIGUOUS"), COLORS["ambiguous"], 2.4)
    _draw_polylines(page, shape, _pipe_polylines(pa, "UNOWNED"), COLORS["unowned"], 1.4)
    for a in pa.anchors:
        if a.state != "VERIFIED_PIPE_ATTACHMENT":
            shape.draw_circle(_pt(page, a.endpoint[0], a.endpoint[1]), 2.4); shape.finish(color=COLORS["ambiguous"], width=0.8)


def _draw_unsupported(page, shape, pa):
    for d in pa.designations:
        if d.unknown_chars > 0:
            shape.draw_rect(_rect(page, d.bbox)); shape.finish(color=COLORS["unsupported"], width=0.8)
    for a in pa.anchors:
        if a.state == "NO_PIPE_ATTACHMENT":
            shape.draw_circle(_pt(page, a.endpoint[0], a.endpoint[1]), 2.0); shape.finish(color=COLORS["unsupported"], width=0.6)
