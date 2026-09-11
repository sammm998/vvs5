"""Ritbordet: blad man ritar själv.

Mängdningen mäter någon annans ritning. Det här är det andra rummet: här finns ingen ritning att ladda upp,
här skapas en. Ett blad är ett pappersformat, en skala och det som ritats på det, och ritobjekten ligger i
byggets egna millimeter - en vägg är 3 000 mm lång vare sig bladet skrivs ut i 1:50 eller 1:100. Skalan hör
till pappret.

Servern äger tre saker: att bladet finns, vad det innehåller, och hur det blir en PDF. Ritandet självt sker i
webbläsaren, för det ska svara på musen. Men måtten på det ritade räknas av samma mätmotor som mängdningen
använder, för en meter ska betyda samma sak i båda rummen.

Utskriften är det som binder ihop rummen: ett blad som tryckts ut blir en handling som alla andra, och kan
läsas av motorn och mängdas för hand precis som en inlämnad ritning.
"""
from __future__ import annotations

import hashlib
import io
import math
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from vvs_engine.takeoff import Scale, measure as engine_measure

from .auth import current_user
from .db import CadSheet, Drawing, Project, User, get_db
from .storage import storage

router = APIRouter(prefix="/api/cad", tags=["cad"])

MM_PER_PT = 25.4 / 72.0
PT_PER_MM = 72.0 / 25.4

# Pappersformaten, stående mått i millimeter. Ett blad ritas liggande, så bredden är det längre måttet.
PAPER = {"A0": (1189.0, 841.0), "A1": (841.0, 594.0), "A2": (594.0, 420.0),
         "A3": (420.0, 297.0), "A4": (297.0, 210.0)}
# Skalor en VVS-ritning faktiskt skrivs i. Listan är en hjälp i gränssnittet; ett eget tal går lika bra.
SCALES = (20, 25, 50, 100, 200, 500)
KINDS = ("line", "polyline", "rect", "circle", "arc", "text", "dim", "pipe")
MAX_ENTITIES = 20000
MAX_POINTS = 4000


def _sheet(db: Session, user: User, sheet_id: str) -> CadSheet:
    s = db.get(CadSheet, sheet_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(404, "Okänt blad")
    return s


def _project(db: Session, user: User, pid: str) -> Project:
    p = db.get(Project, pid)
    if p is None or p.owner_id != user.id:
        raise HTTPException(404, "Okänt projekt")
    return p


def _clean(content: dict | None) -> dict:
    """Vad som sparas av det klienten skickar.

    Ett blad är användarens eget innehåll och ska inte kunna växa fritt eller bära nycklar ingen läser. Det som
    inte går att förstå kastas hellre än gissas: ett ritobjekt utan punkter är inget ritobjekt.
    """
    c = content or {}
    layers = []
    for l in (c.get("layers") or [])[:200]:
        if not isinstance(l, dict) or not l.get("id"):
            continue
        layers.append({"id": str(l["id"])[:32], "name": str(l.get("name") or "Lager")[:80],
                       "color": str(l.get("color") or "#111111")[:16], "visible": bool(l.get("visible", True)),
                       "locked": bool(l.get("locked", False)), "width": float(l.get("width") or 0.35)})
    if not layers:
        layers = [{"id": "l0", "name": "Ritning", "color": "#111111", "visible": True, "locked": False,
                   "width": 0.35}]
    ents = []
    for e in (c.get("entities") or [])[:MAX_ENTITIES]:
        if not isinstance(e, dict) or e.get("type") not in KINDS:
            continue
        pts = []
        for p in (e.get("p") or [])[:MAX_POINTS]:
            try:
                pts.append([round(float(p[0]), 3), round(float(p[1]), 3)])
            except Exception:
                continue
        if e["type"] in ("circle", "arc"):
            if not pts:
                continue
        elif len(pts) < 1:
            continue
        out: dict[str, Any] = {"id": str(e.get("id") or "")[:32] or f"e{len(ents)}", "type": e["type"],
                               "layer": str(e.get("layer") or layers[0]["id"])[:32], "p": pts}
        for k, cast in (("r", float), ("a0", float), ("a1", float), ("h", float), ("off", float),
                        ("closed", bool), ("text", str), ("dn", int), ("designation", str), ("system", str)):
            if e.get(k) is not None:
                try:
                    out[k] = cast(e[k]) if cast is not str else str(e[k])[:120]
                except Exception:
                    pass
        ents.append(out)
    return {"version": 1, "layers": layers, "entities": ents}


def _length_mm(e: dict) -> float:
    """Ritobjektets längd i byggets millimeter - noll för det som inte är en sträcka."""
    t = e.get("type")
    if t in ("circle",):
        return 2 * math.pi * float(e.get("r") or 0.0)
    if t == "arc":
        a = abs(float(e.get("a1") or 0.0) - float(e.get("a0") or 0.0)) % 360.0
        return math.radians(a) * float(e.get("r") or 0.0)
    pts = e.get("p") or []
    if t == "rect" and len(pts) >= 2:
        w = abs(pts[1][0] - pts[0][0]); h = abs(pts[1][1] - pts[0][1])
        return 2 * (w + h)
    if len(pts) < 2:
        return 0.0
    ring = pts + ([pts[0]] if e.get("closed") else [])
    return sum(math.dist(a, b) for a, b in zip(ring, ring[1:]))


def _summary(content: dict) -> dict:
    """Vad bladet innehåller, räknat av mätmotorn.

    Längderna går genom `vvs_engine.takeoff` med en skala på en millimeter per enhet, så att det ritade mäts av
    samma kod som mängdningen mäter med. Ett blad som räknade själv skulle kunna komma till ett annat tal än
    mängden av samma sträcka, och då vore ritbordet inte värt något.
    """
    mm = Scale(meters_per_point=0.001, source="ANGIVEN", label="ritobjektens millimeter")
    rows: dict[str, dict] = {}
    for e in content.get("entities") or []:
        key = e.get("designation") or e.get("layer") or "–"
        r = rows.setdefault(key, {"key": key, "n": 0, "m": 0.0})
        r["n"] += 1
        pts = e.get("p") or []
        if e.get("type") in ("line", "polyline", "pipe") and len(pts) >= 2:
            ring = pts + ([pts[0]] if e.get("closed") else [])
            m = engine_measure("polylinje" if len(ring) > 2 else "langd", ring, mm)
            r["m"] += float(m.value or 0.0)
        else:
            r["m"] += _length_mm(e) / 1000.0
    out = sorted(rows.values(), key=lambda r: -r["m"])
    return {"rows": [{**r, "m": round(r["m"], 3)} for r in out],
            "entities": len(content.get("entities") or []),
            "total_m": round(sum(r["m"] for r in out), 3)}


# ---------------------------------------------------------------- blad

class SheetIn(BaseModel):
    project_id: str
    name: str = Field(default="Nytt blad", max_length=255)
    paper: str = "A3"
    width_mm: float | None = None
    height_mm: float | None = None
    scale_ratio: int = 50


class SheetSave(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    paper: str | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    scale_ratio: int | None = None
    content: dict | None = None


def _row(s: CadSheet, full: bool = False) -> dict:
    d = {"id": s.id, "project_id": s.project_id, "name": s.name, "paper": s.paper,
         "width_mm": s.width_mm, "height_mm": s.height_mm, "scale_ratio": s.scale_ratio,
         "drawing_id": s.drawing_id, "created_at": s.created_at.isoformat(),
         "updated_at": s.updated_at.isoformat() if s.updated_at else None,
         "entities": len((s.content or {}).get("entities") or [])}
    if full:
        d["content"] = _clean(s.content)
        d["summary"] = _summary(d["content"])
    return d


@router.get("/sheets")
def list_sheets(project_id: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(CadSheet).filter(CadSheet.user_id == user.id)
    if project_id:
        q = q.filter(CadSheet.project_id == project_id)
    rows = q.order_by(CadSheet.updated_at.desc()).limit(500).all()
    return {"rows": [_row(s) for s in rows], "paper": PAPER, "scales": list(SCALES)}


@router.post("/sheets")
def create_sheet(body: SheetIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _project(db, user, body.project_id)
    w, h = PAPER.get(body.paper.upper(), PAPER["A3"])
    if body.width_mm and body.height_mm:
        w, h = max(50.0, min(3000.0, body.width_mm)), max(50.0, min(3000.0, body.height_mm))
    ratio = body.scale_ratio if 1 <= (body.scale_ratio or 0) <= 5000 else 50
    s = CadSheet(project_id=body.project_id, user_id=user.id, name=body.name.strip() or "Nytt blad",
                 paper=body.paper.upper()[:16], width_mm=w, height_mm=h, scale_ratio=ratio,
                 content=_clean(None))
    db.add(s); db.commit(); db.refresh(s)
    return _row(s, full=True)


@router.get("/sheets/{sheet_id}")
def get_sheet(sheet_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _row(_sheet(db, user, sheet_id), full=True)


@router.put("/sheets/{sheet_id}")
def save_sheet(sheet_id: str, body: SheetSave, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = _sheet(db, user, sheet_id)
    if body.name is not None:
        s.name = body.name.strip() or s.name
    if body.paper is not None:
        s.paper = body.paper.upper()[:16]
        if s.paper in PAPER:
            s.width_mm, s.height_mm = PAPER[s.paper]
    if body.width_mm and body.height_mm:
        s.width_mm, s.height_mm = max(50.0, min(3000.0, body.width_mm)), max(50.0, min(3000.0, body.height_mm))
    if body.scale_ratio and 1 <= body.scale_ratio <= 5000:
        s.scale_ratio = body.scale_ratio
    if body.content is not None:
        s.content = _clean(body.content)
    db.commit(); db.refresh(s)
    return _row(s, full=True)


@router.delete("/sheets/{sheet_id}")
def delete_sheet(sheet_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = _sheet(db, user, sheet_id)
    db.delete(s); db.commit()
    return {"deleted": sheet_id}


# ---------------------------------------------------------------- utskrift

def _hex(c: str) -> tuple[float, float, float]:
    c = (c or "#111111").lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    try:
        return tuple(int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4))     # type: ignore[return-value]
    except Exception:
        return (0.1, 0.1, 0.1)


def render_pdf(sheet: CadSheet) -> bytes:
    """Bladet som en riktig ritning.

    Ritobjekten ligger i byggets millimeter; pappret är i sina egna. Skalan mellan dem är bladets, och den
    skrivs ut i klartext tillsammans med en skalstock - inte som en artighet, utan därför att en ritning utan
    läsbar skala inte går att mäta, och det här bladet ska gå att mängda som vilket annat som helst.
    """
    import pymupdf

    content = _clean(sheet.content)
    ratio = max(1, int(sheet.scale_ratio or 50))
    doc = pymupdf.open()
    page = doc.new_page(width=sheet.width_mm * PT_PER_MM, height=sheet.height_mm * PT_PER_MM)
    layers = {l["id"]: l for l in content["layers"]}
    ocgs = {lid: doc.add_ocg(l["name"] or lid) for lid, l in layers.items()}

    def P(x: float, y: float) -> tuple[float, float]:
        """Byggets millimeter till papprets punkter."""
        return (x / ratio * PT_PER_MM, y / ratio * PT_PER_MM)

    for e in content["entities"]:
        l = layers.get(e.get("layer") or "") or {"color": "#111111", "width": 0.35, "visible": True}
        if not l.get("visible", True):
            continue
        col = _hex(l.get("color"))
        w = max(0.1, float(l.get("width") or 0.35)) * PT_PER_MM
        oc = ocgs.get(e.get("layer") or "")
        pts = [P(*p) for p in (e.get("p") or [])]
        t = e["type"]
        try:
            if t in ("line", "polyline", "pipe") and len(pts) >= 2:
                for a, b in zip(pts, pts[1:]):
                    page.draw_line(a, b, color=col, width=w, oc=oc)
                if e.get("closed") and len(pts) > 2:
                    page.draw_line(pts[-1], pts[0], color=col, width=w, oc=oc)
            elif t == "rect" and len(pts) >= 2:
                r = pymupdf.Rect(min(pts[0][0], pts[1][0]), min(pts[0][1], pts[1][1]),
                                 max(pts[0][0], pts[1][0]), max(pts[0][1], pts[1][1]))
                page.draw_rect(r, color=col, width=w, oc=oc)
            elif t == "circle" and pts:
                rr = float(e.get("r") or 0.0) / ratio * PT_PER_MM
                page.draw_circle(pts[0], rr, color=col, width=w, oc=oc)
            elif t == "arc" and pts:
                rr = float(e.get("r") or 0.0) / ratio * PT_PER_MM
                a0, a1 = float(e.get("a0") or 0.0), float(e.get("a1") or 0.0)
                steps = max(8, int(abs(a1 - a0) / 6))
                prev = None
                for i in range(steps + 1):
                    a = math.radians(a0 + (a1 - a0) * i / steps)
                    q = (pts[0][0] + rr * math.cos(a), pts[0][1] + rr * math.sin(a))
                    if prev is not None:
                        page.draw_line(prev, q, color=col, width=w, oc=oc)
                    prev = q
            elif t == "text" and pts:
                h = max(1.0, float(e.get("h") or 2.5)) * PT_PER_MM
                page.insert_text(pts[0], str(e.get("text") or ""), fontsize=h, fontname="helv", color=col)
            elif t == "dim" and len(pts) >= 2:
                page.draw_line(pts[0], pts[1], color=col, width=max(w * 0.5, 0.3), oc=oc)
                mm = math.dist(e["p"][0], e["p"][1])
                mid = ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2 - 3)
                page.insert_text(mid, f"{mm / 1000:.3f}".rstrip("0").rstrip(".") + " m",
                                 fontsize=7, fontname="helv", color=col)
        except Exception:
            continue            # ett trasigt ritobjekt tar inte ner utskriften; det ritas bara inte

    # namnruta: vad bladet är, i vilken skala, och en stock att mäta mot
    W, H = sheet.width_mm * PT_PER_MM, sheet.height_mm * PT_PER_MM
    page.draw_rect(pymupdf.Rect(W - 200, H - 60, W - 8, H - 8), color=(0, 0, 0), width=0.6)
    page.insert_text((W - 194, H - 44), (sheet.name or "")[:36], fontsize=9, fontname="helv")
    page.insert_text((W - 194, H - 30), f"SKALA 1:{ratio}", fontsize=9, fontname="helv")
    # skalstocken: fem meter, med sina tal, så att skalan går att läsa geometriskt och inte bara på tro
    step = 1000.0 / ratio * PT_PER_MM           # en meter på pappret
    x0, y0 = 40.0, H - 22.0
    page.draw_line((x0, y0), (x0 + 5 * step, y0), color=(0, 0, 0), width=1.0)
    for i in range(6):
        page.insert_text((x0 + i * step - 2, y0 - 4), str(i), fontsize=8, fontname="helv")
        page.draw_line((x0 + i * step, y0 - 2), (x0 + i * step, y0 + 2), color=(0, 0, 0), width=0.6)
    page.insert_text((x0 + 5 * step + 8, y0 - 4), "m", fontsize=8, fontname="helv")
    out = doc.tobytes()
    doc.close()
    return out


@router.post("/sheets/{sheet_id}/tryck")
def print_sheet(sheet_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Bladet blir en handling i projektet: samma sorts PDF som en inlämnad ritning, och mängdas likadant."""
    s = _sheet(db, user, sheet_id)
    data = render_pdf(s)
    name = f"{(s.name or 'blad').strip().replace('/', '-')[:80]}.pdf"
    d = Drawing(project_id=s.project_id, filename=name, storage_key="",
                sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data), n_pages=1)
    db.add(d); db.flush()
    key = f"drawings/{d.id}/{name}"
    storage.put(key, io.BytesIO(data))
    d.storage_key = key
    s.drawing_id = d.id
    db.commit()
    return {"drawing_id": d.id, "filename": name, "size_bytes": len(data)}


@router.get("/sheets/{sheet_id}/pdf")
def sheet_pdf(sheet_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from fastapi.responses import Response
    s = _sheet(db, user, sheet_id)
    return Response(render_pdf(s), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{(s.name or "blad")[:60]}.pdf"'})


@router.get("/sheets/{sheet_id}/dxf")
def sheet_dxf(sheet_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Bladet som DXF, så att det går att öppna i ett riktigt CAD-program.

    R12-varianten med rena entiteter: LINE, LWPOLYLINE, CIRCLE, ARC och TEXT i byggets millimeter. Det är den
    minsta gemensamma nämnaren alla program läser, och den håller lagren.
    """
    from fastapi.responses import Response
    s = _sheet(db, user, sheet_id)
    c = _clean(s.content)
    o: list[str] = []

    def g(code: int, val) -> None:
        o.append(str(code)); o.append(str(val))

    g(0, "SECTION"); g(2, "TABLES"); g(0, "TABLE"); g(2, "LAYER")
    for l in c["layers"]:
        g(0, "LAYER"); g(2, (l["name"] or l["id"])[:31].replace(" ", "_")); g(70, 0); g(62, 7); g(6, "CONTINUOUS")
    g(0, "ENDTAB"); g(0, "ENDSEC")
    g(0, "SECTION"); g(2, "ENTITIES")
    names = {l["id"]: (l["name"] or l["id"])[:31].replace(" ", "_") for l in c["layers"]}
    for e in c["entities"]:
        lay = names.get(e.get("layer") or "", "0")
        pts = e.get("p") or []
        t = e["type"]
        if t in ("line", "dim") and len(pts) >= 2:
            g(0, "LINE"); g(8, lay); g(10, pts[0][0]); g(20, -pts[0][1]); g(11, pts[1][0]); g(21, -pts[1][1])
        elif t in ("polyline", "pipe", "rect") and len(pts) >= 2:
            ring = pts
            if t == "rect":
                (x0, y0), (x1, y1) = pts[0], pts[1]
                ring = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
            g(0, "LWPOLYLINE"); g(8, lay); g(90, len(ring))
            g(70, 1 if (e.get("closed") or t == "rect") else 0)
            for p in ring:
                g(10, p[0]); g(20, -p[1])
        elif t == "circle" and pts:
            g(0, "CIRCLE"); g(8, lay); g(10, pts[0][0]); g(20, -pts[0][1]); g(40, e.get("r") or 0)
        elif t == "arc" and pts:
            g(0, "ARC"); g(8, lay); g(10, pts[0][0]); g(20, -pts[0][1]); g(40, e.get("r") or 0)
            g(50, -float(e.get("a1") or 0)); g(51, -float(e.get("a0") or 0))
        elif t == "text" and pts:
            g(0, "TEXT"); g(8, lay); g(10, pts[0][0]); g(20, -pts[0][1]); g(40, (e.get("h") or 2.5) * 10)
            g(1, str(e.get("text") or "")[:250])
    g(0, "ENDSEC"); g(0, "EOF")
    body = "\r\n".join(o) + "\r\n"
    return Response(body, media_type="application/dxf",
                    headers={"Content-Disposition": f'attachment; filename="{(s.name or "blad")[:60]}.dxf"'})
