"""Mängdjournalen: varje meter i mängden, tillbaka till det ritade intervall den kom ur.

En mängdrad är i dag en summa. Summan går att lita på precis så länge man litar på hela kedjan som byggde den,
och när en rad ser fel ut finns det inget att öppna. Journalen är den öppningen: en post per **atomärt
intervall** - en bit ritat bläck, eller en överbryggad lucka, eller en lodrät sträcka - med vem som äger det,
hur långt det är och varför det räknades.

Vad som är atomärt är inte självklart, och att ta fel på det gör villkoret nedan obrukbart. Källsträckan
`pid#index` är det inte: när ett T delas mitt på en dragen linje behåller båda bitarna sitt ursprungs namn, och
en huvudledning och en gren som rättmätigt äger var sin halva ser då ut som två ägare till ett intervall. Det
atomära är biten - `pipes.representation.interval_id` - och den bär både härkomsten och var på sträckan den
börjar.

Två saker gör den till mer än en logg.

**Mängden ska gå att räkna om ur journalen.** Stämmer inte summan av posterna med mängdraden är en av dem fel,
och det ska synas som ett brott mot ett villkor - inte som en siffra någon får upptäcka på en byggarbetsplats.

**Ett intervall får ha en ägare.** Samma bit under två rör är dubbelräkning, och det är det fel som är
svårast att se i en summa: båda raderna ser rimliga ut var för sig. Journalen gör det till en kontroll.

Journalen själv ÄNDRAR ingen mängd. Den skriver ned vad läsningen gjorde och säger till när det inte går ihop.
Att göra något åt en tvist är `measure.commit`:s sak, och den håller inne den omtvistade biten från båda
anspråken i stället för att välja åt någon.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

# Vad ett intervall är för sorts meter. En överbryggad lucka är inte ritat bläck men räknas - därför står den
# som en egen sort i stället för att gömma sig i den ritade längden.
DRAWN = "ritat"
BRIDGED = "overbryggad_lucka"
VERTICAL = "lodratt"
TWIN = "dubbellinjens_andra_kant"

# Hur nära summan måste ligga mängdraden för att villkoret ska anses hållet. Avrundning per rad är tillåten;
# en verklig skillnad är det inte.
TOLERANCE_M = 0.005


def entries_of(measures, mpp: float | None) -> list[dict[str, Any]]:
    """Journalens poster, en per atomärt intervall, med den ORUNDADE metern kvar under `_exact`.

    Posterna skrivs innan någon vet om de får räknas: det är `commit` som avgör det, och den behöver se
    anspråken som de är. `totals` tar sedan bort `_exact` när summan är dragen."""
    entries: list[dict[str, Any]] = []
    # Summan per identitet räknas på ORUNDADE tal. Rundar man varje post till fyra decimaler och adderar
    # tretusen av dem blir felet millimetrar som ser ut som ett brott mot ett villkor, och ett villkor som
    # larmar på sin egen avrundning slutar man snart att läsa.
    for m in measures:
        pipe = m.pipe
        key = pipe.identity.key
        if m.twin_of is not None:
            # dubbellinjens andra kant: dess meter hör till partnern och räknas inte en gång till
            entries.append({"interval": f"{pipe.physical_pipe_id}#twin", "kind": TWIN, "owner": pipe.physical_pipe_id,
                            "identity": key, "pdf_units": round(m.twin_pdf_units, 4),
                            "metres": round(m.twin_pdf_units * mpp, 4) if mpp else None, "_exact": 0.0,
                            "counted": False, "why": f"andra kanten av {m.twin_of}"})
            continue
        # Det atomära intervallet, inte källsträckan: ett T mitt på en dragen linje ger två bitar med samma
        # `pid#seg_index`, och skiljer man dem inte åt ser två rättmätiga ägare ut som dubbelräkning.
        segs = list(pipe.source_intervals or pipe.source_segments or [])
        # Mätningens EGEN längd i meter är sanningen, inte rörets råa punkter: den drar redan bort det som
        # ligger i skraffering. Journalen fördelar just det talet, så att summan per rör är exakt vad
        # mängdraden fick. Ett villkor som bygger på en egen räkning prövar bara sin egen räkning.
        horiz_m = m.horizontal_m
        if horiz_m is not None:
            gap_m = min(max(0.0, pipe.bridged_gap_pt * mpp) if mpp else 0.0, max(0.0, horiz_m))
            drawn_m = horiz_m - gap_m
            share = drawn_m / len(segs) if segs else drawn_m
            for sid in segs:
                entries.append({"interval": sid, "kind": DRAWN, "owner": pipe.physical_pipe_id, "identity": key,
                                "metres": round(share, 4), "_exact": share,
                                "counted": True, "why": pipe.state})
            if not segs and drawn_m:
                entries.append({"interval": f"{pipe.physical_pipe_id}#drawn", "kind": DRAWN,
                                "owner": pipe.physical_pipe_id, "identity": key,
                                "metres": round(drawn_m, 4), "_exact": drawn_m,
                                "counted": True, "why": pipe.state})
            if gap_m:
                entries.append({"interval": f"{pipe.physical_pipe_id}#gap", "kind": BRIDGED,
                                "owner": pipe.physical_pipe_id, "identity": key,
                                "metres": round(gap_m, 4), "_exact": gap_m, "counted": True,
                                "why": "lucka överbryggad mellan två ritade bitar"})
        else:
            # ingen skala, ingen meter: sträckan finns men går inte att mäta, och det ska synas
            for sid in segs:
                entries.append({"interval": sid, "kind": DRAWN, "owner": pipe.physical_pipe_id, "identity": key,
                                "metres": None, "_exact": 0.0, "counted": False, "why": "ingen skala att mäta i"})
        if m.vertical_m:
            entries.append({"interval": f"{pipe.physical_pipe_id}#vert", "kind": VERTICAL,
                            "owner": pipe.physical_pipe_id, "identity": key, "pdf_units": None,
                            "metres": round(m.vertical_m, 4), "_exact": m.vertical_m, "counted": True,
                            "why": (m.vertical_evidence or {}).get("kind") or "lodrät sträcka"})
    return entries


def totals(entries: list[dict[str, Any]]) -> dict[str, float]:
    """Summan per identitet över de poster som fick räknas, och `_exact` städas bort på vägen ut.

    Summan räknas på orundade tal. Rundar man varje post till fyra decimaler och adderar tretusen av dem blir
    felet millimetrar som ser ut som ett brott mot ett villkor, och ett villkor som larmar på sin egen
    avrundning slutar man snart att läsa."""
    exact: dict[str, float] = defaultdict(float)
    for e in entries:
        if e.get("counted") and e.get("metres") is not None:
            exact[e["identity"]] += e["_exact"]
        e.pop("_exact", None)
    return {k: round(v, 4) for k, v in sorted(exact.items())}


def build(measures, mpp: float | None) -> dict[str, Any]:
    """Journalen över en sidas mängd, utan att något hålls inne. `measure.commit` är vägen in i produktion;
    den här finns för den som vill se anspråken som de var innan tilldelningen avgjordes."""
    entries = entries_of(measures, mpp)
    return {"entries": entries, "by_identity": totals(entries)}


def check(journal: dict, quantities: list[dict]) -> dict[str, Any]:
    """Villkoren journalen finns för. Ett brott är ett fynd, inte något att jämna ut."""
    entries = journal.get("entries") or []
    breaches: list[dict] = []

    # 1. ett ritat intervall får ha en ägare bland de RÄKNADE posterna. Två rör som räknar samma bit är
    #    dubbelräkning; att två rör gör anspråk på den är däremot bara en tvist, och den löser `commit` genom
    #    att hålla inne biten från båda. Det som står kvar här efter en commit är alltså ett verkligt brott.
    owners: dict[str, set] = defaultdict(set)
    for e in entries:
        if e["kind"] == DRAWN and e.get("counted"):
            owners[e["interval"]].add(e["owner"])
    shared = {k: sorted(v) for k, v in owners.items() if len(v) > 1}
    if shared:
        breaches.append({"invariant": "ett_intervall_en_agare", "n": len(shared),
                         "examples": dict(list(shared.items())[:5])})

    # 2. mängden ska gå att räkna om ur journalen
    from_journal = journal.get("by_identity") or {}
    rows = {q.get("base", "") + f"|DN{q.get('dn') if q.get('dn') is not None else '?'}":
            (q.get("confirmed_total_m") or 0.0)
            for q in quantities}
    off = []
    for k, m in rows.items():
        j = from_journal.get(k, 0.0)
        if abs(j - m) > TOLERANCE_M:
            off.append({"identity": k, "mangdrad_m": round(m, 3), "journal_m": round(j, 3),
                        "skillnad_m": round(j - m, 3)})
    if off:
        breaches.append({"invariant": "mangden_gar_att_rakna_om_ur_journalen", "n": len(off),
                         "examples": off[:5]})

    return {"state": "PASS" if not breaches else "FAIL", "n_entries": len(entries),
            "n_intervals": len(owners), "breaches": breaches}
