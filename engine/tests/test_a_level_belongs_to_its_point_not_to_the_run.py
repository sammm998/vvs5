"""Nivåtalet hör till punkten där ritningen skrev det - aldrig till stråket som helhet.

En självfallsledning faller. Samma rör bär `VG+1,54` vid ett golvbrunnsläge och `VG+1,48` femton meter längre
fram, och båda är sanna om sin punkt. Att hänga ett av dem på hela röret - som färg, som tjocklek, som en
kolumn med ett enda tal - vore att påstå att röret ligger på en enda nivå, och det säger ritningen inte.

Därför gäller två saker, och de prövas här:

  1. varje ankare bär de nivåtal som stod i dess egen etikettenhet, så att bladet kan visa dem där de står;
  2. ingenting av det blir mängd. Nivåtalen får inte röra en enda vågrät meter - den lodräta mängden har sitt
     eget bevis (två nivåtal med samma tagg på samma rör) och räknas där, inte här.
"""
import os

import pymupdf

from vvs_engine.output.artifacts import sheet_reading
from vvs_engine.pdf.extract import extract_document
from vvs_engine.pipeline import analyze_page


def _with_levels(src: str, dst: str) -> str:
    """Samma ritning med nivåtal skrivna under etiketterna - och en andra etikett längre fram på samma rör.

    Två nivåtal på ETT rör är hela poängen: det är där ett tal slutar beskriva stråket och skillnaden mellan
    dem blir fallet. En ritning med ett tal per rör skulle låta testet gå igenom utan att pröva något.
    """
    doc = pymupdf.open(src)
    page = doc[0]
    shape = page.new_shape()
    page.insert_text((150, 212), "VG+1.54", fontsize=10, fontname="helv")
    page.insert_text((470, 424), "VG+1.48", fontsize=10, fontname="helv")
    # samma ledning, längre fram: eget namn, egen hänvisning ned till rör 1, eget nivåtal
    page.insert_text((470, 200), "KV01-X7-40-W40", fontsize=10, fontname="helv")
    page.insert_text((470, 212), "VG+1.42", fontsize=10, fontname="helv")
    shape.draw_line((470, 202), (550, 202)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    shape.draw_line((550, 202), (540, 300)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    shape.draw_line((539, 299), (541, 301)); shape.finish(width=0.72, color=(0, 0, 0), closePath=False)
    shape.commit()
    doc.save(dst)
    doc.close()
    return dst


def _levels_only(src: str, dst: str) -> str:
    """Samma ritning, samma etiketter, bara nivåtalen tillagda: den enda skillnaden som ska prövas."""
    doc = pymupdf.open(src)
    page = doc[0]
    page.insert_text((150, 212), "VG+1.54", fontsize=10, fontname="helv")
    page.insert_text((470, 424), "VG+1.48", fontsize=10, fontname="helv")
    doc.save(dst)
    doc.close()
    return dst


def _read(path: str):
    doc = extract_document(path)
    pa = analyze_page(doc.pages[0])
    return pa, doc


def test_the_level_the_drawing_wrote_follows_the_anchor_it_was_written_at(synthetic_pdf, tmp_path):
    path = _with_levels(synthetic_pdf, os.path.join(tmp_path, "levels.pdf"))
    pa, doc = _read(path)
    art = sheet_reading(pa, doc)

    anchors = art["pipe-code-anchors.json"]["anchors"]
    assert anchors, "ritningen har etiketter som når rör: annars prövar testet ingenting"
    assert all("elevations" in a for a in anchors), "varje ankare ska säga vilka nivåtal som stod vid det"

    with_level = [a for a in anchors if a["elevations"]]
    assert with_level, "nivåtalet under etiketten ska följa med ankaret"
    for a in with_level:
        for e in a["elevations"]:
            assert e["tag"] == "VG"
            assert e["unit"] == "m", "ett tal med decimaltecken är meter; enheten gissas inte"
            assert min(abs(e["value"] - v) for v in (1.54, 1.48, 1.42)) < 0.01


def test_a_level_never_becomes_a_horizontal_metre(synthetic_pdf, tmp_path):
    """Samma ritning med och utan nivåtal ska ge samma vågräta mängd, rad för rad."""
    plain, _ = _read(synthetic_pdf)
    with_lv, _ = _read(_levels_only(synthetic_pdf, os.path.join(tmp_path, "levels2.pdf")))

    def metres(pa):
        return {r["designation"]: round(r["confirmed_horizontal_m"], 6) for r in pa.quantities}

    assert metres(plain), "utan rader säger jämförelsen ingenting"
    assert metres(with_lv) == metres(plain)


def test_two_levels_on_one_run_are_the_fall_and_nothing_else(synthetic_pdf, tmp_path):
    """Den lodräta mängden kommer ur skillnaden mellan två nivåtal på samma rör - inte ur ett av dem."""
    path = _with_levels(synthetic_pdf, os.path.join(tmp_path, "levels3.pdf"))
    pa, _ = _read(path)
    seen = 0
    for m in pa.measures:
        ev = m.vertical_evidence or {}
        if not ev:
            continue
        assert ev["kind"] == "elevation_difference_between_anchors"
        assert len(ev["values"]) >= 2, "ett ensamt nivåtal är ingen höjd: det behövs två för en skillnad"
        assert abs(m.vertical_m - (max(ev["values"]) - min(ev["values"]))) < 1e-6
        seen += 1
    assert seen, "ritningen måste ha ett rör med två nivåtal, annars prövar testet ingenting"
