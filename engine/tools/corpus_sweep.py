"""Läs varje ritning i korpusen, och spara vad läsningen gav - blad för blad, medan den går.

Grinden läser de 59 blad som har en mängdförteckning att jämföras med. Materialet är större än så: 284 unika
ritnings-PDF:er ligger lokalt ur samma mapp, utan facit. Att aldrig läsa dem är att inte veta vad systemet gör
med det mesta av det som finns - och en läsning som bara prövas där svaret är känt är prövad på fel ställe.

Svepet är blint av konstruktion: ingen mängdförteckning öppnas, ingenting jämförs med ett facit. Det som sparas
är vad läsningen själv säger - hur långt den kom, vad den inte kunde avgöra, och när den inte kunde läsa alls -
och det skrivs efter varje blad, så att en avbruten körning inte kostar mer än det blad den stod på.

    python3 tools/corpus_sweep.py <ut.json> [--limit N]
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import traceback

sys.path.insert(0, "/home/user/vvs5/engine")

ROOT = "/home/user/vvs5"
DATA = os.path.join(ROOT, "data")
MANIFEST = os.path.join(ROOT, "results/2026-09-11-topologi/corpus_manifest.json")
DRAWING_CLASSES = ("CLEAN_ORIGINAL_CANDIDATE", "CVAT_SOURCE_PDF", "VIDEO_DRAWING_PDF", "TEST_DRAWING",
                   "SCALE_STUDY_PDF", "OTHER_FORMAT_PDF", "STYLE_SOURCE_PDF")
DEADLINE_S = 240.0


def drawings() -> list[dict]:
    """Varje unik ritnings-PDF som finns lokalt, en gång per innehåll och i en bestämd ordning."""
    with open(MANIFEST, encoding="utf-8") as fh:
        files = json.load(fh)["files"]
    seen: dict[str, dict] = {}
    for f in sorted(files, key=lambda x: (x.get("local_copy") or "", x["filename"])):
        if f["classification"] not in DRAWING_CLASSES or not f.get("local_copy"):
            continue
        path = os.path.join(DATA, f["local_copy"])
        if not os.path.exists(path):
            continue
        try:
            with open(path, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
        except OSError:
            continue
        if digest in seen:
            seen[digest]["also"].append(f["local_copy"])
            continue
        seen[digest] = {"sha256": digest, "path": path, "local": f["local_copy"], "name": f["filename"],
                        "drawing": f.get("drawing_number"), "project": f.get("logical_project"),
                        "classification": f["classification"], "role": f.get("validation_role") or "",
                        "size": os.path.getsize(path), "also": []}
    return [seen[k] for k in sorted(seen)]


def read_one(rec: dict, outdir: str) -> dict:
    from vvs_engine.cli import analyze_pdf
    t0 = time.perf_counter()
    try:
        s = analyze_pdf(rec["path"], outdir, name=os.path.splitext(rec["name"])[0], deadline_s=DEADLINE_S,
                        determinism=False, contamination=True, review=False, review_ocr=False, ocr_assist=False)
    except Exception as e:                                        # noqa: BLE001
        return {"state": "FAILED", "error": f"{type(e).__name__}: {e}"[:300],
                "seconds": round(time.perf_counter() - t0, 1),
                "trace": traceback.format_exc(limit=3)[-400:]}
    summ = s.get("summary") or {}
    cov = {}
    try:
        with open(os.path.join(outdir, "reading-coverage.json"), encoding="utf-8") as fh:
            sheets = (json.load(fh) or {}).get("sheets") or []
        if sheets:
            keep = ("pipe_names", "pipe_names_with_metres", "share", "drawn_m", "confirmed_m", "ambiguous_m",
                    "unowned_m", "scale_state", "scale_settled", "scale_reason")
            cov = {k: sheets[0][k] for k in keep if k in sheets[0]}
    except (OSError, ValueError):
        pass
    rows = []
    try:
        with open(os.path.join(outdir, "quantities.json"), encoding="utf-8") as fh:
            rows = (json.load(fh) or {}).get("rows") or []
    except (OSError, ValueError):
        pass
    return {"state": "OK", "seconds": round(time.perf_counter() - t0, 1),
            "pages": s.get("pages"), "scale": s.get("scale"), "coverage": cov,
            "designations": summ.get("designations"), "anchors": summ.get("anchors"),
            "rows": len(rows),
            "confirmed_horizontal_m": round(sum(r.get("confirmed_horizontal_m") or 0 for r in rows), 2),
            "ambiguous_m": round(sum(r.get("ambiguous_m") or 0 for r in rows), 2),
            "declared_m": round(sum(r.get("declared_m") or 0 for r in rows), 2),
            "in_hatched_area_m": round(sum(r.get("in_hatched_area_m") or 0 for r in rows), 2),
            "top_rows": sorted(({"designation": r["designation"], "m": round(r.get("confirmed_horizontal_m") or 0, 2)}
                                for r in rows), key=lambda r: -r["m"])[:8],
            "contamination": (s.get("contamination") or {}).get("state") if isinstance(s.get("contamination"), dict) else s.get("contamination")}


def main() -> None:
    out = sys.argv[1]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    done: dict = {}
    if os.path.exists(out):
        with open(out, encoding="utf-8") as fh:
            done = json.load(fh)
    todo = [d for d in drawings() if d["sha256"] not in done]
    if limit:
        todo = todo[:limit]
    print(f"{len(done)} lästa sedan tidigare, {len(todo)} kvar", flush=True)
    # Artefakterna per blad är många och tunga; svepets minne är json-filen. Arbetskatalogen ligger därför
    # utanför förrådet om den som kör säger var.
    work = os.environ.get("VVS_SWEEP_WORK") or os.path.join(os.path.dirname(out) or ".", "sweep_work")
    for i, rec in enumerate(todo, 1):
        outdir = os.path.join(work, rec["sha256"][:12])
        got = read_one(rec, outdir)
        done[rec["sha256"]] = {**{k: v for k, v in rec.items() if k != "path"}, **got}
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(done, fh, ensure_ascii=False, indent=1)
        m = got.get("confirmed_horizontal_m")
        print(f"{i:4d}/{len(todo)} {rec['name'][:42]:42s} {got['state']:6s} {got['seconds']:6.1f}s "
              + (f"{m:8.1f} m  {got.get('rows', 0):3d} rader" if got["state"] == "OK" else got.get("error", "")[:60]),
              flush=True)
    print("klart:", len(done), "blad", flush=True)


if __name__ == "__main__":
    main()
