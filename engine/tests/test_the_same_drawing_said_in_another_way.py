"""Metamorfiska prov: samma ritning uttryckt annorlunda ska mäta likadant.

Spec avsnitt M frågar efter dem, och de är en annan sorts prov än de andra. Ett vanligt prov säger vad svaret
ska bli. Ett metamorfiskt prov säger att **två indata som betyder samma sak ska ge samma svar** - utan att
någonsin behöva veta vad svaret är. Det är precis vad som behövs här, eftersom ingen kan skriva ned rätt mängd
för en syntetisk ritning utan att räkna ut den på samma sätt som motorn, och ett prov som räknar som motorn
prövar bara sin egen räkning.

Fyra omskrivningar som inte ändrar vad ritningen betyder:

* **dela en dragen linje i två eller tre kollineära bitar** - CAD-exporter gör det hela tiden;
* **rita samma stråk åt andra hållet** - riktningen är exportörens sak;
* **kasta om vilken ordning etiketterna skrivs i** - samma;
* och åt andra hållet: **slå ihop bitarna igen**.

Delningen är den viktigaste, och den är varför filen finns. Ett T mitt på en sträcka delar linjen inne i
motorn, och båda bitarna behåller sitt ursprungs `pid#seg_index`. Det fick villkoret "ett intervall, en ägare"
att larma på en ritning där ingenting var fel, eftersom källsträckans namn inte namnger ett atomärt intervall.
Ett prov av det här slaget hade fällt antagandet direkt.

**En omskrivning som inte är en omskrivning.** Att dela en STRECKAD linje är inte samma ritning: strecken
börjar om vid delningen, och det ritade bläcket blir verkligen ett annat. Mätt på det här bladet skiljer det
52 mm. Därför delas ett heldraget rör här, och det är inte en förenkling utan skillnaden mellan att pröva
motorn och att pröva sin egen provuppställning.
"""
import os

import pymupdf
import pytest

from vvs_engine.pdf.extract import extract_document
from vvs_engine.pipeline import analyze_page

from conftest import make_dashed_line

TOL_M = 0.001            # en millimeter: rundningen i en punkt, inte en meter

WHOLE = [((100, 300), (600, 300))]
IN_TWO = [((100, 300), (350, 300)), ((350, 300), (600, 300))]
IN_THREE = [((100, 300), (250, 300)), ((250, 300), (430, 300)), ((430, 300), (600, 300))]
BACKWARDS = [((600, 300), (100, 300))]


def _sheet(path, pipe1, labels_first=True):
    """Samma blad som `synthetic_pdf`, men med rör 1 heldraget och möjligt att skriva i bitar.

    Rör 2 är streckat och rörs inte: bladet ska fortfarande vara den ritning de andra proven känner igen."""
    doc = pymupdf.open()
    page = doc.new_page(width=842, height=595)
    shape = page.new_shape()
    for a, b in pipe1:
        shape.draw_line(a, b)
        shape.finish(width=1.44, color=(0, 0, 0), closePath=False)
    make_dashed_line(shape, (400, 300), (400, 500))

    def label_one():
        page.insert_text((150, 200), "KV01-X7-40-W40", fontsize=10, fontname="helv")
        for s, e in (((150, 202), (230, 202)), ((230, 202), (260, 300)), ((259, 299), (261, 301))):
            shape.draw_line(s, e)
            shape.finish(width=0.72, color=(0, 0, 0), closePath=False)

    def label_two():
        page.insert_text((470, 400), "VS21-S13", fontsize=10, fontname="helv")
        page.insert_text((480, 412), "15", fontsize=10, fontname="helv")
        for s, e in (((480, 414), (495, 414)), ((480, 414), (400, 450)), ((399, 449), (401, 451))):
            shape.draw_line(s, e)
            shape.finish(width=0.72, color=(0, 0, 0), closePath=False)

    for fn in ((label_one, label_two) if labels_first else (label_two, label_one)):
        fn()
    page.insert_text((100, 560), "SKALA 1:50", fontsize=10, fontname="helv")
    for i in range(6):
        page.insert_text((300 + i * 56.69, 560), str(i), fontsize=8, fontname="helv")
    shape.draw_line((302, 566), (302 + 5 * 56.69, 566))
    shape.finish(width=1.0, color=(0, 0, 0), closePath=False)
    shape.commit()
    doc.save(path)
    doc.close()
    return path


def _metres(path):
    pa = analyze_page(extract_document(path, pages=[0]).pages[0])
    rows = {q["designation"]: q["confirmed_horizontal_m"] for q in pa.quantities
            if (q.get("confirmed_horizontal_m") or 0) > 0}
    # Ett metamorfiskt prov som jämför två tomma mängder passerar utan att pröva något. Underlaget kontrolleras
    # därför här, en gång, i stället för att varje prov får lita på att bladet alls blev läst.
    assert rows, "bladet gav inga meter: provet hade jämfört två tomheter"
    return rows, (pa.takeoff_journal or {}).get("check", {})


def _same(a, b):
    assert set(a) == set(b), f"olika beteckningar fick meter: {sorted(a)} mot {sorted(b)}"
    for k in a:
        assert a[k] == pytest.approx(b[k], abs=TOL_M), f"{k}: {a[k]} mot {b[k]}"


def test_a_run_drawn_in_two_pieces_measures_the_same_as_one(tmp_path):
    """Det provet som skulle ha fällt antagandet att källsträckans namn namnger ett intervall."""
    hel, _ = _metres(_sheet(os.path.join(tmp_path, "hel.pdf"), WHOLE))
    delad, kontroll = _metres(_sheet(os.path.join(tmp_path, "tva.pdf"), IN_TWO))
    _same(hel, delad)
    assert kontroll.get("state") == "PASS"          # och villkoret larmar inte på delningen


def test_three_pieces_measure_the_same_as_one(tmp_path):
    """Två delningar är inte svårare än en - men om delningen kostar något syns det tydligare."""
    hel, _ = _metres(_sheet(os.path.join(tmp_path, "h3.pdf"), WHOLE))
    tre, _ = _metres(_sheet(os.path.join(tmp_path, "tre.pdf"), IN_THREE))
    _same(hel, tre)


def test_a_run_drawn_backwards_measures_the_same(tmp_path):
    """Åt vilket håll exportören drar linjen är dess sak och inte ritningens."""
    fram, _ = _metres(_sheet(os.path.join(tmp_path, "fram.pdf"), WHOLE))
    bak, _ = _metres(_sheet(os.path.join(tmp_path, "bak.pdf"), BACKWARDS))
    _same(fram, bak)


def test_the_order_the_labels_are_written_in_does_not_change_the_metres(tmp_path):
    """Vilken etikett som råkar behandlas först får inte avgöra vem som äger vad."""
    a, _ = _metres(_sheet(os.path.join(tmp_path, "la.pdf"), WHOLE, labels_first=True))
    b, _ = _metres(_sheet(os.path.join(tmp_path, "lb.pdf"), WHOLE, labels_first=False))
    _same(a, b)


def test_splitting_a_dashed_line_is_not_the_same_drawing(tmp_path):
    """Gränsen för vad som är en omskrivning, mätt och inte antagen.

    Strecken börjar om vid delningen, så det ritade bläcket blir ett annat. Provet står här för att ingen
    senare ska "rätta" de andra proven genom att dela ett streckat rör och undra varför de blir röda."""
    def dashed(path, pieces):
        doc = pymupdf.open()
        page = doc.new_page(width=842, height=595)
        sh = page.new_shape()
        for a, b in pieces:
            make_dashed_line(sh, a, b)
        sh.commit()
        doc.save(path)
        doc.close()
        d = extract_document(path, pages=[0]).pages[0]
        return sum(s.length for p in d.paths if p.width for s in p.segs)

    hel = dashed(os.path.join(tmp_path, "s_hel.pdf"), WHOLE)
    delad = dashed(os.path.join(tmp_path, "s_delad.pdf"), IN_TWO)
    assert abs(hel - delad) > 1.0, "delningen av en streckad linje ändrade inte bläcket - då gäller inte skälet"
