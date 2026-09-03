"""Command line interface: analyze a clean vector VVS PDF and write all artifacts."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from . import __version__
from .contamination import scan_source
from .determinism import run_determinism
from .output.artifacts import why as why_fn, write_all
from .output.overlays import write_overlays
from .pdf.extract import extract_document
from .pipeline import PageAnalysis, analyze_page, summarize

CONFIG = {"contact_tolerance_pt": 0.6, "touch_tolerance_pt": 0.15, "unknown_glyph_threshold": 0.14, "grid": 32}


def analyze_pdf(pdf_path: str, out_dir: str, name: str | None = None, determinism: bool = True, contamination: bool = True,
                progress=None, pages: list[int] | None = None) -> dict:
    t_all = time.perf_counter()
    name = name or os.path.splitext(os.path.basename(pdf_path))[0]
    os.makedirs(out_dir, exist_ok=True)
    timings: dict[str, float] = {}
    if progress:
        progress("READING_PDF")
    t0 = time.perf_counter()
    doc = extract_document(pdf_path, pages, progress=progress)
    timings["extract_ms"] = (time.perf_counter() - t0) * 1000
    analyses: list[PageAnalysis] = []
    for pg in doc.pages:
        analyses.append(analyze_page(pg, progress))
    if progress:
        progress("GENERATING_OVERLAYS")
    t0 = time.perf_counter()
    overlays = write_overlays(pdf_path, analyses, out_dir)
    timings["overlays_ms"] = (time.perf_counter() - t0) * 1000
    det = run_determinism(doc, 0, analyses[0]) if determinism else None
    cont = scan_source(os.path.dirname(os.path.abspath(__file__))) if contamination else None
    t0 = time.perf_counter()
    timings["total_s"] = time.perf_counter() - t_all
    files = write_all(pdf_path, doc, analyses, out_dir, name, timings, det, cont, overlays, CONFIG)
    timings["artifacts_ms"] = (time.perf_counter() - t0) * 1000
    summary = {"name": name, "pages": len(doc.pages), "summary": summarize(analyses[0]), "determinism": det["state"] if det else None,
               "contamination": cont["state"] if cont else None, "files": files, "total_seconds": round(timings["total_s"], 2),
               "input_mode": getattr(doc.pages[0], "input_mode", "vector"), "input": getattr(doc.pages[0], "input_class", None),
               "raster": getattr(doc.pages[0], "raster_report", None)}
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, default=str)
    if progress:
        progress("COMPLETED")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vvs-takeoff", description="Drawing-adaptive VVS pipe takeoff engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="analyze a clean vector VVS PDF")
    a.add_argument("pdf"); a.add_argument("--out", required=True); a.add_argument("--name")
    a.add_argument("--no-determinism", action="store_true"); a.add_argument("--no-contamination", action="store_true")
    w = sub.add_parser("why", help="evidence chain for a physical pipe id (re-analyzes the PDF)")
    w.add_argument("pdf"); w.add_argument("pipe_id")
    sub.add_parser("version")
    args = ap.parse_args(argv)
    if args.cmd == "version":
        print(__version__); return 0
    if args.cmd == "analyze":
        s = analyze_pdf(args.pdf, args.out, args.name, not args.no_determinism, not args.no_contamination, progress=lambda st: print(f"[{st}]", file=sys.stderr))
        print(json.dumps(s["summary"], indent=1, default=str)); return 0
    if args.cmd == "why":
        doc = extract_document(args.pdf)
        pa = analyze_page(doc.pages[0])
        print(json.dumps(why_fn(pa, args.pipe_id), indent=1, default=str)); return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
