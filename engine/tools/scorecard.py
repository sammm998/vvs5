"""Varje rad på varje blad, läsningen mot referensen - hela korpusen i en tabell.

`facit_metrics.py` ger betyget per blad. Det här ger raderna: för varje beteckning på varje blad vad
referensen säger, vad läsningen mätte, skillnaden och vilken klass raden hamnade i. Det är den tabell man
läser när frågan är "vilka rader skiljer sig, och med hur mycket" och inte "hur bra är det".

Två sammanställningar följer med, båda räknade ur samma rader:

  * **flyttat inom stammen** - meter som ligger på fel dimension av rätt stam (`VS1-S13-15` mot `VS1-S13-22`),
    och åt vilket håll de flyttade. Det är ett fel summan per blad inte kan visa, eftersom den tar ut sig
    själv: en rad över och en rad under blir noll.
  * **de tjugo största avvikelserna** i hela korpusen, med blad, namn och skäl.

    python3 engine/tools/scorecard.py <gateNN-facit-metrics.json> [ut.md]

Läser referensmått (via facit_metrics.py:s utdata), aldrig importerat av motorn.
"""
from __future__ import annotations

import collections
import json
import re
import sys


def stem_and_dn(name: str) -> tuple[str, int | None]:
    """`VS1-S13-22` -> (`VS1-S13`, 22). Ett namn utan avslutande tal har ingen dimension i namnet."""
    m = re.match(r"^(.*)-(\d+)$", name)
    return (m.group(1), int(m.group(2))) if m else (name, None)


def rows_of(metrics: dict) -> list[dict]:
    out = []
    for sh in metrics["sheets"]:
        for name, info in sh["extent"].items():
            ref = info.get("reference_m") or 0.0
            ours = info.get("ours_m") or 0.0
            out.append({"sheet": sh["tag"], "style": sh.get("style", ""), "name": name,
                        "reference_m": ref, "ours_m": ours, "diff_m": round(ours - ref, 2),
                        "class": info["class"], "failure": info["failure"]})
    return out


def moved_within_stem(rows: list[dict]) -> dict:
    """Meter som ligger på fel dimension av rätt stam, per blad och stam, och åt vilket håll."""
    per: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for r in rows:
        stem, dn = stem_and_dn(r["name"])
        if dn is None:
            continue
        per[(r["sheet"], stem)].append({**r, "dn": dn})
    cases = []
    for (sheet, stem), items in per.items():
        if len(items) < 2:
            continue
        short = sum(max(0.0, i["reference_m"] - i["ours_m"]) for i in items)
        over = sum(max(0.0, i["ours_m"] - i["reference_m"]) for i in items)
        moved = min(short, over)
        if moved < 2.0:
            continue
        gains = [i["dn"] for i in items if i["ours_m"] > i["reference_m"] * 1.1]
        loses = [i["dn"] for i in items if i["ours_m"] < i["reference_m"] * 0.9]
        way = ""
        if gains and loses:
            way = "finer_takes" if min(gains) < max(loses) else "coarser_takes"
        cases.append({"sheet": sheet, "stem": stem, "moved_m": round(moved, 1), "direction": way,
                      "rows": sorted((i["name"], round(i["reference_m"], 1), round(i["ours_m"], 1)) for i in items)})
    cases.sort(key=lambda c: -c["moved_m"])
    total = sum(c["moved_m"] for c in cases)
    finer = sum(c["moved_m"] for c in cases if c["direction"] == "finer_takes")
    coarser = sum(c["moved_m"] for c in cases if c["direction"] == "coarser_takes")
    return {"total_m": round(total, 1), "finer_takes_m": round(finer, 1), "coarser_takes_m": round(coarser, 1),
            "sheets": len({c["sheet"] for c in cases}), "cases": cases}


def markdown(metrics: dict, rows: list[dict], moved: dict) -> str:
    T = metrics["totals"]
    L = [f"# Radtabell - {metrics.get('gate', '?')}", "",
         f"{T['sheets']} blad, {len(rows)} rader. Referens {T['reference_m']} m, ägt {T['owned_m']} m, "
         f"falskt {T['false_m']} m. **Täckning {T['COVERAGE'] * 100:.2f} %**, "
         f"**falskt ägande {T['FALSE_OWNERSHIP'] * 100:.2f} %**.", ""]

    L += ["## Meter på fel dimension av rätt stam", "",
          f"`{moved['total_m']} m` ligger under fel dimension av en stam referensen känner, på {moved['sheets']} blad.",
          f"Av dem går `{moved['finer_takes_m']} m` åt ett håll (den klenare dimensionen tar den grövres stråk) "
          f"och `{moved['coarser_takes_m']} m` åt det andra.", "",
          "| Blad | Stam | Flyttat m | Riktning | Rader (namn, referens, vår) |", "|---|---|---:|---|---|"]
    for c in moved["cases"][:20]:
        rr = ", ".join(f"`{n}` {a}→{b}" for n, a, b in c["rows"])
        L.append(f"| {c['sheet']} | {c['stem']} | {c['moved_m']} | {c['direction'] or '—'} | {rr} |")
    L.append("")

    worst = sorted(rows, key=lambda r: -abs(r["diff_m"]))[:20]
    L += ["## De tjugo största avvikelserna", "",
          "| Blad | Beteckning | Referens | Vår | Skillnad | Klass | Skäl |", "|---|---|---:|---:|---:|---|---|"]
    for r in worst:
        L.append(f"| {r['sheet']} | `{r['name']}` | {r['reference_m']:.1f} | {r['ours_m']:.1f} | "
                 f"{r['diff_m']:+.1f} | {r['class']} | {r['failure']} |")
    L.append("")

    L += ["## Varje rad, blad för blad", ""]
    for sh in metrics["sheets"]:
        mine = [r for r in rows if r["sheet"] == sh["tag"]]
        m = sh["metres"]
        L += [f"### {sh['tag']} — täckning {m['coverage'] * 100:.1f} %, falskt ägande {m['false_ownership'] * 100:.1f} %"
              f" ({m['reference']:.1f} m referens, {m['owned']:.1f} m ägt)", "",
              "| Beteckning | Referens | Vår | Skillnad | Klass |", "|---|---:|---:|---:|---|"]
        for r in sorted(mine, key=lambda r: (-abs(r["diff_m"]), r["name"])):
            L.append(f"| `{r['name']}` | {r['reference_m']:.1f} | {r['ours_m']:.1f} | {r['diff_m']:+.1f} | {r['class']} |")
        L.append("")
    return "\n".join(L)


def main(argv: list[str]) -> None:
    src = argv[0]
    metrics = json.load(open(src, encoding="utf-8"))
    rows = rows_of(metrics)
    moved = moved_within_stem(rows)
    out = argv[1] if len(argv) > 1 else src.replace(".json", "-scorecard.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(markdown(metrics, rows, moved))
    with open(out.replace(".md", ".json"), "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, "moved_within_stem": moved}, fh, ensure_ascii=False, indent=1)
    T = metrics["totals"]
    print(f"{len(rows)} rader på {T['sheets']} blad -> {out}")
    print(f"  täckning {T['COVERAGE'] * 100:.2f} %  falskt ägande {T['FALSE_OWNERSHIP'] * 100:.2f} %")
    print(f"  fel dimension av rätt stam: {moved['total_m']} m "
          f"(klenare tar {moved['finer_takes_m']}, grövre tar {moved['coarser_takes_m']})")


if __name__ == "__main__":
    main(sys.argv[1:])
