"""What the reading got right and what it got wrong, told apart.

A single total error hides the two failures that matter in opposite ways. Metres missing from the takeoff cost
the estimator work; metres the takeoff invented cost them money and trust, and there is no amount of coverage
that pays for them. So this reports them separately, per drawing and over the set:

  * designations - precision and recall of the identities the reading found against the ones the facit lists
  * metres       - owned (correctly on a designation the facit has), false-owned (on a designation it does not,
                   or beyond what it says), missed (in the facit and not in the reading)
  * reach        - how far the reading got: labels the sheet carries, leaders found for them, attachments
                   verified, and what was left ambiguous rather than guessed

Reads a recorded blind run and the facit. The engine is never invoked here, so nothing a facit says can reach a
measurement; this runs after the blind pass, exactly like the scorer beside it.
"""
import json
import os
import sys

import openpyxl

MATCH_TOL = 0.05        # a designation's metres count as owned up to 5 % over the facit; past that it is invented


def fl(v):
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return 0.0


ROOT = os.environ.get("VVS_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def facit_path(tag):
    """Where a reference drawing's hand takeoff lives.

    The set grew: four drawings written one per directory, and then a whole Bluebeam set of twenty-nine, each in
    a directory of its own under validation_set3. A tag is looked up in both, so the scorer takes the whole set
    without the caller having to know which half a drawing came from.
    """
    a = os.path.join(ROOT, "data", f"validation_{tag}", "facit.xlsx")
    if os.path.exists(a):
        return a
    return os.path.join(ROOT, "data", "validation_set3", tag, "facit.xlsx")


def all_tags():
    """Every reference drawing there is, in a stable order."""
    out = [t for t in ("A", "C", "D", "E") if os.path.exists(facit_path(t))]
    d = os.path.join(ROOT, "data", "validation_set3")
    if os.path.isdir(d):
        out += sorted(n for n in os.listdir(d) if os.path.exists(facit_path(n)))
    return out


def facit(tag):
    """The hand takeoff, split the way the workbook splits it.

    `Längd` is the length of the polyline the estimator drew on the sheet - the horizontal run plus whatever
    riser drops the marker walked - and that is the quantity the engine produces. `Total_vertikalhöjd_VS` is a
    separate column: riser count times a floor height the estimator assumed, which the engine refuses to invent
    without being given one. Both are returned so the report can say which of the two it is scoring against
    instead of quietly presenting one as the whole facit.
    """
    ws = openpyxl.load_workbook(facit_path(tag), data_only=True).worksheets[0]
    hdr = [str(v or "").strip() for v in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
    col = {h: i for i, h in enumerate(hdr)}
    # the subject column is headed "Ämne" on some sheets and "Subject" on others; a missing one is an error,
    # never a guessed index, because scoring against the wrong column reports confident nonsense
    c_subj = next((col[h] for h in ("Ämne", "Subject") if h in col), None)
    c_len = col.get("Längd")
    c_vert = col.get("Total_vertikalhöjd_VS")
    if c_subj is None or c_len is None:
        raise SystemExit(f"facit {tag}: hittar inte kolumnerna (rubriker: {hdr})")
    horiz, vert = {}, {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        s = r[c_subj]
        if not s or s == "Markera":
            continue
        name = str(s).replace(" Vertikal", "").replace(" VERTIKAL", "").strip()
        horiz[name] = horiz.get(name, 0.0) + fl(r[c_len])
        if c_vert is not None:
            vert[name] = vert.get(name, 0.0) + fl(r[c_vert])
    return horiz, vert


def _system(name):
    """The system a designation belongs to: the first token, which is what the facit's layers sort by."""
    return str(name).split("-")[0].strip().upper()


def score_one(tag, rec):
    fh, fv = facit(tag)
    ours = {q["designation"]: q["confirmed_total_m"] for q in rec["quantities"]}
    # a row of 0.00 m is not a claim about the drawing, it is a designation read with no metres behind it
    ours = {k: v for k, v in ours.items() if v > 0.005}
    fh = {k: v for k, v in fh.items() if v > 0.005}

    # What the facit is about. Several sheets in the set were taken off one system at a time: A0211 and A0221
    # carry drainage the drawing plainly draws and labels, and their facit lists heating and nothing else.
    # Scored flat, every correctly measured drainage metre on those sheets counts as invented - A0221 read as
    # 94 % false while measuring the drawing correctly - and a gate that says that would drive the reading to
    # unlearn what it got right. So the score is taken over the systems the facit actually covers, and the rest
    # is reported beside it as out of scope rather than dropped: a system the facit never mentions cannot be
    # scored either way, and saying how much of it there is keeps it from disappearing.
    scope = {_system(k) for k in fh}
    outside = {k: v for k, v in ours.items() if _system(k) not in scope}
    ours = {k: v for k, v in ours.items() if _system(k) in scope}

    hit = set(ours) & set(fh)
    invented_names = set(ours) - set(fh)
    missed_names = set(fh) - set(ours)

    # capped at the facit, not at the facit plus tolerance: metres the drawing does not contain are never
    # coverage, however small the overshoot. The tolerance decides only when an overshoot counts as invented.
    owned = sum(min(ours[k], fh[k]) for k in hit)
    over = sum(max(0.0, ours[k] - fh[k] * (1 + MATCH_TOL)) for k in hit)
    false_owned = over + sum(ours[k] for k in invented_names)
    missed = sum(max(0.0, fh[k] - ours[k]) for k in hit) + sum(fh[k] for k in missed_names)

    cov = rec.get("coverage") or {}
    return {
        "tag": tag,
        "designations": {"facit": len(fh), "found": len(ours), "correct": len(hit),
                         "precision": len(hit) / len(ours) if ours else 0.0,
                         "recall": len(hit) / len(fh) if fh else 0.0,
                         "invented": sorted(invented_names), "missed": sorted(missed_names)},
        "outside_scope": {"systems": sorted({_system(k) for k in outside}), "m": sum(outside.values()),
                          "names": sorted(outside)},
        "metres": {"facit": sum(fh.values()), "owned": owned, "false_owned": false_owned, "missed": missed,
                   "coverage": owned / sum(fh.values()) if fh else 0.0,
                   "false_rate": false_owned / sum(fh.values()) if fh else 0.0,
                   # what the engine does not claim at all, so that it is stated rather than left out
                   "facit_vertical_not_claimed": sum(fv.values())},
        "reach": {"labels": cov.get("designations"), "with_dn": cov.get("with_dn"),
                  "leaders": cov.get("leaders"), "verified": cov.get("verified_attachments"),
                  "ambiguous": cov.get("ambiguous_attachments"), "none": cov.get("no_attachments"),
                  "unresolved": rec.get("n_issues"),
                  "blocking": rec.get("blocking"), "advisory": rec.get("advisory")},
        "scale": (rec.get("scale") or {}).get("state"),
    }


def main(blind_path, tags):
    rec = json.load(open(blind_path))
    rows = []
    for tag in tags:
        r = rec.get(tag)
        if not r or r.get("state") != "OK":
            print(f"### {tag}: {(r or {}).get('state', 'saknas')}")
            continue
        rows.append(score_one(tag, r))

    W = max([4] + [len(r["tag"]) for r in rows])
    print(f"{'':{W}s} {'skala':10s} {'bet. P':>7s} {'bet. R':>7s} "
          f"{'facit m':>9s} {'ägda m':>9s} {'falska m':>9s} {'missade m':>10s} {'täckning':>9s} {'falskt':>8s}")
    for r in rows:
        d, m = r["designations"], r["metres"]
        print(f"{r['tag']:{W}s} {str(r['scale']):10s} {d['precision']:7.1%} {d['recall']:7.1%} "
              f"{m['facit']:9.2f} {m['owned']:9.2f} {m['false_owned']:9.2f} {m['missed']:10.2f} "
              f"{m['coverage']:9.1%} {m['false_rate']:8.1%}")

    tot_f = sum(r["metres"]["facit"] for r in rows)
    tot_o = sum(r["metres"]["owned"] for r in rows)
    tot_x = sum(r["metres"]["false_owned"] for r in rows)
    tot_m = sum(r["metres"]["missed"] for r in rows)
    n_hit = sum(r["designations"]["correct"] for r in rows)
    n_found = sum(r["designations"]["found"] for r in rows)
    n_facit = sum(r["designations"]["facit"] for r in rows)
    print(f"{'ALLA':{W}s} {'':10s} {n_hit / n_found if n_found else 0:7.1%} {n_hit / n_facit if n_facit else 0:7.1%} "
          f"{tot_f:9.2f} {tot_o:9.2f} {tot_x:9.2f} {tot_m:10.2f} "
          f"{tot_o / tot_f if tot_f else 0:9.1%} {tot_x / tot_f if tot_f else 0:8.1%}")
    tot_v = sum(r["metres"]["facit_vertical_not_claimed"] for r in rows)
    print(f"\nAllt ovan mäts mot facits Längd-kolumn - den utritade sträckan, som är det motorn tar fram.")
    print(f"Facit har därutöver {tot_v:.2f} m i Total_vertikalhöjd_VS: stigare gånger en våningshöjd som "
          f"mängdaren\nantagit. Motorn räknar inte fram dem utan att få höjden, så de ingår varken i täckningen "
          f"eller i felet\n- de står här för att inte försvinna.")

    out_m = sum(r["outside_scope"]["m"] for r in rows)
    if out_m:
        print(f"\nUtanför facits omfattning: {out_m:.2f} m på system inget facit i uppsättningen tar upp för sitt "
              f"blad.\nDe räknas varken som täckning eller som fel - ett system facit inte nämner går inte att "
              f"pröva mot det.")
        for r in rows:
            o = r["outside_scope"]
            if o["m"] > 0.005:
                print(f"  {r['tag']}: {o['m']:8.2f} m  {', '.join(o['systems'])}")

    print("\nvad som saknas och vad som hittats på:")
    for r in rows:
        d = r["designations"]
        if d["invented"] or d["missed"]:
            print(f"  {r['tag']}: hittade-på {d['invented'] or '-'}   saknade {d['missed'] or '-'}")

    print("\nhur långt läsningen kom - och vad den lät bli att gissa:")
    print(f"{'':{W}s} {'bet.':>6s} {'m. DN':>7s} {'ledare':>7s} {'fästa':>7s} {'tvetydiga':>10s} {'utan':>6s} "
          f"{'fästgrad':>9s} {'olösta':>7s} {'åtgärda':>8s} {'noterat':>8s}")
    agg = {k: 0 for k in ("labels", "with_dn", "leaders", "verified", "ambiguous", "none")}
    for r in rows:
        k = r["reach"]
        v = {n: (k.get(n) or 0) for n in agg}
        for n in agg:
            agg[n] += v[n]
        att = v["verified"] + v["ambiguous"] + v["none"]
        print(f"{r['tag']:{W}s} {v['labels']:6d} {v['with_dn']:7d} {v['leaders']:7d} {v['verified']:7d} "
              f"{v['ambiguous']:10d} {v['none']:6d} {v['verified'] / att if att else 0:9.1%} "
              f"{k['unresolved'] or 0:7d} {k['blocking'] or 0:8d} {k['advisory'] or 0:8d}")
    att = agg["verified"] + agg["ambiguous"] + agg["none"]
    print(f"{'ALLA':{W}s} {agg['labels']:6d} {agg['with_dn']:7d} {agg['leaders']:7d} {agg['verified']:7d} "
          f"{agg['ambiguous']:10d} {agg['none']:6d} {agg['verified'] / att if att else 0:9.1%}")
    print("\nDe två talen som betyder något står längst till höger i första tabellen: täckningen ska stiga, "
          "falskt ägda meter ska ligga vid noll. Ett fall som inte gick att avgöra ska hamna bland de tvetydiga "
          "eller olösta - aldrig bland de mätta.")

    json.dump(rows, open(blind_path.replace(".json", "-metrics.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or all_tags())
