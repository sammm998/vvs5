"""Tonen bär systemet, tjockleken bär dimensionen - och att det blev så är mätt, inte valt.

Bladet säger två saker om varje rör: vilket system det tillhör och vilken dimension det har. Båda vill synas i
överlägget, och färgen räcker inte till båda. Mätt med databildsverktygets egen mätare, alla par, ljust läge:

    8 toner   ->  ΔE 19,3 normalseende, 10,7 vid färgblindhet   (golven är 15 och 8)
    10 toner  ->  ΔE 13,6 / 7,9
    12 toner  ->  ΔE 12,4 / 6,9                                 <- så många hade paletten förut

och att därtill stega ljusheten inom varje ton för dimensionen kollapsar alltihop: ±0,03 ger värsta par
ΔE 1,4. Fyrtio färger går inte att skilja åt i det utrymme åtta nätt och jämnt får plats i.

Alltså fick dimensionen linjebredden, som stod oanvänd och som ritningen själv använder för samma sak.
Påståendena är skrivna i TypeScript där koden lever (frontend/src/palette.ts) och körs i node; provet här är
sändebudet.
"""
import os
import subprocess

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FRONT = os.path.join(ROOT, "frontend")
ESBUILD = os.path.join(FRONT, "node_modules", ".bin", "esbuild")


@pytest.mark.skipif(not os.path.exists(ESBUILD), reason="frontend/node_modules saknas")
def test_one_hue_one_system_one_width_one_size(tmp_path):
    out = str(tmp_path / "palette.test.js")
    b = subprocess.run([ESBUILD, "src/palette.test.ts", "--bundle", "--platform=node", "--format=cjs",
                        f"--outfile={out}", "--log-level=warning"],
                       cwd=FRONT, capture_output=True, text=True, timeout=120)
    assert b.returncode == 0, b.stderr
    r = subprocess.run(["node", out], capture_output=True, text=True, timeout=120)
    failed = [ln for ln in r.stdout.splitlines() if ln.startswith("FEL")]
    assert r.returncode == 0 and not failed, "\n".join(failed) + "\n" + r.stderr[-800:]
    assert "alla påståenden höll" in r.stdout
