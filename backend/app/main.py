from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile

import subprocess
from functools import lru_cache
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from . import exports, jobs
from vvs_engine.corrections import KINDS as CORRECTION_KINDS, apply as apply_corrections
from vvs_engine.learning import KEYS, lessons, settle, situation
from .auth import create_token, current_user, hash_password, verify_password
from .config import settings
from .db import Correction, AnalysisJob, Drawing, Project, User, get_db, init_db
from .storage import storage

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _startup():
    init_db()


# ---------------------------------------------------------------- health / auth
@lru_cache(maxsize=1)
def _build_stamp() -> dict:
    """Which code produced this reading. A number on screen is only checkable if you can tell what made it."""
    from vvs_engine import __version__
    # the image carries no .git, so take the build from whatever the platform exposes before falling back to git
    # "unknown" is what the image bakes in when nothing was passed at build time, and it is not an answer: taking
    # it as one stops the search before the platform's own variables are ever looked at, which is exactly what
    # happened in production - the endpoint reported "unknown" while Railway knew the commit all along.
    cand = [os.environ.get(k, "") for k in ("VVS_BUILD", "RAILWAY_GIT_COMMIT_SHA", "SOURCE_COMMIT", "GIT_COMMIT",
                                            "RAILWAY_DEPLOYMENT_ID")]
    build = next((v[:12] for v in cand if v.strip() and v.strip().lower() != "unknown"), "")
    if not build:
        try:
            build = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                                   timeout=2, cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                                   ).stdout.strip() or "unknown"
        except Exception:
            build = "unknown"
    return {"engine": __version__, "build": build}


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/health")
def api_health():
    return {"status": "ok"}


@app.get("/api/version")
def version():
    """What is running here, and what it can reach - answerable without logging in.

    A reading is only checkable if you can tell which code produced it, and a second reader is only verifiable if
    you can tell whether this installation is configured for one and can actually reach it. Both are said here as
    plain facts. No credential is returned, and none can be inferred beyond "there is one" or "there is not".
    """
    from .jobs import second_reader_state
    on, why = second_reader_state()
    model = None
    if on:
        try:
            from tools.astra_transport import MODEL as model
        except Exception:                                       # noqa: BLE001
            model = None
    return {**_build_stamp(),
            "second_reader": {"enabled": on, "reason": why, "model": model,
                              "setting": settings.second_reader}}


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


@app.post("/api/auth/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if not settings.allow_registration:
        raise HTTPException(403, "Registrering är avstängd")
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(400, "E-postadressen är redan registrerad")
    if len(body.password) < 6:
        raise HTTPException(400, "Lösenordet måste vara minst 6 tecken")
    u = User(email=body.email.lower(), password_hash=hash_password(body.password))
    db.add(u); db.commit()
    return {"access_token": create_token(u), "token_type": "bearer", "email": u.email}


@app.post("/api/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == form.username.lower()).first()
    if not u or not verify_password(form.password, u.password_hash):
        raise HTTPException(401, "Fel e-post eller lösenord")
    return {"access_token": create_token(u), "token_type": "bearer", "email": u.email}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email}


# ---------------------------------------------------------------- projects
class ProjectIn(BaseModel):
    name: str
    description: str = ""


def _project(db: Session, user: User, project_id: str) -> Project:
    p = db.get(Project, project_id)
    if p is None or p.owner_id != user.id:
        raise HTTPException(404, "Projektet finns inte")
    return p


def _drawing(db: Session, user: User, drawing_id: str) -> Drawing:
    d = db.get(Drawing, drawing_id)
    if d is None or d.project.owner_id != user.id:
        raise HTTPException(404, "Ritningen finns inte")
    return d


def _job(db: Session, user: User, job_id: str) -> AnalysisJob:
    j = db.get(AnalysisJob, job_id)
    if j is None or j.drawing.project.owner_id != user.id:
        raise HTTPException(404, "Analysen finns inte")
    return j


def _proj_out(p: Project):
    return {"id": p.id, "name": p.name, "description": p.description, "created_at": p.created_at, "n_drawings": len(p.drawings)}


def _drawing_out(d: Drawing):
    latest = sorted(d.jobs, key=lambda j: j.created_at)[-1] if d.jobs else None
    return {"id": d.id, "project_id": d.project_id, "filename": d.filename, "size_bytes": d.size_bytes, "n_pages": d.n_pages,
            "sha256": d.sha256, "created_at": d.created_at, "latest_job": _job_out(latest) if latest else None}


def _job_out(j: AnalysisJob):
    return {"id": j.id, "drawing_id": j.drawing_id, "status": j.status, "stage": j.stage, "progress": j.progress, "error": j.error,
            "summary": j.summary, "created_at": j.created_at, "started_at": j.started_at, "finished_at": j.finished_at}


@app.get("/api/projects")
def list_projects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [_proj_out(p) for p in db.query(Project).filter(Project.owner_id == user.id).order_by(Project.created_at.desc()).all()]


@app.post("/api/projects")
def create_project(body: ProjectIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = Project(owner_id=user.id, name=body.name.strip() or "Namnlöst projekt", description=body.description)
    db.add(p); db.commit()
    return _proj_out(p)


@app.get("/api/projects/{project_id}")
def get_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = _project(db, user, project_id)
    return {**_proj_out(p), "drawings": [_drawing_out(d) for d in sorted(p.drawings, key=lambda d: d.created_at, reverse=True)]}


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = _project(db, user, project_id)
    for d in p.drawings:
        storage.delete_prefix(f"results/{d.id}")
        storage.delete_prefix(f"drawings/{d.id}")
    db.delete(p); db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- drawings
@app.post("/api/projects/{project_id}/drawings")
async def upload_drawing(project_id: str, file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = _project(db, user, project_id)
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Endast PDF-filer stöds")
    data = await file.read()
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "Filen är inte en giltig PDF")
    import pymupdf
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
        n_pages = len(doc); doc.close()
    except Exception:
        raise HTTPException(400, "PDF-filen kunde inte läsas")
    d = Drawing(project_id=p.id, filename=os.path.basename(file.filename), storage_key="", sha256=hashlib.sha256(data).hexdigest(),
                size_bytes=len(data), n_pages=n_pages)
    db.add(d); db.flush()
    key = f"drawings/{d.id}/{d.filename}"
    import io
    storage.put(key, io.BytesIO(data))
    d.storage_key = key
    db.commit()
    return _drawing_out(d)


@app.get("/api/drawings/{drawing_id}")
def get_drawing(drawing_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _drawing(db, user, drawing_id)
    return {**_drawing_out(d), "jobs": [_job_out(j) for j in sorted(d.jobs, key=lambda j: j.created_at, reverse=True)]}


@app.get("/api/drawings/{drawing_id}/file")
def drawing_file(drawing_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _drawing(db, user, drawing_id)
    return FileResponse(storage.path(d.storage_key), media_type="application/pdf", filename=d.filename)


@app.delete("/api/drawings/{drawing_id}")
def delete_drawing(drawing_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _drawing(db, user, drawing_id)
    storage.delete_prefix(f"results/{d.id}"); storage.delete_prefix(f"drawings/{d.id}")
    db.delete(d); db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- analysis jobs
@app.post("/api/drawings/{drawing_id}/analyze")
def analyze(drawing_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _drawing(db, user, drawing_id)
    j = AnalysisJob(drawing_id=d.id, status="QUEUED", stage="QUEUED", progress=0.0)
    db.add(j); db.commit()
    jobs.submit(j.id)
    return _job_out(j)


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _job_out(_job(db, user, job_id))


def _proposals(db: Session, user: User, anchors: list, pipes: list, geom: list) -> list[dict]:
    """What this account's earlier corrections would say about the cases this reading could not settle.

    Proposals, never decisions. A lesson may speak only where the engine itself called the case ambiguous and
    only when the answer is among the candidates the drawing offers; accepting one is a correction a person
    makes, recorded like any other, so the takeoff never moves on a lesson alone.
    """
    open_cases = [a for a in anchors if a["state"] == "AMBIGUOUS_PIPE_ATTACHMENT"]
    if not open_cases:
        return []
    mine = (db.query(Correction).join(Drawing, Correction.drawing_id == Drawing.id)
            .join(Project, Drawing.project_id == Project.id)
            .filter(Project.owner_id == user.id, Correction.undone == False).all())  # noqa: E712
    taught = lessons([_correction_out(c) for c in mine])
    if not taught:
        return []
    fam_of = {}
    for p in pipes:
        fam_of[(p.get("identity") or "").replace("|DN", "-").upper()] = p.get("family", "")
    cases = []
    for a in open_cases:
        name = (a.get("designation") or "").upper()
        cands = _candidates_of(a, geom) or [name]
        cases.append({"id": a["anchor_id"], "designation": a.get("designation"),
                      "situation": situation(**_case_shape(a, fam_of.get(name, "")), candidates=cands),
                      "candidates": cands})
    return settle(cases, taught)


def _candidates_of(anchor: dict, geom: list) -> list[str]:
    """The answers the drawing itself puts forward for an unresolved case.

    An ambiguous anchor points at geometry the reading could not give to one identity, and that geometry carries
    the identities that were still in play. Those are the candidates - not a list of every designation on the
    sheet, and not the anchor's own name, which would let a lesson only ever agree with the reading.
    """
    touched = {(c.get("pid"), c.get("seg_index")) for c in (anchor.get("contacts") or [])}
    if not touched:
        return []
    out: set[str] = set()
    for g in geom:
        if g.get("state") != "AMBIGUOUS":
            continue
        if (g.get("pid"), g.get("seg")) not in touched:
            continue
        for c in g.get("candidates") or []:
            out.add(str(c).replace("|DN", "-").upper())
    return sorted(out)


def _case_shape(anchor: dict, family: str) -> dict:
    """Everything about an unresolved case that a later reading could recognise it by, read off the anchor.

    The leader family is how this drawing draws the line that reached the label; the counts are the local shape
    of the junction - label rows in the block, compatible groups at the leader end, pieces of geometry actually
    touched. All of it comes from the reading, none of it from the browser.
    """
    ev = anchor.get("evidence") or {}
    return {"family": family, "reason": anchor.get("reason", ""),
            "designation": anchor.get("designation") or "",
            "leader_family": ev.get("leader_family") or "",
            "n_rows": ev.get("n_rows"), "n_groups": ev.get("n_groups"),
            "n_contacts": len(anchor.get("contacts") or [])}


def _situation_of(db: Session, user: User, job_id: str | None, designation: str | None) -> dict:
    """The case a correction was made in, taken from the reading rather than from the browser.

    The pen the run was drawn with and the reason the engine gave are what make this case what it is, and both
    are in the result. Where they cannot be read the situation stays empty, which means the correction applies
    to this drawing and teaches nothing - the honest outcome when we cannot say what the case was.
    """
    if not job_id or not designation:
        return {}
    try:
        j = _job(db, user, job_id)
        rd = _result_dir(j)
        pipes = _load(rd, "physical-pipes.json")["physical_pipes"]
        anchors = _load(rd, "pipe-code-anchors.json")["anchors"]
        geom = _load(rd, "pipe-geometry-inventory.json")["primitives"]
    except Exception:
        return {}
    want = designation.upper()
    family = next((p.get("family", "") for p in pipes
                   if (p.get("identity") or "").replace("|DN", "-").upper() == want), "")
    case = next((a for a in anchors
                 if (a.get("designation") or "").upper() in (want, want.rsplit("-", 1)[0])
                 and a.get("state") != "VERIFIED_PIPE_ATTACHMENT"), None)
    if case is None:
        # nothing in the reading was unresolved for this designation: the correction is about this drawing only
        return {}
    cands = _candidates_of(case, geom) or [want]
    return situation(**_case_shape(case, family), candidates=cands)


def _is_our_proposal(db: Session, user: User, job_id: str | None, sit: dict) -> bool:
    """Whether this fingerprint is one this reading actually put forward, rather than one a caller made up.

    Accepting a proposal is the only way a situation may arrive from outside, so it is checked against the
    proposals this job offers right now, computed here rather than trusted from the request.
    """
    if not job_id or not isinstance(sit, dict):
        return False
    try:
        j = _job(db, user, job_id)
        rd = _result_dir(j)
        anchors = _load(rd, "pipe-code-anchors.json")["anchors"]
        pipes = _load(rd, "physical-pipes.json")["physical_pipes"]
        geom = _load(rd, "pipe-geometry-inventory.json")["primitives"]
    except Exception:
        return False
    want = {k: sit.get(k) for k in KEYS}
    return any(p.get("situation") == want for p in _proposals(db, user, anchors, pipes, geom))


class CorrectionIn(BaseModel):
    kind: str
    designation: str | None = None
    page: int = 0
    payload: dict = {}
    situation: dict = {}
    note: str | None = None
    job_id: str | None = None


def _correction_out(c: Correction) -> dict:
    return {"id": c.id, "drawing_id": c.drawing_id, "job_id": c.job_id, "page": c.page, "kind": c.kind,
            "designation": c.designation, "payload": c.payload, "situation": c.situation, "note": c.note,
            "undone": c.undone, "created_at": c.created_at.isoformat()}


@app.get("/api/drawings/{drawing_id}/corrections")
def list_corrections(drawing_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _drawing(db, user, drawing_id)
    rows = db.query(Correction).filter(Correction.drawing_id == drawing_id).order_by(Correction.created_at).all()
    return [_correction_out(c) for c in rows]


@app.post("/api/drawings/{drawing_id}/corrections")
def add_correction(drawing_id: str, body: CorrectionIn, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    _drawing(db, user, drawing_id)
    if body.kind not in CORRECTION_KINDS:
        raise HTTPException(400, f"Okänd rättelsetyp: {body.kind}")
    # The situation always comes from the reading, never from the caller: what a lesson may be shown to apply to
    # is a fact about the drawing, and a caller who could supply one could forge a fingerprint, post it twice and
    # have it settle real cases on someone else's later drawing. The only situation that may arrive from outside
    # is one this server itself put forward, and it is taken only when it matches a live proposal exactly.
    sit = _situation_of(db, user, body.job_id, body.designation)
    if not sit and body.situation:
        sit = body.situation if _is_our_proposal(db, user, body.job_id, body.situation) else {}
    c = Correction(drawing_id=drawing_id, job_id=body.job_id, user_id=user.id, page=body.page, kind=body.kind,
                   designation=body.designation, payload=body.payload, situation=sit, note=body.note)
    db.add(c); db.commit()
    return _correction_out(c)


@app.delete("/api/drawings/{drawing_id}/corrections/{correction_id}")
def undo_correction(drawing_id: str, correction_id: str, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    _drawing(db, user, drawing_id)
    c = db.get(Correction, correction_id)
    if c is None or c.drawing_id != drawing_id:
        raise HTTPException(404, "Rättelsen finns inte")
    # kept rather than deleted: what a person changed and then changed back is itself worth having
    c.undone = True
    db.commit()
    return _correction_out(c)


@app.get("/api/lessons")
def my_lessons(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """What this account's corrections have taught, and how often each answer was given.

    A lesson never measures anything on its own; it can only settle a case the engine already called ambiguous,
    and only where the pen, the reason and the shape of the name are the same.
    """
    mine = (db.query(Correction).join(Drawing, Correction.drawing_id == Drawing.id)
            .join(Project, Drawing.project_id == Project.id).filter(Project.owner_id == user.id).all())
    return {"lessons": lessons([_correction_out(c) for c in mine]), "corrections": len(mine)}


@app.get("/api/jobs/{job_id}/film")
def job_film(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """What each stage of the reading found, as far as it has got. Available while the job is still running."""
    j = _job(db, user, job_id)
    if not j.result_key:
        return {"frames": []}
    path = os.path.join(storage.path(j.result_key), "film.json")
    if not os.path.exists(path):
        return {"frames": []}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"frames": []}          # a frame caught mid-write; the next poll gets it


def _result_dir(j: AnalysisJob) -> str:
    if j.status != "COMPLETED" or not j.result_key:
        raise HTTPException(409, "Analysen är inte klar")
    return storage.path(j.result_key)


ARTIFACTS = ["drawing-profile.json", "drawing-profile-report.md", "raw-vector-inventory.json", "cad-layer-map.json", "vector-designations.json",
             "designation-overlay.pdf", "leader-forensics.json", "leader-family-report.json", "pipe-code-anchors.json",
             "endpoint-pipe-attachment-overlay.pdf", "pipe-representation-families.json", "pipe-geometry-inventory.json", "declined-geometry.json", "pipe-topology.json",
             "physical-pipes.json", "quantities.json", "unresolved-issues.json", "evidence-graph.json", "reconciliation.json",
             "route-crosscheck.json", "reading-review.json", "determinism.json",
             "contamination-report.json", "performance-report.json", "production-overlay.pdf", "topology-overlay.pdf", "ambiguous-overlay.pdf",
             "unsupported-style-overlay.pdf", "analysis-report.md", "freeze-manifest.json", "summary.json"]


def _load(rd: str, name: str):
    p = os.path.join(rd, name)
    if not os.path.exists(p):
        raise HTTPException(404, f"Artefakten saknas: {name}")
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


@app.get("/api/jobs/{job_id}/result")
def job_result(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    j = _job(db, user, job_id)
    rd = _result_dir(j)
    quantities = _load(rd, "quantities.json")
    pipes = _load(rd, "physical-pipes.json")["physical_pipes"]
    issues = _load(rd, "unresolved-issues.json")["issues"]
    prof = _load(rd, "drawing-profile.json")
    rec = _load(rd, "reconciliation.json")
    perf = _load(rd, "performance-report.json")
    summary = _load(rd, "summary.json")
    anchors = _load(rd, "pipe-code-anchors.json")["anchors"]
    des = _load(rd, "vector-designations.json")["designations"]
    leaders = _load(rd, "leader-forensics.json")["leaders"]
    geom = _load(rd, "pipe-geometry-inventory.json")["primitives"]
    declined = _load_optional(rd, "declined-geometry.json") or {"families": [], "totals": {}, "drawn_twice": {}}
    unowned = [g for g in geom if g["state"] == "UNOWNED"]
    ambiguous = [g for g in geom if g["state"] == "AMBIGUOUS"]
    hatched = [g for g in geom if g["state"] == "CONFIRMED" and g.get("in_hatch")]
    mpp = quantities["scale"].get("meters_per_pdf_point")
    page = prof["page_structure"]
    # what a person changed is layered over the reading, never into it: the engine's own figure stays on every row
    corr = [_correction_out(c) for c in
            db.query(Correction).filter(Correction.drawing_id == j.drawing_id, Correction.undone == False).all()]  # noqa: E712
    layered = apply_corrections(quantities["rows"], corr, mpp)
    rows = layered["quantities"] if corr else quantities["rows"]
    return {
        "job": _job_out(j), "page": page, "input": prof.get("input"), "scale": quantities["scale"], "quantities": rows, "totals": quantities["totals"],
        "corrections": corr,
        "corrections_applied": layered["applied"] if corr else [],
        "corrected_total_m": layered["corrected_total_m"] if corr else None,
        "pipes": [{k: v for k, v in p.items() if k not in ("source_segments",)} for p in pipes],
        # in_wall: the mark sits inside a hatched area, and pipe length in a wall is already outside the
        # horizontal quantity - so a mark drawn there points at something the takeoff does not count.
        # names_a_pipe: false for a component tag, whose leader reaches a floor drain or a mixer, not a run.
        "designations": [{"id": d["did"], "text": d["text"], "dn": d["dn"], "bbox": d["bbox"], "source": d["source"],
                          "in_wall": d.get("in_wall", False), "names_a_pipe": d.get("names_a_pipe", True)} for d in des],
        "leaders": [{"id": l["lid"], "points": l["points"], "family": l["family"], "in_wall": l.get("in_wall", False)} for l in leaders],
        "anchors": [{"id": a["anchor_id"], "designation": a["designation"], "dn": a["dn"], "state": a["state"], "reason": a["reason"],
                     "endpoint": a["leader_endpoint"], "in_wall": a.get("in_wall", False),
                     "names_a_pipe": a.get("names_a_pipe", True)} for a in anchors],
        "ambiguous_geometry": [{"x0": g["x0"], "y0": g["y0"], "x1": g["x1"], "y1": g["y1"], "candidates": g["candidates"], "reason": g["reason"]} for g in ambiguous],
        "unowned_geometry": [{"x0": g["x0"], "y0": g["y0"], "x1": g["x1"], "y1": g["y1"], "family": g["family"]} for g in unowned],
        "hatched_geometry": [{"x0": g["x0"], "y0": g["y0"], "x1": g["x1"], "y1": g["y1"], "identity": g["identity"]} for g in hatched],
        # Ink the reading looked at and decided was not pipe. Without it a declined wall and a missed run look
        # the same on the sheet - both are simply grey - and the reader has no way to tell which one they see.
        "declined_geometry": declined,
        "issues": issues,
        "proposals": _proposals(db, user, anchors, pipes, geom),
        "build": _build_stamp(),
        "coverage": {
            "designations": len(des), "with_dn": sum(1 for d in des if d["dn"] is not None), "leaders": len(leaders),
            "verified_attachments": sum(1 for a in anchors if a["state"] == "VERIFIED_PIPE_ATTACHMENT"),
            "ambiguous_attachments": sum(1 for a in anchors if a["state"] == "AMBIGUOUS_PIPE_ATTACHMENT"),
            "no_attachments": sum(1 for a in anchors if a["state"] == "NO_PIPE_ATTACHMENT"),
            "physical_pipes": len(pipes),
            "unowned_m": round(rec["unowned_pt"] * mpp, 2) if mpp else None, "ambiguous_m": quantities["totals"]["ambiguous_m"],
            "unsupported_families": len(prof["unknown_structure"]["unsupported_families"]),
            "reconciliation": rec["state"],
            # Determinism is a property of the engine, checked in the test suite on every change. Re-running
            # every production analysis twice to check it again would double what a reader waits for, so it is
            # off unless asked for - and that is said here rather than left as an empty field that reads as a
            # failed check.
            "determinism": summary.get("determinism") or "NOT_RUN_FOR_THIS_JOB",
            "contamination": summary.get("contamination"),
            # whether another machine was consulted about this reading, and what it did - a number on screen is
            # only checkable if you can tell what made it
            "second_reader": summary.get("second_reader") or {"consulted": False},
        },
        "performance": perf,
        "review": _load_optional(rd, "review-findings.json"),
        "crosscheck": _load_optional(rd, "route-crosscheck.json"),
        "reading_review": _load_optional(rd, "reading-review.json"),
        # the drawing's own designation list, as the reading understood it: which codes it took for systems,
        # which for fittings, which for materials, and whether the page itself showed that or its own grouping did
        "legend": _load_optional(rd, "drawing-legend.json") or {"n_entries": 0, "entries": []},
    }


def _load_optional(result_dir: str, name: str):
    path = os.path.join(result_dir, name)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


@app.get("/api/jobs/{job_id}/artifacts")
def list_artifacts(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    j = _job(db, user, job_id)
    rd = _result_dir(j)
    return [{"name": n, "size": os.path.getsize(os.path.join(rd, n))} for n in ARTIFACTS if os.path.exists(os.path.join(rd, n))]


@app.get("/api/jobs/{job_id}/artifacts/{name}")
def get_artifact(job_id: str, name: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    j = _job(db, user, job_id)
    rd = _result_dir(j)
    if name not in ARTIFACTS:
        raise HTTPException(404, "Okänd artefakt")
    p = os.path.join(rd, name)
    if not os.path.exists(p):
        raise HTTPException(404, "Artefakten saknas")
    media = "application/pdf" if name.endswith(".pdf") else ("text/markdown" if name.endswith(".md") else "application/json")
    return FileResponse(p, media_type=media, filename=name)


@app.get("/api/jobs/{job_id}/judge")
def job_judge(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """What, out of everything the reading and its reviewers found, should actually change.

    The reviewers state disagreements and stop; the judge decides. It implements only answers the drawing itself
    puts forward, never touches a measurement the reading confirmed, writes anything it does implement as a
    correction that can be undone, and says plainly where the evidence does not settle a case. It calls no model:
    the same reading judged twice gives the same verdicts.
    """
    from vvs_engine.agent.model import DrawingModel
    from vvs_engine.review.judge import judge as run_judge

    j = _job(db, user, job_id)
    if j.status != "COMPLETED":
        raise HTTPException(409, "analysen är inte klar")
    rd = _result_dir(j)
    anchors = _load(rd, "pipe-code-anchors.json")["anchors"]
    pipes = _load(rd, "physical-pipes.json")["physical_pipes"]
    geom = _load(rd, "pipe-geometry-inventory.json")["primitives"]
    return run_judge(DrawingModel(rd), proposals=_proposals(db, user, anchors, pipes, geom))


class AgentAsk(BaseModel):
    question: str
    page: int | None = None
    pipe_ids: list[str] | None = None
    bbox: list[float] | None = None
    history: list[dict] | None = None


@app.get("/api/agent/tools")
def agent_tools(user: User = Depends(current_user)):
    """The contract, so the interface can show what the agent is actually able to do."""
    from vvs_engine.agent import tools as T
    return {"tools": [{"name": t["name"], "description": t["description"],
                       "parameters": sorted(t["parameters"]["properties"])} for t in T.TOOLS.values()]}


@app.post("/api/jobs/{job_id}/agent")
def agent_ask(job_id: str, body: AgentAsk, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Ask the agent about this reading.

    The model chooses which questions to put to the drawing; the engine answers them. Every number in the reply
    came out of a tool call over the artifacts the measurement wrote, so the chat and the takeoff table cannot
    disagree, and the reply carries the ids it rests on so the claim can be pointed at on the sheet.
    """
    from app.agent import run_turn
    from app.jobs import second_reader_state
    from vvs_engine.agent.model import DrawingModel

    j = _job(db, user, job_id)
    if j.status != "COMPLETED":
        raise HTTPException(409, "analysen är inte klar")
    on, why = second_reader_state()
    if not on:
        raise HTTPException(503, f"ingen modell är konfigurerad för agenten: {why}")
    try:
        from tools.astra_transport import agent_transport
    except Exception as e:                                      # noqa: BLE001
        raise HTTPException(503, f"agenttransporten kunde inte laddas: {type(e).__name__}")
    model = DrawingModel(_result_dir(j))
    sel = {"pipe_ids": body.pipe_ids or [], "bbox": body.bbox, "page": body.page}
    try:
        out = run_turn(model, agent_transport(), body.question, selection=sel, history=body.history or [])
    except Exception as e:                                      # noqa: BLE001
        raise HTTPException(502, f"agenten kunde inte nå modellen: {type(e).__name__}: {str(e)[:160]}")
    return out


@app.post("/api/jobs/{job_id}/vision")
def vision_check(job_id: str, page: int = 0, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """A second opinion by eye on a reading that is already finished.

    Asked for, never automatic: it costs a call and a wait, and the reading does not depend on it. What comes
    back are observations to check in the vector data - designations that look visible but were not read, drawn
    pipe no overlay follows, an overlay running along something that is not a pipe. None of it can move a metre;
    there is no path from a vision finding to a quantity, by construction.
    """
    j = _job(db, user, job_id)
    if j.status != "COMPLETED":
        raise HTTPException(409, "Analysen är inte klar")
    try:
        import pymupdf
        from vvs_engine.pdf.extract import extract_document
        from vvs_engine.pipeline import analyze_page
        from vvs_engine.review import vision as vz
        from tools.astra_transport import vision_transport
    except Exception as e:
        raise HTTPException(503, f"Vision är inte tillgänglig i den här installationen: {type(e).__name__}")
    path = storage.path(j.drawing.storage_key)
    doc = extract_document(path)
    if page < 0 or page >= len(doc.pages):
        raise HTTPException(404, "Sidan finns inte")
    pa = analyze_page(doc.pages[page])
    out = vz.look(pa, pymupdf.open(path), ask=vision_transport())
    return out.as_dict()


@app.get("/api/jobs/{job_id}/why/{pipe_id}")
def why(job_id: str, pipe_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    j = _job(db, user, job_id)
    rd = _result_dir(j)
    pipes = _load(rd, "physical-pipes.json")["physical_pipes"]
    p = next((x for x in pipes if x["physical_pipe_id"] == pipe_id), None)
    if p is None:
        raise HTTPException(404, "Okänt rör")
    anchors = {a["anchor_id"]: a for a in _load(rd, "pipe-code-anchors.json")["anchors"]}
    des = {d["did"]: d for d in _load(rd, "vector-designations.json")["designations"]}
    leaders = {l["lid"]: l for l in _load(rd, "leader-forensics.json")["leaders"]}
    scale = _load(rd, "quantities.json")["scale"]
    chain = []
    for aid in p["supporting_anchors"]:
        a = anchors.get(aid)
        if not a:
            continue
        chain.append({"designation": des.get(a["designation_id"]), "dn": a["dn"], "leader": leaders.get(a["leader_id"]), "attachment": a})
    return {"pipe": p, "evidence_chain": chain, "scale": scale}


@app.get("/api/jobs/{job_id}/export/{fmt}")
def export(job_id: str, fmt: str, floor_height: float | None = None, include_hatched: bool = False,
           riser_source: str = "labels",
           user: User = Depends(current_user), db: Session = Depends(get_db)):
    j = _job(db, user, job_id)
    rd = _result_dir(j)
    base = os.path.splitext(j.drawing.filename)[0]
    fh = floor_height if floor_height and floor_height > 0 else None
    # An export carries the reading as it stands, corrections included. Leaving them out would hand back the
    # figure the reader already rejected on screen, in the file they price from.
    quantities = _load(rd, "quantities.json")
    corr = [_correction_out(c) for c in
            db.query(Correction).filter(Correction.drawing_id == j.drawing_id, Correction.undone == False).all()]  # noqa: E712
    rows = (apply_corrections(quantities["rows"], corr, quantities["scale"].get("meters_per_pdf_point"))["quantities"]
            if corr else quantities["rows"])
    if fmt == "xlsx":
        return Response(exports.to_xlsx(rd, fh, include_hatched, rows, riser_source), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{base}-mangder.xlsx"'})
    if fmt == "csv":
        return Response(exports.to_csv(rd, fh, include_hatched, rows, riser_source).encode("utf-8-sig"), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{base}-mangder.csv"'})
    if fmt == "json":
        return Response(json.dumps({**quantities, "rows": rows, "corrections_applied": len(corr)},
                                   ensure_ascii=False, indent=1).encode("utf-8"),
                        media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{base}-quantities.json"'})
    if fmt == "report":
        return FileResponse(os.path.join(rd, "analysis-report.md"), media_type="text/markdown", filename=f"{base}-analysrapport.md")
    if fmt == "pdf":
        return FileResponse(os.path.join(rd, "production-overlay.pdf"), media_type="application/pdf", filename=f"{base}-markerad.pdf")
    raise HTTPException(404, "Okänt exportformat")


# ---------------------------------------------------------------- built frontend (single-container deployment)
_STATIC = settings.static_root
if os.path.isfile(os.path.join(_STATIC, "index.html")):
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Okänd API-väg")
        candidate = os.path.normpath(os.path.join(_STATIC, full_path))
        if full_path and candidate.startswith(_STATIC) and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_STATIC, "index.html"))
