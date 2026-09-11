"""Den blinda grindkörningen: hela utvecklingskorpusen genom motorn, och bara motorns egna tal skrivs ned.

Ingen referens läses här. Det som sparas per blad är vad motorn själv säger - mängdrader, skalans tillstånd,
läsningens täckning, fronterna, vilka namn som lästes och vilka som fick meter - så att poängsättningen
(engine/tools/facit_metrics.py) efteråt kan säga inte bara *att* en beteckning saknas utan *var* i kedjan den
föll bort. Körningen ska frysas (hashmanifest) innan referensen öppnas; det är ordningen som gör den blind.

    python3 engine/tools/gate_run.py results/<dag>/gateNN.json [--unmarked]

--unmarked väljer den omarkerade filen för V-serien där den finns lokalt (protokollet), annars samma indata som
tidigare grindar så att körningarna är jämförbara.
"""
import hashlib
import json
import os
import sys
import tempfile
import time
import traceback

sys.path.insert(0, "/home/user/vvs5/engine")
from vvs_engine.cli import analyze_pdf  # noqa: E402

ROOT = "/home/user/vvs5/data"


def sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def sheets(unmarked: bool) -> list[tuple[str, str]]:
    out = []
    for tag in ("A", "C", "D", "E"):
        p = f"{ROOT}/validation_{tag}/clean.pdf"
        if os.path.exists(p):
            out.append((tag, p))
    for name in sorted(os.listdir(f"{ROOT}/validation_set3")):
        cands = ([f"{ROOT}/styles/test/{name}.pdf", f"{ROOT}/styles/z/2/{name}.pdf"] if unmarked else []) + [f"{ROOT}/validation_set3/{name}/clean.pdf"]
        for c in cands:
            if os.path.isfile(c):
                out.append((name, c))
                break
    # W-bladen vars referens bara finns på Drive: ren PDF (CVAT-kopian, 0 anteckningar) + facit.csv per blad
    wdir = f"{ROOT}/validation_W"
    seen = {t for t, _ in out}
    if os.path.isdir(wdir):
        for name in sorted(os.listdir(wdir)):
            p = f"{wdir}/{name}/clean.pdf"
            if name.startswith("_") or name in seen or not os.path.isfile(p):
                continue
            out.append((name, p))
    return out


def run(out_path: str, unmarked: bool) -> None:
    res = {}
    for tag, pdf in sheets(unmarked):
        t0 = time.perf_counter()
        d = tempfile.mkdtemp(prefix=f"gate-{tag}-")
        try:
            s = analyze_pdf(pdf, d, determinism=False, contamination=True, review=True, review_ocr=False, ocr_assist=False)
            q = json.load(open(f"{d}/quantities.json"))
            cov = json.load(open(f"{d}/reading-coverage.json"))
            sheet = (cov.get("sheets") or [{}])[0]
            rr = json.load(open(f"{d}/reading-review.json"))
            rec = json.load(open(f"{d}/reconciliation.json"))
            fr = json.load(open(f"{d}/pipe-extent-frontiers.json")) if os.path.exists(f"{d}/pipe-extent-frontiers.json") else {}
            issues = json.load(open(f"{d}/route-crosscheck.json")) if os.path.exists(f"{d}/route-crosscheck.json") else {}
            des = (json.load(open(f"{d}/vector-designations.json")).get("designations") or []) if os.path.exists(f"{d}/vector-designations.json") else []
            anc = (json.load(open(f"{d}/pipe-code-anchors.json")).get("anchors") or []) if os.path.exists(f"{d}/pipe-code-anchors.json") else []
            # vad bladet skriver, och vad som fick meter: det som skiljer "inte läst" från "läst men utan rör"
            names_read = sorted({(x.get("text") or "").strip().upper() for x in des
                                 if x.get("names_a_pipe", True) and (x.get("text") or "").strip()})
            names_with_metres = sorted({(r.get("designation") or "").upper() for r in (q.get("rows") or [])
                                        if (r.get("confirmed_total_m") or 0) > 0})
            anchor_states = {}
            for a in anc:
                anchor_states[a.get("state") or "?"] = anchor_states.get(a.get("state") or "?", 0) + 1
            res[tag] = {
                "state": "OK", "input": pdf.replace(ROOT + "/", ""), "input_sha256": sha(pdf),
                "seconds": round(time.perf_counter() - t0, 1), "n_pages": s.get("n_pages") or 1,
                "scale": {"state": (q.get("scale") or {}).get("state"), "reason": (q.get("scale") or {}).get("reason"),
                          "meters_per_pt": (q.get("scale") or {}).get("meters_per_pdf_point")},
                "coverage": {"designations": len(names_read), "with_dn": sheet.get("with_dn"),
                             "leaders": len(anc), "verified_attachments": anchor_states.get("VERIFIED_PIPE_ATTACHMENT", 0),
                             "ambiguous_attachments": anchor_states.get("AMBIGUOUS_PIPE_ATTACHMENT", 0),
                             "no_attachments": anchor_states.get("NO_PIPE_ATTACHMENT", 0),
                             "anchor_states": anchor_states,
                             "pipe_names": sheet.get("pipe_names"), "pipe_names_with_metres": sheet.get("pipe_names_with_metres"),
                             "without_metres": sheet.get("without_metres"),
                             "physical_pipes": (q.get("totals") or {}).get("physical_pipes"),
                             "unowned_m": rr.get("unnamed_m"), "ambiguous_m": rr.get("ambiguous_m"),
                             "claimed_m": rr.get("closure_only_m"), "reconciliation": rec.get("state"),
                             "named_vs_measured": rr.get("coverage_pct")},
                "names_read": names_read,
                "names_with_metres": names_with_metres,
                "frontiers": (fr.get("summary") or {}),
                "quantities": q.get("rows") or [], "totals": q.get("totals") or {},
                "n_issues": 0, "blocking": 0, "advisory": 0,
            }
            if isinstance(issues, dict):
                rows = issues.get("issues") or []
                res[tag]["n_issues"] = len(rows)
                res[tag]["blocking"] = sum(1 for i in rows if i.get("severity") == "BLOCKING")
                res[tag]["advisory"] = len(rows) - res[tag]["blocking"]
            print(f"{tag:16} OK  {res[tag]['seconds']:6.1f}s  rader {len(res[tag]['quantities']):3}  "
                  f"fronter {res[tag]['frontiers'].get('frontiers', '-')}", flush=True)
        except Exception as e:  # noqa: BLE001
            res[tag] = {"state": "ERROR", "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-800:]}
            print(f"{tag:16} FEL {e}", flush=True)
        json.dump(res, open(out_path, "w"), ensure_ascii=False, indent=1)
    print("klart:", out_path)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    run(args[0] if args else "/home/user/vvs5/results/gate.json", "--unmarked" in sys.argv)
