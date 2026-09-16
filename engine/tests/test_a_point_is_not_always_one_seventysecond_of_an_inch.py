"""Sidans egen enhet: `/UserUnit`, och varför hela mängden hänger på den.

Allt i motorn räknar i PDF-punkter, och skalan gör om punkter till meter genom att en punkt är 25,4/72 mm på
papperet. Det stämmer för varje ritning som lästs hittills, men det är sidans beslut, inte en naturlag:
`/UserUnit` är rätten att säga att en enhet är något annat, och stora format använder den ibland just för att
talen annars blir för stora.

Biblioteket räknar inte om geometrin efter den - `page.rect` är punkter rakt av - så en ritning som skriver 2
skulle mätas dubbelt fel utan att en enda siffra ser konstig ut. Det är den värsta sorten av fel: rätt utseende,
fel mängd.

Ingen av de 59 lästa ritningarna skriver någon `/UserUnit`, så det här provet kan inte ställas mot ett verkligt
blad. Det är avsiktligt en syntetisk sida: spärren finns för en ritning som ännu inte kommit, och den ska vara
provad innan den kommer.
"""
import os

import pymupdf
import pytest

from vvs_engine.pdf.extract import extract_document
from vvs_engine.measure.scale import MM_PER_PT, discover_scale


def _sheet(path: str, user_unit=None, width=1684, height=1191) -> str:
    """En A1-liknande sida med en skaltext och, om det begärs, en egen enhet."""
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)
    page.insert_text((100, 100), "SKALA 1:50", fontsize=14)
    sh = page.new_shape()                       # ritat bläck, annars läser motorn inte sidan som en ritning
    for i in range(6):
        sh.draw_line((200 + 40 * i, 300), (200 + 40 * i, 900))
    sh.finish(color=(0, 0, 0), width=1.4)
    sh.commit()
    if user_unit is not None:
        doc.xref_set_key(page.xref, "UserUnit", str(user_unit))
    doc.save(path)
    doc.close()
    return path


def _mpp(path: str):
    doc = extract_document(path, pages=[0])
    page = doc.pages[0]
    from vvs_engine.text.searchable import searchable_rows
    rows = searchable_rows(page)
    return page, discover_scale(page, rows)


def test_a_page_without_the_key_reads_one_and_measures_as_before(tmp_path):
    """Det normala fallet. Nyckeln saknas, enheten är 1, och ingenting ändras."""
    page, sc = _mpp(_sheet(os.path.join(tmp_path, "utan.pdf")))
    assert page.info.user_unit == 1.0
    assert sc.meters_per_pt is not None
    assert sc.meters_per_pt == pytest.approx(50 * MM_PER_PT / 1000.0, rel=1e-6)
    assert "UserUnit" not in (sc.reason or "")


def test_a_page_that_writes_two_measures_twice_as_long(tmp_path):
    """Sidan säger att en enhet är två punkter. Då är varje sträcka dubbelt så lång i verkligheten."""
    page, sc = _mpp(_sheet(os.path.join(tmp_path, "tva.pdf"), user_unit=2))
    assert page.info.user_unit == 2.0
    assert sc.meters_per_pt == pytest.approx(2 * 50 * MM_PER_PT / 1000.0, rel=1e-6)
    assert "UserUnit" in (sc.reason or "")        # och läsningen säger varför, i stället för att bara bli dubbelt


def test_a_key_that_cannot_be_read_is_treated_as_absent(tmp_path):
    """Att gissa på en faktor som hela mängden multipliceras med vore värre än att inte veta."""
    page, _ = _mpp(_sheet(os.path.join(tmp_path, "skrap.pdf"), user_unit="/Skräp"))
    assert page.info.user_unit == 1.0


def test_a_negative_or_zero_unit_is_not_used(tmp_path):
    """Noll skulle göra varje sträcka noll meter lång. Det är inte ett mått, det är ett trasigt fält."""
    page, _ = _mpp(_sheet(os.path.join(tmp_path, "noll.pdf"), user_unit=0))
    assert page.info.user_unit == 1.0
