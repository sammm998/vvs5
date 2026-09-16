"""Mängdjournalen: en summa som går att öppna, och två villkor som säger till när den inte går ihop.

En mängdrad är ett tal. Talet går att lita på precis så länge man litar på hela kedjan bakom det, och när en
rad ser fel ut finns det inget att öppna. Journalen är den öppningen: en post per atomärt intervall, med ägare,
längd och skäl.

Två villkor gör den till mer än en logg:

* **mängden ska gå att räkna om ur journalen** - annars är antingen raden eller journalen fel;
* **ett intervall får ha en ägare** - samma ritade segment under två rör är dubbelräkning, och det är det fel
  som är svårast att se i en summa, för båda raderna ser rimliga ut var för sig.

Journalen ändrar ingen mängd. Den skriver ned vad läsningen gjorde och säger till när det inte går ihop. En
journal som rättar tyst vore ingen journal.
"""
from dataclasses import dataclass, field

from vvs_engine.measure.journal import BRIDGED, DRAWN, build, check


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
    source_segments: list
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


def _row(base, dn, total):
    return {"base": base, "dn": dn, "confirmed_total_m": total}


def test_the_sum_of_the_journal_is_the_quantity_row():
    """Grundvillkoret. Går summan inte ihop är en av de två fel, och det ska synas som ett brott."""
    p = _Pipe("pp1", _Ident("KV1-X7", 16), ["path_a#0", "path_a#1"])
    m = _Measure(p, horizontal_m=10.0)
    j = build([m], mpp=0.01)
    assert sum(e["metres"] for e in j["entries"]) == 10.0
    assert j["by_identity"]["KV1-X7|DN16"] == 10.0
    assert check(j, [_row("KV1-X7", 16, 10.0)])["state"] == "PASS"


def test_a_row_the_journal_cannot_account_for_is_a_breach():
    p = _Pipe("pp1", _Ident("KV1-X7", 16), ["path_a#0"])
    j = build([_Measure(p, horizontal_m=10.0)], mpp=0.01)
    r = check(j, [_row("KV1-X7", 16, 17.5)])          # raden påstår mer än intervallen bär
    assert r["state"] == "FAIL"
    b = [x for x in r["breaches"] if x["invariant"] == "mangden_gar_att_rakna_om_ur_journalen"]
    assert b and b[0]["examples"][0]["skillnad_m"] == -7.5


def test_the_same_drawn_segment_under_two_pipes_is_caught():
    """Dubbelräkningen. Två rör som äger samma ritade segment ger meter i två rader för ett streck."""
    a = _Pipe("pp1", _Ident("S2-P5", 110), ["delad#0", "egen_a#0"])
    b = _Pipe("pp2", _Ident("S2-P5", 75), ["delad#0", "egen_b#0"])
    j = build([_Measure(a, horizontal_m=4.0), _Measure(b, horizontal_m=6.0)], mpp=0.01)
    r = check(j, [_row("S2-P5", 110, 4.0), _row("S2-P5", 75, 6.0)])
    assert r["state"] == "FAIL"
    brott = [x for x in r["breaches"] if x["invariant"] == "ett_intervall_en_agare"]
    assert brott and brott[0]["n"] == 1
    assert brott[0]["examples"]["delad#0"] == ["pp1", "pp2"]


def test_a_bridged_gap_is_counted_but_kept_apart_from_drawn_ink():
    """Luckan räknas - röret går ju vidare - men den är inte ritat bläck och ska inte se ut som det."""
    p = _Pipe("pp1", _Ident("VS1-S13", 12), ["path_a#0"], bridged_gap_pt=200.0)
    j = build([_Measure(p, horizontal_m=10.0)], mpp=0.01)
    kinds = {e["kind"]: e["metres"] for e in j["entries"]}
    assert kinds[BRIDGED] == 2.0 and kinds[DRAWN] == 8.0
    assert sum(e["metres"] for e in j["entries"]) == 10.0     # summan är fortfarande radens


def test_the_second_edge_of_a_double_line_is_recorded_but_never_counted():
    """Dubbellinjens andra kant är samma rör. Den ska synas i journalen och inte i summan."""
    p = _Pipe("pp2", _Ident("VS1-S13", 12), [])
    j = build([_Measure(p, twin_of="pp1", twin_pdf_units=500.0)], mpp=0.01)
    assert len(j["entries"]) == 1
    assert j["entries"][0]["counted"] is False
    assert j["by_identity"] == {}


def test_without_a_scale_the_interval_exists_but_carries_no_metre():
    """Ingen skala är inte noll meter. Sträckan finns, den går inte att mäta, och det står i journalen."""
    p = _Pipe("pp1", _Ident("KV1-X7", 16), ["path_a#0"])
    j = build([_Measure(p, horizontal_m=None)], mpp=None)
    e = j["entries"][0]
    assert e["metres"] is None and e["counted"] is False
    assert j["by_identity"] == {}
