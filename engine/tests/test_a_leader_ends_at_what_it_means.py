"""En hänvisningslinje slutar vid det den menar.

Drar ritaren linjen från etiketten förbi ett rör och fram till ett annat sätter hon ett streck där linjen
korsar och ett streck där den slutar. Det senare är beteckningens rör; det förra säger bara var linjen gick
fram. Läsningen tog båda som fäste - och då fick stammen radiatoranslutningens dimension: fyra DN15-etiketter
streckade stammen i förbifarten på väg till sitt eget stråk, och en 35 meter lång stam blev DN15 i hela sin
längd medan DN22 fick under två av sina åttiotre meter.

Regeln har en gräns, och den gränsen är själva skälet till att korsstrecket finns: staplar bladet flera rader
över en bunt är korsstrecken fästet - linjen korsar varje rör den namnger och streckar det. Då rörs ingenting.
"""
from types import SimpleNamespace

from vvs_engine.semantics.attachment import Contact, the_run_the_leader_ends_on


def _c(kind, pid):
    return Contact(point=(0.0, 0.0), kind=kind, family="f", pid=pid, seg_index=0, distance=0.0)


def _row(multiplier=1):
    return SimpleNamespace(did="d1", multiplier=multiplier)


def _leader(end_marks=1):
    return SimpleNamespace(end_marks=[object()] * end_marks)


def test_korsstrecket_ar_inte_fastet_nar_linjen_markerar_sitt_eget_slut():
    kept = the_run_the_leader_ends_on([_row()], _leader(), [_c("end_tick", "stammen"), _c("crossing_tick", "grenen")])
    assert [c.pid for c in kept] == ["stammen"]


def test_slutstrecket_racker_aven_nar_det_inte_traffar_nagot_ror():
    """Ritaren har sagt var linjen pekar. Att etiketten inte nådde fram är ärligare än att ge den stammen."""
    assert the_run_the_leader_ends_on([_row()], _leader(), [_c("crossing_tick", "stammen")]) == []


def test_en_omarkerad_linje_som_slutar_strax_bortom_far_behalla_sina_streck():
    """Utan slutstreck är korsstrecken allt ritaren skrivit, och att kasta dem vore att tappa röret."""
    cs = [_c("crossing_tick", "stammen"), _c("crossing_tick", "grannen")]
    assert the_run_the_leader_ends_on([_row()], _leader(end_marks=0), cs) == cs


def test_en_staplad_etikett_over_en_bunt_ror_ingenting():
    """Flera rader: korsstrecken är fästet, ett per rör linjen namnger."""
    cs = [_c("end_tick", "a"), _c("crossing_tick", "b"), _c("crossing_tick", "c")]
    assert the_run_the_leader_ends_on([_row(), _row(), _row()], _leader(), cs) == cs


def test_en_rad_som_namnger_flera_ror_ror_ingenting():
    """'3x' på raden säger att linjen menar tre rör, och då är korsstrecken fästet."""
    cs = [_c("end_tick", "a"), _c("crossing_tick", "b"), _c("crossing_tick", "c")]
    assert the_run_the_leader_ends_on([_row(multiplier=3)], _leader(), cs) == cs


def test_andra_fastvagar_ror_inte_regeln():
    """Symbol- och buntkontakter är egna vägar in och har inget med korsstreck att göra."""
    cs = [_c("via_symbol", "a"), _c("via_symbol", "b")]
    assert the_run_the_leader_ends_on([_row()], _leader(), cs) == cs
