"""Vart tog varje ritad meter vägen?

En täckningssiffra säger att något fattas, aldrig var det tog vägen. Ett blad som redovisar 23 % kan ha förlorat
sina meter på sex helt olika ställen, och varje ställe kräver sin egen åtgärd. Det här är kvittot: allt bläck
bladet ritar, hänfört till det som hände med det.

  bortvald      · en penna läsningen vägde och läste som något annat än rör (vägg, möbel, ram)
  aldrig vägd   · en penna ingen hänvisningslinje någonsin pekade på, så den vägdes aldrig
  mätt          · fick en identitet och en längd
  i vägg        · mätt, men inuti en skrafferad yta och därför utanför den vågräta mängden
  tvetydig      · kunde tillhöra mer än en beteckning; ritningen avgjorde inte
  påpekad       · en beteckning pekar på den, men ingen identitet kunde ta den
  onämnd        · accepterad rörgeometri som ingen beteckning nådde alls

De två sista raderna är de dyra. `onämnd` är räckvidd: etiketterna nådde inte fram. `påpekad` är avgörande:
etiketten nådde fram och läsningen kunde ändå inte namnge sträckan.

Kör direkt mot motorn - det här mäter inte mot något facit och behöver inget.

    python results/validation/loss_ledger.py data/styles/z/9/7.pdf [sida]
    python results/validation/loss_ledger.py --corpus            # hela korpuset, i bakgrunden
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.environ.get("VVS_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "engine"))


def ledger(path: str, pno: int | None = None) -> dict:
    """One sheet's ink, accounted for."""
    from vvs_engine.pdf.extract import extract_document
    from vvs_engine.pipeline import analyze_page, claimed_runs

    doc = extract_document(path, eager=False)
    n = len(doc.pages)
    i = pno if pno is not None else (0 if n == 1 else n // 2)
    pa = analyze_page(doc.pages[i])
    mpp = pa.scale.meters_per_pt or 0.0

    # what the reading weighed and set aside, and what it never weighed at all
    dec = (pa.contact_stats or {}).get("declined_families") or {}
    unc = (pa.contact_stats or {}).get("unconsidered_families") or {}
    out = {"file": os.path.relpath(path, ROOT), "page": i, "sheets": n,
           "scale": pa.scale.state, "mpp": mpp,
           "declined_m": round(sum(v["total_length_pt"] for v in dec.values()) * mpp, 1),
           "never_m": round(sum(v["total_length_pt"] for v in unc.values()) * mpp, 1),
           "declined_why": Counter(v["why"] for v in dec.values()),
           "never_why": Counter(v["why"] for v in unc.values())}

    claimed = claimed_runs(pa.anchors, pa.ownership, pa.graphs)
    measured = ambiguous = unowned = claimed_m = 0.0
    for fk, g in pa.graphs.items():
        states = pa.ownership.prim_states[fk]
        claim = claimed.get(fk) or {}
        for pid, prim in g.prims.items():
            L = prim.seg.length * mpp
            st = states[pid].state
            if st == "CONFIRMED":
                measured += L
            elif st == "AMBIGUOUS":
                ambiguous += L
            elif pid in claim:
                claimed_m += L
            else:
                unowned += L
    hatched = sum(q.get("in_hatched_area_m") or 0.0 for q in pa.quantities)
    out.update({"measured_m": round(measured, 1), "in_wall_m": round(hatched, 1),
                "ambiguous_m": round(ambiguous, 1), "claimed_m": round(claimed_m, 1),
                "unowned_m": round(unowned, 1)})

    # why the labels that reached nothing reached nothing
    st = Counter(a.state for a in pa.anchors)
    out["anchors"] = dict(st)
    out["anchor_why"] = dict(Counter(a.reason for a in pa.anchors if a.state != "VERIFIED_PIPE_ATTACHMENT").most_common(6))
    out["leaderless"] = dict(Counter(
        w for lst in ((pa.contact_stats or {}).get("leaderless_why") or {}).values() for w in lst).most_common(6))
    out["designations"] = len(pa.designations)
    out["names"] = len({q["designation"] for q in pa.quantities})
    out["names_with_m"] = len({q["designation"] for q in pa.quantities
                               if (q.get("confirmed_horizontal_m") or 0) > 0.005})
    doc.pages.release(i)
    return out


def show(r: dict) -> None:
    tot = sum(r[k] for k in ("declined_m", "never_m", "measured_m", "ambiguous_m", "claimed_m", "unowned_m"))
    print(f"\n=== {r['file']} blad {r['page'] + 1}/{r['sheets']} · skala {r['scale']} · "
          f"{r['names_with_m']}/{r['names']} namn fick meter")
    for k, sv in (("measured_m", "mätt"), ("in_wall_m", "  varav i vägg"), ("ambiguous_m", "tvetydig"),
                  ("claimed_m", "påpekad men onämnd"), ("unowned_m", "onämnd"),
                  ("declined_m", "bortvald"), ("never_m", "aldrig vägd")):
        v = r[k]
        share = 100 * v / tot if tot and k != "in_wall_m" else 0
        bar = "█" * int(share / 2.5)
        print(f"  {sv:22s} {v:9.1f} m {share:5.1f}% {bar}")
    print(f"  {'summa ritat':22s} {tot:9.1f} m")
    if r["anchor_why"]:
        print("  etiketter som inte nådde sitt rör:", ", ".join(f"{k}×{v}" for k, v in r["anchor_why"].items()))
    if r["leaderless"]:
        print("  etiketter utan hänvisningslinje:", ", ".join(f"{k}×{v}" for k, v in r["leaderless"].items()))
    if r["declined_why"]:
        print("  bortvalt för att:", ", ".join(f"{k}×{v}" for k, v in r["declined_why"].items()))


def corpus(out_path: str, workers: int = 4) -> None:
    from concurrent.futures import ProcessPoolExecutor, as_completed
    paths = sorted(glob.glob(os.path.join(ROOT, "data", "styles", "**", "*.pdf"), recursive=True))
    paths += sorted(glob.glob(os.path.join(ROOT, "data", "validation_set3", "*", "clean.pdf")))
    paths += sorted(glob.glob(os.path.join(ROOT, "data", "validation_*", "clean.pdf")))
    done = set()
    if os.path.exists(out_path):
        for line in open(out_path):
            try:
                done.add(json.loads(line)["file"])
            except Exception:
                pass
    todo = [p for p in paths if os.path.relpath(p, ROOT) not in done]
    print(f"{len(paths)} filer, {len(todo)} kvar", flush=True)
    fh = open(out_path, "a")
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_safe, p): p for p in todo}
        for k, f in enumerate(as_completed(futs), 1):
            fh.write(json.dumps(f.result(), default=str) + "\n"); fh.flush()
            if k % 10 == 0:
                print(f"  {k}/{len(todo)}", flush=True)
    fh.close()
    print("klart")


def _safe(p: str) -> dict:
    try:
        return ledger(p)
    except Exception as e:  # noqa: BLE001
        return {"file": os.path.relpath(p, ROOT), "err": f"{type(e).__name__}: {e}"[:120]}


def summarise(out_path: str) -> None:
    rows = [json.loads(l) for l in open(out_path)]
    ok = [r for r in rows if "measured_m" in r]
    err = [r for r in rows if "err" in r]
    keys = ("measured_m", "ambiguous_m", "claimed_m", "unowned_m", "declined_m", "never_m")
    tot = {k: sum(r[k] for r in ok) for k in keys}
    all_m = sum(tot.values()) or 1
    print(f"{len(ok)} blad lästa · {len(err)} fel\n")
    for k, sv in zip(keys, ("mätt", "tvetydig", "påpekad men onämnd", "onämnd", "bortvald", "aldrig vägd")):
        print(f"  {sv:22s} {tot[k]:11.0f} m {100 * tot[k] / all_m:5.1f}%")
    print(f"  {'summa ritat':22s} {all_m:11.0f} m")
    print(f"\n  i vägg (inne i mätt): {sum(r['in_wall_m'] for r in ok):.0f} m")
    why = Counter()
    for r in ok:
        for k, v in (r.get("anchor_why") or {}).items():
            why[k] += v
    print("\nvarför en etikett inte nådde sitt rör:")
    for k, v in why.most_common(10):
        print(f"  {v:6d}  {k}")
    lw = Counter()
    for r in ok:
        for k, v in (r.get("leaderless") or {}).items():
            lw[k] += v
    print("\nvarför en etikett inte hade någon hänvisningslinje:")
    for k, v in lw.most_common(10):
        print(f"  {v:6d}  {k}")
    dw = Counter()
    for r in ok:
        for k, v in (r.get("declined_why") or {}).items():
            dw[k] += v
    print("\nvarför en penna valdes bort som rör:")
    for k, v in dw.most_common(10):
        print(f"  {v:6d}  {k}")
    if err:
        print(f"\n{len(err)} blad kraschade:")
        for e in Counter(r["err"] for r in err).most_common(8):
            print(f"  {e[1]:4d}  {e[0]}")


if __name__ == "__main__":
    if sys.argv[1] == "--corpus":
        corpus(sys.argv[2])
    elif sys.argv[1] == "--summary":
        summarise(sys.argv[2])
    else:
        show(ledger(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None))
