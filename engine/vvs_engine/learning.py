"""What a correction is allowed to teach a later reading.

A person correcting one drawing has told us something true about that drawing. Carrying it to the next one is
where a takeoff system usually starts lying: the correction becomes a prior, the prior becomes a guess, and the
guess is indistinguishable from a reading. So the rule here is narrow and stated rather than learned.

A correction may only ever do one thing on a later sheet: settle a case the engine itself has already marked
AMBIGUOUS, in favour of the answer a person gave in the same situation. It may never create a run, never name
geometry no leader reached, never change a run the engine is confident about, and never outvote the drawing.

"The same situation" is not a resemblance score. It is an exact match on the things that make the case what it
is - the pen the geometry is drawn with, the reason the engine gave up, and the shape of the designation - all of
which come from the drawing itself. Anything less and the lesson does not apply, because two sheets that merely
look alike are two different drawings.
"""
from __future__ import annotations

from typing import Any

# What has to match, exactly, before a lesson from one sheet is allowed to speak about another.
KEYS = ("family_style", "reason", "designation_shape")


def situation(*, family: str = "", reason: str = "", designation: str = "") -> dict[str, str]:
    """The fingerprint of a case: the pen, why the engine stopped, and the shape of the name.

    The pen is taken without the layer, because layer names are a project's habit and do not carry between
    offices; the width and colour are how the drawing itself distinguishes one system from another. The
    designation keeps its shape - letters, digits and separators - but not its numbers, so KV1-X31-16 and
    KV2-X31-25 are the same shape and S3-R8-110 is not.
    """
    style = family.split("|s|")[-1] if "|s|" in family else family
    shape = "".join("9" if ch.isdigit() else ("A" if ch.isalpha() else ch) for ch in (designation or "").upper())
    return {"family_style": style, "reason": (reason or "").split(":")[0], "designation_shape": shape}


def lessons(corrections: list[dict]) -> list[dict]:
    """Corrections turned into lessons, one per situation, with how often a person answered the same way.

    A situation a person has answered two different ways teaches nothing: it is dropped rather than decided by
    majority, because the disagreement is the finding.
    """
    by: dict[tuple, dict[str, int]] = {}
    for c in corrections:
        if c.get("undone") or c.get("kind") not in ("retag", "draw", "extend"):
            continue
        sit = c.get("situation") or {}
        if not all(sit.get(k) for k in KEYS):
            continue
        key = tuple(sit[k] for k in KEYS)
        answer = (c.get("designation") or "").upper()
        if not answer:
            continue
        by.setdefault(key, {})
        by[key][answer] = by[key].get(answer, 0) + 1
    out = []
    for key, answers in sorted(by.items()):
        if len(answers) != 1:
            continue                      # answered two ways: the disagreement is the finding, not a vote
        answer, n = next(iter(answers.items()))
        out.append({**dict(zip(KEYS, key)), "answer": answer, "times": n})
    return out


def settle(ambiguous: list[dict], lessons_: list[dict]) -> list[dict]:
    """For each ambiguous case, the lesson that applies to it - if one does, exactly.

    Returns proposals, not decisions: each says which case, which answer, and on what a person taught it. The
    caller decides whether to apply them, and a proposal that would name geometry no leader reached is refused
    here rather than there.
    """
    index = {tuple(l[k] for k in KEYS): l for l in lessons_}
    out = []
    for case in ambiguous:
        sit = case.get("situation") or {}
        if not all(sit.get(k) for k in KEYS):
            continue
        lesson = index.get(tuple(sit[k] for k in KEYS))
        if lesson is None:
            continue
        if lesson["answer"] not in {c.upper() for c in (case.get("candidates") or [])}:
            continue        # the drawing's own candidates do not include the taught answer: it does not apply
        out.append({"case": case.get("id"), "answer": lesson["answer"], "times": lesson["times"],
                    "situation": {k: sit[k] for k in KEYS},
                    "why": "en person svarade så i samma situation på en tidigare ritning"})
    return out
