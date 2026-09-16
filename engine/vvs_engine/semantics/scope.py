"""Vad som ska byggas, och vad som bara står på ritningen.

En ritning visar mer än entreprenaden. Den visar befintliga ledningar som ska vara kvar, ledningar som ska
rivas, och prefabricerade enheter vars rör redan sitter monterade från fabrik. Ingen av dem är ny meter att
bygga - och ingenting i geometrin skiljer dem från det som ska byggas. Skillnaden står i en markering vid
beteckningen, och vad markeringen betyder står i bladets egen förklaring.

Därför avgörs det här inte av en tabell utan av ritningen, precis som allt annat:

* En hel kod inom parentes - `(S1)`, `(KV-15)` - betyder befintligt **där förklaringen säger det**. Sjukhusens
  förklaringar skriver ut det: "( ) AVSER BEFINTLIGT". På ett blad som inte säger det är parentesen inte ett
  bevis för någonting.
* `BEF` vid en beteckning är en omfattningsgräns, inte en mängd.
* `(PB)` och `(PWC)` märker prefabricerade badrum och WC-enheter: rören inuti är fabriksleverans.

**Hittar läsningen en markering som förklaringen inte definierar blir raden OKÄND och går till granskning.**
Den räknas varken som ny eller undantas i tysthet. Att tyst undanta är det farligaste av de två: mängden blir
för liten, ingen rad ser konstig ut, och felet upptäcks först när någon jämför med verkligheten.

Det här modulen läser TEXT. Rivningsmarkeringar ritade som kryss längs en linje, och arbetsområdets streckade
rektangel, är geometri och avgörs inte här; de står som ogjorda.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Omfattningar en rad kan ha. NY är det normala och behöver ingen markering.
NY = "NY"
BEFINTLIG = "BEFINTLIG"
RIVNING = "RIVNING"
PREFAB = "PREFAB"
OKAND = "OKAND_MARKERING"

NOT_NEW = frozenset({BEFINTLIG, RIVNING, PREFAB})

# Vad bladets förklaring kan säga om en markering. Orden är ritspråkets, inte ett enskilt blads.
_LEGEND_MEANINGS: tuple[tuple[str, re.Pattern], ...] = (
    (BEFINTLIG, re.compile(r"BEFINTLIG|BEFINTLIGT|BEF\b", re.I)),
    (RIVNING, re.compile(r"\bRIV(?:AS|NING|ES)?\b|DEMONTER", re.I)),
    (PREFAB, re.compile(r"PREFAB|FABRIKS(?:MONTERAD|LEVERANS)", re.I)),
)

# Hur en markering kan se ut vid en beteckning.
_PARENTHESISED = re.compile(r"^\s*\((?P<inner>[^()]+)\)\s*$")
# En bokstav inom parentes sist i en beteckning är INTE automatiskt en omfattningsmarkering: ritspråket
# använder samma plats för annat, bland annat luftning (`110L`, `100V`). Därför fångas en ensam bokstav bara
# när förklaringen själv har definierat just den; två till fyra bokstäver prövas alltid.
_SUFFIX_CODE = re.compile(r"\(\s*(?P<code>[A-ZÅÄÖ]{1,4})\s*\)\s*$")
_BARE_SUFFIX = re.compile(r"[\s\-]((?:BEF))\s*$", re.I)


@dataclass(frozen=True)
class ScopeReading:
    """Radens omfattning, och varför.

    `review` är sant när ritningen visade en markering men inte förklarade den. Då är `scope` OKAND, och raden
    ska synas för den som granskar - inte försvinna och inte räknas som ny.
    """
    scope: str
    marker: str | None
    why: str
    review: bool = False

    def as_dict(self) -> dict:
        return {"scope": self.scope, "marker": self.marker, "why": self.why, "review": self.review}


def markers_from_legend(legend) -> dict[str, str]:
    """Vilka omfattningsmarkeringar bladets egen förklaring definierar: markering -> omfattning.

    En rad i förklaringen som visar en parentes och säger "avser befintligt" definierar parentesen. En rad som
    ger koden `PB` beskrivningen "prefabricerat badrum" definierar `PB`. Ingenting antas: säger förklaringen
    ingenting om en markering finns den inte här, och då blir varje förekomst av den okänd.
    """
    out: dict[str, str] = {}
    if legend is None:
        return out
    for e in getattr(legend, "entries", ()) or ():
        text = f"{getattr(e, 'code', '') or ''} {getattr(e, 'description', '') or ''}"
        meaning = next((name for name, pat in _LEGEND_MEANINGS if pat.search(text)), None)
        if meaning is None:
            continue
        code = (getattr(e, "code", "") or "").strip().upper()
        # "( )" som kod betyder att parentesen själv är markeringen
        if code and set(code) <= {"(", ")", " ", "-", "_"}:
            out["()"] = meaning
        elif code and re.fullmatch(r"[A-ZÅÄÖ]{1,4}", code):
            out[code] = meaning
        elif re.search(r"\(\s*\)", getattr(e, "description", "") or ""):
            out["()"] = meaning
    return out


def scope_of(text: str, markers: dict[str, str] | None) -> ScopeReading:
    """Radens omfattning, läst ur beteckningens egen text mot bladets förklarade markeringar."""
    raw = (text or "").strip()
    known = markers or {}
    if not raw:
        return ScopeReading(NY, None, "ingen text att läsa markering ur")

    m = _SUFFIX_CODE.search(raw)
    if m:
        code = m.group("code").upper()
        if code in known:
            return ScopeReading(known[code], f"({code})", f"förklaringen ger ({code}) betydelsen {known[code].lower()}")
        if len(code) >= 2:
            return ScopeReading(OKAND, f"({code})", f"beteckningen bär markeringen ({code}) som förklaringen inte definierar",
                                review=True)
        # en ensam bokstav som förklaringen inte nämner är inte en omfattningsmarkering; den kan vara vad som helst

    p = _PARENTHESISED.match(raw)
    if p:
        if "()" in known:
            return ScopeReading(known["()"], "()", f"förklaringen säger att parentes betyder {known['()'].lower()}")
        return ScopeReading(OKAND, "()", "hela beteckningen står inom parentes och förklaringen säger inte vad det betyder",
                            review=True)

    b = _BARE_SUFFIX.search(raw)
    if b:
        code = b.group(1).upper()
        if code in known:
            return ScopeReading(known[code], code, f"förklaringen ger {code} betydelsen {known[code].lower()}")
        return ScopeReading(OKAND, code, f"beteckningen slutar på {code} som förklaringen inte definierar", review=True)

    return ScopeReading(NY, None, "ingen omfattningsmarkering vid beteckningen")


def strip_marker(text: str) -> str:
    """Beteckningen utan sin omfattningsmarkering, så att identiteten går att jämföra med samma kod utan den.

    `(S1)` och `S1` är samma ledning i två omfattningar, inte två olika ledningar. Råtexten bevaras av den som
    anropar; det här är bara nyckeln att jämföra på.
    """
    raw = (text or "").strip()
    m = _SUFFIX_CODE.search(raw)
    if m:
        raw = raw[:m.start()].strip(" -")
    p = _PARENTHESISED.match(raw)
    if p:
        raw = p.group("inner").strip()
    b = _BARE_SUFFIX.search(raw)
    if b:
        raw = raw[:b.start()].strip(" -")
    return raw
