"""The last word: what, out of everything the reading and its reviewers found, should actually change.

The reviewers state disagreements and stop there, on purpose - a review that could edit the result would hide the
disagreement it exists to surface. But nobody was deciding either, and a pile of findings that leads to nothing
is not a review, it is a wait. So one judge goes through them all afterwards and says, for each, what happens.

It works under four rules, and they are what make it safe to let it decide at all.

  * It never invents a number. Anything it implements is one of the answers the drawing itself put forward.
  * It never touches a measurement the reading confirmed. Only cases the reading itself left open are open.
  * Everything it implements is written as a correction: attributable, versioned, and undoable like any other.
  * Where the evidence does not settle a case, saying so is a verdict. Leaving it to a person is an answer, and
    a better one than a confident guess.

Nothing here calls a model. Every verdict below follows from what the artifacts already hold, which is why the
same reading judged twice gives the same verdicts.
"""
from __future__ import annotations

from typing import Any

IMPLEMENT = "GENOMFOR"
LEAVE = "LAMNA"
ASK = "FRAGA_EN_MANNISKA"


def _v(kind: str, decision: str, what: str, why: str, **extra: Any) -> dict:
    return {"typ": kind, "beslut": decision, "gäller": what, "skäl": why, **extra}


def judge(model, proposals: list[dict] | None = None) -> dict[str, Any]:
    """Go through the reading and say what should happen to each open case.

    `model` is a DrawingModel; `proposals` are what earlier corrections on this account would say about the cases
    this reading could not settle - the only place a change can come from that the drawing did not itself offer,
    and even then only among its own candidates.
    """
    verdicts: list[dict] = []
    by_case = {p.get("id"): p for p in (proposals or []) if p.get("id")}

    def names_a_pipe(text: str) -> bool:
        """The sheet's own list decides. A fitting tag whose leader lands on the run it connects to is not an
        open case: the drawing meant it to end there, and asking a person about it wastes the one thing a
        review of this kind is for."""
        head = (text or "").upper().strip()
        if not head or not model.systems:
            return bool(head)
        if any(head == c or head.startswith(c) for c in model.components):
            return False
        return any(head == c or head.startswith(c) for c in model.systems)

    # 1. the cases the reading itself called open
    ambiguous = [a for a in model.anchors
                 if a.get("state") == "AMBIGUOUS_PIPE_ATTACHMENT" and names_a_pipe(a.get("designation") or "")]
    for a in ambiguous:
        p = by_case.get(a["anchor_id"])
        cands = (p or {}).get("candidates") or []
        if p and p.get("answer") and p.get("answer") in cands:
            verdicts.append(_v(
                "tvetydig_anslutning", IMPLEMENT, a.get("designation") or a["anchor_id"],
                f"tidigare rättelser i det här kontot avgör samma situation, och svaret är en av de kandidater "
                f"ritningen själv erbjuder ({', '.join(cands)})",
                ankare=a["anchor_id"], svar=p["answer"], kandidater=cands,
                rättelse={"kind": "attachment", "anchor_id": a["anchor_id"], "designation": p["answer"]},
                punkt=a.get("leader_endpoint")))
        else:
            verdicts.append(_v(
                "tvetydig_anslutning", ASK, a.get("designation") or a["anchor_id"],
                "hänvisningslinjen når mer än en möjlig ledning och ingenting i ritningen skiljer dem åt; "
                "att gissa här är att flytta en meter på ingenting",
                ankare=a["anchor_id"], kandidater=cands, punkt=a.get("leader_endpoint")))

    # 2. labels the sheet writes that never got a metre
    for i in model.issues:
        kind = i.get("kind")
        if i.get("severity") != "blocking":
            continue
        if kind == "missing_leader":
            verdicts.append(_v(
                "saknad_hänvisning", LEAVE, i.get("text") or "",
                f"ritningen drar ingen linje från etiketten ({i.get('reason') or 'inget skäl noterat'}); "
                "det finns inget att genomföra utan att peka ut ett rör som ritningen inte pekar ut",
                bbox=i.get("bbox")))
        elif kind == "missing_dn":
            verdicts.append(_v(
                "saknad_dimension", ASK, i.get("text") or "",
                "beteckningen namnger ett rör men ingen dimension står att läsa på raden; "
                "storleken måste komma från handlingen, inte från en gissning",
                bbox=i.get("bbox")))
        elif kind == "missing_pipe_attachment":
            verdicts.append(_v(
                "nådde_inget_rör", LEAVE, i.get("text") or "",
                "hänvisningslinjen slutar där ritningen inte ritar någon accepterad rörgeometri; "
                "vad den pekar på syns bara på ritningen",
                bbox=i.get("bbox")))
        else:
            verdicts.append(_v(kind or "olöst", ASK, i.get("text") or "",
                               i.get("reason") or "läsningen lämnade fallet öppet", bbox=i.get("bbox")))

    # 3. geometry the drawing drew twice
    dt = model.declined.get("drawn_twice") or {}
    if dt.get("n_places"):
        verdicts.append(_v(
            "dubbelritad_geometri", LEAVE, f"{dt['n_places']} ställen, {dt.get('length_m')} m",
            "samma linje är ritad två gånger, men att dra bort den kostar mer än den sparar: de dubbla "
            "stumparna sitter i skarvar, och när de togs bort flyttades en dimensionsgräns dit ritningen inte "
            "gör någon skarv - sex meter bytte storlek för att spara åtta tiondels meter dubbelräkning",
            ställen=(dt.get("places") or [])[:20]))

    # 4. the scale everything rests on
    s = model.scale
    if s.get("state") != "VERIFIED":
        verdicts.append(_v(
            "skala", ASK, f"skalan är {s.get('state')}",
            f"{s.get('reason') or 'skalstocken bekräftar inte skaltexten'}; varje meter på bladet hänger på "
            "det här, så det ska en människa avgöra mot handlingen"))

    # 5. does the drawn geometry still add up
    r = model.reconciliation
    if r and r.get("state") != "VALID":
        verdicts.append(_v(
            "avstämning", ASK, r.get("state") or "okänd",
            "den ritade rörgeometrin summerar inte till bekräftat plus tvetydigt plus utan ägare; "
            "en sådan läsning ska inte rättas, den ska undersökas",
            dubbelräknade=r.get("double_counted_prims")))

    # 6. what the reviewers said that nothing above already covers
    for f in model.review.get("findings", []):
        if f.get("severity") == "INFO":
            continue
        if f.get("agent") in ("scale",) and s.get("state") != "VERIFIED":
            continue        # already judged above, and once is enough
        verdicts.append(_v(
            f"granskare_{f.get('agent')}", ASK, f.get("code") or "",
            f.get("message") or "", allvar=f.get("severity")))

    counts = {IMPLEMENT: 0, LEAVE: 0, ASK: 0}
    for v in verdicts:
        counts[v["beslut"]] = counts.get(v["beslut"], 0) + 1
    return {"antal": len(verdicts), "sammanfattning": counts, "utslag": verdicts,
            "regel": "Domaren genomför bara svar ritningen själv erbjuder, rör aldrig en bekräftad mätning, "
                     "skriver varje ändring som en rättelse som kan ångras, och lämnar det som inte går att "
                     "avgöra till en människa."}
