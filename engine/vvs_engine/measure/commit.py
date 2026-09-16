"""Tilldelningen commit:as som en helhet, och det omtvistade räknas inte åt någon.

Fram till nu har ägandet avgjorts löpande: ett rör får sin identitet, nästa får sin, och mängden faller ut ur
summan av det som blev. Det fungerar så länge besluten inte rör varandra. Där de rör varandra - två rör som
båda gör anspråk på samma bit ritat bläck - finns det ingen punkt i kedjan där någon ser båda anspråken
samtidigt, och då blir biten räknad två gånger utan att något larmar.

Det här är den punkten. Anspråken samlas först, hela tilldelningen ses på en gång, och sedan skrivs mängden:

* en bit med **en** ägare räknas, som förut;
* en bit med **två** ägare räknas åt ingen av dem. Meterna flyttas till radens tvetydiga mängd, biten står kvar
  i journalen med sina alternativ och sitt skäl, och den som granskar ser vad tvisten gällde.

Att hålla inne är avsiktligt och inte försiktighet. Att välja den ena ägaren vore att gissa, och en gissning
som ser ut som ett besked är det fel systemet är byggt för att inte göra. Tvetydigt är ett giltigt svar;
felaktig säkerhet är det inte.

Ordningen spelar ingen roll: tvisterna hittas ur den färdiga postmängden, och både urvalet och vad som skrivs
ned är sorterat. Två körningar som läser samma blad skriver samma journal.

I dag är det här en spärr som inte slår till på korpusen - efter att det atomära intervallet fick rätt namn
(`pipes.representation.interval_id`) finns det ingen bit med två ägare kvar. Det är avsikten. Spärren finns för
den ritning som ännu inte lästs.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from . import journal as _journal

# Skälet en omtvistad bit bär med sig, så att den går att söka på i journalen och i granskningen.
DISPUTED_REASON = "tva_ror_gor_ansprak_pa_samma_intervall"


def _disputes(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Vilka intervall två eller flera rör räknar, och vilka de är. Sorterat, så utfallet inte beror på ordning."""
    owners: dict[str, set[str]] = defaultdict(set)
    idents: dict[str, set[str]] = defaultdict(set)
    for e in entries:
        if e["kind"] == _journal.DRAWN and e.get("counted"):
            owners[e["interval"]].add(e["owner"])
            idents[e["interval"]].add(e["identity"])
    return {iv: {"interval": iv, "owners": sorted(o), "identities": sorted(idents[iv]), "reason": DISPUTED_REASON}
            for iv, o in sorted(owners.items()) if len(o) > 1}


def _withhold(entries: list[dict[str, Any]], disputed: dict[str, dict]) -> dict[str, float]:
    """Ta de omtvistade posterna ur mängden och lämna kvar vad de var. Returnerar de innehållna metrarna per
    identitet, så att mängdraden kan säga var de tog vägen i stället för att bara bli kortare."""
    held: dict[str, float] = defaultdict(float)
    for e in entries:
        d = disputed.get(e["interval"]) if e["kind"] == _journal.DRAWN and e.get("counted") else None
        if d is None:
            continue
        held[e["identity"]] += e.get("_exact") or 0.0
        e["counted"] = False
        e["disputed"] = True
        # Alternativen är de andra som gjorde anspråk på just den här biten. Att skriva dem hit är hela
        # poängen med att hålla inne: den som granskar ska slippa leta reda på motparten.
        e["alternatives"] = [o for o in d["owners"] if o != e["owner"]]
        e["why"] = DISPUTED_REASON
    return dict(held)


def _row_index(quantities: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for q in quantities:
        dn = q.get("dn")
        out[q.get("base", "") + f"|DN{dn if dn is not None else '?'}"] = q
    return out


def _move_to_ambiguous(quantities: list[dict], held: dict[str, float]) -> list[dict]:
    """Innehållna meter lämnar den bekräftade mängden och blir tvetydiga. Raden behåller sin plats och sin
    beteckning - det som ändras är vad den påstår sig veta."""
    idx = _row_index(quantities)
    moved = []
    for key in sorted(held):
        m = held[key]
        r = idx.get(key)
        if r is None or not m:
            continue
        # Den horisontella mängden är den enda ritade biten kan ha hamnat i; en lodrät sträcka har ingen
        # ritad bit att tvista om och rörs inte.
        take = min(m, r.get("confirmed_horizontal_m") or 0.0)
        r["confirmed_horizontal_m"] = round((r.get("confirmed_horizontal_m") or 0.0) - take, 3)
        r["confirmed_total_m"] = round((r.get("confirmed_total_m") or 0.0) - take, 3)
        r["ambiguous_m"] = round((r.get("ambiguous_m") or 0.0) + take, 3)
        r["disputed_m"] = round((r.get("disputed_m") or 0.0) + take, 3)
        moved.append({"identity": key, "metres": round(take, 3)})
    return moved


def commit(measures, quantities: list[dict], mpp: float | None) -> dict[str, Any]:
    """Skriv journalen, lös tvisterna, rätta mängden efter dem, och kontrollera villkoren på det som blev.

    Ordningen är avsiktlig och är det som gör steget transaktionellt: ingenting av det här syns utåt förrän
    hela tilldelningen har setts på en gång. `quantities` ändras på plats, eftersom det är den mängdraden
    resten av läsningen redan håller i."""
    entries = _journal.entries_of(measures, mpp)
    disputed = _disputes(entries)
    held = _withhold(entries, disputed)
    moved = _move_to_ambiguous(quantities, held)
    for q in quantities:
        q.setdefault("disputed_m", 0.0)
    out: dict[str, Any] = {"entries": entries, "by_identity": _journal.totals(entries),
                           "disputed": [disputed[k] for k in sorted(disputed)],
                           "withheld": moved}
    out["check"] = _journal.check(out, quantities)
    out["check"]["n_disputed"] = len(disputed)
    out["check"]["withheld_m"] = round(sum(w["metres"] for w in moved), 3)
    return out
