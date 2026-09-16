"""Stilkorpusen genom motorn: elva producentkedjor, ingen referens, öppen värld.

Det här är inte en grind. Stilkällorna i `data/styles/pipestudio/` bär inga facitmängder, så ingenting här kan
säga om metrarna blev rätt. Det som går att svara på är om bladet blev LÄST: hittades skalan, lästes
beteckningarna, nådde hänvisningarna fram till rör, kom det ut mängder, och hände det inom rimlig tid utan att
något small. Det är öppen värld - filer motorn aldrig sett, ritade av åtta andra företag i andra CAD-program
och skrivna av andra PDF-skrivare än korpusens.

Varje blad får också sin egen strukturrad, för det är den som förklarar utfallet: bär exporten CAD-lager alls,
hur många pennor finns det att skilja system på, finns det riktig text eller är allt sprängt till geometri, och
hur mycket är klippt. En läsning som ger noll rör på ett blad utan lager, utan text och med en enda penna är
inte samma fel som en läsning som ger noll rör på ett välordnat blad.

    python3 engine/tools/style_run.py results/<dag>/stilar.json [--only <delsträng>]

Läser inga referensmängder. Aldrig importerad av motorn.
"""
import json
import os
import sys
import tempfile
import time
import traceback
from collections import Counter

sys.path.insert(0, "/home/user/vvs5/engine")
from vvs_engine.cli import analyze_pdf  # noqa: E402

ROOT = "/home/user/vvs5/data/styles/pipestudio"


def sheets(only: str | None) -> list[tuple[str, str, str]]:
    """(stilnamn, blad, sökväg) - stilnamnet är mappen, som bär producentkedjan i klartext."""
    out = []
    for dirpath, _, files in os.walk(ROOT):
        for f in sorted(files):
            if not f.lower().endswith(".pdf"):
                continue
            style = os.path.basename(dirpath)
            p = os.path.join(dirpath, f)
            if only and only.lower() not in (style + " " + f).lower():
                continue
            out.append((style, os.path.splitext(f)[0], p))
    return sorted(out)


def structure(path: str) -> dict:
    """Vad exporten ger motorn att arbeta med, innan någon läsning skett."""
    import pymupdf
    d = pymupdf.open(path)
    pg = d[0]
    drawn, clips = [], 0
    for e in pg.get_drawings(extended=True):
        if e.get("type") == "clip":
            clips += 1
        elif e.get("type") in ("s", "f", "fs"):
            drawn.append(e)
    layers = {e.get("layer") or "" for e in drawn}
    pens = Counter((round(e.get("width") or 0, 2), str(e.get("color"))) for e in drawn)
    md = d.metadata or {}
    out = {"paths": len(drawn), "clips": clips,
           "named_layers": len([x for x in layers if x]),
           "pens": len(pens),
           "words": len(pg.get_text("words")), "fonts": len(pg.get_fonts()),
           "producer": md.get("producer") or "", "creator": md.get("creator") or "",
           "page": [round(pg.rect.width), round(pg.rect.height)]}
    d.close()
    return out


def run(out_path: str, only: str | None) -> None:
    res: dict = {}
    for style, tag, pdf in sheets(only):
        key = f"{style} :: {tag}"
        t0 = time.perf_counter()
        st = structure(pdf)
        d = tempfile.mkdtemp(prefix="style-")
        try:
            analyze_pdf(pdf, d, determinism=False, contamination=True, review=True,
                        review_ocr=False, ocr_assist=False)
            q = json.load(open(f"{d}/quantities.json"))
            cov = json.load(open(f"{d}/reading-coverage.json"))
            sheet = (cov.get("sheets") or [{}])[0]
            rows = q.get("rows") or []
            res[key] = {
                "state": "OK", "seconds": round(time.perf_counter() - t0, 1), "structure": st,
                "scale": {"state": (q.get("scale") or {}).get("state"),
                          "reason": (q.get("scale") or {}).get("reason")},
                "designations": sheet.get("designations"),
                "verified_attachments": sheet.get("verified_attachments"),
                "ambiguous_attachments": sheet.get("ambiguous_attachments"),
                "rows": len(rows),
                "rows_with_metres": sum(1 for r in rows if (r.get("confirmed_total_m") or 0) > 0),
                "total_m": round(sum(r.get("confirmed_total_m") or 0.0 for r in rows), 1),
            }
        except Exception as e:                                   # noqa: BLE001
            res[key] = {"state": "FEL", "seconds": round(time.perf_counter() - t0, 1), "structure": st,
                        "error": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()[-1500:]}
        r = res[key]
        note = (f"rader {r.get('rows', 0):3}  meter {r.get('total_m', 0):8}  skala {(r.get('scale') or {}).get('state')}"
                if r["state"] == "OK" else r.get("error", "")[:70])
        print(f"{tag[:28]:30}{r['state']:5}{r['seconds']:7.1f}s  lager {st['named_layers']:3} "
              f"pennor {st['pens']:3} ord {st['words']:5}  {note}", flush=True)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        json.dump(res, open(out_path, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = None
    for i, a in enumerate(sys.argv):
        if a == "--only" and i + 1 < len(sys.argv):
            only = sys.argv[i + 1]
    run(args[0] if args else "results/stilar.json", only)
