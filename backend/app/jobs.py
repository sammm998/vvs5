"""Background analysis jobs: a thread-pool worker executes the engine; stages reflect real pipeline stages."""
from __future__ import annotations

import datetime as dt
import os
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

STAGE_ORDER = ["QUEUED", "READING_PDF", "DISCOVERING_DRAWING_GRAMMAR", "EXTRACTING_VECTORS", "RECONSTRUCTING_TEXT", "READING_DESIGNATIONS",
               "FINDING_LEADERS", "RESOLVING_PIPE_REPRESENTATION", "ATTACHING_PIPES", "BUILDING_TOPOLOGY", "BUILDING_PHYSICAL_PIPES",
               "MEASURING", "GENERATING_OVERLAYS", "COMPLETED"]

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
        idx = STAGE_ORDER.index(stage) if stage in STAGE_ORDER else 0
        _set(job_id, stage=stage, progress=round(idx / (len(STAGE_ORDER) - 1), 3), status="RUNNING" if stage != "COMPLETED" else "COMPLETED")
    return cb


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
        job.status = "RUNNING"; job.started_at = dt.datetime.now(dt.timezone.utc); job.result_key = result_key
        db.commit()
    out_dir = storage.path(result_key)
    try:
        summary = analyze_pdf(pdf_path, out_dir, name=os.path.splitext(drawing.filename)[0], determinism=settings.run_determinism,
                              contamination=True, progress=_progress_cb(job_id))
        _set(job_id, status="COMPLETED", stage="COMPLETED", progress=1.0, finished_at=dt.datetime.now(dt.timezone.utc),
             summary={"total_seconds": summary["total_seconds"], **summary["summary"]})
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
