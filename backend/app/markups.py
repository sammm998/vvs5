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
from .db import AnalysisJob, Calibration, Drawing, Markup, ToolPreset, User, get_db
from .storage import storage

router = APIRouter(prefix="/api/drawings", tags=["markeringar"])

TOOLS = ("langd", "area", "antal", "polylinje", "rektangel", "text", "moln", "frihand", "volym", "vinkel")
MAX_POINTS = 4000                 # en frihandslinje har många punkter; en ritning har inte oändligt många
LENGTH_TOOLS = ("langd", "polylinje", "frihand")
AREA_TOOLS = ("area", "rektangel", "moln", "volym")
COUNT_TOOLS = ("antal",)


def _drawing(db: Session, user: User, drawing_id: str) -> Drawing:
    d = db.get(Drawing, drawing_id)
    if d is None or d.project.owner_id != user.id:
        raise HTTPException(404, "Okänd handling")
    return d


def _read_scale(db: Session, drawing_id: str) -> float | None:
    """Meter per punkt, ur bladets senaste färdiga läsning."""
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


def _calibration(db: Session, drawing_id: str, page: int) -> Calibration | None:
    return (db.query(Calibration).filter(Calibration.drawing_id == drawing_id, Calibration.page == page)
            .order_by(Calibration.created_at.desc()).first())


def _mpp(db: Session, drawing_id: str, page: int = 0) -> tuple[float | None, str]:
    """Skalan markeringarna mäts i, och varifrån den kom.

    En uppmätt skala går före läsningens: den som drog linjen över något vars mått står på ritningen vet mer
    om det här bladet än stocken gjorde. Finns ingen av dem finns ingen skala, och då redovisas markeringen i
    punkter i stället för i påhittade meter."""
    c = _calibration(db, drawing_id, page)
    if c is not None and c.meters_per_pdf_point:
        return c.meters_per_pdf_point, "UPPMÄTT"
    m = _read_scale(db, drawing_id)
    return (m, "LÄSNINGEN") if m else (None, "INGEN")


def _ring_area(pts: list) -> float:
    """Skoformeln över den slutna formen; sista punkten binds till den första."""
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2.0


def _measure(tool: str, points: list, mpp: float | None, props: dict | None = None, source: str = "INGEN") -> dict:
    """Vad markeringen mäter, räknat ur punkterna och mängdarens egna påslag.

    En längd är summan av sträckorna, gånger multiplikatorn och plus tillägget - så att en stigare räknad som
    en punkt på planen ändå kan bära sina meter. En yta är polygonens area minus de avdrag som ritats i den,
    och med ett djup blir den en volym. Ett antal är antalet punkter gånger multiplikatorn. Varje steg
    redovisas: rått mått, påslag, resultat - annars är slutsiffran ett tal ingen kan följa.
    """
    P = props or {}
    mult = float(P.get("multiplikator") or 1.0)
    add_m = float(P.get("tillagg_m") or 0.0)
    depth = float(P.get("djup_m") or 0.0)
    pts = [(float(x), float(y)) for x, y in points]
    out: dict = {"points": len(pts), "scale": {"UPPMÄTT": "UPPMÄTT", "LÄSNINGEN": "VERIFIERAD"}.get(source, "INGEN_SKALA")}
    if mult != 1.0:
        out["multiplikator"] = mult
    if add_m:
        out["tillagg_m"] = add_m
    if tool in COUNT_TOOLS:
        out["antal"] = round(len(pts) * mult, 3) if mult != 1.0 else len(pts)
        return out
    if len(pts) < 2:
        return out
    length_pt = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    out["langd_pt"] = round(length_pt, 2)
    if mpp:
        raw = length_pt * mpp
        out["ratt_m"] = round(raw, 3)
        out["m"] = round(raw * mult + add_m, 3)
    if tool in AREA_TOOLS and len(pts) >= 3:
        area_pt = _ring_area(pts)
        cut_pt = 0.0
        for ring in (P.get("avdrag") or []):
            r = [(float(x), float(y)) for x, y in ring]
            if len(r) >= 3:
                cut_pt += _ring_area(r)
        cut_pt = min(cut_pt, area_pt)
        out["area_pt"] = round(area_pt - cut_pt, 2)
        if cut_pt:
            out["avdrag_pt"] = round(cut_pt, 2)
        if mpp:
            kvm = (area_pt - cut_pt) * mpp * mpp
            out["kvm"] = round(kvm * mult, 3)
            if cut_pt:
                out["avdrag_kvm"] = round(cut_pt * mpp * mpp, 3)
            if depth:
                out["djup_m"] = depth
                out["m3"] = round(kvm * mult * depth, 3)
        # omkretsen är en längd men ingen tar av den som en sträcka: den står för sig
        out["omkrets_pt"] = round(length_pt + math.dist(pts[-1], pts[0]), 2)
        if mpp:
            out["omkrets_m"] = round(out["omkrets_pt"] * mpp, 3)
        out.pop("m", None)
    return out


def _out(m: Markup) -> dict:
    return {"id": m.id, "page": m.page, "tool": m.tool, "layer": m.layer, "designation": m.designation,
            "points": m.points, "style": m.style, "text": m.text, "measure": m.measure,
            "props": m.props or {}, "seq": m.seq,
            "created_at": m.created_at.isoformat(), "updated_at": m.updated_at.isoformat() if m.updated_at else None}


class MarkupIn(BaseModel):
    page: int = Field(default=0, ge=0, le=9999)
    tool: str
    layer: str = "Mängdning"
    designation: str | None = None
    points: list = Field(default_factory=list)
    style: dict = Field(default_factory=dict)
    props: dict = Field(default_factory=dict)
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
    P = body.props or {}
    for key, lo, hi in (("multiplikator", 0.0, 1000.0), ("tillagg_m", -10_000.0, 10_000.0), ("djup_m", 0.0, 1000.0)):
        if key in P and P[key] not in (None, ""):
            try:
                v = float(P[key])
            except (TypeError, ValueError):
                raise HTTPException(400, f"{key} är inget tal")
            if not lo <= v <= hi:
                raise HTTPException(400, f"{key} ligger utanför vad det kan betyda ({lo}-{hi})")
    rings = P.get("avdrag") or []
    if not isinstance(rings, list) or len(rings) > 50:
        raise HTTPException(400, "Avdragen skrivs som en lista med högst femtio ytor")
    for ring in rings:
        if not isinstance(ring, list) or len(ring) > MAX_POINTS:
            raise HTTPException(400, "Ett avdrag skrivs som en lista med punkter")


@router.get("/{drawing_id}/markups")
def list_markups(drawing_id: str, page: int = 0, user: User = Depends(current_user),
                 db: Session = Depends(get_db)):
    _drawing(db, user, drawing_id)
    rows = (db.query(Markup).filter(Markup.drawing_id == drawing_id, Markup.page == page,
                                    Markup.deleted.is_(False))
            .order_by(Markup.created_at).all())
    mpp, source = _mpp(db, drawing_id, page)
    c = _calibration(db, drawing_id, page)

    def sums(rs) -> dict:
        # Summeras efter vad verktyget mäter, inte efter vilka tal raden råkar bära. En ytas omkrets är en längd
        # i punkter räknat, men ingen tar av den som en sträcka - och lades den till i meterraden blev totalen
        # ett tal som inte svarar mot något någon ritat.
        return {"m": round(sum((m.measure or {}).get("m") or 0.0 for m in rs if m.tool in LENGTH_TOOLS), 2),
                "kvm": round(sum((m.measure or {}).get("kvm") or 0.0 for m in rs if m.tool in AREA_TOOLS), 2),
                "m3": round(sum((m.measure or {}).get("m3") or 0.0 for m in rs if m.tool in AREA_TOOLS), 3),
                "antal": round(sum((m.measure or {}).get("antal") or 0 for m in rs if m.tool in COUNT_TOOLS), 3),
                "rader": len(rs)}

    by_layer, by_tool, by_des = {}, {}, {}
    for m in rows:
        by_layer.setdefault(m.layer, []).append(m)
        by_tool.setdefault(m.tool, []).append(m)
        if m.designation:
            by_des.setdefault(m.designation, []).append(m)
    return {"rows": [_out(m) for m in rows], "meters_per_pdf_point": mpp, "scale_source": source,
            "calibration": ({"meters_per_pdf_point": c.meters_per_pdf_point, "length_m": c.length_m,
                             "points": c.points, "note": c.note, "at": c.created_at.isoformat()} if c else None),
            "layers": sorted({m.layer for m in rows}),
            "totals": sums(rows),
            "by_layer": {k: sums(v) for k, v in sorted(by_layer.items())},
            "by_tool": {k: sums(v) for k, v in sorted(by_tool.items())},
            "by_designation": {k: sums(v) for k, v in sorted(by_des.items())},
            "unscaled": sum(1 for m in rows if (m.measure or {}).get("scale") == "INGEN_SKALA")}


@router.post("/{drawing_id}/markups")
def add_markup(drawing_id: str, body: MarkupIn, user: User = Depends(current_user),
               db: Session = Depends(get_db)):
    _drawing(db, user, drawing_id)
    _check(body)
    m = Markup(drawing_id=drawing_id, user_id=user.id, **body.model_dump())
    mpp, source = _mpp(db, drawing_id, body.page)
    m.measure = _measure(body.tool, body.points, mpp, body.props, source)
    if body.tool in COUNT_TOOLS:
        # löpnummer inom lagret, som i en mängdningslista: den femte pumpen ska gå att peka ut
        last = (db.query(Markup).filter(Markup.drawing_id == drawing_id, Markup.layer == body.layer,
                                        Markup.tool.in_(COUNT_TOOLS), Markup.deleted.is_(False))
                .order_by(Markup.seq.desc()).first())
        m.seq = ((last.seq or 0) if last else 0) + 1
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
    mpp, source = _mpp(db, drawing_id, body.page)
    m.measure = _measure(body.tool, body.points, mpp, body.props, source)
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


@router.get("/{drawing_id}/markups.csv")
def markups_csv(drawing_id: str, page: int = 0, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Markeringslistan som en fil att öppna i Excel: en rad per markering, med måttet och vad det räknades på."""
    from fastapi.responses import Response

    from .main import _attachment
    d = _drawing(db, user, drawing_id)
    rows = (db.query(Markup).filter(Markup.drawing_id == drawing_id, Markup.page == page,
                                    Markup.deleted.is_(False)).order_by(Markup.layer, Markup.created_at).all())
    mpp, source = _mpp(db, drawing_id, page)
    head = ["Lager", "Verktyg", "Löpnr", "Beteckning", "Längd m", "Yta m²", "Volym m³", "Antal",
            "Djup m", "Multiplikator", "Tillägg m", "Avdrag m²", "Text", "Skala", "Skapad"]
    lines = [";".join(head)]
    for m in rows:
        me = m.measure or {}
        P = m.props or {}
        cells = [m.layer, m.tool, str(m.seq or ""), m.designation or "",
                 f"{me.get('m', ''):}", f"{me.get('kvm', ''):}", f"{me.get('m3', ''):}", f"{me.get('antal', ''):}",
                 f"{P.get('djup_m', ''):}", f"{P.get('multiplikator', ''):}", f"{P.get('tillagg_m', ''):}",
                 f"{me.get('avdrag_kvm', ''):}", (m.text or "").replace(";", ","),
                 me.get("scale", ""), m.created_at.isoformat(timespec="minutes")]
        lines.append(";".join(str(c).replace(".", ",") if isinstance(c, float) else str(c) for c in cells))
    lines.append("")
    lines.append(f"Skalan;{source};{('%.6f' % mpp).replace('.', ',') if mpp else ''};m per punkt")
    body = "\n".join(lines)
    return Response(body.encode("utf-8-sig"), media_type="text/csv",
                    headers=_attachment(f"{d.filename.rsplit('.', 1)[0]}-markeringar.csv"))


# ------------------------------------------------------------------------------------------------------------
# Kalibrering: skalan mängdaren mäter upp själv
# ------------------------------------------------------------------------------------------------------------
class CalibrationIn(BaseModel):
    page: int = Field(default=0, ge=0, le=9999)
    points: list = Field(default_factory=list)      # [[x0, y0], [x1, y1]] i sidans punkter
    length_m: float = Field(gt=0, le=10_000)
    note: str = ""


@router.get("/{drawing_id}/calibration")
def read_calibration(drawing_id: str, page: int = 0, user: User = Depends(current_user),
                     db: Session = Depends(get_db)):
    _drawing(db, user, drawing_id)
    mpp, source = _mpp(db, drawing_id, page)
    c = _calibration(db, drawing_id, page)
    return {"meters_per_pdf_point": mpp, "source": source,
            "read_scale": _read_scale(db, drawing_id),
            "calibration": ({"meters_per_pdf_point": c.meters_per_pdf_point, "length_m": c.length_m,
                             "points": c.points, "note": c.note, "at": c.created_at.isoformat()} if c else None)}


@router.put("/{drawing_id}/calibration")
def set_calibration(drawing_id: str, body: CalibrationIn, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    """Dra en linje över något vars längd är känd och skriv vad det är. Måtten på bladet räknas om direkt."""
    _drawing(db, user, drawing_id)
    pts = body.points or []
    if len(pts) != 2 or any(len(p) != 2 for p in pts):
        raise HTTPException(400, "Kalibreringen är en sträcka: två punkter")
    d = math.dist((float(pts[0][0]), float(pts[0][1])), (float(pts[1][0]), float(pts[1][1])))
    if d < 5.0:
        raise HTTPException(400, "Sträckan är för kort för att mäta skalan på - dra en längre")
    mpp = body.length_m / d
    if not 1e-6 < mpp < 1.0:
        raise HTTPException(400, "Den skalan kan inte stämma - kontrollera längden du skrev")
    c = Calibration(drawing_id=drawing_id, page=body.page, meters_per_pdf_point=mpp, length_m=body.length_m,
                    points=pts, note=body.note or "", user_id=user.id)
    db.add(c)
    # varje markering på sidan mäts om i den nya skalan: en gammal siffra i ny skala är fel siffra
    for m in db.query(Markup).filter(Markup.drawing_id == drawing_id, Markup.page == body.page,
                                     Markup.deleted.is_(False)).all():
        m.measure = _measure(m.tool, m.points, mpp, m.props, "UPPMÄTT")
    db.commit()
    return read_calibration(drawing_id, body.page, user, db)


@router.delete("/{drawing_id}/calibration")
def drop_calibration(drawing_id: str, page: int = 0, user: User = Depends(current_user),
                     db: Session = Depends(get_db)):
    """Ta bort den uppmätta skalan: läsningens egen gäller igen."""
    _drawing(db, user, drawing_id)
    for c in db.query(Calibration).filter(Calibration.drawing_id == drawing_id, Calibration.page == page).all():
        db.delete(c)
    db.commit()
    mpp, source = _mpp(db, drawing_id, page)
    for m in db.query(Markup).filter(Markup.drawing_id == drawing_id, Markup.page == page,
                                     Markup.deleted.is_(False)).all():
        m.measure = _measure(m.tool, m.points, mpp, m.props, source)
    db.commit()
    return read_calibration(drawing_id, page, user, db)


# ------------------------------------------------------------------------------------------------------------
# Verktygslådan: förval som följer med till nästa blad
# ------------------------------------------------------------------------------------------------------------
presets = APIRouter(prefix="/api/tools", tags=["verktyg"])


class PresetIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    tool: str
    layer: str = "Mängdning"
    designation: str | None = None
    style: dict = Field(default_factory=dict)
    props: dict = Field(default_factory=dict)


@presets.get("")
def list_presets(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(ToolPreset).filter(ToolPreset.user_id == user.id).order_by(ToolPreset.created_at).all()
    return {"rows": [{"id": t.id, "name": t.name, "tool": t.tool, "layer": t.layer,
                      "designation": t.designation, "style": t.style, "props": t.props} for t in rows]}


@presets.post("")
def add_preset(body: PresetIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.tool not in TOOLS:
        raise HTTPException(400, f"Okänt verktyg: {body.tool}")
    t = ToolPreset(user_id=user.id, **body.model_dump())
    db.add(t); db.commit()
    return {"id": t.id, "name": t.name, "tool": t.tool, "layer": t.layer, "designation": t.designation,
            "style": t.style, "props": t.props}


@presets.delete("/{preset_id}")
def drop_preset(preset_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.get(ToolPreset, preset_id)
    if t is None or t.user_id != user.id:
        raise HTTPException(404, "Okänt verktyg")
    db.delete(t); db.commit()
    return {"ok": True}
