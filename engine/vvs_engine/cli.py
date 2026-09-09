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
from .semantics.legend import DrawingLegend, merged

CONFIG = {"contact_tolerance_pt": 0.6, "touch_tolerance_pt": 0.15, "unknown_glyph_threshold": 0.14, "grid": 32}


class AnalysisTookTooLong(Exception):
    """A reading that ran past its budget. Raised between pages, so what is reported is a refusal, not a guess."""


def analyze_pdf(pdf_path: str, out_dir: str, name: str | None = None, determinism: bool = True, contamination: bool = True,
                progress=None, pages: list[int] | None = None, review: bool = True, review_ocr: bool = True,
                film_sink=None,
                ocr_assist: bool = False, deadline_s: float | None = None, second_reader=None, known_families: dict | None = None,
                known_legend: DrawingLegend | None = None) -> dict:
    """deadline_s: a wall-clock budget for the whole document, checked between pages.

    A drawing set can carry a page dense enough that reading it takes longer than anyone will wait, and without a
    budget that page does not just delay itself - it holds the worker thread and everything queued behind it. The
    budget is checked between pages rather than inside one, so a single page that runs long still finishes; what
    it bounds is a document that would never end.

    known_legend: a designation list the rest of the project already wrote, for sheets that carry none of their
    own. The document's own sheets are the first source of it - see below - and this is what a project that spans
    several files can pass in besides.
    """
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
    # A set writes its designation list once and lets the rest of its sheets stand on it. So the list is read
    # from whatever sheet carries it and held for the whole document, and the sheets read before it turned up
    # are read again against it. Without that second look the same set is read one way at the front and another
    # way at the back, which is a difference nothing in the drawing asked for.
    vocab = known_legend
    saw: list[DrawingLegend | None] = []        # what each sheet was actually given, so a re-reading can match it

    def check_budget():
        if deadline_s is not None and time.perf_counter() - t_all > deadline_s and analyses:
            raise AnalysisTookTooLong(
                f"läsningen hann {len(analyses)} av {len(doc.pages)} sidor inom {deadline_s:.0f} s och avbröts; "
                f"en halv mängd är sämre än ingen, så inget delresultat sparas")

    def read(pg, vocab):
        return analyze_page(pg, progress, ocr_assist=ocr_assist,
                            film_sink=film_sink if pg.info.index == 0 else None,
                            second_reader=second_reader, known_families=known_families, known_legend=vocab)

    for pg in doc.pages:
        check_budget()
        saw.append(vocab)
        pa = read(pg, vocab)
        analyses.append(pa)
        if pa.legend.own and pa.legend.entries:
            vocab = merged(vocab, pa.legend)
    reread = 0
    n_final = len(vocab.entries) if vocab is not None else 0
    for i, pa in enumerate(analyses):
        if pa.legend.own and pa.legend.entries:
            continue                    # this sheet carries its own list and is not waiting on anybody else's
        if (len(saw[i].entries) if saw[i] is not None else 0) >= n_final:
            continue                    # it already saw everything the set turned out to have
        check_budget()
        saw[i] = vocab
        analyses[i] = read(doc.pages[i], vocab)
        reread += 1
    if progress:
        progress("GENERATING_OVERLAYS")
    t0 = time.perf_counter()
    overlays = write_overlays(pdf_path, analyses, out_dir)
    timings["overlays_ms"] = (time.perf_counter() - t0) * 1000
    rev = None
    if review:
        if progress:
            progress("REVIEWING")
        t0 = time.perf_counter()
        from .review import run_review
        rev = run_review(analyses[0], ocr=review_ocr,
                         progress=(lambda t: progress(f"REVIEWING {t}")) if progress else None)
        timings["review_ms"] = (time.perf_counter() - t0) * 1000
    # A second reader is asked only about cases the geometry already declared open, and only among candidates the
    # drawing itself offers - but it is still a machine outside this one, so a reading that consulted it is not
    # the same kind of answer as one that did not, and the determinism check is meaningless over it.
    consulted = any(a.second_reader and a.second_reader.get("asked") for a in analyses)
    det = run_determinism(doc, 0, analyses[0], known_families=known_families, known_legend=saw[0]) \
        if determinism and not consulted else None
    cont = scan_source(os.path.dirname(os.path.abspath(__file__))) if contamination else None
    t0 = time.perf_counter()
    timings["total_s"] = time.perf_counter() - t_all
    files = write_all(pdf_path, doc, analyses, out_dir, name, timings, det, cont, overlays, CONFIG, rev)
    timings["artifacts_ms"] = (time.perf_counter() - t0) * 1000
    summary = {"name": name, "pages": len(doc.pages), "summary": summarize(analyses[0]),
               "determinism": det["state"] if det else ("NOT_APPLICABLE_A_SECOND_READER_WAS_CONSULTED" if consulted else None),
               "second_reader": {"consulted": consulted,
                                 "asked": sum((a.second_reader or {}).get("asked", 0) for a in analyses),
                                 "settled": sum((a.second_reader or {}).get("settled", 0) for a in analyses),
                                 "refused": sum((a.second_reader or {}).get("refused", 0) for a in analyses)},
               "legend": {"codes": len(vocab.entries) if vocab else 0,
                          "own_sheet": bool(analyses[0].legend.own and analyses[0].legend.entries),
                          "sheets_reread": reread},
               "contamination": cont["state"] if cont else None, "files": files, "total_seconds": round(timings["total_s"], 2),
               "input": getattr(doc.pages[0], "input_class", None), "skipped_pages": doc.skipped_pages,
               "review": {"state": rev["state"], "n_findings": rev["n_findings"], "agents": rev["agents"]} if rev else None,
               "ocr_assist": analyses[0].ocr_assist}
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
        pa = analyze_page(doc.pages[0], known_families=known_families)
        print(json.dumps(why_fn(pa, args.pipe_id), indent=1, default=str)); return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
