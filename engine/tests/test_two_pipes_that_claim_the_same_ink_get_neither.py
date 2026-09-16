"""Den transaktionella tilldelningen: hela ägandet ses på en gång, och det omtvistade räknas åt ingen.

Ägandet avgörs i dag löpande - ett rör får sin identitet, nästa får sin - och mängden faller ut ur summan av
det som blev. Där besluten inte rör varandra fungerar det. Där de rör varandra, två rör som båda gör anspråk på
samma bit ritat bläck, finns det ingen punkt i kedjan där någon ser båda anspråken samtidigt, och biten blir
räknad två gånger utan att något larmar.

`measure.commit` är den punkten. Proven här säger vad den ska göra, och minst lika viktigt vad den inte ska:

* två rör som gör anspråk på **samma bit** får ingen av dem räkna den, och biten blir tvetydig med sina
  alternativ - inte tilldelad den ena på en gissning;
* två rör som äger var sin **halva av samma dragna linje** är inget att tvista om. Det är ett T mitt på en
  sträcka, och det är så ritningen ser ut. Ett prov som inte skiljer de två fallen åt skulle godkänna en spärr
  som raderar riktiga meter;
* utfallet får inte bero på i vilken ordning rören råkar komma.
"""
from dataclasses import dataclass, field

from vvs_engine.measure.commit import DISPUTED_REASON, commit
from vvs_engine.pipes.representation import Prim, interval_id
from vvs_engine.geometry.core import Seg


@dataclass
class _Ident:
    base: str
    dn: int | None

    @property
    def key(self):
        return f"{self.base}|DN{self.dn if self.dn is not None else '?'}"


@dataclass
class _Pipe:
    physical_pipe_id: str
    identity: _Ident
    source_intervals: list
    source_segments: list = field(default_factory=list)
    raw_length_pt: float = 0.0
    bridged_gap_pt: float = 0.0
    state: str = "CONFIRMED"
    evidence: list = field(default_factory=list)


@dataclass
class _Measure:
    pipe: _Pipe
    horizontal_pdf_units: float = 0.0
    horizontal_m: float | None = None
    vertical_m: float | None = None
    vertical_evidence: dict | None = None
    twin_of: str | None = None
    twin_pdf_units: float = 0.0


def _row(base, dn, horiz):
    return {"base": base, "dn": dn, "confirmed_horizontal_m": horiz, "confirmed_total_m": horiz,
            "ambiguous_m": 0.0}


def test_a_piece_two_pipes_both_claim_is_counted_for_neither():
    """Tvisten. Fyra meter mot sex, en delad bit - och den biten hamnar i ingens bekräftade mängd."""
    a = _Pipe("pp1", _Ident("S2-P5", 110), ["delad", "egen_a"])
    b = _Pipe("pp2", _Ident("S2-P5", 75), ["delad", "egen_b"])
    rows = [_row("S2-P5", 110, 4.0), _row("S2-P5", 75, 6.0)]
    j = commit([_Measure(a, horizontal_m=4.0), _Measure(b, horizontal_m=6.0)], rows, mpp=0.01)

    assert j["check"]["n_disputed"] == 1
    assert j["disputed"][0]["interval"] == "delad"
    assert j["disputed"][0]["owners"] == ["pp1", "pp2"]
    # halva av vardera rörets mängd låg på den delade biten
    assert rows[0]["confirmed_total_m"] == 2.0 and rows[0]["ambiguous_m"] == 2.0
    assert rows[1]["confirmed_total_m"] == 3.0 and rows[1]["ambiguous_m"] == 3.0
    assert rows[0]["disputed_m"] == 2.0 and rows[1]["disputed_m"] == 3.0
    # ...och villkoret håller efteråt, eftersom ingen räknar den längre
    assert j["check"]["state"] == "PASS"


def test_the_withheld_piece_keeps_its_alternatives_and_its_reason():
    """Att hålla inne utan att säga vad tvisten gällde vore att tappa bort den. Motparten står i posten."""
    a = _Pipe("pp1", _Ident("S2-P5", 110), ["delad"])
    b = _Pipe("pp2", _Ident("S2-P5", 75), ["delad"])
    rows = [_row("S2-P5", 110, 4.0), _row("S2-P5", 75, 6.0)]
    j = commit([_Measure(a, horizontal_m=4.0), _Measure(b, horizontal_m=6.0)], rows, mpp=0.01)

    poster = [e for e in j["entries"] if e["interval"] == "delad"]
    assert len(poster) == 2
    assert all(e["counted"] is False and e["disputed"] is True for e in poster)
    assert all(e["why"] == DISPUTED_REASON for e in poster)
    assert {e["owner"]: e["alternatives"] for e in poster} == {"pp1": ["pp2"], "pp2": ["pp1"]}


def test_two_halves_of_one_drawn_line_are_not_a_dispute():
    """Ett T mitt på en sträcka. Båda bitarna bär samma källsträckas namn och är ändå skilda intervall - och
    hade spärren gått på källsträckans namn hade den raderat meter på en ritning där ingenting är fel."""
    huvud = Prim(prim_id=1, pid="path_x", seg_index=6, seg=Seg(0.0, 0.0, 4.0, 0.0),
                 family="f", layer="L", width=2.0)
    gren = Prim(prim_id=2, pid="path_x", seg_index=6, seg=Seg(4.0, 0.0, 15.0, 0.0),
                family="f", layer="L", width=2.0)
    assert interval_id(huvud) != interval_id(gren)

    a = _Pipe("pp1", _Ident("S2-P5", 110), [interval_id(huvud)])
    b = _Pipe("pp2", _Ident("S2-P5", 75), [interval_id(gren)])
    rows = [_row("S2-P5", 110, 4.0), _row("S2-P5", 75, 11.0)]
    j = commit([_Measure(a, horizontal_m=4.0), _Measure(b, horizontal_m=11.0)], rows, mpp=0.01)

    assert j["check"]["n_disputed"] == 0 and j["check"]["withheld_m"] == 0.0
    assert rows[0]["confirmed_total_m"] == 4.0 and rows[1]["confirmed_total_m"] == 11.0
    assert j["check"]["state"] == "PASS"


def test_the_commit_does_not_depend_on_which_pipe_comes_first():
    """Samma tilldelning, omvänd ordning: samma journal och samma mängd. Annars är besked en slump."""
    def kör(ordning):
        a = _Pipe("pp1", _Ident("S2-P5", 110), ["delad", "egen_a"])
        b = _Pipe("pp2", _Ident("S2-P5", 75), ["delad", "egen_b"])
        ms = [_Measure(a, horizontal_m=4.0), _Measure(b, horizontal_m=6.0)]
        rows = [_row("S2-P5", 110, 4.0), _row("S2-P5", 75, 6.0)]
        j = commit(ms[::ordning], rows, mpp=0.01)
        return (j["disputed"], j["by_identity"], j["withheld"],
                [(r["confirmed_total_m"], r["ambiguous_m"]) for r in rows])

    assert kör(1) == kör(-1)


def test_a_reading_with_nothing_disputed_is_left_exactly_as_it_was():
    """Spärren får inte kosta något där den inte behövs. Ingen tvist, ingen ändrad siffra."""
    a = _Pipe("pp1", _Ident("KV1-X7", 16), ["a1", "a2"])
    b = _Pipe("pp2", _Ident("VV1-X7", 16), ["b1"])
    rows = [_row("KV1-X7", 16, 10.0), _row("VV1-X7", 16, 7.5)]
    före = [dict(r) for r in rows]
    j = commit([_Measure(a, horizontal_m=10.0), _Measure(b, horizontal_m=7.5)], rows, mpp=0.01)

    assert j["check"]["n_disputed"] == 0
    for r, f in zip(rows, före):
        assert {k: v for k, v in r.items() if k != "disputed_m"} == f
        assert r["disputed_m"] == 0.0
    assert j["by_identity"] == {"KV1-X7|DN16": 10.0, "VV1-X7|DN16": 7.5}


def test_withholding_never_takes_more_than_the_row_confirmed():
    """En rad kan inte bli skyldig meter - och när den ändå inte går ihop ska det SYNAS.

    Raden här påstår nio meter som inte finns bland de ritade intervallen. Spärren tar inte mer än vad raden
    har, så raden blir inte negativ; men journalen kan då inte räkna om raden, och det är ett brott mot det
    andra villkoret. Att tysta det genom att låta spärren ta för mycket vore att byta ett synligt fel mot ett
    osynligt."""
    a = _Pipe("pp1", _Ident("S2-P5", 110), ["delad"])
    b = _Pipe("pp2", _Ident("S2-P5", 75), ["delad"])
    rows = [{"base": "S2-P5", "dn": 110, "confirmed_horizontal_m": 0.0, "confirmed_total_m": 9.0,
             "ambiguous_m": 0.0},
            _row("S2-P5", 75, 6.0)]
    j = commit([_Measure(a, horizontal_m=4.0), _Measure(b, horizontal_m=6.0)], rows, mpp=0.01)
    assert rows[0]["confirmed_total_m"] == 9.0 and rows[0]["ambiguous_m"] == 0.0
    assert rows[1]["confirmed_total_m"] == 0.0 and rows[1]["ambiguous_m"] == 6.0
    assert j["check"]["state"] == "FAIL"
    brott = [b for b in j["check"]["breaches"] if b["invariant"] == "mangden_gar_att_rakna_om_ur_journalen"]
    assert brott and brott[0]["examples"][0]["skillnad_m"] == -9.0
