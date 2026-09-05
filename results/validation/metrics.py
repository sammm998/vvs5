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
import sys

import openpyxl

MATCH_TOL = 0.05        # a designation's metres count as owned up to 5 % over the facit; past that it is invented


def fl(v):
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return 0.0


def facit(tag):
    ws = openpyxl.load_workbook(f"/home/user/vvs5/data/validation_{tag}/facit.xlsx", data_only=True).worksheets[0]
    hdr = [str(v or "").strip() for v in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
    col = {h: i for i, h in enumerate(hdr)}
    c_subj, c_len = col.get("Ämne", 2), col.get("Längd", 7)
    out = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        s = r[c_subj]
        if not s or s == "Markera":
            continue
        name = str(s).replace(" Vertikal", "").replace(" VERTIKAL", "").strip()
        out[name] = out.get(name, 0.0) + fl(r[c_len])
    return out


def score_one(tag, rec):
    fh = facit(tag)
    ours = {q["designation"]: q["confirmed_total_m"] for q in rec["quantities"]}
    # a row of 0.00 m is not a claim about the drawing, it is a designation read with no metres behind it
    ours = {k: v for k, v in ours.items() if v > 0.005}
    fh = {k: v for k, v in fh.items() if v > 0.005}

    hit = set(ours) & set(fh)
    invented_names = set(ours) - set(fh)
    missed_names = set(fh) - set(ours)

    owned = sum(min(ours[k], fh[k] * (1 + MATCH_TOL)) for k in hit)
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
        "metres": {"facit": sum(fh.values()), "owned": owned, "false_owned": false_owned, "missed": missed,
                   "coverage": owned / sum(fh.values()) if fh else 0.0,
                   "false_rate": false_owned / sum(fh.values()) if fh else 0.0},
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

    print(f"{'':4s} {'skala':10s} {'bet. P':>7s} {'bet. R':>7s} "
          f"{'facit m':>9s} {'ägda m':>9s} {'falska m':>9s} {'missade m':>10s} {'täckning':>9s} {'falskt':>8s}")
    for r in rows:
        d, m = r["designations"], r["metres"]
        print(f"{r['tag']:4s} {str(r['scale']):10s} {d['precision']:7.1%} {d['recall']:7.1%} "
              f"{m['facit']:9.2f} {m['owned']:9.2f} {m['false_owned']:9.2f} {m['missed']:10.2f} "
              f"{m['coverage']:9.1%} {m['false_rate']:8.1%}")

    tot_f = sum(r["metres"]["facit"] for r in rows)
    tot_o = sum(r["metres"]["owned"] for r in rows)
    tot_x = sum(r["metres"]["false_owned"] for r in rows)
    tot_m = sum(r["metres"]["missed"] for r in rows)
    n_hit = sum(r["designations"]["correct"] for r in rows)
    n_found = sum(r["designations"]["found"] for r in rows)
    n_facit = sum(r["designations"]["facit"] for r in rows)
    print(f"{'ALLA':4s} {'':10s} {n_hit / n_found if n_found else 0:7.1%} {n_hit / n_facit if n_facit else 0:7.1%} "
          f"{tot_f:9.2f} {tot_o:9.2f} {tot_x:9.2f} {tot_m:10.2f} "
          f"{tot_o / tot_f if tot_f else 0:9.1%} {tot_x / tot_f if tot_f else 0:8.1%}")

    print("\nvad som saknas och vad som hittats på:")
    for r in rows:
        d = r["designations"]
        if d["invented"] or d["missed"]:
            print(f"  {r['tag']}: hittade-på {d['invented'] or '-'}   saknade {d['missed'] or '-'}")

    print("\nhur långt läsningen kom - och vad den lät bli att gissa:")
    print(f"{'':4s} {'bet.':>6s} {'m. DN':>7s} {'ledare':>7s} {'fästa':>7s} {'tvetydiga':>10s} {'utan':>6s} "
          f"{'fästgrad':>9s} {'olösta':>7s} {'åtgärda':>8s} {'noterat':>8s}")
    agg = {k: 0 for k in ("labels", "with_dn", "leaders", "verified", "ambiguous", "none")}
    for r in rows:
        k = r["reach"]
        v = {n: (k.get(n) or 0) for n in agg}
        for n in agg:
            agg[n] += v[n]
        att = v["verified"] + v["ambiguous"] + v["none"]
        print(f"{r['tag']:4s} {v['labels']:6d} {v['with_dn']:7d} {v['leaders']:7d} {v['verified']:7d} "
              f"{v['ambiguous']:10d} {v['none']:6d} {v['verified'] / att if att else 0:9.1%} "
              f"{k['unresolved'] or 0:7d} {k['blocking'] or 0:8d} {k['advisory'] or 0:8d}")
    att = agg["verified"] + agg["ambiguous"] + agg["none"]
    print(f"{'ALLA':4s} {agg['labels']:6d} {agg['with_dn']:7d} {agg['leaders']:7d} {agg['verified']:7d} "
          f"{agg['ambiguous']:10d} {agg['none']:6d} {agg['verified'] / att if att else 0:9.1%}")
    print("\nDe två talen som betyder något står längst till höger i första tabellen: täckningen ska stiga, "
          "falskt ägda meter ska ligga vid noll. Ett fall som inte gick att avgöra ska hamna bland de tvetydiga "
          "eller olösta - aldrig bland de mätta.")

    json.dump(rows, open(blind_path.replace(".json", "-metrics.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or ["A", "C", "D", "E"])
