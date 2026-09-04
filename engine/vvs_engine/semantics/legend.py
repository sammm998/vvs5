"""The drawing's own designation list.

Every one of these sheets carries a legend - a column of short codes, each with the words that say what it is,
under headings that group them. It is the drawing telling us its own vocabulary: which codes are systems, which
are pipe materials, which are components that will never be a pipe. Read from the page like everything else, per
job, and never carried between drawings.

Nothing here knows any Swedish. A legend is found by its shape - a stack of rows sharing a left edge, each a
short code beside a description - and a code's role is settled by how the drawing itself uses it: a code that
opens a dimensioned designation is a system, a code that stands alone as a whole label is a component.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..text.model import TextRow

MIN_ENTRIES = 6                 # a shorter stack is a table cell or a note, not a designation list
MAX_CODE_LEN = 10
DESC_GAP_ROWS = 12.0            # how far right of the code its description may start, in row heights

_INLINE = re.compile(r"^([^\s]{1,%d})\s+(\S.{2,})$" % MAX_CODE_LEN)


def is_code_token(tok: str) -> bool:
    """A legend code, as opposed to a heading word.

    Codes carry a digit ('KV01', 'S13'), or a placeholder run ('ALxxx'), or are very short ('W', 'P2'). A word of
    five letters or more with no digit in it is a heading - the drawing's own section title."""
    t = tok.strip().rstrip(".:,;")
    if not t or not t[0].isalnum():
        return False
    if any(c.isdigit() for c in t):
        return True
    up = t.upper()
    if up.count("X") >= 2 and len(up) <= 6:
        return True
    return len(t) <= 4


def code_matches(label: str, code: str) -> bool:
    """Whether a drawn label is this legend code.

    A legend writes the varying part of a component tag as a run of placeholder letters ("ALxxx"), so those
    positions match any digit; everything else must agree."""
    L, C = label.upper(), code.upper()
    if L == C:
        return True
    if "X" not in C[1:] or len(L) < 2:
        return False
    # a run of placeholders stands for the number, however many digits the drawing actually writes
    pat = re.sub(r"(?<!\\)X{2,}", r"\\d+", re.escape(C))
    return re.fullmatch(pat, L) is not None


@dataclass
class LegendEntry:
    code: str
    description: str
    heading: str
    bbox: tuple[float, float, float, float]
    role: str = "unused"        # system | component | material | unused

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "description": self.description, "heading": self.heading,
                "role": self.role, "bbox": [round(v, 1) for v in self.bbox]}


@dataclass
class DrawingLegend:
    entries: list[LegendEntry] = field(default_factory=list)
    column_x: float | None = None

    @property
    def by_code(self) -> dict[str, LegendEntry]:
        return {e.code.upper(): e for e in self.entries}

    def systems(self) -> set[str]:
        return {e.code.upper() for e in self.entries if e.role == "system"}

    def names_a_pipe(self, designation) -> bool:
        """Whether the sheet's own designation list says this label names a pipe.

        True when the label opens with a code the legend lists as a system. When the legend named no systems at
        all - it was not found, or the sheet does not carry one - nothing is claimed and every label passes."""
        systems = self.systems()
        if not systems:
            return True
        head = (getattr(designation, "system_token", "") or "").upper()
        return any(head == c or head.startswith(c) for c in systems)

    def components(self) -> set[str]:
        return {e.code.upper() for e in self.entries if e.role == "component"}

    def bbox(self) -> tuple[float, float, float, float] | None:
        """The block the legend occupies, so its own rows can be told from labels out on the drawing."""
        if not self.entries:
            return None
        xs = [v for e in self.entries for v in (e.bbox[0], e.bbox[2])]
        ys = [v for e in self.entries for v in (e.bbox[1], e.bbox[3])]
        return (min(xs), min(ys), max(xs), max(ys))

    def as_dict(self) -> dict[str, Any]:
        return {"column_x": round(self.column_x, 1) if self.column_x is not None else None,
                "n_entries": len(self.entries), "entries": [e.as_dict() for e in self.entries]}


def read_legend(lines: list[TextRow]) -> DrawingLegend:
    """Find the sheet's designation list and read it.

    A legend row is a short code with a description: either both in one text row, or the code in one row and the
    description in another on the same baseline a little to the right. The legend is the left edge that carries
    the most such rows; rows on that edge whose leading word is not a code are the headings above them."""
    rows = [l for l in lines if abs(l.angle) <= 5.0 and l.text.strip()]
    if not rows:
        return DrawingLegend()
    by_band: dict[int, list[TextRow]] = defaultdict(list)
    for l in rows:
        by_band[round(l.bbox[1] / 2.0)].append(l)
    found: list[tuple[TextRow, str, str]] = []
    for l in rows:
        t = l.text.strip()
        h = max(l.bbox[3] - l.bbox[1], 1.0)
        m = _INLINE.match(t)
        if m and any(c.isalpha() for c in m.group(2)):
            found.append((l, m.group(1), m.group(2)))
            continue
        if len(t) > MAX_CODE_LEN or " " in t:
            continue
        best = None
        band = round(l.bbox[1] / 2.0)
        for k in (band - 1, band, band + 1):
            for o in by_band.get(k, []):
                if o is l or o.bbox[0] <= l.bbox[2] - 0.1 or abs(o.bbox[1] - l.bbox[1]) > 0.6 * h:
                    continue
                gap = o.bbox[0] - l.bbox[2]
                if 0.0 <= gap <= DESC_GAP_ROWS * h and (best is None or gap < best[0]):
                    best = (gap, o)
        if best is not None and any(c.isalpha() for c in best[1].text):
            found.append((l, t, best[1].text.strip()))
    cols: dict[int, list[tuple[TextRow, str, str]]] = defaultdict(list)
    for f in found:
        cols[round(f[0].bbox[0] / 3.0)].append(f)
    best_col = max(cols.items(), key=lambda kv: (len(kv[1]), -kv[0]), default=None)
    if best_col is None:
        return DrawingLegend()
    key = best_col[0]
    split = {f[0].rid: f for f in found}
    # walk every row on the legend's own left edge, top to bottom: the ones that read as a code with a
    # description are its entries, and the rest are the section headings standing above them
    column = sorted((l for l in rows if round(l.bbox[0] / 3.0) == key), key=lambda l: (l.bbox[1], l.bbox[0]))
    entries: list[LegendEntry] = []
    heading = ""
    for line in column:
        f = split.get(line.rid)
        if f is None or not is_code_token(f[1]):
            heading = line.text.strip()
            continue
        entries.append(LegendEntry(code=f[1].strip().rstrip(".:,;"), description=f[2].strip(), heading=heading,
                                   bbox=tuple(line.bbox)))
    if len(entries) < MIN_ENTRIES:
        return DrawingLegend()
    return DrawingLegend(entries=entries, column_x=key * 3.0)


def assign_roles(legend: DrawingLegend, designations) -> None:
    """Settle what each legend code is, from how the drawing uses it.

    A code that opens a designation carrying a dimension is a system code. A code that appears as a whole label
    of its own out on the drawing, and never opens a dimensioned one, is a component tag: a floor drain or a
    mixer, never a pipe. The rest are the materials and insulation classes the designations spell in the middle.

    The legend's own rows are read as designations too, so they are left out of this: a legend line proves only
    that the code exists, never how the drawing uses it."""
    box = legend.bbox()
    opens: set[str] = set()
    standalone: set[str] = set()
    codes = sorted({e.code.upper() for e in legend.entries}, key=len, reverse=True)
    for d in designations:
        b = getattr(d, "bbox", None)
        if box is not None and b is not None and box[0] - 4.0 <= b[0] and b[2] <= box[2] + 4.0 \
                and box[1] - 4.0 <= b[1] and b[3] <= box[3] + 4.0:
            continue                                    # this is the legend line itself
        text = (d.text or "").upper()
        head = (d.system_token or "").upper()
        if d.dn is not None:
            for c in codes:
                if head == c or (head.startswith(c) and len(head) > len(c)):
                    opens.add(c)
                    break
        else:
            for c in codes:
                if code_matches(text, c):
                    standalone.add(c)
                    break
    for e in legend.entries:
        c = e.code.upper()
        if c in opens:
            e.role = "system"
        elif c in standalone:
            e.role = "component"
        else:
            e.role = "material"
