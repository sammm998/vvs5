"""Kalkylen och anbudet: från mängd till pris.

En mängd är meter och antal. Ett anbud är tid och pengar. Det här är bron, i två steg som hålls isär så att
varje krona går att spåra tillbaka till en rad på ritningen:

  * **Material.** Varje beteckning matchas mot materialboken - bladets egen förklaringslista säger vad
    materialkoden betyder, dimensionen står i beteckningen - och får en artikel med nettopris. Matchningen är
    ett FÖRSLAG med alternativ bredvid; den som räknar väljer, och valet sparas.
  * **Arbete.** Timmarna kommer ur Normtid VVS (`vvs_engine.normtid`): grundtid per meter efter dimension och
    material, tillägg för skarvmetod och höjd, och avvikelseanalysens bedömning av objektet. Där boken inte har
    någon tid står det - en gissad normtid är värre än ingen, för den ser ut som ett besked.

Sedan spill, påslag och moms, allt utskrivet. Anbudet är samma tal i en form en beställare kan läsa, med
förutsättningarna och förbehållen på samma papper som summan.

Ingenting här rör läsningen. Kalkylen läser mängderna med kundens rättelser ovanpå - samma meter som står på
bladet - och skriver aldrig tillbaka.
"""
from __future__ import annotations

import datetime as dt
import html
import io
import json
import os
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from vvs_engine import normtid as NT

from .auth import current_user
from .db import AnalysisJob, Calculation, User, get_db
from .storage import storage

router = APIRouter(prefix="/api/jobs", tags=["kalkyl"])

# ------------------------------------------------------------------------------------------------------------
# antaganden
# ------------------------------------------------------------------------------------------------------------
DEFAULTS = {
    "timpris": 650.0,            # kr per timme, montör
    "spill_pct": 5.0,            # kalkylmängd = netto + spill (lathunden §28)
    "paslag_material_pct": 12.0,
    "paslag_arbete_pct": 10.0,
    "moms_pct": 25.0,
    "floor_height_m": 3.0,       # en stigare räknas som en våningshöjd när ritningen inte säger höjden
    "supplements": ["pressfog"],  # normtidens tillägg: skarvmetod, höjd, ombyggnad
    "factors": {},               # avvikelseanalysen: faktor-id -> -4..+4
    "valid_days": 30,
    "company": "", "customer": "", "reference": "", "intro": "",
}

# Ytterdiameter för en nominell dimension. Metallrör: DN -> dy enligt gängse rörtabell; plaströr (avlopp) har
# ytterdiametern som beteckning, så där är DN redan dy. Normtidens tabeller går på dy.
DN_TO_DY_METAL = {10: 12.0, 12: 15.0, 15: 18.0, 16: 18.0, 18: 18.0, 20: 22.0, 22: 22.0, 25: 28.0, 28: 28.0,
                  32: 35.0, 35: 35.0, 40: 42.0, 42: 42.0, 50: 54.0, 54: 54.0, 65: 76.1, 80: 88.9, 100: 114.3,
                  125: 139.7, 150: 168.3, 200: 219.1}
PLASTIC_LETTERS = ("P", "R", "E", "G")     # PP, PEM/PE, PVC ... - avlopps- och markrör i plast
STOP = {"och", "med", "för", "av", "i", "till", "enligt", "typ", "el", "eller", "samt", "mm", "m", "st",
        "ledningar", "ledning", "rör", "röret"}

# Materialklasser: vad förklaringens ord betyder, och vilka ord boken använder för samma sak. Förklaringen på
# bladet säger "LEDNINGAR AV ROSTFRIA RÖR"; boken säger "rostfritt rör", "rf AISI 304" eller "1.4432". Ingen
# av dem använder den andras ord, så klassen är bron: ett mönster för förklaringen, ett för artikelnamnet.
MATERIAL_CLASSES: list[tuple[str, str, str, bool]] = [
    # (klass, mönster i förklaringen, mönster i artikelnamnet, plaströr)
    ("pex",     r"pe-?x|ipe-?x|\brir\b|rör.?i.?rör|multipex|sanipex", r"pex|pe-x|\brir\b|rör i rör|kombirör", True),
    ("koppar",  r"koppar|\bcu\b",                                   r"koppar|cupori|\bcu\b",                  False),
    ("rostfri", r"rostfri|syrafast|\brf\b|aisi|1[.,]44",               r"rostfri|syrafast|\brf\b|aisi|1[.,]44",   False),
    ("pp",      r"\bpp\b|pp-|polypropen|\bhtp\b",                    r"\bpp\b|pp-|polypropen|\bhtp\b",         True),
    ("pe",      r"\bpem\b|\bpeh\b|\bpe\s?\d{2,3}\b|polyet(en|ylen)",  r"\bpem\b|\bpeh\b|\bpe\d{2,3}|pe-rör|\bpe\b", True),
    ("pvc",     r"pvc",                                                r"pvc",                                     True),
    ("gjut",    r"gjut|\bgjj\b|segjärn|\bsml\b|\bma-?rör",              r"\bgjj\b|gjut|segjärn|\bsml\b|ma-rör",      False),
    ("galv",    r"förzink|galv",                                       r"förzink|galv",                            False),
    ("stal",    r"stål|svart|tunnvägg|mapress|kolstål|\bsms\b",         r"stål|svartrör|tunnvägg|mapress|kolstål",   False),
]
_CLASS = {c[0]: c for c in MATERIAL_CLASSES}


def _legend_text(code: str, legend: list[dict]) -> str:
    code = (code or "").upper()
    for e in legend or []:
        c = str(e.get("code") or e.get("kod") or "").upper()
        if c and c == code:
            return str(e.get("description") or e.get("text") or e.get("label") or "")
    return ""


def _material_class(text: str) -> str | None:
    """Klassen ur förklaringens ord - eller ingen. En bokstav utan förklaring säger inte vad röret är gjort av
    (R8 var rostfritt på ett blad och skulle kunna vara PE på nästa), så här gissas inget."""
    t = (text or "").lower()
    for klass, in_legend, _, _ in MATERIAL_CLASSES:
        if re.search(in_legend, t):
            return klass
    return None


def _material_words(code: str, legend: list[dict]) -> list[str]:
    """Orden som visar vad raden matchades på: klassen först, sedan förklaringens egna ord."""
    text = _legend_text(code, legend)
    klass = _material_class(text)
    words = [w for w in re.findall(r"[a-zåäöA-ZÅÄÖ][a-zåäö0-9A-ZÅÄÖ-]{2,}", text.lower()) if w not in STOP and w != klass]
    return ([klass] if klass else []) + words[:3]


def _is_plastic(code: str, klass: str | None = None) -> bool:
    if klass and klass in _CLASS:
        return _CLASS[klass][3]
    return (code or "").upper()[:1] in PLASTIC_LETTERS


def _split(base: str) -> tuple[str, str]:
    """System och materialkod ur beteckningens stam: KV01-X7-W40 -> (KV01, X7)."""
    parts = [p for p in (base or "").split("-") if p]
    return (parts[0] if parts else ""), (parts[1] if len(parts) > 1 else "")


def _book() -> dict:
    from .main import _material
    return _material()


def _leading_dim(name: str) -> float | None:
    """Dimensionen ett artikelnamn börjar med: '18x1,0 Cupori', '75 Blücher', 'Dy48 ...', '76,1x3,0 rör'."""
    m = re.match(r"\s*(?:dy|dn|d|ø)?\s*(\d+(?:[.,]\d+)?)(?![.,]?\d)", name or "", re.I)
    if not m:
        m = re.search(r"\b(\d+(?:[.,]\d+)?)x\d", name or "")
    return float(m.group(1).replace(",", ".")) if m else None


def _dims_for(dn: int | None, plastic: bool) -> set[float]:
    """Talen boken kan skriva för en nominell dimension: DN själv, och för metallrör ytterdiametern."""
    if not dn:
        return set()
    out = {float(dn)}
    if not plastic and dn in DN_TO_DY_METAL:
        out.add(DN_TO_DY_METAL[dn])
    return out


def _shape(r: dict) -> dict:
    p = r.get("p")
    net = None if p is None else round(float(p) * (1 - float(r.get("r") or 0)), 2)
    return {"a": r["a"], "n": r["n"], "e": r.get("e"), "brutto": p, "netto": net, "w": r.get("w"), "co2": r.get("co2")}


def _find_articles(words: list[str], dn: int | None, unit: str = "m", limit: int = 6,
                   klass: str | None = None, plastic: bool = False) -> list[dict]:
    """Metervaror i rätt material och rätt dimension, bäst först.

    Materialet är ett krav när klassen är känd, dimensionen ett krav när den står i beteckningen. Bland dem som
    klarar båda går ett riktigt pris före ett tomt, sedan vinner den som bär flest av förklaringens egna ord
    (säger förklaringen RIR vinner rör-i-rör), sedan ett rör före annat, sedan det billigaste. Utan känd klass
    returneras rör i rätt dimension som ALTERNATIV att välja bland - inget väljs åt någon."""
    rows = _book()["rows"]
    if klass is None and words:
        klass = _material_class(" ".join(words))
    in_name = re.compile(_CLASS[klass][2], re.I) if klass else None
    dims = _dims_for(dn, plastic if klass is None else _CLASS[klass][3])
    extra = [w for w in words if w != klass and len(w) >= 3]
    scored = []
    for r in rows:
        if (r.get("e") or "").lower() != unit:
            continue
        n = r.get("n") or ""
        if in_name is not None and not in_name.search(n):
            continue
        if in_name is None and "rör" not in n.lower():
            continue
        if dims:
            d = _leading_dim(n)
            if d is None or not any(abs(d - x) <= 0.6 for x in dims):
                continue
        low = n.lower()
        hits = sum(1 for w in extra if w in low)
        price = float(r.get("p") or 0.0)
        scored.append((price < 1.0, -hits, "rör" not in low, price, len(n), r))
    scored.sort(key=lambda t: t[:5])
    return [_shape(r) for *_, r in scored[:limit]]


def _article_by_number(a: str) -> dict | None:
    for r in _book()["rows"]:
        if r["a"] == a:
            return _shape(r)
    return None


def _norm_hours_per_m(dn: int | None, plastic: bool, riser: bool) -> tuple[float | None, str]:
    """Grundtid per meter ur boken, och vilken tabell den kom ur. Ingen tid är ett svar."""
    if dn is None:
        return None, "dimension saknas"
    # Plaströr och rostfria avloppsrör (75, 110, 160) bär ytterdiametern som beteckning; för övriga metallrör
    # står DN på bladet och boken går på dy. En DN utanför rörtabellen läses som dy - det är vad den är på de
    # blad som skriver så, och boken svarar ändå bara inom sina egna band.
    dy = float(dn) if plastic else DN_TO_DY_METAL.get(int(dn), float(dn))
    if not riser and not plastic and dy <= 35.0:
        t = NT.base_time("kopplingsledning", dy, 1)
        if t is not None:
            return t, "Kopplingsledningar (s. 33)"
    t = NT.base_time("stammar", dy, 2 if plastic else 1)
    return (t, "Stammar (s. 30)") if t is not None else (None, f"boken har ingen tid för dy {dy:g}")


def _deviation_pct(factors: dict) -> float:
    total = 0.0
    for fid, v in (factors or {}).items():
        f = NT.FACTOR_BY_ID.get(fid)
        if f is None:
            continue
        try:
            v = int(v)
        except (TypeError, ValueError):
            continue
        if v in f.scale:
            total += v
    return total


# ------------------------------------------------------------------------------------------------------------
# kalkylen
# ------------------------------------------------------------------------------------------------------------
def build(rows: list[dict], legend: list[dict], assumptions: dict, overrides: dict) -> dict:
    """Kalkylen ur mängdraderna. Varje rad bär sina egna steg, så en krona går att spåra till en meter."""
    A = {**DEFAULTS, **{k: v for k, v in (assumptions or {}).items() if k in DEFAULTS}}
    dev = _deviation_pct(A.get("factors") or {})
    sup = [s for s in (A.get("supplements") or []) if s in NT.SUPPLEMENT_BY_ID]
    out_rows = []
    caveats: list[str] = []
    for q in rows:
        name = q.get("designation") or ""
        if not name:
            continue
        ov = (overrides or {}).get(name) or {}
        system, mcode = _split(q.get("base") or name)
        dn = q.get("dn")
        words = _material_words(mcode, legend)
        klass = words[0] if words and words[0] in _CLASS else None
        plastic = _is_plastic(mcode, klass)
        horiz = float(q.get("confirmed_horizontal_m") or 0.0)
        risers = int(max(q.get("riser_count") or 0, q.get("riser_count_from_labels") or 0))
        vert = risers * float(A["floor_height_m"])
        netto_m = horiz + vert
        kalkyl_m = netto_m * (1 + float(A["spill_pct"]) / 100.0)

        # material: förslaget, alternativen, eller det som valdes. Utan känd materialklass föreslås inget -
        # alternativen finns att välja bland, men ett rör i fel material prissatt med säker min är värre än en
        # tom ruta.
        alts = _find_articles(words, dn, klass=klass, plastic=plastic) if (klass or dn) else []
        art = _article_by_number(ov["artikel"]) if ov.get("artikel") else (alts[0] if alts and klass else None)
        unit_price = None if art is None else art.get("netto")
        material_kr = round(unit_price * kalkyl_m, 2) if unit_price is not None else None

        # arbete: grundtid ur boken, tillägg, avvikelse - eller en timme någon skrev själv
        base, source = _norm_hours_per_m(dn, plastic, riser=False)
        base_r, source_r = _norm_hours_per_m(dn, plastic, riser=True)
        if ov.get("timmar") is not None:
            timmar = float(ov["timmar"]); steps = {"timmar": timmar}; source = "angiven för hand"
        elif base is not None:
            steps_h = NT.hours(base, horiz, sup, dev)
            steps_v = NT.hours(base_r, vert, sup, dev) if base_r is not None and vert else {"timmar": 0.0}
            timmar = round(steps_h["timmar"] + steps_v["timmar"], 3)
            steps = {"grundtid_per_m": base, "grundtid": steps_h["grundtid"], "tillagg_pct": steps_h["tillagg_pct"],
                     "avvikelse_pct": steps_h["avvikelse_pct"], "stigare_timmar": steps_v["timmar"], "timmar": timmar}
        else:
            timmar = None; steps = {}
        arbete_kr = round(timmar * float(A["timpris"]), 2) if timmar is not None else None

        row = {"designation": name, "system": system, "material_kod": mcode, "dn": dn,
               "material_ord": words, "plast": plastic,
               "horisontellt_m": round(horiz, 2), "stigare": risers, "vertikalt_m": round(vert, 2),
               "netto_m": round(netto_m, 2), "kalkyl_m": round(kalkyl_m, 2),
               "artikel": art, "alternativ": alts, "a_pris": unit_price, "material_kr": material_kr,
               "normtid_kalla": source, "steg": steps, "timmar": timmar, "arbete_kr": arbete_kr,
               "summa_kr": round((material_kr or 0) + (arbete_kr or 0), 2),
               "vald_artikel": bool(ov.get("artikel")), "timmar_for_hand": ov.get("timmar") is not None}
        out_rows.append(row)
        if art is None and klass is None:
            caveats.append(f"{name}: materialet framgår inte av bladets förklaring ({mcode or 'ingen kod'}) - välj artikel.")
        elif art is None:
            caveats.append(f"{name}: ingen artikel i materialboken för {klass} DN{dn or '?'} - välj en.")
        if timmar is None:
            caveats.append(f"{name}: normtid saknas ({source}) - ange timmar.")

    mat = sum(r["material_kr"] or 0 for r in out_rows)
    hrs = sum(r["timmar"] or 0 for r in out_rows)
    arb = sum(r["arbete_kr"] or 0 for r in out_rows)
    pm = mat * float(A["paslag_material_pct"]) / 100.0
    pa = arb * float(A["paslag_arbete_pct"]) / 100.0
    netto = mat + arb + pm + pa
    moms = netto * float(A["moms_pct"]) / 100.0
    totals = {"material_kr": round(mat, 2), "timmar": round(hrs, 2), "arbete_kr": round(arb, 2),
              "paslag_material_kr": round(pm, 2), "paslag_arbete_kr": round(pa, 2),
              "netto_kr": round(netto, 2), "moms_kr": round(moms, 2), "brutto_kr": round(netto + moms, 2),
              "rader": len(out_rows), "utan_artikel": sum(1 for r in out_rows if r["artikel"] is None),
              "utan_normtid": sum(1 for r in out_rows if r["timmar"] is None)}
    return {"assumptions": A, "avvikelse_pct": dev, "rows": out_rows, "totals": totals, "caveats": caveats}


# ------------------------------------------------------------------------------------------------------------
# underlaget ur läsningen
# ------------------------------------------------------------------------------------------------------------
def _job(db: Session, user: User, job_id: str) -> AnalysisJob:
    j = db.get(AnalysisJob, job_id)
    if j is None or j.drawing.project.owner_id != user.id:
        raise HTTPException(404, "Analysen finns inte")
    if j.status != "COMPLETED" or not j.result_key:
        raise HTTPException(409, "Analysen är inte klar - kalkylen räknar på det som lästs, aldrig på något annat")
    return j


def _inputs(db: Session, j: AnalysisJob) -> tuple[list[dict], list[dict]]:
    from .projects_api import _rows_of
    rows = _rows_of(db, j)
    rd = storage.path(j.result_key)
    legend = []
    p = os.path.join(rd, "drawing-legend.json")
    if os.path.isfile(p):
        with open(p, "r", encoding="utf-8") as fh:
            legend = (json.load(fh) or {}).get("entries") or []
    return rows, legend


class CalcIn(BaseModel):
    assumptions: dict = Field(default_factory=dict)
    overrides: dict = Field(default_factory=dict)      # beteckning -> {artikel, timmar}


@router.get("/{job_id}/calc/underlag")
def underlag(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Normtidsunderlaget och standardantagandena, så att gränssnittet kan visa vad som går att ställa in."""
    _job(db, user, job_id)
    return {"defaults": DEFAULTS, "normtid": NT.catalogue()}


@router.post("/{job_id}/calc/preview")
def preview(job_id: str, body: CalcIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    j = _job(db, user, job_id)
    rows, legend = _inputs(db, j)
    return build(rows, legend, body.assumptions, body.overrides)


@router.put("/{job_id}/calc")
def save(job_id: str, body: CalcIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Spara kalkylen: antagandena och valen. Talen räknas om ur läsningen varje gång - de är aldrig lagrade fakta."""
    j = _job(db, user, job_id)
    rows, legend = _inputs(db, j)
    calc = build(rows, legend, body.assumptions, body.overrides)
    c = db.query(Calculation).filter(Calculation.job_id == j.id).order_by(Calculation.created_at.desc()).first()
    if c is None:
        c = Calculation(job_id=j.id, user_id=user.id)
        db.add(c)
    c.assumptions, c.overrides, c.totals = calc["assumptions"], body.overrides, calc["totals"]
    db.commit()
    return {**calc, "saved_at": c.updated_at.isoformat() if c.updated_at else None}


@router.get("/{job_id}/calc")
def latest(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    j = _job(db, user, job_id)
    c = db.query(Calculation).filter(Calculation.job_id == j.id).order_by(Calculation.created_at.desc()).first()
    if c is None:
        return {"status": "NONE"}
    rows, legend = _inputs(db, j)
    return {"status": "SAVED", **build(rows, legend, c.assumptions or {}, c.overrides or {}),
            "saved_at": c.updated_at.isoformat() if c.updated_at else None}


# ------------------------------------------------------------------------------------------------------------
# anbudet
# ------------------------------------------------------------------------------------------------------------
def _kr(v: float | None) -> str:
    if v is None:
        return "–"
    s = f"{v:,.2f}".replace(",", " ").replace(".", ",")
    return f"{s} kr"


def _num(v: float | None, d: int = 2) -> str:
    return "–" if v is None else f"{v:,.{d}f}".replace(",", " ").replace(".", ",")


def tender_html(calc: dict, meta: dict) -> str:
    """Anbudet som HTML. Samma tal som kalkylen, i en form en beställare läser: summan först, sedan vad den
    består av, sedan vad den förutsätter. Förbehållen står på samma papper som summan."""
    A = calc["assumptions"]; T = calc["totals"]
    e = html.escape
    today = dt.date.today()
    valid = today + dt.timedelta(days=int(A.get("valid_days") or 30))
    sup_labels = [NT.SUPPLEMENT_BY_ID[s].label for s in A.get("supplements") or [] if s in NT.SUPPLEMENT_BY_ID]
    rows_html = "".join(
        f"<tr><td class='n'>{i + 1}</td><td><b>{e(r['designation'])}</b><br><span class='muted'>"
        f"{e(r['artikel']['n']) if r['artikel'] else 'artikel ej vald'}</span></td>"
        f"<td class='r'>{_num(r['kalkyl_m'])} m</td><td class='r'>{_kr(r['material_kr'])}</td>"
        f"<td class='r'>{_num(r['timmar'])}</td><td class='r'>{_kr(r['arbete_kr'])}</td>"
        f"<td class='r'><b>{_kr(r['summa_kr'])}</b></td></tr>"
        for i, r in enumerate(calc["rows"]))
    caveats = "".join(f"<li>{e(c)}</li>" for c in calc["caveats"])
    intro = e(A.get("intro") or "Vi tackar för förfrågan och lämnar härmed anbud på rörinstallationer enligt "
                                 "bifogad handling. Mängderna är läsna ur ritningens egna vektorer och kan spåras "
                                 "rad för rad; förutsättningarna står nedan.")
    return f"""<html><body>
<div class="band"><div class="co">{e(A.get('company') or meta.get('company') or 'VVS Mängdning')}</div>
<div class="title">ANBUD</div></div>
<table class="meta"><tr>
<td><span class="k">Beställare</span><br>{e(A.get('customer') or '–')}</td>
<td><span class="k">Objekt</span><br>{e(meta.get('project') or '–')}<br><span class="muted">{e(meta.get('drawing') or '')}</span></td>
<td><span class="k">Referens</span><br>{e(A.get('reference') or meta.get('job') or '–')}</td>
<td><span class="k">Datum</span><br>{today.isoformat()}<br><span class="muted">giltigt till {valid.isoformat()}</span></td>
</tr></table>
<p class="intro">{intro}</p>
<div class="total"><div class="k">Anbudssumma exkl. moms</div><div class="v">{_kr(T['netto_kr'])}</div>
<div class="sub">Moms {_num(A['moms_pct'], 0)} %: {_kr(T['moms_kr'])} · inkl. moms {_kr(T['brutto_kr'])}</div></div>
<h2>Specifikation</h2>
<table class="spec"><tr><th class='n'>#</th><th>Post</th><th class='r'>Kalkylmängd</th><th class='r'>Material</th>
<th class='r'>Timmar</th><th class='r'>Arbete</th><th class='r'>Summa</th></tr>{rows_html}
<tr class="sum"><td></td><td>Material och arbete</td><td></td><td class='r'>{_kr(T['material_kr'])}</td>
<td class='r'>{_num(T['timmar'])}</td><td class='r'>{_kr(T['arbete_kr'])}</td><td class='r'>{_kr(T['material_kr'] + T['arbete_kr'])}</td></tr>
<tr><td></td><td>Påslag material {_num(A['paslag_material_pct'], 0)} %</td><td></td><td></td><td></td><td></td><td class='r'>{_kr(T['paslag_material_kr'])}</td></tr>
<tr><td></td><td>Påslag arbete {_num(A['paslag_arbete_pct'], 0)} %</td><td></td><td></td><td></td><td></td><td class='r'>{_kr(T['paslag_arbete_kr'])}</td></tr>
<tr class="sum"><td></td><td><b>Summa exkl. moms</b></td><td></td><td></td><td></td><td></td><td class='r'><b>{_kr(T['netto_kr'])}</b></td></tr>
</table>
<h2>Förutsättningar</h2>
<ul>
<li>Timpris {_kr(A['timpris'])} per montörtimme. Normtider enligt Normtid VVS (Införlag): grundtid per meter efter dimension och material.</li>
<li>Tillägg: {e(', '.join(sup_labels) or 'inga')}. Avvikelseanalys: {_num(calc['avvikelse_pct'], 0)} %.</li>
<li>Kalkylmängd = nettomängd + {_num(A['spill_pct'], 0)} % spill. Stigare räknade som {_num(A['floor_height_m'], 1)} m per stigare där ritningen inte anger höjd.</li>
<li>Materialpriser är nettopriser ur materialboken vid anbudsdagen.</li>
</ul>
<h2>Förbehåll</h2>
<ul>{caveats or '<li>Inga.</li>'}
<li>Rör som ingen beteckning på ritningen når ingår inte i mängden; de redovisas som onämnda i läsningen.</li>
<li>Fittings, genomföringar, isolering som egen post och rivning ingår inte om de inte står som egna rader.</li>
</ul>
<table class="sign"><tr><td>Ort och datum<br><br>______________________________</td><td>Underskrift<br><br>______________________________</td></tr></table>
</body></html>"""


TENDER_CSS = """
body { font-family: sans-serif; font-size: 9.5pt; color: #111; }
.band { border-bottom: 2pt solid #0b7285; padding-bottom: 6pt; margin-bottom: 10pt; }
.co { font-size: 9pt; letter-spacing: 1pt; color: #0b7285; text-transform: uppercase; }
.title { font-size: 30pt; font-weight: bold; margin-top: 2pt; }
.meta { width: 100%; border-collapse: collapse; margin-bottom: 10pt; }
.meta td { vertical-align: top; padding: 4pt 6pt 4pt 0; font-size: 9pt; }
.k { font-size: 7.5pt; letter-spacing: 1pt; color: #777; text-transform: uppercase; }
.muted { color: #777; font-size: 8pt; }
.intro { margin: 6pt 0 10pt 0; line-height: 1.4; }
/* en ram, ingen fyllning: Story ritar om ett blocks bakgrund överst på varje följande sida */
.total { border: 0.8pt solid #b9d3d9; border-left: 3pt solid #0b7285; padding: 8pt 10pt; margin: 6pt 0 12pt 0; }
.total .v { font-size: 20pt; font-weight: bold; margin: 2pt 0; }
.total .sub { color: #555; font-size: 8.5pt; }
h2 { font-size: 11pt; margin: 12pt 0 4pt 0; letter-spacing: 0.5pt; text-transform: uppercase; color: #0b7285; }
.spec { width: 100%; border-collapse: collapse; }
.spec th { text-align: left; font-size: 7.5pt; letter-spacing: 0.8pt; text-transform: uppercase; color: #777;
           border-bottom: 1pt solid #999; padding: 4pt 4pt; }
.spec td { padding: 4pt 4pt; border-bottom: 0.5pt solid #ddd; vertical-align: top; }
.spec .r, .spec th.r { text-align: right; white-space: nowrap; }
.spec .n { width: 14pt; color: #999; }
.spec tr.sum td { border-top: 1pt solid #999; border-bottom: none; }
ul { margin: 2pt 0 0 12pt; padding: 0; line-height: 1.4; }
li { margin: 0 0 2pt 0; }
.sign { width: 100%; margin-top: 22pt; }
.sign td { width: 50%; font-size: 8.5pt; color: #555; }
"""


def tender_pdf(html_doc: str) -> bytes:
    import pymupdf
    story = pymupdf.Story(html=html_doc, user_css=TENDER_CSS)
    buf = io.BytesIO()
    writer = pymupdf.DocumentWriter(buf)
    rect = pymupdf.paper_rect("a4")
    more = True
    while more:
        dev = writer.begin_page(rect)
        more, _ = story.place(rect + (46, 46, -46, -52))
        story.draw(dev)
        writer.end_page()
    writer.close()
    return buf.getvalue()


def _tender(db: Session, user: User, job_id: str) -> tuple[str, dict]:
    j = _job(db, user, job_id)
    c = db.query(Calculation).filter(Calculation.job_id == j.id).order_by(Calculation.created_at.desc()).first()
    if c is None:
        raise HTTPException(409, "Spara kalkylen först - anbudet skrivs ur den sparade kalkylen.")
    rows, legend = _inputs(db, j)
    calc = build(rows, legend, c.assumptions or {}, c.overrides or {})
    meta = {"project": j.drawing.project.name, "drawing": j.drawing.filename, "job": j.id[:8].upper(),
            "company": (user.name or "") or None}
    return tender_html(calc, meta), meta


@router.get("/{job_id}/calc/anbud.html")
def anbud_html(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc, _ = _tender(db, user, job_id)
    return Response(f"<style>{TENDER_CSS} body{{max-width:760px;margin:24px auto;padding:0 16px}}</style>" + doc,
                    media_type="text/html; charset=utf-8")


@router.get("/{job_id}/calc/anbud.pdf")
def anbud_pdf(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .main import _attachment
    doc, meta = _tender(db, user, job_id)
    name = f"Anbud {meta['project']} {dt.date.today().isoformat()}.pdf"
    return Response(tender_pdf(doc), media_type="application/pdf", headers=_attachment(name))
