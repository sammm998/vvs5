"""Vilket svar ett blad får ska inte bero på vilken process det råkade läsas i.

Buntutjämningen - den som avgör vilken linje i en staplad etikett som är vilken - läste sina domäner medan
den ändrade dem. Villkoren gicks igenom i ordningen hos en `set` av systemnamn, och den ordningen är Pythons
slumpade strängnycklar, alltså olika i varje process. Två läsningar av SAMMA fil med SAMMA kod gav därför
olika meter: på W-50-1-A0122 blev en hänvisning VERIFIERAD i en process och TVETYDIG i en annan, och 6,3 m
flyttade sig mellan två beteckningar. Ingen fråga om ritningen hade ändrats - bara vilket mynt processen
råkade singla.

Utjämningen räknar nu i rundor mot en ögonblicksbild och lägger ihop slutsatserna med mängdoperationer, som
inte bryr sig om ordning. Proven nedan permuterar allt som går att permutera och kräver ett enda svar.
"""
import itertools
import random

from vvs_engine.pipeline import _bundle_domains


def _case(pieces, systems):
    return (list(pieces), list(systems))


def test_a_bundle_the_sheet_settles_is_settled_the_same_way_in_every_order():
    """Två block över samma två stycken: det ena namnger KV och VV, det andra bara VV på det ena stycket."""
    A, B = ("fam", 1), ("fam", 2)
    cases = [_case([A, B], ["KV1", "VV1"]), _case([B, A], ["VV1", "KV1"])]
    want = _bundle_domains(cases, {A: {"KV1"}})
    assert want[A] == {"KV1"} and want[B] == {"VV1"}
    for order in itertools.permutations(cases):
        assert _bundle_domains(list(order), {A: {"KV1"}}) == want


def test_a_symmetric_sheet_settles_nothing_however_the_constraints_are_ordered():
    """Inget stycke är fastnaglat och båda blocken säger samma två system: att byta dem överallt duger lika
    bra. Ritningen har inte sagt vilket som är vilket, och då ska ingenting sägas."""
    A, B = ("fam", 1), ("fam", 2)
    cases = [_case([A, B], ["KV1", "VV1"]), _case([A, B], ["KV1", "VV1"])]
    d = _bundle_domains(cases)
    assert d[A] == {"KV1", "VV1"} and d[B] == {"KV1", "VV1"}       # ingen har ett enda möjligt system
    for order in itertools.permutations(cases):
        assert _bundle_domains(list(order)) == d


def test_three_systems_in_a_chain_reach_the_same_fixpoint_from_any_order():
    """Kedjan: A är fastnaglat som KV, vilket lämnar VV och VVC på B och C, och B:s block nämner inte VVC."""
    A, B, C = ("fam", 1), ("fam", 2), ("fam", 3)
    cases = [_case([A, B, C], ["KV1", "VV1", "VVC1"]), _case([A, B], ["KV1", "VV1"])]
    want = _bundle_domains(cases, {A: {"KV1"}})
    assert want[A] == {"KV1"} and want[B] == {"VV1"} and want[C] == {"VVC1"}
    for order in itertools.permutations(cases):
        assert _bundle_domains(list(order), {A: {"KV1"}}) == want


def test_the_system_names_own_order_never_decides():
    """Samma fall, men med systemnamnen givna i varje inbördes ordning: svaret är ett."""
    A, B, C = ("fam", 1), ("fam", 2), ("fam", 3)
    want = None
    for perm in itertools.permutations(["KV1", "VV1", "VVC1"]):
        cases = [_case([A, B, C], list(perm)), _case([A, B], [p for p in perm if p != "VVC1"])]
        got = _bundle_domains(cases, {A: {"KV1"}})
        want = got if want is None else want
        assert got == want


def test_a_round_that_contradicts_itself_settles_nothing_rather_than_guessing():
    """Just det fall som avgjordes av myntet.

    Bunten har två linjer och etiketten namnger VV och VVC. Men den ena linjen är redan fastnaglad som KV av
    en verifierad etikett någon annanstans - bladet säger emot sig själv. Kvar står ett enda stycke som både
    VV och VVC måste ligga på, vilket ingetdera kan.

    Den gamla koden läste domänen medan den skrev den: det system som råkade komma först ur mängden tog
    stycket, och det andra fann det upptaget. Vilket av dem som vann bestämdes av strängnycklarnas ordning i
    just den processen. Nu blir stycket tomt, ingen rad avgörs, och raden förblir tvetydig - vilket är sant.
    """
    A, B = ("fam", 1), ("fam", 2)
    cases = [_case([A, B], ["VV1", "VVC1"])]
    d = _bundle_domains(cases, {B: {"KV1"}})
    assert d[A] == set() and d[B] == set()        # inget stycke har ett system, alltså avgörs ingen rad
    for order in itertools.permutations(cases):
        assert _bundle_domains(list(order), {B: {"KV1"}}) == d
    for perm in itertools.permutations(["VV1", "VVC1"]):
        assert _bundle_domains([_case([A, B], list(perm))], {B: {"KV1"}}) == d


def test_many_random_bundles_give_one_answer_whatever_the_order():
    """Det generella kravet, inte ett enskilt fall: slumpade bunthögar, permuterade på alla sätt som finns."""
    rng = random.Random(4711)
    for _ in range(40):
        pieces = [("fam", i) for i in range(rng.randint(2, 4))]
        systems = rng.sample(["KV1", "VV1", "VVC1", "VS1"], len(pieces))
        cases = [_case(rng.sample(pieces, len(pieces)), rng.sample(systems, len(systems)))
                 for _ in range(rng.randint(1, 3))]
        pinned = {pieces[0]: {systems[0]}} if rng.random() < 0.5 else {}
        want = _bundle_domains([(list(p), list(s)) for p, s in cases], dict(pinned))
        for order in itertools.permutations(cases):
            assert _bundle_domains([(list(p), list(s)) for p, s in order], dict(pinned)) == want


# --------------------------------------------------------------------------------------------------------
# Provet ovan permuterar listorna, och det är inte där felet satt: en `set` bryr sig inte om i vilken ordning
# man stoppade in något, utan om nycklarnas hash - och den slumpas per process. Samma lista, samma kod, olika
# process, olika ordning. Det går bara att pröva över en processgräns, så det gör det här provet.
_SKRIPT = """
import sys
sys.path.insert(0, {root!r})
from vvs_engine.pipeline import _bundle_domains
A, B = ("fam", 1), ("fam", 2)
d = _bundle_domains([([A, B], ["VV1", "VVC1"])], {{B: {{"KV1"}}}})
print(",".join(sorted(d[A])) or "-")
"""


def test_the_processs_own_string_keys_never_decide_what_a_drawing_says():
    """Samma fall i åtta processer med åtta olika strängnyckelfrön. Ett svar, åtta gånger.

    Med den gamla utjämningen gav det här fallet 'VV1' på frö 0, 1, 2 och 4 och 'VVC1' på 3, 5, 6 och 7. Inte
    en gissning som ibland blev fel, utan samma ritning som mängdades olika beroende på vilken process den
    råkade läsas i - och det syns inte i något tal, för varje enskild körning ser lika säker ut.
    """
    import os
    import subprocess
    import sys

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    svar = set()
    for seed in range(8):
        env = dict(os.environ, PYTHONHASHSEED=str(seed))
        out = subprocess.run([sys.executable, "-c", _SKRIPT.format(root=root)],
                             capture_output=True, text=True, env=env, timeout=120)
        assert out.returncode == 0, out.stderr
        svar.add(out.stdout.strip())
    assert len(svar) == 1, f"samma ritning gav {len(svar)} olika svar: {sorted(svar)}"
