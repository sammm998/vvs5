"""Det som står i parentes säger något om röret - det döper det inte.

En ritning skriver måttet på raden under koden, och ibland med ett tillägg: `S3-P2` över `160(L)`. Måttet är
160; parentesen säger något mer om just det röret. En mängdförteckning som skriver in tillägget i namnet får två
rader där ritningen har ett rör - `S3-P2-160` och `S3-P2-160(L)` - och båda blir fel mot en förteckning som
bara känner den ena. Tillägget behålls på beteckningen, så att en läsare ser det, men namnet är namnet.
"""
from vvs_engine.semantics.annotation import Designation


def _des(text: str, row: str | None, dn: int = 160, source: str = "row") -> Designation:
    return Designation(did="d", page=0, block_id="b", row_index=0, text=text, raw_text=text, pattern="A9-A9",
                       tokens=text.split("-"), system_token=text.split("-")[0], dn=dn, dn_source=source,
                       dn_row_index=1, dn_row_text=row, multiplier=1, bbox=(0.0, 0.0, 1.0, 1.0), angle=0.0,
                       layer="", source="stroke", glyph_scores=[], unknown_chars=0)


def test_the_dimension_row_names_the_pipe_and_the_bracket_stays_an_aside():
    d = _des("S3-P2", "160(L)")
    assert d.display_text == "S3-P2-160"
    assert d.aside == "(L)" and d.dimension_text == "160"


def test_a_dimension_row_without_an_aside_is_unchanged():
    d = _des("KV2-X31", "16", dn=16)
    assert d.display_text == "KV2-X31-16" and d.aside == "" and d.dimension_text == "16"


def test_a_bracket_that_is_the_whole_row_leaves_the_code_alone():
    """Ingen siffra kvar när tillägget tagits bort: raden var inget mått, och koden står som den står."""
    d = _des("S3-P2", "(L)", dn=None)
    assert d.display_text == "S3-P2"


def test_an_inline_dimension_is_not_touched():
    d = _des("S3-P2-160", None, source="inline")
    assert d.display_text == "S3-P2-160" and d.aside == ""
