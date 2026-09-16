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
