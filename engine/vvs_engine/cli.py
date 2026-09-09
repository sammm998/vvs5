"""Command line interface: analyze a clean vector VVS PDF and write all artifacts."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

from . import __version__
from .contamination import scan_source
from .determinism import run_determinism
from .output.artifacts import why as why_fn, write_all
from .output.overlays import OverlayWriter
from .pdf.extract import extract_document
from .pipeline import PageAnalysis, analyze_page, prepare_page, reading_coverage, summarize
from .semantics.legend import DrawingLegend, merged

CONFIG = {"contact_tolerance_pt": 0.6, "touch_tolerance_pt": 0.15, "unknown_glyph_threshold": 0.14, "grid": 32}


class AnalysisTookTooLong(Exception):
    """A reading that ran past its budget. Raised between pages, so what is reported is a refusal, not a guess."""


VOCAB_HOLD = 2          # readings kept from the search for the list; past that, looking again is cheaper than keeping


def _vocabulary(doc, known_legend: DrawingLegend | None, progress, ocr_assist: bool, film_sink=None):
    """The set's designation list, and the sheet readings the search for it already paid for.

    Sheets are looked at in order and the search stops at the first that carries a list, which on almost every
    set is the front sheet. What it looked at is handed back so the reading proper does not do that work twice -
    but only the first couple of them, because holding a sheet's reading costs more than reading it again.
    """
    from .film import Film
    vocab = known_legend
    held: dict[int, Any] = {}
    for i in range(len(doc.pages)):
        # The search for the list reads the front half of a sheet, and that is the half that takes the longest
        # with nothing to show. So it narrates while it goes, on the sheet the film is about.
        prep = prepare_page(doc.pages[i], progress if i == 0 else None, ocr_assist,
                            Film(film_sink) if i == 0 else None)
        if len(held) < VOCAB_HOLD:
            held[i] = prep
        elif i > 0:
            doc.pages.release(i)
        if prep.legend.own and prep.legend.entries:
            vocab = merged(vocab, prep.legend)
            break
    return vocab, held


SET_SCALE_MIN = 2           # sheets that must agree before the set is taken to have one scale
SET_SCALE_TOL = 0.02        # ...and how far apart two of them may be and still be the same scale


def scale_of_the_set(sheets: list[dict]) -> float | None:
    """The scale the set is drawn in, where its sheets agree about it.

    A set of plan sheets is drawn in one scale and every stamp says so. Two sheets that settled the same figure
    are that statement; one sheet is a sheet, and a set whose sheets disagree has details among its plans and is
    not saying anything about the sheet that failed. Where nothing is agreed, nothing is lent.
    """
    settled = [(sh.get("scale") or {}).get("meters_per_pt") for sh in sheets
               if (sh.get("scale") or {}).get("state") in ("VERIFIED", "TEXT_ONLY", "BAR_ONLY")]
    got = [v for v in settled if v]
    if len(got) < SET_SCALE_MIN:
        return None
    got.sort()
    mid = got[len(got) // 2]
    if any(abs(v - mid) > SET_SCALE_TOL * mid for v in got):
        return None                 # plans and details in one file: the set has no single scale to lend
    return mid


def sheet_record(pa) -> dict:
    """One sheet of the set, as the takeoff for the whole set needs it.

    A reading is a large object and a set has many sheets. What a set-wide takeoff wants from each is small: what
    was measured, how far the reading got, and under what scale - so that is what is kept, and the reading itself
    is let go of.
    """
    anchors = pa.anchors
    return {
        "page": pa.page.info.index,
        "scale": {"state": pa.scale.state, "meters_per_pt": pa.scale.meters_per_pt, "reason": pa.scale.reason},
        "designations": len(pa.designations),
        "leaders": len(pa.leaders),
        "verified_attachments": sum(1 for a in anchors if a.state == "VERIFIED_PIPE_ATTACHMENT"),
        "ambiguous_attachments": sum(1 for a in anchors if a.state == "AMBIGUOUS_PIPE_ATTACHMENT"),
        "no_attachments": sum(1 for a in anchors if a.state == "NO_PIPE_ATTACHMENT"),
        "legend": {"codes": len(pa.legend.entries), "own": pa.legend.own},
        "coverage": reading_coverage(pa),
        "quantities": [{k: q.get(k) for k in ("designation", "base", "dn", "state", "label_count",
                                              "physical_pipe_count", "confirmed_horizontal_m",
                                              "confirmed_vertical_m", "confirmed_total_m", "ambiguous_m",
                                              "in_hatched_area_m", "riser_count")}
                       for q in pa.quantities],
        "second_reader": pa.second_reader,
    }


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
    doc = extract_document(pdf_path, pages, progress=progress, eager=False)
    timings["extract_ms"] = (time.perf_counter() - t0) * 1000
    n_pages = len(doc.pages)
    done = 0

    def check_budget():
        if deadline_s is not None and time.perf_counter() - t_all > deadline_s and done:
            raise AnalysisTookTooLong(
                f"läsningen hann {done} av {n_pages} sidor inom {deadline_s:.0f} s och avbröts; "
                f"en halv mängd är sämre än ingen, så inget delresultat sparas")

    # First the set's own vocabulary, then the sheets read against it. A set writes its designation list once, on
    # the sheet that has room for it, and lets the rest stand on that; a reading that takes each sheet as it comes
    # would have to go back and read the early ones again once the list turned up. Looking for the list first
    # costs nothing where it is on the front sheet, because that sheet's reading is kept and used.
    vocab, held = _vocabulary(doc, known_legend, progress, ocr_assist, film_sink)
    if progress:
        progress("READING_PDF")
    overlay = OverlayWriter(pdf_path, out_dir)
    first: PageAnalysis | None = None
    sheets: list[dict] = []
    for i in range(n_pages):
        check_budget()
        pg = doc.pages[i]
        pa = analyze_page(pg, progress, ocr_assist=ocr_assist,
                          film_sink=film_sink if pg.info.index == 0 else None,
                          second_reader=second_reader, known_families=known_families, known_legend=vocab,
                          prepared=held.pop(i, None))
        overlay.add(pa)
        sheets.append(sheet_record(pa))
        done += 1
        # A sheet's reading is used the moment it exists - drawn onto the overlays, written down as a row - and
        # then let go of. Keeping all of them is what makes a fifty-sheet set need a reading's worth of geometry
        # per sheet all at once; the first sheet is kept because the artifacts and the checks are about it.
        if i == 0:
            first = pa
        else:
            doc.pages.release(i)
    # A sheet whose own stamp settled nothing is not unmeasurable when its siblings all say the same thing about
    # how big the drawing is. Those sheets - and only those - are read again with the set's scale, which is a
    # bounded amount of work: on a set where one stamp is unclear, it is one sheet.
    set_scale = scale_of_the_set(sheets)
    rescaled = 0
    if set_scale is not None:
        for i, sh in enumerate(sheets):
            if (sh.get("scale") or {}).get("state") not in ("NONE", "CONFLICT"):
                continue
            check_budget()
            pa = analyze_page(doc.pages[i], progress, ocr_assist=ocr_assist,
                              film_sink=film_sink if i == 0 else None, second_reader=second_reader,
                              known_families=known_families, known_legend=vocab, known_scale=set_scale)
            overlay.replace(pa)
            sheets[i] = sheet_record(pa)
            rescaled += 1
            if i == 0:
                first = pa
            else:
                doc.pages.release(i)
    if progress:
        progress("GENERATING_OVERLAYS")
    t0 = time.perf_counter()
    overlays = overlay.close()
    timings["overlays_ms"] = (time.perf_counter() - t0) * 1000
    rev = None
    if review:
        if progress:
            progress("REVIEWING")
        t0 = time.perf_counter()
        from .review import run_review
        rev = run_review(first, ocr=review_ocr,
                         progress=(lambda t: progress(f"REVIEWING {t}")) if progress else None)
        timings["review_ms"] = (time.perf_counter() - t0) * 1000
    # A second reader is asked only about cases the geometry already declared open, and only among candidates the
    # drawing itself offers - but it is still a machine outside this one, so a reading that consulted it is not
    # the same kind of answer as one that did not, and the determinism check is meaningless over it.
    consulted = any((sh.get("second_reader") or {}).get("asked") for sh in sheets)
    det = run_determinism(doc, 0, first, known_families=known_families, known_legend=vocab) \
        if determinism and not consulted else None
    cont = scan_source(os.path.dirname(os.path.abspath(__file__))) if contamination else None
    t0 = time.perf_counter()
    timings["total_s"] = time.perf_counter() - t_all
    files = write_all(pdf_path, doc, [first], out_dir, name, timings, det, cont, overlays, CONFIG, rev,
                      sheets=sheets, doc_legend=vocab)
    timings["artifacts_ms"] = (time.perf_counter() - t0) * 1000
    summary = {"name": name, "pages": n_pages, "summary": summarize(first),
               "determinism": det["state"] if det else ("NOT_APPLICABLE_A_SECOND_READER_WAS_CONSULTED" if consulted else None),
               "second_reader": {"consulted": consulted,
                                 "asked": sum((sh.get("second_reader") or {}).get("asked", 0) for sh in sheets),
                                 "settled": sum((sh.get("second_reader") or {}).get("settled", 0) for sh in sheets),
                                 "refused": sum((sh.get("second_reader") or {}).get("refused", 0) for sh in sheets)},
               "legend": {"codes": len(vocab.entries) if vocab else 0,
                          "own_sheet": bool(first.legend.own and first.legend.entries),
                          "from_sheet": next((e.page for e in (vocab.entries if vocab else []) if e.page is not None), None)},
               "sheets": sheets,
               "scale": {"of_the_set": set_scale, "sheets_reread_with_it": rescaled},
               "contamination": cont["state"] if cont else None, "files": files, "total_seconds": round(timings["total_s"], 2),
               "input": getattr(doc.pages[0], "input_class", None), "skipped_pages": doc.skipped_pages,
               "review": {"state": rev["state"], "n_findings": rev["n_findings"], "agents": rev["agents"]} if rev else None,
               "ocr_assist": first.ocr_assist}
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
