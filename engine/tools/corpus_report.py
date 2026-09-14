"""Vad svepet över hela korpusen gav, som en läsbar sida.

Svepet sparar en rad per ritning medan det går. Det här gör raderna till en text: hur många som gick att läsa,
var skalan kom ifrån, hur långt läsningen kom, och - viktigast - vilka som inte gick och varför. En korpus som
bara redovisas som ett medelvärde döljer just det som är värt att veta.

    python3 tools/corpus_report.py <sweep.json> <ut.md>
"""
from __future__ import annotations

import collections
import json
import sys


def pct(n: int, of: int) -> str:
    return f"{100.0 * n / of:.1f} %".replace(".", ",") if of else "–"


def main() -> None:
    src, out = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as fh:
        rows = list(json.load(fh).values())
    ok = [r for r in rows if r["state"] == "OK"]
    bad = [r for r in rows if r["state"] != "OK"]
    with_m = [r for r in ok if (r.get("confirmed_horizontal_m") or 0) > 0]
    # skalans läge står i läsningens täckningsrad, inte i dokumentets sammanfattning: den senare säger bara
    # vad omgången var enig om
    scale = collections.Counter((r.get("coverage") or {}).get("scale_state") or "–" for r in ok)
    klass = collections.Counter(r["classification"] for r in rows)
    errs = collections.Counter((r.get("error") or "").split(":")[0] for r in bad)
    secs = sorted(r["seconds"] for r in rows)
    L = [
        "# Svep över hela korpusen",
        "",
        f"Varje unik ritnings-PDF som finns lokalt ur ritningsmappen, läst blint: **{len(rows)} filer**, ingen",
        "mängdförteckning öppnad och ingenting jämfört med ett facit. Det som står här är vad läsningen själv",
        "säger. Grindens 59 blad är de som har ett facit att mätas mot; de här är resten av materialet, och",
        "poängen med dem är att en läsning som bara prövas där svaret är känt är prövad på fel ställe.",
        "",
        "## Utfall",
        "",
        "| | antal | andel |",
        "|---|---:|---:|",
        f"| lästa | {len(ok)} | {pct(len(ok), len(rows))} |",
        f"| varav med meter | {len(with_m)} | {pct(len(with_m), len(rows))} |",
        f"| gick inte att läsa | {len(bad)} | {pct(len(bad), len(rows))} |",
        "",
        f"Tid per blad: median {secs[len(secs) // 2]:.0f} s, längsta {secs[-1]:.0f} s." if secs else "",
        "",
        "## Var skalan kom ifrån",
        "",
        "| läge | blad |",
        "|---|---:|",
    ]
    for k, n in scale.most_common():
        L.append(f"| {k} | {n} |")
    L += ["", "## Material", "", "| klass | filer |", "|---|---:|"]
    for k, n in klass.most_common():
        L.append(f"| {k} | {n} |")
    if bad:
        L += ["", "## Det som inte gick", "", "| fel | filer |", "|---|---:|"]
        for k, n in errs.most_common():
            L.append(f"| {k or '–'} | {n} |")
        L += ["", "De tio första, med namn:", ""]
        for r in bad[:10]:
            L.append(f"- `{r['name']}` ({r['classification']}): {(r.get('error') or '')[:140]}")
    top = sorted(ok, key=lambda r: -(r.get("confirmed_horizontal_m") or 0))[:15]
    L += ["", "## Femton blad med mest bekräftad rörlängd", "",
          "| ritning | meter | rader | beteckningar | skala |", "|---|---:|---:|---:|---|"]
    for r in top:
        L.append(f"| {r['name']} | {r.get('confirmed_horizontal_m', 0):.1f} | {r.get('rows', 0)} | "
                 f"{r.get('designations') or '–'} | {(r.get('coverage') or {}).get('scale_state') or '–'} |")
    zero = [r for r in ok if (r.get("confirmed_horizontal_m") or 0) == 0]
    if zero:
        L += ["", f"## {len(zero)} blad som lästes utan att ge en meter", "",
              "Ett blad utan meter är inte med nödvändighet ett fel: en sektionsritning, ett blad i en annan",
              "disciplin eller en handling utan rör ska ge noll. Skälet står i skalan och i antalet beteckningar.",
              "", "| ritning | beteckningar | skala | skäl |", "|---|---:|---|---|"]
        for r in zero[:25]:
            sc = r.get("coverage") or {}
            L.append(f"| {r['name']} | {r.get('designations') or 0} | {sc.get('scale_state') or '–'} | {sc.get('scale_reason') or '–'} |")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(x for x in L if x is not None) + "\n")
    print(out, len(rows), "rader")


if __name__ == "__main__":
    main()
