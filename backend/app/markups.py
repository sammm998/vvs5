"""Vad mängdaren själv ritar ovanpå ritningen.

Det ligger vid sidan av läsningen, aldrig i den. Motorn mäter det ritaren ritade; det här är vad mängdaren
lade till för hand - en sträcka verktyget inte kunde namnge, en yta, ett antal, en anteckning - och de två
redovisas var för sig så att ingen behöver undra vilket som är vilket.

Måtten räknas här, ur punkterna och bladets egen skala, och aldrig i webbläsaren. Ett mått som klienten
räknar fram är ett mått som inte går att härleda till någonting, och det skulle stå bredvid motorns meter i
samma tabell.

Skalan hämtas ur den senaste färdiga läsningen av bladet. Finns ingen sådan finns ingen skala, och då
redovisas markeringen i punkter med ett uttryckligt "ingen skala" i stället för i påhittade meter.
"""
from __future__ import annotations

import json
import math
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .auth import current_user
from .db import AnalysisJob, Drawing, Markup, User, get_db
from .storage import storage

router = APIRouter(prefix="/api/drawings", tags=["markeringar"])

TOOLS = ("langd", "area", "antal", "polylinje", "rektangel", "text", "moln", "frihand")
MAX_POINTS = 4000                 # en frihandslinje har många punkter; en ritning har inte oändligt många
LENGTH_TOOLS = ("langd", "polylinje", "frihand")
AREA_TOOLS = ("area", "rektangel", "moln")


def _drawing(db: Session, user: User, drawing_id: str) -> Drawing:
    d = db.get(Drawing, drawing_id)
    if d is None or d.project.owner_id != user.id:
        raise HTTPException(404, "Okänd handling")
    return d


def _mpp(db: Session, drawing_id: str) -> float | None:
    """Meter per punkt, ur bladets senaste färdiga läsning. Ingen läsning, ingen skala."""
    j = (db.query(AnalysisJob).filter(AnalysisJob.drawing_id == drawing_id,
                                      AnalysisJob.status == "COMPLETED")
         .order_by(AnalysisJob.created_at.desc()).first())
    if j is None or not j.result_key:
        return None
    path = os.path.join(storage.path(j.result_key), "quantities.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return (json.load(fh).get("scale") or {}).get("meters_per_pdf_point")


def _measure(tool: str, points: list, mpp: float | None) -> dict:
    """Vad markeringen mäter, räknat ur punkterna.

    En längd är summan av sträckorna. En yta är polygonens area med skoformeln - och den räknas på den
    slutna formen, för en yta som inte är sluten är ingen yta. Ett antal är antalet punkter.
    """
    pts = [(float(x), float(y)) for x, y in points]
    out: dict = {"points": len(pts), "scale": "VERIFIERAD" if mpp else "INGEN_SKALA"}
    if tool == "antal":
        out["antal"] = len(pts)
        return out
    if len(pts) < 2:
        return out
    length_pt = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    out["langd_pt"] = round(length_pt, 2)
    if mpp:
        out["m"] = round(length_pt * mpp, 3)
    if tool in AREA_TOOLS and len(pts) >= 3:
        # skoformeln över den slutna formen; sista punkten binds till den första
        a = 0.0
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            a += x0 * y1 - x1 * y0
        area_pt = abs(a) / 2.0
        out["area_pt"] = round(area_pt, 2)
        if mpp:
            out["kvm"] = round(area_pt * mpp * mpp, 3)
    return out


def _out(m: Markup) -> dict:
    return {"id": m.id, "page": m.page, "tool": m.tool, "layer": m.layer, "designation": m.designation,
            "points": m.points, "style": m.style, "text": m.text, "measure": m.measure,
            "created_at": m.created_at.isoformat(), "updated_at": m.updated_at.isoformat() if m.updated_at else None}


class MarkupIn(BaseModel):
    page: int = Field(default=0, ge=0, le=9999)
    tool: str
    layer: str = "Mängdning"
    designation: str | None = None
    points: list = Field(default_factory=list)
    style: dict = Field(default_factory=dict)
    text: str = ""


def _check(body: MarkupIn) -> None:
    if body.tool not in TOOLS:
        raise HTTPException(400, f"Okänt verktyg: {body.tool}")
    if len(body.points) > MAX_POINTS:
        raise HTTPException(400, f"För många punkter (högst {MAX_POINTS})")
    for p in body.points:
        if not (isinstance(p, (list, tuple)) and len(p) == 2
                and all(isinstance(c, (int, float)) for c in p)):
            raise HTTPException(400, "En punkt skrivs som [x, y] i sidans punkter")


@router.get("/{drawing_id}/markups")
def list_markups(drawing_id: str, page: int = 0, user: User = Depends(current_user),
                 db: Session = Depends(get_db)):
    _drawing(db, user, drawing_id)
    rows = (db.query(Markup).filter(Markup.drawing_id == drawing_id, Markup.page == page,
                                    Markup.deleted.is_(False))
            .order_by(Markup.created_at).all())
    mpp = _mpp(db, drawing_id)
    # Summeras efter vad verktyget mäter, inte efter vilka tal raden råkar bära. En ytas omkrets är en längd
    # i punkter räknat, men ingen tar av den som en sträcka - och lades den till i meterraden blev totalen
    # ett tal som inte svarar mot något någon ritat.
    return {"rows": [_out(m) for m in rows], "meters_per_pdf_point": mpp,
            "layers": sorted({m.layer for m in rows}),
            "totals": {"m": round(sum((m.measure or {}).get("m") or 0.0 for m in rows
                                      if m.tool in LENGTH_TOOLS), 2),
                       "kvm": round(sum((m.measure or {}).get("kvm") or 0.0 for m in rows
                                        if m.tool in AREA_TOOLS), 2),
                       "antal": sum((m.measure or {}).get("antal") or 0 for m in rows)},
            "unscaled": sum(1 for m in rows if (m.measure or {}).get("scale") == "INGEN_SKALA")}


@router.post("/{drawing_id}/markups")
def add_markup(drawing_id: str, body: MarkupIn, user: User = Depends(current_user),
               db: Session = Depends(get_db)):
    _drawing(db, user, drawing_id)
    _check(body)
    m = Markup(drawing_id=drawing_id, user_id=user.id, **body.model_dump())
    m.measure = _measure(body.tool, body.points, _mpp(db, drawing_id))
    db.add(m); db.commit()
    return _out(m)


@router.put("/{drawing_id}/markups/{markup_id}")
def edit_markup(drawing_id: str, markup_id: str, body: MarkupIn, user: User = Depends(current_user),
                db: Session = Depends(get_db)):
    _drawing(db, user, drawing_id)
    _check(body)
    m = db.get(Markup, markup_id)
    if m is None or m.drawing_id != drawing_id or m.deleted:
        raise HTTPException(404, "Okänd markering")
    for k, v in body.model_dump().items():
        setattr(m, k, v)
    m.measure = _measure(body.tool, body.points, _mpp(db, drawing_id))
    db.commit()
    return _out(m)


@router.delete("/{drawing_id}/markups/{markup_id}")
def drop_markup(drawing_id: str, markup_id: str, user: User = Depends(current_user),
                db: Session = Depends(get_db)):
    """Markeringen stryks men står kvar i lagret. Den som ritat tjugo sträckor och råkar ta bort en ska kunna
    få tillbaka den, och en rad som försvunnit spårlöst går inte att fråga om."""
    _drawing(db, user, drawing_id)
    m = db.get(Markup, markup_id)
    if m is None or m.drawing_id != drawing_id:
        raise HTTPException(404, "Okänd markering")
    m.deleted = True
    db.commit()
    return {"ok": True}
