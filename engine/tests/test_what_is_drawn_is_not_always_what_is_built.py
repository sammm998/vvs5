"""En ritning visar mer än entreprenaden, och geometrin skiljer inte.

Befintliga ledningar som ska vara kvar, ledningar som ska rivas och prefabricerade badrum vars rör redan
sitter från fabrik ritas med samma streck som det som ska byggas. Räknas de som ny meter blir mängden för
stor; undantas de i tysthet blir den för liten. Båda felen ser likadana ut på skärmen: inget.

Regeln är densamma som för allt annat på ett blad: ritningen avgör. En parentes betyder befintligt DÄR
FÖRKLARINGEN SÄGER DET. Säger den ingenting är markeringen okänd, och en okänd markering går till granskning
i stället för att tyst bli det ena eller det andra.
"""
from dataclasses import dataclass

from vvs_engine.semantics.scope import (BEFINTLIG, NY, OKAND, PREFAB, RIVNING,
                                        markers_from_legend, scope_of, strip_marker)


@dataclass
class _Rad:
    code: str
    description: str


class _Forklaring:
    def __init__(self, *rader):
        self.entries = [_Rad(c, d) for c, d in rader]


def test_a_marker_the_sheet_never_explains_is_unknown_and_goes_to_review():
    """Kärnan. Utan förklaring är parentesen inte ett bevis - varken för eller emot."""
    s = scope_of("(S1)", markers={})
    assert s.scope == OKAND and s.review is True
    assert s.marker == "()"
    assert s.scope != BEFINTLIG and s.scope != NY      # varken undantagen eller inräknad i tysthet


def test_the_sheet_that_says_what_its_parenthesis_means_is_believed():
    """Sjukhusförklaringarnas egen rad: "( ) AVSER BEFINTLIGT"."""
    markers = markers_from_legend(_Forklaring(("( )", "AVSER BEFINTLIGT")))
    assert markers == {"()": BEFINTLIG}
    s = scope_of("(KV-15)", markers)
    assert s.scope == BEFINTLIG and s.review is False
    assert "parentes" in s.why


def test_a_designation_without_any_marker_is_new_and_says_nothing_else():
    for text in ("KV1-X7-40/W", "VS1-S13-12/W", "S3-R8-160"):
        s = scope_of(text, {"()": BEFINTLIG})
        assert s.scope == NY and s.marker is None and s.review is False


def test_prefab_units_are_factory_scope_when_the_legend_defines_them():
    """`(PB)` på ett element: rören inuti är fabriksleverans, inte platsbyggd meter."""
    markers = markers_from_legend(_Forklaring(("PB", "PREFABRICERAT BADRUM")))
    assert markers == {"PB": PREFAB}
    assert scope_of("S-STAM (PB)", markers).scope == PREFAB
    assert scope_of("KOPPLINGSSKÅP (PB)", markers).scope == PREFAB


def test_an_undefined_suffix_code_is_unknown_not_guessed_as_prefab():
    """Två bokstäver inom parentes är inte automatiskt prefab - koderna krockar över kategorier."""
    s = scope_of("S-STAM (PB)", markers={})
    assert s.scope == OKAND and s.review is True and s.marker == "(PB)"


def test_demolition_and_existing_are_different_answers():
    markers = markers_from_legend(_Forklaring(("BEF", "BEFINTLIG LEDNING"),
                                              ("R", "LEDNING SOM SKA RIVAS")))
    assert markers["BEF"] == BEFINTLIG and markers["R"] == RIVNING
    assert scope_of("KV1-25 BEF", markers).scope == BEFINTLIG


def test_the_same_pipe_in_two_scopes_is_one_identity_not_two():
    """`(S1)` och `S1` är samma ledning i två omfattningar. Nyckeln att jämföra på är densamma."""
    assert strip_marker("(S1)") == "S1"
    assert strip_marker("S-STAM (PB)") == "S-STAM"
    assert strip_marker("KV1-25 BEF") == "KV1-25"
    assert strip_marker("VS1-S13-12/W") == "VS1-S13-12/W"       # orörd när ingen markering finns


def test_a_legend_that_says_nothing_about_scope_yields_no_markers():
    """Vanliga förklaringsrader ska inte råka bli omfattningsmarkeringar."""
    markers = markers_from_legend(_Forklaring(("KV", "TAPPKALLVATTEN"), ("S13", "ROSTFRITT STÅL")))
    assert markers == {}


def test_no_legend_at_all_is_not_an_error():
    assert markers_from_legend(None) == {}
    assert scope_of("KV1-25", None).scope == NY


# --------------------------------------------------------------------------------------------------------
# Inkopplingen: att modulen kan klassificera hjälper ingen om mängdraden inte bär svaret.

def test_every_designation_on_a_sheet_gets_a_scope_keyed_by_its_own_row():
    """Två rader kan skriva samma kod och bära olika markering. Det är RADEN som har en omfattning."""
    from vvs_engine.semantics.scope import read_designations, summary

    class _Des:
        def __init__(self, did, raw):
            self.did, self.raw_text = did, raw

    des = [_Des("d1", "(S1)"), _Des("d2", "S1"), _Des("d3", "S-STAM (PB)")]
    r = read_designations(des, _Forklaring(("( )", "AVSER BEFINTLIGT")))
    assert r["d1"].scope == BEFINTLIG
    assert r["d2"].scope == NY                       # samma kod, ingen markering, annan omfattning
    assert r["d3"].scope == OKAND and r["d3"].review is True
    s = summary(r)
    assert s["per_scope"] == {BEFINTLIG: 1, NY: 1, OKAND: 1}
    assert s["markers_not_explained"] == ["(PB)"]
    assert s["n_marked"] == 2


def test_the_reading_carries_scope_onto_the_quantity_row_without_moving_a_metre():
    """Kärnan i inkopplingen: raden får en omfattning, och summan är densamma som förut.

    Metrarna mäts och tillhör samma rad. Det som tillkommer är att raden säger vilken omfattning den hör till,
    så att den som läser mängden kan skilja det som ska byggas från det som bara står på ritningen.
    """
    from vvs_engine.cli import _scope_counts, _scope_metres

    rader = [{"designation": "KV1-25", "confirmed_total_m": 10.0, "scope": NY},
             {"designation": "(S1)", "confirmed_total_m": 4.0, "scope": BEFINTLIG},
             {"designation": "S-STAM", "confirmed_total_m": 2.0, "scope": OKAND}]
    assert _scope_counts(rader) == {NY: 1, BEFINTLIG: 1, OKAND: 1}
    assert _scope_metres(rader) == {NY: 10.0, BEFINTLIG: 4.0, OKAND: 2.0}
    # summan rörs inte: uppdelningen är en uppdelning, inte ett avdrag
    assert sum(_scope_metres(rader).values()) == sum(r["confirmed_total_m"] for r in rader)


def test_a_row_with_no_marker_anywhere_on_the_sheet_is_plain_new_build():
    from vvs_engine.cli import _scope_counts
    assert _scope_counts([{"confirmed_total_m": 5.0}]) == {"NY": 1}


# --------------------------------------------------------------------------------------------------------
# Luftningens bokstav: `110L` är dimension 110 på en luftledning, inte en oläslig token.

def test_a_dimension_figure_may_carry_the_vent_letter():
    from vvs_engine.semantics.grammar import dimension_figure
    assert dimension_figure("110") == (110, None)
    assert dimension_figure("110L") == (110, "L")
    assert dimension_figure("100V") == (100, "V")
    assert dimension_figure("110l") == (110, "L")       # gemen bokstav är samma bokstav
    assert dimension_figure("X7") == (None, None)       # det här tolkar inte, det läser
    assert dimension_figure("") == (None, None)


def test_the_vent_letter_is_not_part_of_the_number_and_not_thrown_away():
    """Båda felen finns: att läsa bokstaven som siffra, och att kasta den.

    Läses `110L` som ett tal faller dimensionen bort helt - och på korpusen hamnade metrarna då på en rad utan
    DN, oprissatt, medan samma rör med bar siffra fick en egen rad. En beteckning blev två. Kastas bokstaven i
    stället försvinner att röret är en luftledning.
    """
    from vvs_engine.semantics.grammar import dimension_figure
    v, vent = dimension_figure("110L")
    assert v == 110 and vent == "L"
    assert v != 110110 and str(v) == "110"


def test_only_the_two_letters_the_drawing_language_uses_are_read_as_vent():
    """L för luftning och V för vent. Andra bokstäver är något annat och ska inte tvingas till en dimension."""
    from vvs_engine.semantics.grammar import dimension_figure
    for t in ("110W", "110K", "110A", "110S"):
        assert dimension_figure(t) == (None, None), t
