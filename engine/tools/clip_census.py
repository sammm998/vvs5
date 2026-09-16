"""Vad av en ritnings bläck som aldrig når papperet - och beviset för att vi läser klippningen rätt.

En PDF kan rita mer än den visar. CAD-exporten lägger ut hela xref:en och klipper sedan bort det som ligger
utanför planens ram, och det bortklippta finns kvar i filen som fullvärdig geometri. Läser man `get_drawings()`
utan att bry sig om klippningen mäter man rör som ingen någonsin ser.

Det här verktyget räknar hur mycket det rör sig om. Men dess egentliga uppgift är den omvända: att försöka
**motbevisa sin egen klippbindning**, för en felaktig bindning raderar synliga rörmeter, och det är ett värre
fel än det den rättar.

Provet är ett rutnät över bladet. Varje ruta får tre svar - bär rågeometrin bläck här, bär den klippta
geometrin bläck här, och målar renderaren något här? De omtvistade rutorna är de där rågeometrin säger bläck
och den klippta säger tomt. Är bindningen rätt ska renderaren vara tom i precis dem. Provets känslighet mäts
samtidigt på rutorna där båda är överens: hittar det inte bläck där bevisar dess tystnad ingenting.

    python3 engine/tools/clip_census.py [pdf ...]

Skriver en rad per blad och en sammanfattning. Inget i motorn ändras härifrån.
"""
import math
import os
import sys

import numpy as np
import pymupdf
from shapely.geometry import LineString, Polygon

CELL = 4.0          # pt: rutans sida - grovt nog att gå fort, fint nog att skilja två rör åt
SCALE = 2           # bildpunkter per pt i kontrollrenderingen
DARK = 170          # gråvärde under detta räknas som bläck
MIN_DARK = 3        # så många mörka bildpunkter krävs för att kalla en ruta bläckig


def clip_polygon(clip: dict):
    """Klippbanans yta som en geometri, eller None när den inte beskriver någon.

    Varje delbana är en egen ring och de förenas; att slå ihop deras punkter till EN ring vore nonsens så fort
    klippet består av mer än en form. Och en fyrhörning skrivs ul, ur, ll, lr - läser man dem i den ordningen
    får man en rosett som korsar sig själv, med noll area. Den ordningen kostade mig en hel mätning: ytan blev
    en fjärdedel av den rätta och tusentals synliga vägar såg dolda ut.
    """
    rings = []
    for it in clip.get("items") or []:
        if it[0] == "re":
            r = it[1]
            rings.append([(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)])
        elif it[0] == "qu":
            q = it[1]
            rings.append([(q.ul.x, q.ul.y), (q.ur.x, q.ur.y), (q.lr.x, q.lr.y), (q.ll.x, q.ll.y)])
    lines = [it for it in (clip.get("items") or []) if it[0] == "l"]
    if lines:
        pts: list[tuple[float, float]] = []
        for it in lines:
            for p in (it[1], it[2]):
                if not pts or abs(p.x - pts[-1][0]) > 1e-9 or abs(p.y - pts[-1][1]) > 1e-9:
                    pts.append((p.x, p.y))
        if len(pts) >= 3:
            rings.append(pts)
    polys = []
    for ring in rings:
        g = Polygon(ring)
        if not g.is_valid:
            g = g.buffer(0)
        if not g.is_empty and g.area > 0:
            polys.append(g)
    if not polys:
        return None
    out = polys[0]
    for p in polys[1:]:
        out = out.union(p)
    return out


def path_segments(d: dict) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Vägens ritade sträckor som räta bitar. En kurva tas mellan sina ändpunkter - grovt, men det här är en
    räkning av var bläck finns, inte en mätning av längd."""
    out = []
    for it in d.get("items") or []:
        if it[0] == "l":
            out.append(((it[1].x, it[1].y), (it[2].x, it[2].y)))
        elif it[0] == "c":
            out.append(((it[1].x, it[1].y), (it[4].x, it[4].y)))
        elif it[0] == "re":
            r = it[1]
            c = [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1), (r.x0, r.y0)]
            out += list(zip(c, c[1:]))
    return out


def visible_parts(seg, area):
    """Sträckans synliga delar. Utan klippyta är hela sträckan synlig."""
    a, b = seg
    if area is None:
        return [seg]
    g = LineString([a, b]).intersection(area)
    parts = []
    for piece in (g.geoms if hasattr(g, "geoms") else [g]):
        if piece.geom_type == "LineString" and piece.length > 0:
            cs = list(piece.coords)
            parts += list(zip(cs, cs[1:]))
    return parts


def census(pdf_path: str, page_no: int = 0) -> dict:
    with pymupdf.open(pdf_path) as doc:
        page = doc[page_no]
        ext = page.get_drawings(extended=True)
        W = int(page.rect.width / CELL) + 1
        H = int(page.rect.height / CELL) + 1
        raw = np.zeros((H, W), bool)
        vis = np.zeros((H, W), bool)

        def stamp(grid, a, b):
            n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 1.5) + 1)
            t = np.linspace(0.0, 1.0, n + 1)
            cx = ((a[0] + (b[0] - a[0]) * t) / CELL).astype(int)
            cy = ((a[1] + (b[1] - a[1]) * t) / CELL).astype(int)
            m = (cx >= 0) & (cx < W) & (cy >= 0) & (cy < H)
            grid[cy[m], cx[m]] = True

        area = None
        n_paths = raw_pt = vis_pt = 0.0
        n_paths = 0
        hidden_paths = 0
        clipped_paths = 0
        hidden_by_layer: dict[str, int] = {}
        for d in ext:
            if d.get("type") == "clip":
                area = clip_polygon(d)
                continue
            if d.get("type") not in ("s", "f", "fs"):
                continue
            segs = path_segments(d)
            if not segs:
                continue
            n_paths += 1
            length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs)
            raw_pt += length
            seen = 0.0
            for a, b in segs:
                if a == b:
                    continue
                stamp(raw, a, b)
                for u, v in visible_parts((a, b), area):
                    stamp(vis, u, v)
                    seen += math.hypot(v[0] - u[0], v[1] - u[1])
            vis_pt += seen
            if length > 1e-9 and seen <= 1e-9:
                hidden_paths += 1
                key = d.get("layer") or ""
                hidden_by_layer[key] = hidden_by_layer.get(key, 0) + 1
            elif seen < length - 1e-6:
                clipped_paths += 1

        pix = page.get_pixmap(matrix=pymupdf.Matrix(SCALE, SCALE))
        img = (np.frombuffer(pix.samples, np.uint8)
               .reshape(pix.height, pix.stride)[:, :pix.width * pix.n]
               .reshape(pix.height, pix.width, pix.n))
        dark = img[:, :, 0].astype(np.int16) < DARK
        ph = pw = int(CELL * SCALE)
        Hc, Wc = dark.shape[0] // ph, dark.shape[1] // pw
        ink = dark[:Hc * ph, :Wc * pw].reshape(Hc, ph, Wc, pw).sum(axis=(1, 3)) >= MIN_DARK

        h, w = min(H, Hc), min(W, Wc)
        R, V, I = raw[:h, :w], vis[:h, :w], ink[:h, :w]
        disputed = R & ~V
        n_disp = int(disputed.sum())
        n_disp_ink = int((disputed & I).sum())
        n_vis = int(V.sum())
        n_vis_ink = int((V & I).sum())
        sensitivity = n_vis_ink / n_vis if n_vis else 0.0
        # Tre skilda utfall, och de får inte blandas ihop. Ett blad där klippningen inte döljer något ger
        # inga omtvistade rutor - då finns ingenting att pröva, vilket varken är ett fel eller ett bevis. Och
        # ett prov som inte hittar bläck ens där båda läsningarna är överens ser inte bläck alls; dess tystnad
        # bevisar då ingenting.
        verdict = ("INGET KLIPPT" if n_disp == 0
                   else "OKONKLUSIVT" if sensitivity < 0.5
                   else "FALSK" if n_disp_ink > 0.10 * n_disp else "HÅLLER")
        return {"sheet": os.path.basename(pdf_path), "page": page_no, "paths": n_paths,
                "raw_pt": round(raw_pt, 1), "visible_pt": round(vis_pt, 1),
                "hidden_share": round(1 - vis_pt / raw_pt, 4) if raw_pt else None,
                "hidden_paths": hidden_paths, "partly_clipped": clipped_paths,
                "hidden_by_layer": dict(sorted(hidden_by_layer.items(), key=lambda kv: -kv[1])[:6]),
                "cells_disputed": n_disp, "cells_disputed_with_ink": n_disp_ink,
                "probe_sensitivity": round(sensitivity, 4), "verdict": verdict}


def main(argv: list[str]) -> int:
    paths = argv or [f"/home/user/vvs5/data/dev/DRAWING_{t}.pdf" for t in ("A", "B", "C")]
    rows = []
    for p in paths:
        if not os.path.isfile(p):
            print(f"{os.path.basename(p):24} saknas", flush=True)
            continue
        r = census(p)
        rows.append(r)
        print(f"{r['sheet']:24} dolt {r['hidden_share']:6.2%}  dolda vägar {r['hidden_paths']:5}  "
              f"delvis {r['partly_clipped']:4}  omtvistade rutor {r['cells_disputed']:6} "
              f"varav bläck {r['cells_disputed_with_ink']:5}  känslighet {r['probe_sensitivity']:5.1%}  "
              f"-> {r['verdict']}", flush=True)
    bad = [r for r in rows if r["verdict"] in ("FALSK", "OKONKLUSIVT")]
    proven = [r for r in rows if r["verdict"] == "HÅLLER"]
    print("\n" + (f"bindningen bevisad på {len(proven)} blad, inget att pröva på {len(rows) - len(proven)}"
                  if rows and not bad
                  else f"EJ BEVISAD på {len(bad)} blad: " + ", ".join(f"{r['sheet']} ({r['verdict']})" for r in bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
