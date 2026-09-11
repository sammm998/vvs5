"""Vilket bläck en path faktiskt lägger på pappret - sagt på ett ställe.

En PDF ritar på tre sätt: den stryker en penna längs en väg (`s`), den fyller en väg (`f`), eller den gör
båda (`fs`). Läsningen frågade det på sjutton ställen och fick olika svar. Topologin tog bara `s` och såg
därför aldrig `fs`; anknytningen tog allt utom `f` och såg därför `fs`. Ett blad där de två är oense är ett
blad där en beteckning kan peka på bläck som ingen mätning känner till - en etikett med en representation
som inte finns.

Vad mätningen visade över referensomgången: `fs` är 27,6 % av allt bläck, och **varenda** sådan path har
pennbredd 0,00. Det är inte rör ritade med fyllning; det är fyllda former - bokstavskonturer, symboler,
skrafferingar - vars kant råkar vara en väg. Hälften av dem tar textrekonstruktionen redan.

Därav kontraktet, och det är smalt med flit:

* En path bär **struket** bläck bara om den verkligen stryks: `s` eller `fs` **med en penna som har bredd**.
  Det är den geometri som får bli rör, mätas och ägas.
* En `fs` utan bredd, och en `f`, är en **fylld form**. Dess kant är en gräns, inte ett streck. Den får vara
  symbol, figur eller skraffering - aldrig en ritad linje som något mäts längs.
* Det som avvisas försvinner inte. Varje path får ett omdöme med skäl och källa, så att en granskning kan
  fråga varför en viss väg inte blev rör och få ett svar som pekar på pappret.

Att låta anknytningen se fyllda former är farligt åt det håll som kostar meter: en hänvisningslinje kan sluta
på en fylld bokstav och kallas anknuten till ett rör som inte finns. Att topologin inte ser dem kostar inget
på den här omgången - noll punkter av det bläcket ligger på ett rörlager - men kontraktet ska ändå vara ett,
för nästa ritning kan vara ritad av någon annan.
"""
from __future__ import annotations

from dataclasses import dataclass

# Pennbredden under vilken ett "streck" inte är ett streck. En PDF skriver 0 för "tunnast möjliga" också när
# den stryker på riktigt, så gränsen kan inte vara noll utan att tunna hårstreck försvinner - men en fylld
# form med `w 0` är alltid exakt 0,0 medan en ritad hårlinje bär sin faktiska bredd. Gränsen är därför under
# varje riktig penna och över ingen alls.
HAIRLINE = 0.0

STROKED = "STROKED"              # ett ritat streck: en penna med bredd har gått längs vägen
FILL_BOUNDARY = "FILL_BOUNDARY"  # kanten på en fylld form: en gräns, inte en linje
EMPTY = "EMPTY"                  # ingen geometri att tala om


@dataclass(frozen=True)
class InkVerdict:
    """Vad den här vägen lägger på pappret, och varför läsningen säger så."""
    kind: str                    # STROKED | FILL_BOUNDARY | EMPTY
    reason: str
    width: float
    path_kind: str               # 's' | 'f' | 'fs', som PDF:en skrev den
    source: str                  # pid, så att omdömet går att slå upp på bladet

    @property
    def stroked(self) -> bool:
        return self.kind == STROKED

    def as_dict(self) -> dict:
        return {"ink": self.kind, "reason": self.reason, "width": round(self.width, 3),
                "path_kind": self.path_kind, "source": self.source}


def ink_of(path) -> InkVerdict:
    """Omdömet om en råväg. Samma svar var det än frågas."""
    w = float(getattr(path, "width", 0.0) or 0.0)
    k = getattr(path, "kind", "s")
    pid = getattr(path, "pid", "")
    if not getattr(path, "segs", None):
        return InkVerdict(EMPTY, "vägen har ingen geometri", w, k, pid)
    if k == "s":
        return InkVerdict(STROKED, "struken väg", w, k, pid)
    if k == "fs":
        if w > HAIRLINE:
            return InkVerdict(STROKED, "fylld väg som också stryks med en penna som har bredd", w, k, pid)
        return InkVerdict(FILL_BOUNDARY, "fylld väg vars streck saknar bredd: kanten är en gräns, inte en linje",
                          w, k, pid)
    return InkVerdict(FILL_BOUNDARY, "fylld väg", w, k, pid)


def is_stroked(path) -> bool:
    """Ska den här vägen räknas som ritad linje - den enda sortens bläck som får bli rör och mätas?"""
    return ink_of(path).stroked


def is_fill_boundary(path) -> bool:
    """Är det här kanten på en fylld form? Symbol, figur och skraffering får läsa den; mätningen inte."""
    return ink_of(path).kind == FILL_BOUNDARY


def ink_census(page) -> dict:
    """Bladets bläck uppdelat efter kontraktet, till granskningen.

    Redovisningen är poängen: den som undrar varför en väg inte blev rör ska kunna läsa hur mycket sådant
    bläck bladet har och på vilka lager det ligger, inte behöva gissa.
    """
    from collections import defaultdict
    out: dict[str, dict] = {}
    layers: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for p in getattr(page, "paths", []):
        v = ink_of(p)
        r = out.setdefault(v.kind, {"paths": 0, "length_pt": 0.0, "reasons": defaultdict(float)})
        r["paths"] += 1
        r["length_pt"] += p.length
        r["reasons"][v.reason] += p.length
        layers[p.layer or ""][v.kind] += p.length
    for r in out.values():
        r["length_pt"] = round(r["length_pt"], 1)
        r["reasons"] = {k: round(v, 1) for k, v in sorted(r["reasons"].items(), key=lambda t: -t[1])}
    top = sorted(layers.items(), key=lambda t: -sum(t[1].values()))[:25]
    return {"by_ink": out,
            "by_layer": [{"layer": k, **{kk: round(vv, 1) for kk, vv in sorted(v.items())}} for k, v in top]}
