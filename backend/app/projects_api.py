"""Projektanalys: hela handlingen läst som en modell.

En enkel analys läser en ritning och svarar med meter. Den här läser alla blad i ett projekt och svarar med vad
handlingen består av: vilka hus, vilka discipliner, vilka versioner, vad som hör ihop och vad som inte gick att
avgöra.

Den återanvänder allt som redan finns - projekten, ritningarna, lagringen, jobbkön - och lägger till två saker:
en klassificering per blad, och en parning av versioner som aldrig hittar på ett före och ett efter.

Läsningen är billig med flit. Att köra mängdningen på trehundra blad tar timmar; att läsa deras namnrutor tar
sekunder. Så fas ett är metadata, och mängderna hämtas från de analyser som redan körts på bladen - projektet
mängdar inte om något det redan mängdat.
"""
from __future__ import annotations

import datetime as dt
import os
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from vvs_engine.handling import Handling, as_report, read_handling

from .auth import current_user
from .db import (AnalysisJob, DocumentOverride, Drawing, Project, ProjectAnalysis, User, get_db)
from .storage import storage

router = APIRouter(prefix="/api/projects", tags=["projektanalys"])

MODES = ("simple", "project")
OVERRIDE_FIELDS = ("building", "discipline", "role", "number", "floor", "part")
ROLES = ("underlag", "fore", "efter", "revision", "relation", "referens", "kravhandling",
         "teknisk_beskrivning", "annat")


def _project(db: Session, user: User, pid: str) -> Project:
    p = db.get(Project, pid)
    if p is None or p.owner_id != user.id:
        raise HTTPException(404, "Okänt projekt")
    return p


class ModeIn(BaseModel):
    mode: str


@router.put("/{project_id}/mode")
def set_mode(project_id: str, body: ModeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Vilken sorts analys projektet använder. Valet sparas på projektet och går att se senare."""
    p = _project(db, user, project_id)
    if body.mode not in MODES:
        raise HTTPException(400, "Okänd analystyp")
    p.analysis_mode = body.mode
    db.commit()
    return {"mode": p.analysis_mode}


@router.get("/{project_id}/mode")
def get_mode(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Vad projektet valt, och om det redan finns arbete gjort under valet.

    Ett projekt utan valt läge är ett av de gamla. De fortsätter fungera precis som förut - det svaret säger
    "simple" utan att skriva något, så ingenting ändras för dem förrän någon väljer.
    """
    p = _project(db, user, project_id)
    n_drawings = db.query(Drawing).filter(Drawing.project_id == p.id).count()
    n_jobs = (db.query(AnalysisJob).join(Drawing, AnalysisJob.drawing_id == Drawing.id)
              .filter(Drawing.project_id == p.id).count())
    last = (db.query(ProjectAnalysis).filter(ProjectAnalysis.project_id == p.id)
            .order_by(ProjectAnalysis.created_at.desc()).first())
    return {"mode": p.analysis_mode or "", "effective": p.analysis_mode or "simple",
            "chosen": bool(p.analysis_mode), "drawings": n_drawings, "readings": n_jobs,
            "analysis": {"id": last.id, "status": last.status, "stage": last.stage,
                         "progress": last.progress, "created_at": last.created_at.isoformat()} if last else None}


def _apply_overrides(docs: list[Handling], by_path: dict[str, dict]) -> None:
    """Vad en människa rättat går före vad läsningen kom fram till, och det syns att den gjorde det."""
    from vvs_engine.handling import Field
    for d in docs:
        for fld, value in (by_path.get(d.path) or {}).items():
            if fld in ("building", "discipline", "number", "floor", "part"):
                setattr(d, fld, Field(value, "rättat av en människa", "rättelse", 1.0))


def run_project_analysis(analysis_id: str) -> None:
    """Läs varje blad och bygg handlingen. Körs på jobbkön, som mängdningen."""
    from .db import SessionLocal
    db = SessionLocal()
    try:
        pa = db.get(ProjectAnalysis, analysis_id)
        if pa is None:
            return
        pa.status, pa.stage, pa.progress = "RUNNING", "LÄSER NAMNRUTOR", 0.0
        db.commit()

        drawings = db.query(Drawing).filter(Drawing.project_id == pa.project_id).all()
        over = defaultdict(dict)
        for o in db.query(DocumentOverride).filter(DocumentOverride.project_id == pa.project_id).all():
            over[o.drawing_id][o.field] = o.value

        docs: list[Handling] = []
        by_drawing: dict[str, str] = {}
        for i, d in enumerate(drawings):
            path = storage.path(d.storage_key)
            h = read_handling(path)
            h.filename = d.filename                      # visa det namn användaren laddade upp, inte lagringens
            by_drawing[h.path] = d.id
            docs.append(h)
            pa.progress = round((i + 1) / max(len(drawings), 1) * 0.8, 3)
            if i % 5 == 0:
                db.commit()

        _apply_overrides(docs, {h.path: over.get(by_drawing[h.path], {}) for h in docs})
        pa.stage, pa.progress = "PARAR VERSIONER", 0.85
        db.commit()

        report = as_report(docs)
        for row in report["documents"]:
            row["drawing_id"] = by_drawing.get(row["path"])
            row.pop("path", None)                        # lagringsvägen hör inte hemma i ett svar
        for group in ("pairs", "unclear"):
            for item in report[group]:
                for k in ("before", "after"):
                    if k in item:
                        item[k]["drawing_id"] = by_drawing.get(item[k].pop("path", None))
                for sub in item.get("docs", []):
                    sub["drawing_id"] = by_drawing.get(sub.pop("path", None))
        for b in report["tree"].values():
            for rows in b.values():
                for row in rows:
                    row["drawing_id"] = by_drawing.get(row.pop("path", None))

        pa.stage, pa.progress = "HÄMTAR MÄNGDER", 0.92
        db.commit()
        report["quantities"] = _quantities_by_building(db, pa.project_id, report)

        pa.report, pa.status, pa.stage, pa.progress = report, "DONE", "KLAR", 1.0
        pa.finished_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
    except Exception as e:                                # noqa: BLE001
        pa = db.get(ProjectAnalysis, analysis_id)
        if pa is not None:
            pa.status, pa.error, pa.stage = "FAILED", f"{type(e).__name__}: {e}"[:400], "FEL"
            db.commit()
    finally:
        db.close()


def _quantities_by_building(db: Session, project_id: str, report: dict) -> dict:
    """Mängderna från de läsningar som redan gjorts, hållna per hus.

    Hus A och hus B har var sin beteckningslista, och hus A:s koder får aldrig vandra över till hus B. Så
    summeringen görs per hus och aldrig över hela projektet: en beteckning som bara finns i ett av husen ska
    stå under det huset och ingen annanstans.
    """
    by_drawing = {r["drawing_id"]: r for r in report["documents"] if r.get("drawing_id")}
    rows = (db.query(AnalysisJob, Drawing).join(Drawing, AnalysisJob.drawing_id == Drawing.id)
            .filter(Drawing.project_id == project_id, AnalysisJob.status == "DONE").all())
    out: dict[str, dict[str, dict]] = {}
    for job, d in rows:
        doc = by_drawing.get(d.id) or {}
        b = ((doc.get("building") or {}).get("value")) or "Okänt hus"
        s = job.summary or {}
        for q in (s.get("quantities") or []):
            name = q.get("designation")
            if not name:
                continue
            e = out.setdefault(b, {}).setdefault(name, {
                "designation": name, "dn": q.get("dn"), "horizontal_m": 0.0, "risers": 0,
                "sheets": [], "labels": 0})
            e["horizontal_m"] += q.get("confirmed_horizontal_m") or 0.0
            e["risers"] += max(q.get("riser_count") or 0, q.get("riser_count_from_labels") or 0)
            e["labels"] += q.get("label_count") or 0
            if d.filename not in e["sheets"]:
                e["sheets"].append(d.filename)
    for b in out:
        for e in out[b].values():
            e["horizontal_m"] = round(e["horizontal_m"], 2)
    return {b: sorted(v.values(), key=lambda e: e["designation"]) for b, v in out.items()}


@router.post("/{project_id}/analysis")
def start_analysis(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Starta projektanalysen. Körs på samma kö som mängdningen."""
    p = _project(db, user, project_id)
    if not db.query(Drawing).filter(Drawing.project_id == p.id).count():
        raise HTTPException(400, "Projektet har inga handlingar att läsa")
    if not p.analysis_mode:
        p.analysis_mode = "project"
    pa = ProjectAnalysis(project_id=p.id)
    db.add(pa); db.commit()
    from .jobs import _executor
    _executor.submit(run_project_analysis, pa.id)
    return {"id": pa.id, "status": pa.status}


@router.get("/{project_id}/analysis")
def latest_analysis(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = _project(db, user, project_id)
    pa = (db.query(ProjectAnalysis).filter(ProjectAnalysis.project_id == p.id)
          .order_by(ProjectAnalysis.created_at.desc()).first())
    if pa is None:
        raise HTTPException(404, "Ingen projektanalys körd ännu")
    return {"id": pa.id, "status": pa.status, "stage": pa.stage, "progress": pa.progress,
            "error": pa.error, "report": pa.report,
            "created_at": pa.created_at.isoformat(),
            "finished_at": pa.finished_at.isoformat() if pa.finished_at else None}


class OverrideIn(BaseModel):
    drawing_id: str
    field: str
    value: str
    note: str = ""


@router.post("/{project_id}/overrides")
def set_override(project_id: str, body: OverrideIn, user: User = Depends(current_user),
                 db: Session = Depends(get_db)):
    """Rätta vad läsningen kom fram till om ett blad.

    Rättelsen ligger kvar när analysen körs om - det är hela poängen med den. Att köra om analysen är det som
    räknar om modellen och parningen, så svaret säger att det behövs.
    """
    p = _project(db, user, project_id)
    if body.field not in OVERRIDE_FIELDS:
        raise HTTPException(400, f"Går inte att rätta: {body.field}")
    if body.field == "role" and body.value not in ROLES:
        raise HTTPException(400, "Okänd roll")
    d = db.get(Drawing, body.drawing_id)
    if d is None or d.project_id != p.id:
        raise HTTPException(404, "Okänd handling")
    old = (db.query(DocumentOverride)
           .filter(DocumentOverride.drawing_id == d.id, DocumentOverride.field == body.field).first())
    if old is not None:
        old.value, old.note = body.value, body.note
    else:
        db.add(DocumentOverride(project_id=p.id, drawing_id=d.id, user_id=user.id,
                                field=body.field, value=body.value, note=body.note))
    db.commit()
    return {"ok": True, "rerun_needed": True}


@router.get("/{project_id}/overrides")
def list_overrides(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = _project(db, user, project_id)
    rows = db.query(DocumentOverride).filter(DocumentOverride.project_id == p.id).all()
    return {"rows": [{"drawing_id": o.drawing_id, "field": o.field, "value": o.value, "note": o.note,
                      "at": o.created_at.isoformat()} for o in rows]}
