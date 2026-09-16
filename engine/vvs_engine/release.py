"""Vad en läsning kördes under, och hur en regeländring aktiveras utan att gå att ta tillbaka.

Två saker som hänger ihop och båda handlar om att kunna svara på frågan *varför blev det så här den gången*.

**Releaseidentiteten** är allt som kan få två läsningar av samma PDF att svara olika: koden, reglerna och vad de
står på, ritningsprofilen, renderarens och textläsarens versioner, körningsflaggorna och dokumentet självt. Den
är ett enda värde, och den är cachenyckeln. Det är inte en bokföringsdetalj: ett mellanresultat som återanvänds
under en annan identitet är gammalt ägarskap ovanpå ny geometri, och det är den sortens fel som inte syns i en
summa.

**Regeländringen** är hur en gräns i motorn får flyttas. En regel som ändras för att ett blad blev bättre är en
regel som anpassats efter ett blad. Förfarandet nedan är spec avsnitt K, steg för steg, och det är avsiktligt
obekvämt:

1. hypotesen och exakt vilka regler som ändras skrivs ned **först**;
2. underlaget delas på oberoende dokument - varianter av samma PDF är samma dokument, inte två;
3. den generella regeln prövas mot **alla** stilgrupper som stöds, med både fall som ska bli bättre och fall
   som inte får bli sämre;
4. kandidaten aktiveras bara om regressionen fortfarande stämmer;
5. ett stilundantag tillåts först när en **mätt** konflikt visar att den gemensamma regeln skadar en annan stil
   och att undantaget hjälper den avsedda;
6. aktiveringen är atomär, får ett versionsnummer, och den förra versionen finns kvar att gå tillbaka till.

Modulen håller förfarandet, inte omdömet. Den avgör inte om en regressionskörning är bra nog - den vägrar att
kalla något aktiverat som inte har gått igenom stegen, och den kan alltid säga vilken version som gällde.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

# En regeländrings tillstånd. Ordningen är den enda tillåtna vägen framåt.
PROPOSED = "FORESLAGEN"          # hypotesen nedskriven, ingenting prövat
TESTED = "PROVAD"                # regressionen körd, utfallet bifogat
ACTIVE = "AKTIV"                 # aktiverad atomärt, med versionsnummer
REJECTED = "AVSLAGEN"            # prövad och underkänd
ROLLED_BACK = "ATERTAGEN"        # var aktiv, är det inte längre

# Minsta underlag innan en ändring alls får prövas. PipeStudios miniminivå är två oberoende dokument och minst
# ett undanhållet fall. Den är en mekanisk grind, inte en statistisk prövning, och står här som ett golv -
# inte som ett mått på att en ändring är riktig.
MIN_INDEPENDENT_SOURCES = 2
MIN_HELD_OUT = 1


def _h(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


@dataclass(frozen=True)
class ReleaseIdentity:
    """Allt som kan få två läsningar av samma PDF att svara olika."""
    code: str                    # källans hash (frysningsmanifestet) eller commit
    rules: str                   # vad varje regel stod på, inte bara vilka som finns
    profile: str                 # ritningsprofilens version/hash
    renderer: str                # PyMuPDF/MuPDF
    text_reader: str             # glyfläsaren och eventuell OCR
    flags: dict[str, Any] = field(default_factory=dict)
    document: str = ""           # dokumentets SHA-256
    model: str = ""              # etikettmodellens fil, när en sådan används

    @property
    def key(self) -> str:
        """Cachenyckeln. Ändras en enda del ska varje steg som berodde på den räknas om."""
        return _h({"code": self.code, "rules": self.rules, "profile": self.profile, "renderer": self.renderer,
                   "text_reader": self.text_reader, "flags": self.flags, "document": self.document,
                   "model": self.model})

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "rules": self.rules, "profile": self.profile, "renderer": self.renderer,
                "text_reader": self.text_reader, "flags": dict(self.flags), "document": self.document,
                "model": self.model, "key": self.key}

    def covers(self, other: "ReleaseIdentity") -> bool:
        """Får ett mellanresultat från `other` återanvändas under den här identiteten?

        Bara om ingenting alls skiljer. Det finns en frestelse att säga att en ändrad tolerans inte påverkar
        textläsningen och att den delen får återanvändas; den frestelsen är hur gammalt ägarskap hamnar ovanpå
        ny geometri. Vill man dela upp cachen ska stegen ha var sin identitet, inte en gemensam med undantag.
        """
        return self.key == other.key


def identity_of_run(pdf_path: str, *, code: str, flags: dict[str, Any] | None = None,
                    profile: str = "", model: str = "") -> ReleaseIdentity:
    """Identiteten för en körning, med de delar som går att läsa ur miljön hämtade där.

    Renderarens och textläsarens versioner kommer ur biblioteken själva och inte ur en sträng någon skrivit:
    en uppgraderad MuPDF som inte ändrar nyckeln är en uppgradering som inte syns förrän någon undrar varför
    två körningar av samma ritning gav olika mängd."""
    from . import __version__
    from .rules import catalogue
    try:
        import pymupdf
        # (bindningens version, MuPDF:s version, byggdatum) - alla tre, eftersom en ny MuPDF under samma
        # bindning ritar annorlunda och det är renderaren som avgör vad som är synligt bläck
        renderer = "pymupdf-" + "-".join(str(v) for v in pymupdf.version)
    except Exception:                                        # noqa: BLE001
        renderer = "pymupdf-okand"
    return ReleaseIdentity(code=code, rules=rules_fingerprint(catalogue()), profile=profile,
                           renderer=renderer, text_reader=f"vvs-{__version__}",
                           flags=dict(flags or {}), document=file_sha(pdf_path), model=model)


def file_sha(path: str) -> str:
    """Dokumentets SHA-256. Två filer med samma namn är inte samma dokument; två med samma innehåll är det."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def rules_fingerprint(catalogue: dict[str, Any]) -> str:
    """Vad varje regel STÅR PÅ, inte bara vilka som finns.

    En ändrad tolerans som inte ändrar cachenyckeln är en ändring som inte syns förrän någon undrar varför två
    körningar av samma ritning gav olika mängd."""
    vals = sorted((r["id"], r.get("value", r.get("default")))
                  for g in catalogue.get("groups", []) for r in g.get("rules", []))
    return _h(vals)


def independent_sources(documents: list[dict]) -> list[str]:
    """Hur många OBEROENDE dokument ett underlag består av.

    En omkörning av samma PDF, en rasterexport av den, en beskärning, en ny revision av samma blad genom en
    annan pipeline - allt det är samma dokument sagt om igen. Räknas de som skilda källor uppfylls varje
    tröskel av ett enda blad, och det är samma fel som projektpriorn hade innan den räknade källor i stället
    för körningar.

    Dokument skiljs på sin SHA. Saknas den faller räkningen tillbaka på projekt och blad tillsammans - aldrig
    på filnamnet ensamt, eftersom samma blad kan heta olika i två mappar."""
    seen: dict[str, None] = {}
    for d in documents:
        sha = (d.get("sha") or "").strip()
        key = sha or f"{d.get('project', '')}|{d.get('sheet', '')}"
        if key.strip("|"):
            seen.setdefault(key, None)
    return sorted(seen)


@dataclass
class Regression:
    """Vad en kandidat gjorde med varje stilgrupp den prövades mot."""
    per_style: dict[str, dict[str, float]]      # stil -> {"fore": x, "efter": y} i det mått som gäller
    held_out: list[str] = field(default_factory=list)      # dokument som inte användes för att ta fram regeln
    note: str = ""

    def worse(self, tol: float = 0.0) -> list[str]:
        """Stilgrupper som blev sämre. Det är den lista som avgör, inte den som blev bättre."""
        return sorted(s for s, v in self.per_style.items()
                      if (v.get("efter", 0.0) - v.get("fore", 0.0)) < -tol)

    def better(self, tol: float = 0.0) -> list[str]:
        return sorted(s for s, v in self.per_style.items()
                      if (v.get("efter", 0.0) - v.get("fore", 0.0)) > tol)

    def as_dict(self) -> dict[str, Any]:
        return {"per_style": self.per_style, "held_out": list(self.held_out), "note": self.note,
                "better": self.better(), "worse": self.worse()}


@dataclass
class RuleChange:
    """En föreslagen ändring av en eller flera regler, och hela dess väg genom förfarandet."""
    change_id: str
    hypothesis: str                              # vad ändringen påstår, skrivet FÖRE prövningen
    changes: dict[str, Any]                      # regel-id -> nytt värde
    before: dict[str, Any]                       # regel-id -> värdet den hade
    sources: list[dict] = field(default_factory=list)      # dokumenten underlaget består av
    style_scope: str | None = None               # None = generell regel; annars stilgruppen undantaget gäller
    state: str = PROPOSED
    version: int = 0
    previous_version: int | None = None
    regression: Regression | None = None
    reason: str = ""

    # ------------------------------------------------------------------ steg 2-3: underlaget och prövningen
    def enough_evidence(self) -> tuple[bool, str]:
        src = independent_sources(self.sources)
        if len(src) < MIN_INDEPENDENT_SOURCES:
            return False, (f"{len(src)} oberoende dokument, {MIN_INDEPENDENT_SOURCES} krävs - varianter av "
                           f"samma PDF räknas som ett")
        held = list((self.regression.held_out if self.regression else []) or [])
        if len(held) < MIN_HELD_OUT:
            return False, f"{len(held)} undanhållna fall, {MIN_HELD_OUT} krävs"
        return True, f"{len(src)} oberoende dokument, {len(held)} undanhållna"

    def tested(self, regression: Regression) -> "RuleChange":
        """Steg 3: regressionen körd mot alla stilgrupper. Utfallet fästs vid ändringen, gott som dåligt."""
        self.regression = regression
        ok, why = self.enough_evidence()
        if not ok:
            self.state, self.reason = REJECTED, f"underlaget räcker inte: {why}"
            return self
        if self.style_scope is None and regression.worse():
            # Steg 5 baklänges: en generell regel som skadar en annan stil är inte generell. Vägen framåt är
            # ett stilundantag med mätt konflikt, inte att aktivera ändå.
            self.state = REJECTED
            self.reason = ("en generell regel som gör en annan stil sämre är inte generell; "
                           f"sämre: {', '.join(regression.worse())}")
            return self
        if not regression.better():
            self.state, self.reason = REJECTED, "ingen stilgrupp blev bättre"
            return self
        self.state, self.reason = TESTED, f"{why}; bättre: {', '.join(regression.better())}"
        return self

    # ------------------------------------------------------------------ steg 5: stilundantaget
    def exception_is_warranted(self, common_rule: Regression) -> tuple[bool, str]:
        """Ett undantag får finnas när den gemensamma regeln MÄTT skadar en annan stil och undantaget hjälper
        den avsedda. Båda leden krävs: att en stil är besvärlig räcker inte, och att undantaget hjälper räcker
        inte heller - annars blir varje stil sin egen regel och det finns ingen gemensam läsning kvar."""
        if self.style_scope is None:
            return False, "ingen stilgrupp angiven: det här är inte ett undantag"
        harmed = common_rule.worse()
        if not harmed:
            return False, "den gemensamma regeln skadar ingen stil - då behövs inget undantag"
        if not self.regression or self.style_scope not in self.regression.better():
            return False, f"undantaget gör inte {self.style_scope} bättre"
        return True, f"gemensam regel skadar {', '.join(harmed)}; undantaget hjälper {self.style_scope}"

    # ------------------------------------------------------------------ steg 6: aktivering och återtagning
    def activate(self, previous_version: int | None) -> "RuleChange":
        """Atomärt: antingen gäller hela ändringen eller ingen del av den."""
        if self.state != TESTED:
            raise ValueError(f"en ändring i tillståndet {self.state} kan inte aktiveras; den måste vara {TESTED}")
        self.previous_version = previous_version
        self.version = (previous_version or 0) + 1
        self.state = ACTIVE
        return self

    def rollback(self) -> dict[str, Any]:
        """Tillbaka till det som gällde. Returnerar de värden som ska sättas, så att återgången är en handling
        och inte en förhoppning."""
        if self.state != ACTIVE:
            raise ValueError(f"bara en aktiv ändring kan tas tillbaka; den här är {self.state}")
        self.state = ROLLED_BACK
        return dict(self.before)

    def as_dict(self) -> dict[str, Any]:
        return {"change_id": self.change_id, "hypothesis": self.hypothesis, "changes": dict(self.changes),
                "before": dict(self.before), "style_scope": self.style_scope, "state": self.state,
                "version": self.version, "previous_version": self.previous_version, "reason": self.reason,
                "n_independent_sources": len(independent_sources(self.sources)),
                "regression": self.regression.as_dict() if self.regression else None}
