"""Hur en gräns i motorn får flyttas, och vad som ska hindra att den flyttas av fel skäl.

En regel som ändras för att ett blad blev bättre är en regel som anpassats efter ett blad. Nästa ritning får
då betala för den, och ingen kommer att kunna säga varför. Spec avsnitt K ger förfarandet, och proven här
säger vad det ska hindra:

* **för tunt underlag** - två omkörningar av samma PDF är inte två oberoende dokument;
* **en generell regel som skadar en annan stil** - då är den inte generell, och vägen framåt är ett undantag
  med mätt konflikt, inte att aktivera ändå;
* **ett stilundantag utan mätt konflikt** - annars blir varje stil sin egen regel och det finns ingen
  gemensam läsning kvar;
* **aktivering utan prövning** - tillståndet ska göra det omöjligt, inte disciplinen;
* **en aktivering som inte går att ta tillbaka**.

Och releaseidentiteten: ett mellanresultat som återanvänds under en annan identitet är gammalt ägarskap ovanpå
ny geometri.
"""
import pytest

from vvs_engine.release import (ACTIVE, MIN_INDEPENDENT_SOURCES, PROPOSED, REJECTED, ROLLED_BACK, TESTED,
                                Regression, ReleaseIdentity, RuleChange, independent_sources,
                                rules_fingerprint)


def _identity(**over):
    base = {"code": "abc123", "rules": "r1", "profile": "p1", "renderer": "mupdf-1.28.2",
            "text_reader": "glyf-3", "flags": {"ocr": False}, "document": "sha-A"}
    base.update(over)
    return ReleaseIdentity(**base)


def _change(**over):
    base = {"change_id": "c1", "hypothesis": "ledaren når fram en aning längre än vi tror",
            "changes": {"attachment.NEAR_MISS": 9.0}, "before": {"attachment.NEAR_MISS": 7.0},
            "sources": [{"sha": "sha-A", "sheet": "ett"}, {"sha": "sha-B", "sheet": "tva"}]}
    base.update(over)
    return RuleChange(**base)


# -------------------------------------------------------------------------------------- releaseidentiteten
def test_the_same_run_under_the_same_everything_has_the_same_key():
    assert _identity().key == _identity().key


def test_a_moved_tolerance_changes_the_key():
    """En ändrad regel som inte ändrar cachenyckeln syns inte förrän någon undrar varför två körningar av
    samma ritning gav olika mängd."""
    assert _identity().key != _identity(rules="r2").key


def test_every_part_of_the_identity_can_change_the_key():
    for field, value in (("code", "def456"), ("profile", "p2"), ("renderer", "mupdf-1.29"),
                         ("text_reader", "glyf-4"), ("document", "sha-B"), ("model", "m.onnx")):
        assert _identity().key != _identity(**{field: value}).key, field
    assert _identity().key != _identity(flags={"ocr": True}).key


def test_a_cached_step_is_only_reused_under_an_identical_identity():
    """Frestelsen att säga att en ändrad tolerans inte påverkar textläsningen är hur gammalt ägarskap hamnar
    ovanpå ny geometri."""
    assert _identity().covers(_identity())
    assert not _identity().covers(_identity(rules="r2"))


def test_the_rule_fingerprint_follows_the_value_and_not_the_name():
    kat = {"groups": [{"group": "g", "rules": [{"id": "a.X", "default": 7.0, "value": 7.0}]}]}
    andrad = {"groups": [{"group": "g", "rules": [{"id": "a.X", "default": 7.0, "value": 9.0}]}]}
    assert rules_fingerprint(kat) != rules_fingerprint(andrad)


# ----------------------------------------------------------------------------------------------- underlaget
def test_the_same_pdf_read_twice_is_one_source_and_not_two():
    """Samma fel som projektpriorn hade innan den räknade källor i stället för körningar."""
    assert independent_sources([{"sha": "x", "sheet": "a"}, {"sha": "x", "sheet": "a"}]) == ["x"]
    assert len(independent_sources([{"sha": "x"}, {"sha": "y"}])) == 2


def test_a_raster_export_of_the_same_drawing_does_not_add_a_source():
    """En rasterexport, en beskärning eller en annan pipeline är samma dokument sagt om igen."""
    docs = [{"sha": "x", "sheet": "A-plan"}, {"sha": "x", "sheet": "A-plan (raster)"}]
    assert len(independent_sources(docs)) == 1


def test_a_change_on_too_thin_evidence_is_rejected():
    c = _change(sources=[{"sha": "x"}, {"sha": "x"}])
    c.tested(Regression(per_style={"stil1": {"fore": 0.7, "efter": 0.8}}, held_out=["y"]))
    assert c.state == REJECTED and "oberoende dokument" in c.reason
    assert str(MIN_INDEPENDENT_SOURCES) in c.reason


def test_a_change_without_a_held_out_case_is_rejected():
    c = _change()
    c.tested(Regression(per_style={"stil1": {"fore": 0.7, "efter": 0.8}}, held_out=[]))
    assert c.state == REJECTED and "undanhållna" in c.reason


# ------------------------------------------------------------------------------------------- prövningen
def test_a_general_rule_that_makes_another_style_worse_is_not_general():
    """Det avgörande ledet. Listan över vad som blev SÄMRE avgör, inte listan över vad som blev bättre."""
    c = _change()
    c.tested(Regression(per_style={"stil1": {"fore": 0.70, "efter": 0.82},
                                   "stil2": {"fore": 0.66, "efter": 0.59}}, held_out=["h"]))
    assert c.state == REJECTED
    assert "stil2" in c.reason


def test_a_change_that_helps_nobody_is_rejected():
    c = _change()
    c.tested(Regression(per_style={"stil1": {"fore": 0.7, "efter": 0.7}}, held_out=["h"]))
    assert c.state == REJECTED and "ingen stilgrupp blev bättre" in c.reason


def test_a_change_that_helps_one_style_and_harms_none_passes_the_test():
    c = _change()
    c.tested(Regression(per_style={"stil1": {"fore": 0.70, "efter": 0.82},
                                   "stil2": {"fore": 0.66, "efter": 0.66}}, held_out=["h"]))
    assert c.state == TESTED and "stil1" in c.reason


# ------------------------------------------------------------------------------------------ stilundantaget
def test_a_style_exception_needs_a_measured_conflict_and_not_just_a_difficult_style():
    gemensam = Regression(per_style={"stil1": {"fore": 0.70, "efter": 0.80},
                                     "stil2": {"fore": 0.66, "efter": 0.55}}, held_out=["h"])
    c = _change(style_scope="stil2")
    c.tested(Regression(per_style={"stil2": {"fore": 0.55, "efter": 0.71}}, held_out=["h"]))
    ok, why = c.exception_is_warranted(gemensam)
    assert ok and "stil2" in why


def test_an_exception_is_refused_when_the_common_rule_harms_nobody():
    """Annars blir varje stil sin egen regel och det finns ingen gemensam läsning kvar."""
    gemensam = Regression(per_style={"stil1": {"fore": 0.70, "efter": 0.80},
                                     "stil2": {"fore": 0.66, "efter": 0.66}}, held_out=["h"])
    c = _change(style_scope="stil2")
    c.tested(Regression(per_style={"stil2": {"fore": 0.66, "efter": 0.71}}, held_out=["h"]))
    ok, why = c.exception_is_warranted(gemensam)
    assert not ok and "skadar ingen stil" in why


def test_an_exception_that_does_not_help_its_own_style_is_refused():
    gemensam = Regression(per_style={"stil2": {"fore": 0.66, "efter": 0.55}}, held_out=["h"])
    c = _change(style_scope="stil2")
    c.tested(Regression(per_style={"stil1": {"fore": 0.7, "efter": 0.8}}, held_out=["h"]))
    ok, why = c.exception_is_warranted(gemensam)
    assert not ok and "stil2" in why


# ------------------------------------------------------------------------------- aktivering och återtagning
def test_an_untested_change_cannot_be_activated():
    """Tillståndet ska göra det omöjligt. Disciplin är inte en mekanism."""
    c = _change()
    assert c.state == PROPOSED
    with pytest.raises(ValueError, match=PROPOSED):
        c.activate(previous_version=3)


def test_activation_gets_a_new_version_and_keeps_the_previous_one():
    c = _change()
    c.tested(Regression(per_style={"stil1": {"fore": 0.7, "efter": 0.8}}, held_out=["h"]))
    c.activate(previous_version=4)
    assert c.state == ACTIVE and c.version == 5 and c.previous_version == 4


def test_a_rollback_hands_back_the_values_that_held_before():
    """Återgången ska vara en handling och inte en förhoppning: den lämnar ifrån sig talen att sätta."""
    c = _change()
    c.tested(Regression(per_style={"stil1": {"fore": 0.7, "efter": 0.8}}, held_out=["h"]))
    c.activate(previous_version=1)
    back = c.rollback()
    assert back == {"attachment.NEAR_MISS": 7.0}
    assert c.state == ROLLED_BACK
    with pytest.raises(ValueError):
        c.rollback()
