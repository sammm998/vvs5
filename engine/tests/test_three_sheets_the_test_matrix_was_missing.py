"""Tre fall ur specens provmatris som saknades: hårfin penna, två skalregioner, överlappande system.

De övriga sju - klippning, rotation, korsning, T-gren, hänvisningslinje, reducering och tvilling - hade redan
egna syntetiska prov. De här tre hade det inte, och var och en av dem kan gå fel utan att synas: en hårfin
penna har bredd noll och kan därför falla ur pennbegreppet helt; två skalor på ett blad kan ge en mängd i fel
storleksordning utan att något ser konstigt ut; och två system ritade ovanpå varandra kan smälta ihop till ett.

Proven är KARAKTÄRISERANDE. De skriver ned vad motorn faktiskt gör, inte vad jag hoppas att den gör. Där
svaret är ett ärligt nej står det som ett ärligt nej.
"""
import os

import pymupdf
import pytest

from vvs_engine.pdf.extract import extract_document
from vvs_engine.text.searchable import searchable_rows


def _sheet(path, draw, width=842, height=595, rotate=0):
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)
    if rotate:
        page.set_rotation(rotate)
    draw(page)
    doc.save(path)
    doc.close()
    return path


# ---------------------------------------------------------------------------------------------- hårfin penna
def test_a_hairline_pen_is_still_a_pen(tmp_path):
    """Bredd noll betyder "tunnast möjliga streck", inte "ingen penna".

    En hårfin export sätter `w 0` på varje drag. Faller bredden bort ur pennans identitet hamnar rörlagret och
    arkitektens lager i samma familj, och då kan ingenting skiljas åt. Provet kräver bara att strecken finns
    kvar som geometri med sin bredd läst som 0 - att de inte tappas för att de saknar bredd.
    """
    # PyMuPDF normaliserar `finish(width=0)` till 1.0, så hårfinheten måste skrivas i innehållsströmmen
    # själv: `0 w` är det CAD-exporten lägger ut, och det är den filen som ska läsas.
    path = os.path.join(tmp_path, "hairline.pdf")
    doc0 = pymupdf.open()
    page = doc0.new_page(width=842, height=595)
    sh = page.new_shape()                       # en ritning för att alls få en innehållsström
    sh.draw_line((0, 0), (1, 1))
    sh.finish(width=1.0, color=(0, 0, 0), closePath=False)
    sh.commit()
    xref = page.get_contents()[0]
    doc0.update_stream(xref, b"0 w 0 0 0 RG 100 295 m 600 295 l S "
                             b"0 w 0.5 0.5 0.5 RG 100 275 m 600 275 l S ")
    doc0.save(path)
    doc0.close()

    doc = extract_document(path)
    paths = doc.pages[0].paths
    assert len(paths) >= 2, "hårfina drag får inte försvinna ur extraktionen"
    assert all(p.width is not None for p in paths), "bredden ska läsas, även när den är noll"
    # och två hårfina drag i olika färg är två pennor, inte en
    pens = {(round(p.width or 0, 3), str(p.color)) for p in paths}
    assert len(pens) >= 2, f"färgen skiljer pennorna åt även vid bredd noll: {pens}"


# ------------------------------------------------------------------------------------------- två skalregioner
def test_two_scales_on_one_sheet_are_not_silently_averaged(tmp_path):
    """Ett blad med både 1:50 och 1:20 utskrivet.

    Det farliga svaret är ett tal. Väljer läsningen en av dem, eller värre, något däremellan, blir halva
    bladets mängd fel i storleksordning och ingenting på skärmen visar det. Rätt svar är att säga att bladet
    säger emot sig själv.
    """
    def draw(page):
        page.insert_text((100, 100), "SKALA 1:50", fontsize=10, fontname="helv")
        page.insert_text((500, 100), "SKALA 1:20", fontsize=10, fontname="helv")
        s = page.new_shape()
        s.draw_line((100, 300), (600, 300))
        s.finish(width=1.44, color=(0, 0, 0), closePath=False)
        s.commit()

    from vvs_engine.measure.scale import discover_scale
    doc = extract_document(_sheet(os.path.join(tmp_path, "tvaskalor.pdf"), draw))
    pg = doc.pages[0]
    sc = discover_scale(pg, searchable_rows(pg))
    assert sc.state != "VERIFIED", (
        f"två motstridiga skalor får inte ge ett verifierat tal - fick {sc.state} {sc.meters_per_pt}")
    assert sc.reason, "och läsningen ska säga varför den inte avgör"


# --------------------------------------------------------------------------------------- överlappande system
def test_two_systems_drawn_over_each_other_do_not_become_one(tmp_path):
    """Samma sträcka, två pennor: ett rör i varje system, ritade ovanpå varandra.

    Det händer på riktigt där två system följs åt i samma schakt. Slås de ihop försvinner det ena systemets
    hela längd ur mängden, och den kvarvarande raden ser fullständig ut.
    """
    def draw(page):
        s = page.new_shape()
        s.draw_line((100, 300), (600, 300))
        s.finish(width=1.44, color=(0, 0, 0), closePath=False)
        s.draw_line((100, 300.4), (600, 300.4))       # praktiskt taget ovanpå, annan penna
        s.finish(width=2.04, color=(0, 0, 0), closePath=False)
        s.commit()

    doc = extract_document(_sheet(os.path.join(tmp_path, "overlapp.pdf"), draw))
    paths = doc.pages[0].paths
    fams = {(round(p.width or 0, 2), str(p.color)) for p in paths}
    assert len(paths) >= 2, "båda dragen ska finnas kvar"
    assert len(fams) >= 2, f"två pennor ska förbli två familjer, inte en: {fams}"
    # och geometrin ska inte ha vikts ihop till en enda sträcka
    total = sum(sg.length for p in paths for sg in p.segs)
    assert total > 900, f"båda sträckornas längd ska finnas kvar, fick {total:.1f} pt"
