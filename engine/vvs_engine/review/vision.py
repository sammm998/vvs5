"""Looking at the drawing, after having read it - to find what the reading missed, never to measure.

The vector reading is the geometry. It knows where every line is, to the point, because it took them out of the
PDF. What it cannot do is notice that a whole family of pipe was never accepted, or that the overlay it drew
runs along a wall instead of a pipe. A person spots that in a second by looking.

So this renders the page and the reading's own overlay, and asks a model what it sees. The discipline is one
sentence, and it is enforced by what this module returns: **findings, never measurements**. Nothing here
produces a coordinate, a length, a designation or a pipe. Everything it returns is a question for the vector
code to answer - "there seems to be pipe here that nothing measured" is a place to go and look for a real vector
family, not a licence to draw one from pixels.

That is why the return type is a list of Finding and there is no apply(). A vision finding cannot move a metre
because there is no path from here to a metre. It reaches the reader, as an unresolved case, and the fix is
always made in the vector code afterwards.
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field
from typing import Any, Callable

# what the eye is asked, in the order a reader would ask it
QUESTIONS = [
    ("missed_labels", "Syns det VVS-beteckningar på ritningen som INTE finns i listan över lästa beteckningar?"),
    ("missed_pipes", "Syns det ritade rörledningar som ingen färgad överläggning följer?"),
    ("overlay_wrong", "Följer någon färgad överläggning något annat än ett rör - en vägg, en möbel, en måttlinje?"),
    ("paired_wall", "Finns det ställen där två parallella linjer är ett ritat föremål snarare än två rör?"),
]


@dataclass
class Finding:
    kind: str
    detail: str
    where: str = ""                 # in the model's own words; never turned into a coordinate
    source: str = "vision_second_opinion"

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "detail": self.detail[:400], "where": self.where[:120],
                "source": self.source,
                "note": "observation to check in the vector data; never used as geometry or as a measurement"}


@dataclass
class VisionReview:
    asked: bool = False
    findings: list[Finding] = field(default_factory=list)
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"asked": self.asked, "n_findings": len(self.findings), "note": self.note,
                "findings": [f.as_dict() for f in self.findings],
                "contract": "vision reports what the vector reading may have missed; it never creates geometry"}


def render_page_png(page_doc, page_index: int, dpi: int = 110, clip=None) -> bytes:
    """The page as the eye would see it. Used for looking, never for measuring."""
    import pymupdf
    pg = page_doc[page_index]
    m = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
    pix = pg.get_pixmap(matrix=m, clip=clip)
    return pix.tobytes("png")


def overlay_png(png: bytes, runs: list[list[list[float]]], dpi: int = 110, colour=(220, 30, 30)) -> bytes:
    """The same view with the reading's own confirmed runs drawn over it, so the two can be compared."""
    from PIL import Image, ImageDraw
    im = Image.open(io.BytesIO(png)).convert("RGB")
    d = ImageDraw.Draw(im)
    k = dpi / 72.0
    for poly in runs:
        pts = [(p[0] * k, p[1] * k) for p in poly]
        if len(pts) >= 2:
            d.line(pts, fill=colour, width=3)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def compose(pa, max_labels: int = 120) -> str:
    """What the reading claims, in words, so the eye is checking a stated answer rather than free-associating."""
    lg = pa.legend
    des = sorted({(d.display_text or d.text or "").strip() for d in pa.designations if (d.text or "").strip()})
    measured = sorted({q["designation"] for q in pa.quantities if q.get("confirmed_total_m", 0) > 0})
    return "\n".join([
        f"Läsningen hittade {len(des)} textbeteckningar och mätte {len(measured)} av dem.",
        f"Ritningens egen beteckningslista: {'hittad, ' + str(len(lg.entries)) + ' poster' if lg.entries else 'hittades inte'}.",
        f"Rörfamiljer som accepterades: {len(pa.pipe_families)}.",
        "",
        "Beteckningar som mättes:",
        ", ".join(measured[:max_labels]) or "(inga)",
        "",
        "Beteckningar som lästes men inte mättes:",
        ", ".join([d for d in des if d not in measured][:max_labels]) or "(inga)",
    ])


def look(pa, page_doc, ask: Callable[[str, list[bytes]], str] | None = None, dpi: int = 110) -> VisionReview:
    """Ask the eye about a page that has already been read. Without a transport, nothing is asked."""
    if ask is None:
        return VisionReview(asked=False, note="ingen vision-transport angiven; läsningen står på sin egen geometri")
    try:
        base = render_page_png(page_doc, pa.page.info.index, dpi=dpi)
        runs = [poly for p in (pa.ownership.pipes if pa.ownership else []) for poly in p.points]
        shots = [base, overlay_png(base, runs, dpi=dpi)]
    except Exception as e:
        return VisionReview(asked=False, note=f"kunde inte rendera sidan: {type(e).__name__}")

    prompt = "\n".join([
        "Du ser samma VVS-ritning två gånger: först som den är, sedan med den automatiska läsningens rör",
        "utritade i rött ovanpå. Läsningen påstår följande:",
        "",
        compose(pa),
        "",
        "Svara på var och en av frågorna nedan. Svara med en rad per iakttagelse, i formen",
        "  NYCKEL | vad du ser | ungefär var på ritningen",
        "och skriv INGET för en fråga där du inte ser något. Hitta inte på koordinater, längder eller",
        "beteckningar - beskriv bara med ord vad du ser och var.",
        "",
    ] + [f"{k}: {q}" for k, q in QUESTIONS])

    try:
        raw = ask(prompt, shots)
    except Exception as e:
        return VisionReview(asked=False, note=f"vision kunde inte nås: {type(e).__name__}")
    return VisionReview(asked=True, findings=parse(raw), note="andra åsikt; ingen geometri härifrån")


def parse(raw: str) -> list[Finding]:
    """Lines the eye wrote, kept only where they name one of the questions that were asked."""
    keys = {k for k, _ in QUESTIONS}
    out: list[Finding] = []
    for line in (raw or "").splitlines():
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        kind = parts[0].strip().lower().strip("-* ").split()[0] if parts[0].strip() else ""
        if kind not in keys or len(parts) < 2 or not parts[1]:
            continue
        out.append(Finding(kind=kind, detail=parts[1], where=parts[2] if len(parts) > 2 else ""))
    return out
