"""Background analysis jobs: a thread-pool worker executes the engine; stages reflect real pipeline stages."""
from __future__ import annotations

import datetime as dt
import os
import time
import json
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor

from .config import settings
from .db import AnalysisJob, Drawing, SessionLocal
from .storage import storage

ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "engine"))
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

STAGE_ORDER = ["QUEUED", "READING_PDF", "DISCOVERING_DRAWING_GRAMMAR", "EXTRACTING_VECTORS", "RECONSTRUCTING_TEXT",
               "RESOLVING_UNREADABLE_TEXT", "READING_DESIGNATIONS",
               "FINDING_LEADERS", "RESOLVING_PIPE_REPRESENTATION", "ATTACHING_PIPES", "BUILDING_TOPOLOGY", "BUILDING_PHYSICAL_PIPES",
               "MEASURING", "REVIEWING", "GENERATING_OVERLAYS", "COMPLETED"]

_executor = ThreadPoolExecutor(max_workers=max(1, settings.worker_threads))
_lock = threading.Lock()


def _set(job_id: str, **fields) -> None:
    with SessionLocal() as db:
        job = db.get(AnalysisJob, job_id)
        if job is None:
            return
        for k, v in fields.items():
            setattr(job, k, v)
        db.commit()


def _progress_cb(job_id: str):
    def cb(stage: str):
        # a stage may carry a detail after its name ("RESOLVING_UNREADABLE_TEXT ruta 3/7"); the name is what
        # places it in the order, and without this split a slow step reported itself as no progress at all
        name = stage.split(" ")[0]
        idx = STAGE_ORDER.index(name) if name in STAGE_ORDER else 0
        _set(job_id, stage=stage, progress=round(idx / (len(STAGE_ORDER) - 1), 3), status="RUNNING" if name != "COMPLETED" else "COMPLETED")
    return cb


def _film_sink(out_dir: str):
    """Write each stage's frame as it lands, so the browser can watch the reading happen.

    The whole film is rewritten every frame: a frame is a few hundred shapes, the sheet has a dozen stages, and
    a single replace is cheaper to reason about than an append the reader might catch half-written.
    """
    frames: list[dict] = []
    path = os.path.join(out_dir, "film.json")

    def sink(stage: str, payload: dict) -> None:
        frames.append({"stage": stage, "at": round(time.time(), 2), **payload})
        os.makedirs(out_dir, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"frames": frames}, fh, ensure_ascii=False)
        os.replace(tmp, path)

    return sink


def _second_reader():
    """The second reader, if this installation is configured for one and can actually reach it.

    Returns None otherwise, which is what the engine expects: without a transport nothing is asked, the reading
    is deterministic and runs with no network at all. A configuration that asks for a second reader and cannot
    reach one says so in the log rather than failing an analysis over it - the takeoff does not depend on it.
    """
    on, why = second_reader_state()
    if not on:
        return None
    try:
        from tools.astra_transport import transport
    except Exception:
        return None
    return transport()


def second_reader_state() -> tuple[bool, str]:
    """Whether a model may settle a case *during the measurement*, and the reason.

    This is not the same question as whether the agent may answer a question about a finished reading. The agent
    only reads, and turning this off is a promise about the takeoff, not a gag order.

    Unset means yes where a key is present. Explicitly on means yes wherever the transport can reach the model at
    all, which includes a machine behind a proxy that attaches the credential and holds no key itself.
    """
    if settings.second_reader is False:
        return False, "avstängd i den här installationen (VVS_SECOND_READER=false)"
    try:
        from tools.astra_transport import available
    except Exception as e:                                      # noqa: BLE001
        return False, f"transporten kunde inte laddas: {type(e).__name__}"
    has_key = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    if settings.second_reader is None:
        return (True, "OPENAI_API_KEY finns i miljön") if has_key else \
            (False, "ingen OPENAI_API_KEY i miljön; sätt den, eller VVS_SECOND_READER=true bakom en proxy")
    ok, why = available()
    return (ok, why) if ok else (False, f"påslagen men inte nåbar: {why}")


# A pen has to be stated this often, and this consistently, before another sheet may lean on it. One stray
# label on one drawing is not an office's habit; two hundred agreeing ones are.
PROJECT_MIN_TIMES = 3
PROJECT_MIN_SHARE = 0.8


def project_system_families(db, drawing) -> dict[str, str]:
    """What the rest of this project's drawings have already stated: drawn family -> system.

    A set of drawings is one office drawing one building. Where a sheet labels a run on its own, it says which
    pen that office uses for that system - and on a sheet whose bundles are symmetric, that is the fixpoint that
    settles them. It is a fact read off other drawings, never something a person was asked for.
    """
    from collections import defaultdict

    from vvs_engine.pipeline import pen_key
    rows = (db.query(AnalysisJob, Drawing)
            .join(Drawing, AnalysisJob.drawing_id == Drawing.id)
            .filter(Drawing.project_id == drawing.project_id, AnalysisJob.status == "COMPLETED",
                    AnalysisJob.drawing_id != drawing.id, AnalysisJob.result_key.isnot(None))
            .all())
    tally: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for job, _ in rows:
        path = os.path.join(storage.path(job.result_key), "drawn-system-families.json")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                stated = json.load(fh).get("stated") or []
        except Exception:                                       # noqa: BLE001
            continue
        for st in stated:
            fam, sysname, n = st.get("family"), st.get("system"), int(st.get("times") or 0)
            if fam and sysname and n > 0:
                tally[pen_key(fam)][sysname] += n
    out: dict[str, str] = {}
    for fam, systems in tally.items():
        total = sum(systems.values())
        best, n = max(systems.items(), key=lambda kv: kv[1])
        if n >= PROJECT_MIN_TIMES and n >= PROJECT_MIN_SHARE * total:
            out[fam] = best
    return out


def project_legend(db, drawing):
    """The designation list the rest of this project already read, for a drawing that carries none.

    A project is one office's set for one building, and it writes its vocabulary once. Uploading the plan sheets
    without the sheet that carries the list left every one of them with no vocabulary at all - so every label
    passed as possibly a pipe, and the review list filled with door marks. The list is a fact read off the other
    drawings' own artifacts, never something a person was asked for.

    Only a list a drawing carried itself counts, so a borrowed list is never re-lent; and where two drawings
    disagree about what a code is, the code is dropped rather than settled by whichever was read first.
    """
    from collections import defaultdict

    from vvs_engine.semantics.legend import DrawingLegend, LegendEntry
    rows = (db.query(AnalysisJob, Drawing)
            .join(Drawing, AnalysisJob.drawing_id == Drawing.id)
            .filter(Drawing.project_id == drawing.project_id, AnalysisJob.status == "COMPLETED",
                    AnalysisJob.drawing_id != drawing.id, AnalysisJob.result_key.isnot(None))
            .all())
    seen: dict[str, dict] = {}
    roles: dict[str, set] = defaultdict(set)
    for job, _ in rows:
        path = os.path.join(storage.path(job.result_key), "drawing-legend.json")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except Exception:                                       # noqa: BLE001
            continue
        for e in doc.get("entries") or []:
            code = str(e.get("code") or "").strip()
            if not code or e.get("role_from") == "other_sheet":
                continue
            roles[code.upper()].add(e.get("role"))
            seen.setdefault(code.upper(), e)
    entries = [LegendEntry(code=e["code"], description=e.get("description") or "", heading=e.get("heading") or "",
                           bbox=(0.0, 0.0, 0.0, 0.0), role=e.get("role") or "material", role_from="other_sheet")
               for c, e in sorted(seen.items()) if len(roles[c]) == 1]
    return DrawingLegend(own=False, entries=entries) if entries else None


def run_job(job_id: str) -> None:
    from vvs_engine.cli import analyze_pdf
    from vvs_engine.pdf.extract import UnsupportedInputError
    with SessionLocal() as db:
        job = db.get(AnalysisJob, job_id)
        if job is None:
            return
        drawing = db.get(Drawing, job.drawing_id)
        pdf_path = storage.path(drawing.storage_key)
        result_key = f"results/{drawing.id}/{job.id}"
        known = project_system_families(db, drawing)
        vocab = project_legend(db, drawing)
        job.status = "RUNNING"; job.started_at = dt.datetime.now(dt.timezone.utc); job.result_key = result_key
        db.commit()
    out_dir = storage.path(result_key)
    try:
        summary = analyze_pdf(pdf_path, out_dir, name=os.path.splitext(drawing.filename)[0],
                              deadline_s=settings.analysis_deadline_s, determinism=settings.run_determinism,
                              contamination=True, progress=_progress_cb(job_id),
                              review=settings.run_review, review_ocr=settings.review_ocr,
                              ocr_assist=settings.ocr_assist, film_sink=_film_sink(out_dir),
                              second_reader=_second_reader(), known_families=known, known_legend=vocab)
        # which readers this installation actually had available, and by what name - a reading that quietly used a
        # model, or quietly did without one, is not a reading anyone can check
        on, why = second_reader_state()
        sr = dict(summary["summary"].get("second_reader") or {})
        sr.update({"enabled": on, "why": why,
                   "model": os.environ.get("VVS_SECOND_READER_MODEL", "gpt-6-astra") if on else None})
        _set(job_id, status="COMPLETED", stage="COMPLETED", progress=1.0, finished_at=dt.datetime.now(dt.timezone.utc),
             summary={"total_seconds": summary["total_seconds"], **summary["summary"], "second_reader": sr})
    except UnsupportedInputError as e:
        # not a defect: the PDF carries no vector drawing, so there is nothing to read
        _set(job_id, status="FAILED", stage="FAILED", finished_at=dt.datetime.now(dt.timezone.utc),
             error="Ritningen är inte en vektor-PDF. Systemet läser ritningens egna vektorkoder och gissar aldrig "
                   "utifrån bildpunkter, så en skannad eller bildbaserad PDF kan inte mängdas. Ladda upp filen som "
                   f"vektor-PDF (exporterad från CAD, inte skannad). Klassificering: {e}")
    except Exception as e:  # noqa: BLE001
        _set(job_id, status="FAILED", stage="FAILED", error=f"{e}\n{traceback.format_exc()[-4000:]}", finished_at=dt.datetime.now(dt.timezone.utc))


def submit(job_id: str) -> None:
    _executor.submit(run_job, job_id)
