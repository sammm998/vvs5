"""Ett textmått får inte se ut som ett längdmått.

`facit_metrics.py` räknade träffar som `set(facit) & set(vårt)` - en ren namnmängdssnittsmängd. En rad som
läste sin beteckning perfekt och mätte NOLL meter hamnade i den mängden, och gav 100 % recall mot en
referensrad på tio meter. Det är inte ett litet fel i en siffra: det är två helt olika frågor som fått ett
gemensamt namn, och den ena döljer den andra. "Hittade vi beteckningen?" och "mätte vi rätt längd?" måste
kunna svaras var för sig, annars går det inte att veta om en förbättring rör läsningen eller mätningen.

Och en kvot utan nämnare finns inte. Den är varken 0 % eller 100 %, och skrivs som N/A.
"""
import pytest

from tools.facit_metrics import pct, score_sheet


def _run(rows):
    return {"state": "OK", "quantities": [{"designation": d, "confirmed_total_m": m} for d, m in rows],
            "names_read": [d for d, _ in rows], "coverage": {}}


def test_a_row_that_read_its_name_but_measured_nothing_is_not_coverage():
    """Kärnan: tio meter i referensen, noll mätta. Namnet är läst - längden är det inte."""
    s = score_sheet("X", _run([("KV1-X31-16", 0.0)]), {"KV1-X31-16": 10.0}, fold=False)
    assert s["metres"]["coverage"] == 0.0            # ingen längd
    assert s["metres"]["missed"] == 10.0             # och den saknade längden syns
    assert s["designations"]["found"] == 1           # namnet lästes...
    assert s["designations"]["recall"] == 1.0        # ...och textmåttet säger så
    assert s["designations"]["found_with_metres"] == 0     # men ingen bar en meter
    assert s["designations"]["recall_with_metres"] == 0.0


def test_missed_and_extra_length_do_not_cancel_out():
    """Tio meter saknade och tio meter felaktiga är två fel, inte noll fel."""
    s = score_sheet("X", _run([("KV1-X31-16", 0.0), ("KV2-X31-99", 10.0)]),
                    {"KV1-X31-16": 10.0}, fold=False)
    assert s["metres"]["missed"] == 10.0
    assert s["metres"]["wrong_name"] == 10.0         # namn referensen inte har
    assert s["metres"]["over_extent"] == 0.0
    assert s["metres"]["coverage"] == 0.0


def test_a_system_the_reference_never_mengdar_is_set_aside_not_counted_as_wrong():
    """Gränsen för de nya måtten: de gäller referensens systemomfång, och det sägs var meterna tog vägen.

    Referensen mängdar KV. Läser vi VV på samma blad är det inte en felläsning mot den referensen - den har
    inget att säga om VV. De metrarna får varken bli `wrong_name` eller försvinna tyst; de redovisas för sig.
    """
    s = score_sheet("X", _run([("KV1-X31-16", 10.0), ("VV9-Z9-99", 10.0)]),
                    {"KV1-X31-16": 10.0}, fold=False)
    assert s["metres"]["wrong_name"] == 0.0
    assert s["outside_reference_systems"] == {"systems": ["VV"], "m": 10.0}


def test_a_run_that_is_too_long_is_over_extent_not_a_wrong_name():
    """Rätt beteckning, för långt stråk: det är en annan sorts fel än fel identitet."""
    s = score_sheet("X", _run([("KV1-X31-16", 15.0)]), {"KV1-X31-16": 10.0}, fold=False)
    assert s["metres"]["over_extent"] == 5.0
    assert s["metres"]["wrong_name"] == 0.0
    assert s["metres"]["owned"] == 10.0


def test_an_undefined_ratio_is_not_a_hundred_percent_and_not_zero():
    assert pct(None) == "N/A"
    assert pct(0.0) == "0.0%"
    assert pct(1.0) == "100.0%"


def test_no_measure_can_exceed_a_hundred_percent():
    """Tre rader i vårt, en i referensen: precisionen är en tredjedel, inte trehundra procent."""
    s = score_sheet("X", _run([("A1-1-1", 5.0), ("A2-1-1", 5.0), ("A3-1-1", 5.0)]), {"A1-1-1": 5.0}, fold=False)
    assert s["designations"]["precision"] == 0.3333
    for key in ("recall", "precision", "recall_with_metres"):
        assert s["designations"][key] is None or 0.0 <= s["designations"][key] <= 1.0
    assert s["metres"]["coverage"] <= 1.0
