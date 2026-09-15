from __future__ import annotations

import math

"""Övningsritningarna.

Ett övningsblad är inte en bild. Det är geometri: väggar, rörstråk med system och dimension, symboler med
plats och sort. Gränssnittet ritar det, den som övar mäter på det, och facit räknas **ur samma geometri** -
aldrig ur ett tal någon skrivit in för hand. Skriver någon om ett stråk följer facit med.

Skalan anges som meter per ritningsenhet. Bladen är ritade i en ruta på 1200 x 760 enheter, och 0,05 m per
enhet ger ett hus på 60 x 38 meter — det är för stort för ett badrum, så varje blad sätter sin egen.
"""

Pt = tuple[float, float]


def length(points: list[Pt]) -> float:
    return sum(math.dist(points[i - 1], points[i]) for i in range(1, len(points)))


def metres(points: list[Pt], m_per_unit: float) -> float:
    return round(length(points) * m_per_unit, 2)


def path_d(points: list[Pt]) -> str:
    return "M" + " L".join(f"{x} {y}" for x, y in points)


class Plan:
    """Ett blad. `runs` är rörstråk, `symbols` är komponenter, `rooms` är rum med namn."""

    def __init__(self, slug: str, title: str, m_per_unit: float, view=(0, 0, 1200, 760)):
        self.slug, self.title, self.m_per_unit, self.view = slug, title, m_per_unit, view
        self.walls: list[list[Pt]] = []
        self.runs: list[dict] = []
        self.symbols: list[dict] = []
        self.rooms: list[dict] = []

    def wall(self, *pts: Pt) -> "Plan":
        self.walls.append(list(pts))
        return self

    def run(self, rid: str, sys: str, dn: int, *pts: Pt, label: str = "") -> "Plan":
        self.runs.append({
            "id": rid, "sys": sys, "dn": dn, "label": label or f"{sys}-{dn}",
            "points": [list(p) for p in pts], "d": path_d(list(pts)),
            "m": metres(list(pts), self.m_per_unit),
        })
        return self

    def symbol(self, sid: str, kind: str, x: float, y: float, name: str = "", rot: float = 0) -> "Plan":
        self.symbols.append({"id": sid, "kind": kind, "x": x, "y": y, "name": name or kind, "rot": rot})
        return self

    def room(self, name: str, x: float, y: float, w: float, h: float) -> "Plan":
        self.rooms.append({"name": name, "x": x, "y": y, "w": w, "h": h})
        return self

    # ---- frågor facit ställs mot -------------------------------------------------------------------

    def metres_of(self, *ids: str) -> float:
        return round(sum(r["m"] for r in self.runs if r["id"] in ids), 2)

    def metres_where(self, sys: str | None = None, dn: int | None = None) -> float:
        return round(sum(r["m"] for r in self.runs
                         if (sys is None or r["sys"] == sys) and (dn is None or r["dn"] == dn)), 2)

    def ids_of_kind(self, *kinds: str) -> list[str]:
        return sorted(s["id"] for s in self.symbols if s["kind"] in kinds)

    def count_of(self, *kinds: str) -> int:
        return len(self.ids_of_kind(*kinds))

    def names(self) -> dict[str, str]:
        return {s["id"]: s["name"] for s in self.symbols}

    def data(self) -> dict:
        return {
            "plan": self.slug, "title": self.title, "m_per_unit": self.m_per_unit, "view": list(self.view),
            "walls": [[list(p) for p in w] for w in self.walls],
            "runs": [{k: v for k, v in r.items() if k != "points"} for r in self.runs],
            "symbols": self.symbols, "rooms": self.rooms,
            "names": self.names(),
        }


# ---------------------------------------------------------------- blad 1: ett badrum

BAD = Plan("badrum-1", "Badrum med WC, tvättställ, dusch och golvbrunn", 0.012, (0, 0, 900, 620))
(BAD
 .wall((60, 60), (840, 60), (840, 560), (60, 560), (60, 60))
 .wall((460, 60), (460, 300))
 .room("Badrum", 60, 60, 400, 500)
 .room("WC", 460, 60, 380, 240)
 # tappkallvatten: från stam till tvättställ, WC och dusch
 .run("kv-stam", "KV", 20, (110, 540), (110, 200), label="KV1-B2-20")
 .run("kv-tvatt", "KV", 15, (110, 200), (300, 200), label="KV1-B2-15")
 .run("kv-dusch", "KV", 15, (110, 330), (250, 330), (250, 430), label="KV1-B3-15")
 .run("kv-wc", "KV", 15, (110, 130), (620, 130), label="KV1-B4-15")
 # tappvarmvatten följer kallvattnet fram till tvättställ och dusch
 .run("vv-stam", "VV", 20, (140, 540), (140, 230), label="VV1-B2-20")
 .run("vv-tvatt", "VV", 15, (140, 230), (300, 230), label="VV1-B2-15")
 .run("vv-dusch", "VV", 15, (140, 350), (250, 350), (250, 430), label="VV1-B3-15")
 # spillvatten med självfall mot stammen
 .run("s-golvbrunn", "S", 75, (250, 470), (360, 470), (360, 540), label="S1-B1-75")
 .run("s-wc", "S", 110, (620, 190), (620, 470), (360, 470), label="S1-B1-110")
 .run("s-tvatt", "S", 50, (300, 260), (360, 260), (360, 470), label="S1-B2-50")
 .symbol("v-kv-stam", "kulventil", 110, 500, "Avstängning KV vid stam")
 .symbol("v-vv-stam", "kulventil", 140, 500, "Avstängning VV vid stam")
 .symbol("v-tvatt", "kulventil", 285, 215, "Avstängning tvättställ")
 .symbol("v-wc", "kulventil", 600, 130, "Avstängning WC")
 .symbol("gb1", "golvbrunn", 250, 470, "Golvbrunn")
 .symbol("wc1", "wc", 620, 165, "WC-stol")
 .symbol("tv1", "tvattstall", 315, 245, "Tvättställ")
 .symbol("du1", "dusch", 250, 430, "Duschplats")
 .symbol("bl1", "blandare", 315, 215, "Tvättställsblandare")
 .symbol("bl2", "blandare", 250, 390, "Duschblandare")
 )

# ---------------------------------------------------------------- blad 2: en värmekrets

VARME = Plan("varme-1", "Radiatorkrets med fram- och returledning", 0.03, (0, 0, 1100, 700))
(VARME
 .wall((60, 60), (1040, 60), (1040, 640), (60, 640), (60, 60))
 .wall((400, 60), (400, 380)).wall((740, 260), (740, 640))
 .room("Kontor 1", 60, 60, 340, 580).room("Kontor 2", 400, 60, 340, 320).room("Korridor", 740, 260, 300, 380)
 .run("vs-fram", "VS", 32, (120, 600), (120, 140), (900, 140), label="VS1-F-32")
 .run("vs-retur", "VS", 32, (150, 600), (150, 170), (900, 170), label="VS1-R-32")
 .run("vs-gren1", "VS", 20, (300, 140), (300, 250), label="VS1-F-20")
 .run("vs-gren2", "VS", 20, (600, 140), (600, 250), label="VS1-F-20")
 .run("vs-gren3", "VS", 20, (860, 140), (860, 320), label="VS1-F-20")
 .run("vs-ret1", "VS", 20, (330, 170), (330, 250), label="VS1-R-20")
 .run("vs-ret2", "VS", 20, (630, 170), (630, 250), label="VS1-R-20")
 .symbol("rad1", "radiator", 300, 270, "Radiator kontor 1", 0)
 .symbol("rad2", "radiator", 600, 270, "Radiator kontor 2", 0)
 .symbol("rad3", "radiator", 860, 340, "Radiator korridor", 0)
 .symbol("p1", "pump", 120, 560, "Cirkulationspump")
 .symbol("v1", "kulventil", 120, 480, "Avstängning framledning")
 .symbol("v2", "kulventil", 150, 480, "Avstängning returledning")
 .symbol("inj1", "injustering", 330, 210, "Injusteringsventil radiator 1")
 .symbol("inj2", "injustering", 630, 210, "Injusteringsventil radiator 2")
 .symbol("bv1", "backventil", 120, 420, "Backventil")
 .symbol("exp1", "expansionskarl", 190, 560, "Expansionskärl")
 )

# ---------------------------------------------------------------- blad 3: en tappvattenstam

STAM = Plan("stam-1", "Tappvattenstam med KV, VV och VVC genom tre plan", 0.02, (0, 0, 1000, 760))
(STAM
 .wall((80, 60), (920, 60), (920, 700), (80, 700), (80, 60))
 .wall((80, 280), (920, 280)).wall((80, 490), (920, 490))
 .room("Plan 3", 80, 60, 840, 220).room("Plan 2", 80, 280, 840, 210).room("Plan 1", 80, 490, 840, 210)
 .run("kv-stig", "KV", 32, (200, 660), (200, 120), label="KV1-S1-32")
 .run("vv-stig", "VV", 25, (240, 660), (240, 120), label="VV1-S1-25")
 .run("vvc-stig", "VVC", 15, (280, 660), (280, 120), label="VVC1-S1-15")
 .run("kv-p3", "KV", 20, (200, 160), (700, 160), label="KV1-S1-20")
 .run("kv-p2", "KV", 20, (200, 380), (700, 380), label="KV1-S1-20")
 .run("kv-p1", "KV", 20, (200, 590), (700, 590), label="KV1-S1-20")
 .run("vv-p3", "VV", 20, (240, 190), (700, 190), label="VV1-S1-20")
 .run("vv-p2", "VV", 20, (240, 410), (700, 410), label="VV1-S1-20")
 .run("vv-p1", "VV", 20, (240, 620), (700, 620), label="VV1-S1-20")
 .symbol("v3", "kulventil", 200, 200, "Avstängning plan 3")
 .symbol("v2", "kulventil", 200, 420, "Avstängning plan 2")
 .symbol("v1", "kulventil", 200, 630, "Avstängning plan 1")
 .symbol("bv", "backventil", 200, 690, "Backventil inkommande")
 .symbol("i1", "injustering", 280, 300, "Injustering VVC")
 )

PLANS = {p.slug: p for p in (BAD, VARME, STAM)}
