"""What the eye is allowed to do to a reading: report, and nothing else.

The danger with vision on a measurement product is obvious - a model looks at a picture, says "there is a pipe
here", and a metre appears that no vector ever supported. These tests hold the line by shape: there is no path
from a vision finding to a quantity, and the parser throws away anything that is not an answer to a question
that was asked.
"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vvs_engine.review import vision


def test_without_a_transport_nothing_is_asked():
    class _PA:
        pass
    r = vision.look(_PA(), None, ask=None)
    assert r.asked is False and r.findings == []


def test_only_answers_to_the_questions_that_were_asked_survive():
    raw = "\n".join([
        "missed_pipes | en ledning längs södra väggen som inget rött följer | nedre vänstra hörnet",
        "hallucination | jag ser ett rör på 14,3 meter | mitten",
        "overlay_wrong | en röd linje följer en måttlinje | uppe till höger",
        "bara löptext utan nyckel",
        "missed_labels |  | någonstans",
    ])
    got = vision.parse(raw)
    assert [f.kind for f in got] == ["missed_pipes", "overlay_wrong"]
    assert "hallucination" not in {f.kind for f in got}, "en nyckel ingen frågade om får inte tas in"


def test_a_finding_says_that_it_is_not_geometry():
    f = vision.Finding(kind="missed_pipes", detail="en ledning som inget följer", where="nere till vänster")
    d = f.as_dict()
    assert d["source"] == "vision_second_opinion"
    assert "never used as geometry" in d["note"]


def test_there_is_no_way_to_turn_a_vision_finding_into_a_measurement():
    """The guarantee is structural: this module has no apply(), and a finding carries no number."""
    assert not hasattr(vision, "apply"), "vision får inte kunna skriva tillbaka in i läsningen"
    assert not hasattr(vision, "apply_findings")
    f = vision.Finding(kind="missed_pipes", detail="x")
    assert not any(isinstance(v, (int, float)) for v in f.as_dict().values()), \
        "en iakttagelse får inte bära ett tal som kan förväxlas med en mätning"


def test_the_review_states_its_own_contract():
    r = vision.VisionReview(asked=True, findings=[vision.Finding("missed_pipes", "x")])
    d = r.as_dict()
    assert d["n_findings"] == 1
    assert "never creates geometry" in d["contract"]
