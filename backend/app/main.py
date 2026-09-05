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
from vvs_engine.learning import lessons, situation
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
    build = (os.environ.get("VVS_BUILD") or os.environ.get("RAILWAY_GIT_COMMIT_SHA")
             or os.environ.get("SOURCE_COMMIT") or os.environ.get("GIT_COMMIT") or "")[:12]
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
        pipes = _load(rd, "physical-pipes.json")["pipes"]
        anchors = _load(rd, "pipe-code-anchors.json")["anchors"]
    except Exception:
        return {}
    want = designation.upper()
    family = next((p.get("family", "") for p in pipes
                   if (p.get("identity") or "").replace("|DN", "-").upper() == want), "")
    reason = next((a.get("reason", "") for a in anchors
                   if (a.get("designation") or "").upper() in (want, want.rsplit("-", 1)[0])
                   and a.get("state") != "VERIFIED_PIPE_ATTACHMENT"), "")
    return situation(family=family, reason=reason, designation=designation)


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
    sit = body.situation or {}
    if not all(sit.get(k) for k in ("family_style", "reason", "designation_shape")):
        sit = _situation_of(db, user, body.job_id, body.designation)
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
            .join(Project, Drawing.project_id == Project.id).filter(Project.user_id == user.id).all())
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
             "endpoint-pipe-attachment-overlay.pdf", "pipe-representation-families.json", "pipe-geometry-inventory.json", "pipe-topology.json",
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
        "designations": [{"id": d["did"], "text": d["text"], "dn": d["dn"], "bbox": d["bbox"], "source": d["source"]} for d in des],
        "leaders": [{"id": l["lid"], "points": l["points"], "family": l["family"]} for l in leaders],
        "anchors": [{"id": a["anchor_id"], "designation": a["designation"], "dn": a["dn"], "state": a["state"], "reason": a["reason"], "endpoint": a["leader_endpoint"]} for a in anchors],
        "ambiguous_geometry": [{"x0": g["x0"], "y0": g["y0"], "x1": g["x1"], "y1": g["y1"], "candidates": g["candidates"], "reason": g["reason"]} for g in ambiguous],
        "unowned_geometry": [{"x0": g["x0"], "y0": g["y0"], "x1": g["x1"], "y1": g["y1"], "family": g["family"]} for g in unowned],
        "hatched_geometry": [{"x0": g["x0"], "y0": g["y0"], "x1": g["x1"], "y1": g["y1"], "identity": g["identity"]} for g in hatched],
        "issues": issues,
        "build": _build_stamp(),
        "coverage": {
            "designations": len(des), "with_dn": sum(1 for d in des if d["dn"] is not None), "leaders": len(leaders),
            "verified_attachments": sum(1 for a in anchors if a["state"] == "VERIFIED_PIPE_ATTACHMENT"),
            "ambiguous_attachments": sum(1 for a in anchors if a["state"] == "AMBIGUOUS_PIPE_ATTACHMENT"),
            "no_attachments": sum(1 for a in anchors if a["state"] == "NO_PIPE_ATTACHMENT"),
            "physical_pipes": len(pipes),
            "unowned_m": round(rec["unowned_pt"] * mpp, 2) if mpp else None, "ambiguous_m": quantities["totals"]["ambiguous_m"],
            "unsupported_families": len(prof["unknown_structure"]["unsupported_families"]),
            "reconciliation": rec["state"], "determinism": summary.get("determinism"), "contamination": summary.get("contamination"),
        },
        "performance": perf,
        "review": _load_optional(rd, "review-findings.json"),
        "crosscheck": _load_optional(rd, "route-crosscheck.json"),
        "reading_review": _load_optional(rd, "reading-review.json"),
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
           user: User = Depends(current_user), db: Session = Depends(get_db)):
    j = _job(db, user, job_id)
    rd = _result_dir(j)
    base = os.path.splitext(j.drawing.filename)[0]
    fh = floor_height if floor_height and floor_height > 0 else None
    if fmt == "xlsx":
        return Response(exports.to_xlsx(rd, fh, include_hatched), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{base}-mangder.xlsx"'})
    if fmt == "csv":
        return Response(exports.to_csv(rd, fh, include_hatched).encode("utf-8-sig"), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{base}-mangder.csv"'})
    if fmt == "json":
        return FileResponse(os.path.join(rd, "quantities.json"), media_type="application/json", filename=f"{base}-quantities.json")
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
