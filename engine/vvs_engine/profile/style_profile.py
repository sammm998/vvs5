"""Ritningsprofilen: vad bladet självt är för sorts ritning, mätt ur bladet.

Motorns toleranser står i punkter. En ändpunkt får snappa inom så många punkter, två linjer räknas som samma
bläck inom så många punkter, en etikett når ett rör inom så många punkter. Talen är rimliga - på en A1 i skala
1:50 ritad med 11-punkters text. Samma ritning nedförminskad till A3 har hälften så stora avstånd mellan
allting, och då är samma tolerans i punkter dubbelt så grov mätt i vad ritaren menade. Den snappar ihop det som
inte hör ihop.

Profilen är måttet på den skillnaden. Den mäter bladets egen geometri - pappersstorlek, texthöjd, pennor,
färger, lager, streckmönster, kurvandel, textläge - och räknar ut en **pappersfaktor**: hur stort bladet är i
förhållande till den ritning toleranserna skrevs för.

Tre saker om den, och alla tre är gränser snarare än funktioner.

**Pappersfaktorn justerar toleranser. Den säger ingenting om meter per punkt.** Skalan kommer ur bladets
skaltext eller skalstock och ingen annanstans ifrån. En profil som började påverka mängden vore inte en profil
utan en gissad skala.

**Profilen är en förmodan, inte ett avgörande.** Den säger vad bladet liknar. Där den och den lokala evidensen
är oense vinner evidensen. En okänd stil ska få en uttalad status och hamna i granskning, inte tyst bli stil 1.

**Den mäter, den verkar inte.** Det här steget räknar ut profilen och skriver ned den. Att låta faktorn skala
toleranserna ändrar varje läsning på varje blad och är därför sitt eget steg med sin egen grind. Att bygga
båda på en gång vore att inte kunna säga vilket av dem som flyttade en meter.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ..pdf.extract import RawPage
from ..pipes.ink import is_stroked

# PipeStudios referens för pappersstorlek: texthöjden på det blad toleranserna skrevs för. Talet är deras
# empiriska startvärde och används som just det - en referenspunkt att mäta mot, inte ett bevisat värde.
REFERENCE_TEXT_PT = 11.0

# Faktorn begränsas. En texthöjd som råkar mätas fel - en enda stor rubrik, en teckenklump som blev en rad -
# får inte kunna halvera eller fyrdubbla varje tolerans i motorn. Utanför intervallet är mätningen misstänkt,
# och då ska profilen säga att den är osäker i stället för att lämna ett tal.
FACTOR_MIN = 0.35
FACTOR_MAX = 2.5

MM_PER_PT = 25.4 / 72.0

# Pappersformat i mm, för den fallback som behövs när bladet inte bär tillräckligt med text att mäta på.
# Fallbacken är uttryckligen svagare evidens: att ett blad är A3 betyder inte att det är en nedförminskad A1.
PAPER_MM = {"A0": (841, 1189), "A1": (594, 841), "A2": (420, 594), "A3": (297, 420), "A4": (210, 297)}

# Textläget, som spec avsnitt F frågar efter.
TEXT_NATIVE = "native"          # filen bär sin text som text
TEXT_GLYPHS = "glyfer"          # texten är ritad med streck och måste byggas ur formerna
TEXT_MIXED = "blandat"          # båda, på olika ställen
TEXT_UNKNOWN = "okant"          # ingen text alls gick att läsa

# Hur säker profilen är på sin pappersfaktor.
MEASURED = "MATT"               # räknad ur texthöjden i sannolika beteckningar
FALLBACK = "PAPPERSFORMAT"      # ingen användbar text: gissad ur pappersformatet, svagare
UNSURE = "OSAKER"               # varken text eller format räckte, eller talet hamnade utanför gränserna


@dataclass
class StyleProfile:
    """Vad bladet är för sorts ritning. Beskrivande - ingenting här avgör något ensamt."""
    page: int
    width_pt: float
    height_pt: float
    width_mm: float
    height_mm: float
    paper_format: str | None
    user_unit: float
    rotation: int

    text_mode: str
    text_height_pt: float | None
    text_height_source: str              # vilken text höjden mättes på
    n_native_rows: int
    n_glyph_rows: int

    paper_factor: float | None
    paper_factor_state: str
    paper_factor_reason: str

    n_paths: int
    n_stroked: int
    n_filled: int
    curve_share: float                   # andel av ritobjekten som är kurvor
    closed_share: float                  # andel stängda vägar
    widths: list[tuple[float, float]] = field(default_factory=list)   # (bredd pt, längd pt), störst först
    colours: list[tuple[str, float]] = field(default_factory=list)
    layers: list[tuple[str, float]] = field(default_factory=list)
    hairline_share: float = 0.0          # hur stor del av bläcket som är ritat med bredd 0
    widths_separate_families: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "page": self.page, "width_pt": round(self.width_pt, 2), "height_pt": round(self.height_pt, 2),
            "width_mm": round(self.width_mm, 1), "height_mm": round(self.height_mm, 1),
            "paper_format": self.paper_format, "user_unit": self.user_unit, "rotation": self.rotation,
            "text_mode": self.text_mode,
            "text_height_pt": None if self.text_height_pt is None else round(self.text_height_pt, 2),
            "text_height_source": self.text_height_source,
            "n_native_rows": self.n_native_rows, "n_glyph_rows": self.n_glyph_rows,
            "paper_factor": None if self.paper_factor is None else round(self.paper_factor, 3),
            "paper_factor_state": self.paper_factor_state, "paper_factor_reason": self.paper_factor_reason,
            "n_paths": self.n_paths, "n_stroked": self.n_stroked, "n_filled": self.n_filled,
            "curve_share": round(self.curve_share, 4), "closed_share": round(self.closed_share, 4),
            "hairline_share": round(self.hairline_share, 4),
            "widths_separate_families": self.widths_separate_families,
            "widths": [[round(w, 2), round(l, 1)] for w, l in self.widths],
            "colours": [[c, round(l, 1)] for c, l in self.colours],
            "layers": [[k, round(l, 1)] for k, l in self.layers],
        }


def paper_format_of(width_pt: float, height_pt: float, user_unit: float = 1.0) -> str | None:
    """Vilket pappersformat sidan har, inom 12 mm. Sidans egen enhet räknas in - en A1 som skriver
    `/UserUnit 2` är ritad i halva talet och skulle annars läsas som en A3."""
    w, h = sorted([width_pt * user_unit * MM_PER_PT, height_pt * user_unit * MM_PER_PT])
    for name, (a, b) in PAPER_MM.items():
        if abs(w - a) <= 12 and abs(h - b) <= 12:
            return name
    return None


def _box_height(b) -> float:
    """En textrutas höjd, oavsett åt vilket håll raden läses.

    En rad med flera tecken är alltid längre i läsriktningen än den är hög, så den korta sidan av rutan är
    texthöjden - och den regeln håller både för en vågrät rad och för en som står på sidan, vilket elva av de
    femtionio bladen gör."""
    return min(abs(b[2] - b[0]), abs(b[3] - b[1]))


def _typical_height(heights: list[float], what: str) -> tuple[float | None, str]:
    """Texthöjden bladet skriver sina beteckningar i.

    Beteckningarna först, för det är dem toleranserna handlar om. Finns de inte faller mätningen tillbaka på
    all text - och säger att den gjorde det, eftersom en rubrikrad är dubbelt så hög som en beteckning och en
    höjd mätt på rubriker skulle ge en pappersfaktor som är dubbelt fel."""
    heights = [h for h in heights if h > 0.5]
    if not heights:
        return None, "ingen text"
    # Typvärdet, inte medelvärdet: en enda stor rubrik ska inte kunna dra höjden. Halvpunktsupplösning räcker,
    # och den binder inte mätningen till exakta flyttal som skiljer sig mellan exporter av samma ritning.
    hist = Counter(round(h * 2) / 2 for h in heights)
    top = max(hist.items(), key=lambda kv: (kv[1], -kv[0]))
    return float(top[0]), what


def _paper_factor(height_pt: float | None, fmt: str | None, source: str) -> tuple[float | None, str, str]:
    """Hur stort bladet är i förhållande till den ritning toleranserna skrevs för."""
    if height_pt and height_pt > 0:
        f = height_pt / REFERENCE_TEXT_PT
        if FACTOR_MIN <= f <= FACTOR_MAX:
            return f, MEASURED, f"texthöjd {height_pt:.2f} pt ur {source} mot referensens {REFERENCE_TEXT_PT:g} pt"
        return None, UNSURE, (f"texthöjd {height_pt:.2f} pt ger faktorn {f:.2f}, utanför "
                              f"[{FACTOR_MIN}, {FACTOR_MAX}] - mätningen är misstänkt och lämnar inget tal")
    if fmt:
        # Svagare, och det ska stå. Att ett blad är A3 betyder att det är litet, inte att det är en A1 som
        # någon förminskat: en ritning som ritats för A3 från början har text i A3-storlek och faktorn 1.
        return None, FALLBACK, (f"ingen text att mäta på; sidan är {fmt}, vilket säger något om storleken "
                                f"men inte om texten - ingen faktor sätts på den grunden ensam")
    return None, UNSURE, "varken text eller känt pappersformat"


def profile_page(page: RawPage, rows=None, designations=None) -> StyleProfile:
    """Bladets profil, mätt ur det som faktiskt är ritat.

    rows: alla textrader läsningen fick fram. designations: de rader som blev beteckningar - höjden mäts helst
    på dem, eftersom det är etiketternas storlek toleranserna handlar om."""
    info = page.info
    uu = float(getattr(info, "user_unit", 1.0) or 1.0)
    paths = page.paths
    n_stroked = n_filled = n_curves = n_items = n_closed = 0
    widths: Counter = Counter()
    colours: Counter = Counter()
    layers: Counter = Counter()
    hairline_len = 0.0
    ink_len = 0.0
    for p in paths:
        L = sum(s.length for s in p.segs)
        # Bläckkontraktet står på ETT ställe (pipes/ink.py) och profilen läser samma. En hårfin penna har
        # bredd 0 och är ändå en penna; `bool(p.width)` hade kallat varje hårlinje för en fylld form och
        # gjort profilens hårfinhetsmått till en nolla just på de blad det finns till för.
        if is_stroked(p):
            n_stroked += 1
            widths[round(p.width, 2)] += L
            ink_len += L
            if float(p.width or 0.0) <= 0.0:
                hairline_len += L
        else:
            n_filled += 1
        colours[str(p.color)] += L
        layers[p.layer] += L
        n_curves += getattr(p, "n_curves", 0)
        n_items += len(p.segs)
        if getattr(p, "closed", False):
            n_closed += 1

    rows = list(rows or [])
    n_native = sum(1 for r in rows if getattr(r, "source", "") == "text")
    n_glyph = len(rows) - n_native
    if n_native and n_glyph:
        mode = TEXT_MIXED
    elif n_native:
        mode = TEXT_NATIVE
    elif n_glyph:
        mode = TEXT_GLYPHS
    else:
        mode = TEXT_UNKNOWN

    dboxes = [_box_height(d.bbox) for d in (designations or []) if getattr(d, "bbox", None)]
    if dboxes:
        h, src = _typical_height(dboxes, "beteckningsrader")
    else:
        h, src = _typical_height([r.height for r in rows if getattr(r, "height", 0)], "all text")
    fmt = paper_format_of(info.width, info.height, uu)
    factor, state, reason = _paper_factor(h, fmt, src)

    # Skiljer bredder alls familjer åt? På en hårfin export har allt bredd 0 och svaret är nej - och då får
    # ingenting i läsningen luta sig mot bredden för att skilja rörlagret från arkitektens.
    distinct = [w for w, L in widths.items() if L > 0.01 * max(ink_len, 1e-9)]
    return StyleProfile(
        page=info.index, width_pt=info.width, height_pt=info.height,
        width_mm=info.width * uu * MM_PER_PT, height_mm=info.height * uu * MM_PER_PT,
        paper_format=fmt, user_unit=uu, rotation=info.rotation,
        text_mode=mode, text_height_pt=h, text_height_source=src,
        n_native_rows=n_native, n_glyph_rows=n_glyph,
        paper_factor=factor, paper_factor_state=state, paper_factor_reason=reason,
        n_paths=len(paths), n_stroked=n_stroked, n_filled=n_filled,
        curve_share=n_curves / max(1, n_curves + n_items),
        closed_share=n_closed / max(1, len(paths)),
        widths=sorted(((w, L) for w, L in widths.items()), key=lambda t: (-t[1], t[0]))[:12],
        colours=sorted(((c, L) for c, L in colours.items()), key=lambda t: (-t[1], t[0]))[:8],
        layers=sorted(((k, L) for k, L in layers.items()), key=lambda t: (-t[1], t[0]))[:12],
        hairline_share=hairline_len / max(ink_len, 1e-9),
        widths_separate_families=len(distinct) > 1,
    )


def tolerance_overrides(profile: StyleProfile | None) -> dict[str, float]:
    """Vilka toleranser bladets storlek flyttar, och vart.

    Bara de regler som själva säger att de följer papperet (`Rule.scales_with_paper`). Skillnaden mot att skala
    allt i punkter är hela poängen: ett avstånd som säger hur långt en hänvisningslinje får sträcka sig är
    skrivet för en ritning av en viss storlek, medan ett avstånd som säger om två streck är samma bläck följer
    PENNAN. Det senare skalas inte här.

    Två gränser till:

    * en regel som användes för att LÄSA texten kan inte skalas med en faktor som räknats ur den texten. Den
      cirkeln går bara att bryta genom att läsa bladet två gånger, och det är inte värt det - därför är inga
      textregler märkta;
    * varje flyttat värde hålls inom regelns egna `lo`/`hi`. Registret vet vad som är ett rimligt tal för just
      den regeln; pappersfaktorn vet bara hur stort bladet är."""
    f = tolerance_scale(profile)
    if f == 1.0:
        return {}
    from ..rules import RULES
    out: dict[str, float] = {}
    for r in RULES:
        if not (r.scales_with_paper and r.tunable):
            continue
        v = float(r.default) * f
        if r.lo is not None:
            v = max(float(r.lo), v)
        if r.hi is not None:
            v = min(float(r.hi), v)
        out[r.id] = v
    return out


def tolerance_scale(profile: StyleProfile | None) -> float:
    """Vad toleranserna SKULLE skalas med om profilen fick verka. Ingen kallar den ännu.

    Den står här för att gränsen ska stå i koden och inte bara i ett beslut: saknas faktorn är svaret 1, alltså
    toleranserna som de är. Att gissa en faktor på ett blad där texthöjden inte gick att mäta vore att låta ett
    fel i textläsningen bli ett fel i geometrin."""
    if profile is None or profile.paper_factor is None:
        return 1.0
    return max(FACTOR_MIN, min(FACTOR_MAX, profile.paper_factor))
