"""Ritningsprofilen: hur stort bladet är i förhållande till den ritning toleranserna skrevs för.

Motorns toleranser står i punkter och är skrivna för en A1 med 11-punkters text. Samma ritning nedförminskad
till A3 har hälften så stora avstånd mellan allting, och då snappar samma tolerans ihop det som inte hör ihop.
Profilen mäter den skillnaden.

Proven här handlar mest om vad profilen INTE får göra:

* pappersfaktorn får aldrig röra meter per punkt - skalan kommer ur bladets skaltext och ingen annanstans;
* en texthöjd som ger en orimlig faktor ska ge **ingen** faktor, inte en avhuggen;
* ett litet pappersformat ensamt är inget skäl att skala: en ritning som ritats för A3 från början har text i
  A3-storlek och faktorn 1, och att anta att varje A3 är en förminskad A1 vore en gissning;
* hårfin penna ska räknas som penna, annars blir hårfinhetsmåttet noll just på de blad det finns till för.
"""
from dataclasses import dataclass, field

import pytest

from vvs_engine.profile.style_profile import (FACTOR_MAX, FACTOR_MIN, FALLBACK, MEASURED, REFERENCE_TEXT_PT,
                                              TEXT_GLYPHS, TEXT_MIXED, TEXT_NATIVE, TEXT_UNKNOWN, UNSURE,
                                              paper_format_of, profile_page, tolerance_overrides,
                                              tolerance_scale)
from vvs_engine.rules import BY_ID, RULES
from vvs_engine.geometry.core import Seg


@dataclass
class _Info:
    index: int = 0
    width: float = 2384.0        # A1 liggande i punkter: 841 x 594 mm
    height: float = 1684.0
    rotation: int = 0
    user_unit: float = 1.0


@dataclass
class _Path:
    pid: str
    layer: str = "V-52"
    kind: str = "s"
    width: float = 1.44
    color: tuple = (0.0, 0.0, 0.0)
    closed: bool = False
    n_curves: int = 0
    segs: list = field(default_factory=list)


@dataclass
class _Page:
    info: _Info = field(default_factory=_Info)
    paths: list = field(default_factory=list)
    spans: list = field(default_factory=list)


@dataclass
class _Row:
    height: float
    source: str = "stroke"


@dataclass
class _Des:
    bbox: tuple


def _ink(n=6, width=1.44, layer="V-52"):
    return [_Path(f"p{i}", layer=layer, width=width, segs=[Seg(0, 10 * i, 300, 10 * i)]) for i in range(n)]


def test_an_a1_with_eleven_point_text_is_the_reference_and_scales_nothing():
    """Den ritning toleranserna skrevs för. Faktorn ska vara 1 och ingenting ska skalas."""
    p = _Page(paths=_ink())
    pr = profile_page(p, rows=[_Row(11.0)] * 20, designations=[_Des((0, 0, 40, 11.0))] * 12)
    assert pr.paper_format == "A1"
    assert pr.paper_factor_state == MEASURED
    assert abs(pr.paper_factor - 1.0) < 1e-9
    assert tolerance_scale(pr) == 1.0


def test_a_sheet_with_half_the_text_height_gets_half_the_factor():
    """En nedförminskad ritning: allt är hälften så stort, och toleranserna ska följa med."""
    p = _Page(paths=_ink())
    pr = profile_page(p, rows=[_Row(5.5)] * 20, designations=[_Des((0, 0, 20, 5.5))] * 12)
    assert pr.paper_factor_state == MEASURED
    assert abs(pr.paper_factor - 0.5) < 1e-9


def test_a_text_height_that_gives_an_absurd_factor_gives_no_factor_at_all():
    """En enda felmätt rad får inte kunna fyrdubbla varje tolerans i motorn. Inget tal är bättre än fel tal."""
    p = _Page(paths=_ink())
    pr = profile_page(p, rows=[_Row(60.0)] * 5, designations=[_Des((0, 0, 200, 60.0))] * 5)
    assert pr.paper_factor is None
    assert pr.paper_factor_state == UNSURE
    assert f"[{FACTOR_MIN}, {FACTOR_MAX}]" in pr.paper_factor_reason
    assert tolerance_scale(pr) == 1.0          # ingen faktor betyder toleranserna som de är


def test_a_small_sheet_without_text_is_not_assumed_to_be_a_shrunken_large_one():
    """A3 säger att bladet är litet, inte att texten är det. Formatet ensamt sätter ingen faktor."""
    p = _Page(info=_Info(width=1191.0, height=842.0), paths=_ink())   # A3 i punkter: 420 x 297 mm
    pr = profile_page(p, rows=[], designations=[])
    assert pr.paper_format == "A3"
    assert pr.paper_factor is None and pr.paper_factor_state == FALLBACK
    assert tolerance_scale(pr) == 1.0


def test_the_paper_factor_says_nothing_about_metres_per_point():
    """Gränsen som gör profilen till en profil. Den finns inget fält för, och det är avsiktligt."""
    pr = profile_page(_Page(paths=_ink()), rows=[_Row(5.5)] * 9, designations=[_Des((0, 0, 20, 5.5))] * 9)
    d = pr.as_dict()
    assert not any("meter" in k or "mpp" in k or "scale" in k for k in d)


def test_the_text_mode_says_which_kind_of_text_the_sheet_carries():
    p = _Page(paths=_ink())
    assert profile_page(p, rows=[_Row(11, "text")] * 4).text_mode == TEXT_NATIVE
    assert profile_page(p, rows=[_Row(11, "stroke")] * 4).text_mode == TEXT_GLYPHS
    assert profile_page(p, rows=[_Row(11, "text"), _Row(11, "stroke")]).text_mode == TEXT_MIXED
    assert profile_page(p, rows=[]).text_mode == TEXT_UNKNOWN


def test_a_hairline_pen_is_counted_as_ink_and_shows_up_as_hairline():
    """Bredd noll är tunnast möjliga streck, inte ingen penna. Räknas den som fylld form blir måttet noll
    just på den stil det finns till för."""
    pr = profile_page(_Page(paths=_ink(width=0.0)), rows=[_Row(10.12)] * 8)
    assert pr.n_stroked == 6 and pr.n_filled == 0
    assert pr.hairline_share == 1.0
    assert pr.widths_separate_families is False        # allt är en bredd: bredden skiljer ingenting


def test_two_pens_mean_width_separates_families_and_one_does_not():
    p = _Page(paths=_ink(3, width=1.44) + _ink(3, width=2.28))
    assert profile_page(p, rows=[_Row(11)] * 4).widths_separate_families is True
    assert profile_page(_Page(paths=_ink(6)), rows=[_Row(11)] * 4).widths_separate_families is False


def test_the_pages_own_unit_is_part_of_how_big_the_paper_is():
    """En A1 som skriver /UserUnit 2 är ritad i halva talet och skulle annars läsas som en A3."""
    assert paper_format_of(1192.0, 842.0) == "A3"
    assert paper_format_of(1192.0, 842.0, user_unit=2.0) == "A1"


def test_a_sideways_sheet_measures_the_short_side_of_the_label_box():
    """Elva av de femtionio bladen står på sidan. Höjden är rutans korta sida åt båda hållen."""
    p = _Page(paths=_ink())
    stAende = profile_page(p, rows=[], designations=[_Des((0, 0, 11.0, 40.0))] * 12)
    liggande = profile_page(p, rows=[], designations=[_Des((0, 0, 40.0, 11.0))] * 12)
    assert stAende.text_height_pt == liggande.text_height_pt == 11.0


# ------------------------------------------------------------------------ vilka toleranser faktorn flyttar
def test_a_reference_sheet_moves_no_tolerance_at_all():
    """Faktorn 1 ska inte ge nio värden som råkar vara desamma - den ska ge ingenting.

    Skillnaden syns i registret: ett värde satt till sitt eget förval är ändå ett satt värde, och då kan ingen
    längre se på en läsning om profilen verkade eller inte."""
    pr = profile_page(_Page(paths=_ink()), rows=[], designations=[_Des((0, 0, 40, 11.0))] * 12)
    assert pr.paper_factor == 1.0
    assert tolerance_overrides(pr) == {}


def test_a_half_size_sheet_halves_the_distances_that_follow_the_paper():
    pr = profile_page(_Page(paths=_ink()), rows=[], designations=[_Des((0, 0, 20, 5.5))] * 12)
    ov = tolerance_overrides(pr)
    assert ov, "en faktor på 0,5 ska flytta något"
    for rid, v in ov.items():
        assert v == pytest.approx(float(BY_ID[rid].default) * 0.5, rel=1e-9), rid


def test_only_the_rules_that_say_they_follow_the_paper_are_moved():
    """Gränsen som gör faktorn till en pappersfaktor och inte en generell hopkrympning."""
    pr = profile_page(_Page(paths=_ink()), rows=[], designations=[_Des((0, 0, 20, 5.5))] * 12)
    moved = set(tolerance_overrides(pr))
    assert moved == {r.id for r in RULES if r.scales_with_paper and r.tunable}
    for rid in moved:
        assert BY_ID[rid].unit == "pt"


def test_the_tolerances_that_say_whether_two_strokes_are_the_same_ink_are_left_alone():
    """De följer PENNAN, inte papperet. Att krympa dem med pappersfaktorn vore att byta ut en mätning mot en
    annan storhet som råkar ha samma enhet."""
    pr = profile_page(_Page(paths=_ink()), rows=[], designations=[_Des((0, 0, 20, 5.5))] * 12)
    moved = set(tolerance_overrides(pr))
    for rid in ("semantics.attachment.CONTACT_TOL", "pipes.representation.OVERLAP_OFF",
                "pipes.ownership.SLIVER_RUN", "semantics.attachment.COLLINEAR_OFF",
                "pipes.ownership.BOUNDARY_TOL"):
        assert rid not in moved, rid


def test_no_rule_used_to_read_the_text_is_moved_by_a_factor_taken_from_that_text():
    """Cirkeln. Texthöjden kommer ur beteckningarna, som lästes med de här reglerna - att sedan flytta dem med
    en faktor räknad ur resultatet skulle bara gå genom att läsa bladet två gånger."""
    moved = {r.id for r in RULES if r.scales_with_paper}
    for rid in moved:
        assert not rid.startswith("text."), rid
        assert not rid.startswith("semantics.legend."), rid


def test_a_moved_value_stays_inside_the_rules_own_limits():
    """Registret vet vad som är ett rimligt tal för just den regeln; pappersfaktorn vet bara hur stort bladet
    är. Där de två är oense vinner registret."""
    pr = profile_page(_Page(paths=_ink()), rows=[], designations=[_Des((0, 0, 14, 4.0))] * 12)
    for rid, v in tolerance_overrides(pr).items():
        r = BY_ID[rid]
        assert (r.lo is None or v >= r.lo) and (r.hi is None or v <= r.hi), rid


def test_a_sheet_whose_factor_could_not_be_measured_moves_nothing():
    """Ingen faktor betyder toleranserna som de är - inte en gissad hopkrympning."""
    pr = profile_page(_Page(paths=_ink()), rows=[_Row(60.0)] * 5, designations=[_Des((0, 0, 200, 60.0))] * 5)
    assert pr.paper_factor is None
    assert tolerance_overrides(pr) == {}
