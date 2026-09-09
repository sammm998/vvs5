"""The drawing's own designation list.

Every one of these drawings carries a legend - a column of short codes, each with the words that say what it
is, under headings that group them. It is the drawing telling us its own vocabulary: which codes are systems,
which are pipe materials, which are components that will never be a pipe. Read from the page like everything
else, per job, and never carried between drawings.

Per job, not per sheet. A set writes its designation list once, on the sheet that has room for it, and the plan
sheets are governed by it without repeating it. A reading that looks for the list on each sheet alone finds it
on one of them and, on all the others, concludes the drawing has no vocabulary at all - so every label passes as
possibly a pipe, the review list fills with door marks and room numbers, and the same project is read one way on
one sheet and another way on the next. A sheet that carries no list of its own is handed the set's, marked as
having come from elsewhere; what it may never do is silently borrow the other sheet's geometry with it.

Nothing here knows any Swedish. A legend is found by its shape - a stack of rows sharing a left edge, each a
short code beside a description - and a code's role is settled by how the drawing itself uses it: a code that
opens a dimensioned designation is a system, a code that stands alone as a whole label is a component.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..text.model import TextRow

from .. import rules as _rules


def _R(rule_id, default):
    """Vad regeln står på för den läsning som körs på den här tråden."""
    return _rules.value(rule_id, default)


MIN_ENTRIES = 6                 # a shorter stack is a table cell or a note, not a designation list
MIN_CODES = 6                   # ...and it must say six different things, or it is one table column repeated
USED_MIN = 2                    # codes the drawing writes out itself, for the list to be its own vocabulary
ALIGNED_SHARE = 0.6             # ...or the share of descriptions that share a left edge, which a note's do not
MAX_CODE_LEN = 10
DESC_GAP_ROWS = 12.0            # how far right of the code its description may start, in row heights
COL_TOL = 3.0                   # how far two rows' left edges may differ and still be one column

_INLINE = re.compile(r"^([^\s]{1,%d})\s+(\S.{2,})$" % _R("semantics.legend.MAX_CODE_LEN", MAX_CODE_LEN))


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

    A legend writes the varying part of a component tag as a run of placeholder letters ("ALxxx", "Bxxx"), so
    those positions stand for the number the drawing actually writes - and, on a real sheet, for the letters an
    office hangs off it. `Bxxx GOLVBRUNN` is written B1 and B10, but also B12ML, B12KL and B21M, and reading the
    placeholder as digits alone left every one of those unrecognised: the drawing named a floor drain and the
    reading had it down as something that might be a pipe.

    The letters are a suffix, never a prefix and never the whole varying part: everything outside the placeholder
    run must still agree character for character, so this widens what a tag matches without letting it reach a
    designation. `S3-R8-110` cannot match `Bxxx` however the placeholder is read."""
    L, C = label.upper(), code.upper()
    if L == C:
        return True
    if "X" not in C[1:] or len(L) < 2:
        return False
    pat = re.sub(r"(?<!\\)X{2,}", r"\\d+[A-ZÅÄÖ]{0,3}", re.escape(C))
    return re.fullmatch(pat, L) is not None


@dataclass
class LegendEntry:
    code: str
    description: str
    heading: str
    bbox: tuple[float, float, float, float]
    role: str = "unused"        # system | component | material | unused
    role_from: str = "usage"    # usage | heading | other_sheet - what settled the role
    page: int | None = None     # the sheet of the set that wrote this line

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "description": self.description, "heading": self.heading,
                "role": self.role, "role_from": self.role_from, "page": self.page,
                "bbox": [round(v, 1) for v in self.bbox]}


@dataclass
class DrawingLegend:
    entries: list[LegendEntry] = field(default_factory=list)
    column_x: float | None = None
    own: bool = True            # False when the list was written on another sheet of the same set

    @property
    def by_code(self) -> dict[str, LegendEntry]:
        return {e.code.upper(): e for e in self.entries}

    def systems(self) -> set[str]:
        return {e.code.upper() for e in self.entries if e.role == "system"}

    def names_a_pipe(self, designation) -> bool:
        """Whether the sheet's own designation list says this label names a pipe.

        True when the label opens with a code the legend lists as a system. When the legend named no systems at
        all - it was not found, or the sheet does not carry one - nothing is claimed and every label passes.

        A list read off another sheet of the set carries less authority than the sheet's own, and it is worth
        being exact about how much less. It is a vocabulary, not a census: it says what the codes in it are, and
        the sheet that wrote it may simply never have covered what this sheet draws. So a borrowed list may
        refuse a code it lists as something other than a run, and may not refuse a code it has never heard of -
        which is what it would be doing if silence counted as a verdict. That keeps the borrowing one-directional:
        it can take away a label the set itself calls a floor drain, and it can never take away a pipe."""
        systems = self.systems()
        if not systems:
            return True
        head = (getattr(designation, "system_token", "") or "").upper()
        if self.names_a_component(getattr(designation, "text", "") or head):
            return False
        if any(head == c or head.startswith(c) for c in systems):
            return True
        return not self.own and not any(head == c or head.startswith(c) for c in self.by_code)

    def components(self) -> set[str]:
        return {e.code.upper() for e in self.entries if e.role == "component"}

    def names_a_component(self, text: str) -> bool:
        """Whether the sheet's own list says this label is a fitting rather than a run.

        A designation list does not write out every floor drain it has; it writes the family once, with the
        drawing's own placeholder for the number that varies: `BXXX GOLVBRUNN`, `TSXXX TVATTSTALL`,
        `RLX RENSROR MED LOCK`. So `B1`, `B10` and `B221BL` are that entry, and comparing the text letter for
        letter never finds them. A trailing run of X after at least one other character is that placeholder;
        `X31`, whose X leads, is not. A label that also opens with a system code stays a pipe."""
        head = (text or "").upper().strip()
        if not head:
            return False
        if any(head == c or head.startswith(c) for c in self.systems()):
            return False
        for code in self.components():
            stem = code.rstrip("X")
            if not stem or stem == code:                     # no trailing placeholder: an exact code
                if head == code:
                    return True
                continue
            rest = head[len(stem):]
            if head.startswith(stem) and rest[:1].isdigit():
                return True
        return False

    def bbox(self) -> tuple[float, float, float, float] | None:
        """The block the legend occupies, so its own rows can be told from labels out on the drawing.

        A list read from another sheet occupies nothing here. Its coordinates describe a block on that sheet, and
        on this one they are a rectangle in an arbitrary place - one that would quietly disqualify whatever real
        labels happen to fall inside it. A borrowed vocabulary brings no geometry with it."""
        if not self.entries or not self.own:
            return None
        xs = [v for e in self.entries for v in (e.bbox[0], e.bbox[2])]
        ys = [v for e in self.entries for v in (e.bbox[1], e.bbox[3])]
        return (min(xs), min(ys), max(xs), max(ys))

    def as_dict(self) -> dict[str, Any]:
        return {"column_x": round(self.column_x, 1) if self.column_x is not None else None,
                "own": self.own, "n_entries": len(self.entries),
                "entries": [e.as_dict() for e in self.entries]}


def densest_edge(xs: list[float], tol: float | None = None) -> float | None:
    """The left edge that carries the most rows: the start of the narrow window holding the most of them.

    A designation list is found by the edge its codes share, and rows on a real sheet do not share one exactly -
    a column can jitter a point either way. Rounding each left edge onto a fixed grid decides that by where the
    boundaries happen to fall: two rows of one column at x=100.4 and x=101.6 land in different cells, and a list
    of eight entries becomes two of four, each too short to be a list at all. Nothing about the drawing changed;
    only where the grid was drawn. Grouping by the distance between edges instead has no boundaries to fall on.

    Ties go to the leftmost edge, as the widest thing a column can be is what stands furthest left.
    """
    if tol is None:
        tol = _R("semantics.legend.COL_TOL", COL_TOL)
    xs = sorted(xs)
    best_n, best_x, j = 0, None, 0
    for i, x in enumerate(xs):
        while j < len(xs) and xs[j] <= x + tol:
            j += 1
        if j - i > best_n:
            best_n, best_x = j - i, x
    return best_x


def _description_x(line: TextRow, at: int) -> float:
    """Where the words beside the code start, in page coordinates.

    For a row written as one piece of text the description begins at a character index, and the glyph boxes say
    where that character sits. It matters because whether the descriptions line up is one of the two things that
    tell a designation list from a note."""
    lead = len(line.text) - len(line.text.lstrip())
    i = lead + at
    if 0 <= i < len(line.glyphs):
        return line.glyphs[i].bbox[0]
    return line.bbox[2]


def _candidate(rows: list[TextRow], found: dict, edge: float) -> list[LegendEntry]:
    """The list that would be read off one left edge: its entries, under the headings standing above them."""
    column = sorted((l for l in rows if edge - 0.1 <= l.bbox[0] <= edge + _R("semantics.legend.COL_TOL", COL_TOL)),
                    key=lambda l: (l.bbox[1], l.bbox[0]))
    entries: list[LegendEntry] = []
    heading = ""
    for line in column:
        f = found.get(line.rid)
        if f is None or not is_code_token(f[0]):
            heading = line.text.strip()
            continue
        entries.append(LegendEntry(code=f[0].strip().rstrip(".:,;"), description=f[1].strip(), heading=heading,
                                   bbox=tuple(line.bbox), page=getattr(line, "page", None)))
    return entries


def read_legend(lines: list[TextRow], designations=()) -> DrawingLegend:
    """Find the sheet's designation list and read it.

    A legend row is a short code with a description: either both in one text row, or the code in one row and the
    description in another on the same baseline a little to the right. Rows on one left edge that read that way
    are a candidate list, and rows on that edge whose leading word is not a code are the headings above them.

    Being a stack of short words with sentences beside them is not enough to be a designation list, and taking it
    to be enough is how a note block becomes the drawing's vocabulary. `FALL 1:100 MOT GOLVBRUNN`, `MED
    ISOLERING`, `OBS! SAMORDNAS MED EL` is six rows on one edge, each a short leading token with words after it,
    and the reading filed it as the sheet saying what its codes mean. A parts table repeating the word POS sixty
    times is the same mistake with a straighter face.

    Two things separate the real list from those, and either will do:

      * the drawing uses the codes. A designation list is a vocabulary for what is drawn on the paper, so its
        codes turn up out on the drawing at the head of the labels. A note's leading words turn up nowhere else.
      * the descriptions line up. A list is set as a table - the codes in one column, the words in another - so
        the descriptions share a left edge of their own. A note's words start wherever its leading word ended.

    The first is the stronger evidence and decides between candidates; the second is what lets an index sheet,
    which carries the list for a set without drawing any of it, still be read. A stack that shows neither is a
    stack of text, and the sheet is left with no list rather than a made-up one - which costs nothing, because
    a legend that was never found claims nothing.
    """
    rows = [l for l in lines if abs(l.angle) <= 5.0 and l.text.strip()]
    if not rows:
        return DrawingLegend()
    by_band: dict[int, list[TextRow]] = defaultdict(list)
    for l in rows:
        by_band[round(l.bbox[1] / 2.0)].append(l)
    found: dict[str, tuple[str, str, float]] = {}
    for l in rows:
        t = l.text.strip()
        h = max(l.bbox[3] - l.bbox[1], 1.0)
        m = _INLINE.match(t)
        if m and any(c.isalpha() for c in m.group(2)):
            found[l.rid] = (m.group(1), m.group(2), _description_x(l, m.start(2)))
            continue
        if len(t) > _R("semantics.legend.MAX_CODE_LEN", MAX_CODE_LEN) or " " in t:
            continue
        best = None
        band = round(l.bbox[1] / 2.0)
        for k in (band - 1, band, band + 1):
            for o in by_band.get(k, []):
                if o is l or o.bbox[0] <= l.bbox[2] - 0.1 or abs(o.bbox[1] - l.bbox[1]) > 0.6 * h:
                    continue
                gap = o.bbox[0] - l.bbox[2]
                if 0.0 <= gap <= _R("semantics.legend.DESC_GAP_ROWS", DESC_GAP_ROWS) * h and (best is None or gap < best[0]):
                    best = (gap, o)
        if best is not None and any(c.isalpha() for c in best[1].text):
            found[l.rid] = (t, best[1].text.strip(), best[1].bbox[0])
    if not found:
        return DrawingLegend()
    heads = {(getattr(d, "system_token", "") or "").upper() for d in designations}
    heads |= {(getattr(d, "text", "") or "").upper().strip() for d in designations}
    heads.discard("")
    by_rid = {l.rid: l for l in rows}
    best_list: tuple[tuple, list[LegendEntry], float] | None = None
    for edge in sorted({by_rid[rid].bbox[0] for rid in found}):
        entries = _candidate(rows, found, edge)
        if len(entries) < _R("semantics.legend.MIN_ENTRIES", MIN_ENTRIES):
            continue
        codes = {e.code.upper() for e in entries}
        if len(codes) < _R("semantics.legend.MIN_CODES", MIN_CODES):
            continue                    # a column that repeats one word is a table, not a vocabulary
        used = sum(1 for c in codes if any(h == c or h.startswith(c) for h in heads))
        dxs = [found[rid][2] for rid in (l.rid for l in rows)
               if rid in found and edge - 0.1 <= by_rid[rid].bbox[0] <= edge + _R("semantics.legend.COL_TOL", COL_TOL)]
        dedge = densest_edge(dxs)
        lined = sum(1 for x in dxs if dedge is not None and dedge - 0.1 <= x <= dedge + _R("semantics.legend.COL_TOL", COL_TOL))
        if used < _R("semantics.legend.USED_MIN", USED_MIN) and lined < _R("semantics.legend.ALIGNED_SHARE", ALIGNED_SHARE) * len(dxs):
            continue
        score = (used, lined, len(entries))
        if best_list is None or score > best_list[0]:
            best_list = (score, entries, edge)
    if best_list is None:
        return DrawingLegend()
    return DrawingLegend(entries=best_list[1], column_x=best_list[2])


def adopt(legend: DrawingLegend) -> DrawingLegend:
    """The same designation list, as it stands for a sheet that does not carry it.

    What travels between the sheets of one set is the vocabulary and nothing else: the codes, the words beside
    them, the headings that group them, and the roles the sheet that carried the list settled from its own use.
    What does not travel is where any of it sat on paper. Roles arrive as a starting point, not a verdict - this
    sheet's own use of a code still outranks what another sheet made of it."""
    return DrawingLegend(own=False, column_x=None,
                         entries=[LegendEntry(code=e.code, description=e.description, heading=e.heading,
                                              bbox=(0.0, 0.0, 0.0, 0.0), role=e.role, role_from=e.role_from,
                                              page=e.page)
                                  for e in legend.entries])


def merged(a: DrawingLegend | None, b: DrawingLegend) -> DrawingLegend:
    """The set's vocabulary after reading one more of its sheets.

    Sets do not always write the whole list in one place: a big project puts the water systems on one sheet and
    the heating systems on another, and either sheet alone is a partial vocabulary. Codes accumulate, and the
    first sheet to write a code keeps it - a later sheet repeating the same list says nothing new, and a later
    sheet that disagrees about a code is not evidence enough to overwrite the sheet that introduced it. The
    result is nobody's own list, so it never lends its geometry to anything."""
    if a is None or not a.entries:
        return DrawingLegend(own=False, entries=list(b.entries))
    have = {e.code.upper() for e in a.entries}
    return DrawingLegend(own=False, entries=list(a.entries) + [e for e in b.entries if e.code.upper() not in have])


def roles_of(legend: DrawingLegend) -> dict[str, str]:
    """What each code was settled as, in the form another sheet of the set can be given it."""
    return {e.code.upper(): e.role for e in legend.entries if e.role in ("system", "component")}


# what a role is worth against another claim on the same code: a sheet that showed a code opening a dimensioned
# label has said more than a sheet on which the code never appeared
_ROLE_RANK = {"unused": 0, "material": 1, "component": 2, "system": 2}


def learn_roles(vocab: DrawingLegend | None, sheet: DrawingLegend) -> None:
    """Carry back into the set's vocabulary what a sheet settled about its codes by using them.

    The vocabulary is read before any sheet is, so its rows start out saying only that the codes exist - a list
    of words with no verdict on any of them. What a code IS - a pipe system, a fitting, a material - is something
    a sheet shows by using it, and a set is read one sheet at a time. Without this the list travels between the
    sheets as bare words: every row stays 'unused', the next sheet is handed nothing to stand on, and the list
    that is written down at the end says the reading made nothing of any of its sixty-four rows.

    Only what a sheet showed travels. A role a sheet was handed by the vocabulary is not evidence, and letting it
    back in would harden the first guess into a fact that every later sheet then agrees with.
    """
    if vocab is None or not vocab.entries:
        return
    by_code = vocab.by_code
    for e in sheet.entries:
        if e.role_from != "usage":
            continue
        v = by_code.get(e.code.upper())
        if v is None or _ROLE_RANK[e.role] <= _ROLE_RANK.get(v.role, 0):
            continue
        v.role, v.role_from = e.role, "usage"


def assign_roles(legend: DrawingLegend, designations, prior: dict[str, str] | None = None) -> None:
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

    def owner(head: str) -> str | None:
        for c in codes:
            if head == c or (head.startswith(c) and len(head) > len(c)):
                return c
        return None

    def outside(d) -> bool:
        b = getattr(d, "bbox", None)
        return not (box is not None and b is not None and box[0] - 4.0 <= b[0] and b[2] <= box[2] + 4.0
                    and box[1] - 4.0 <= b[1] and b[3] <= box[3] + 4.0)

    # Which shapes this sheet writes its pipe designations in. A code carrying a size is not yet a system: a
    # valve tag carries one too - `AV201-22` is a shut-off valve of 22 mm, not twenty-two metres of AV pipe -
    # and reading it as a system handed the drawing a pipe it does not draw. What separates them is the shape
    # the sheet writes: a pipe designation puts a material token after the system code and a fitting tag does
    # not. A shape only one code ever writes is that code's own tag; a shape several codes share is the sheet's
    # designation grammar, and that is what says a code opens one.
    by_pattern: dict[str, set[str]] = defaultdict(set)
    for d in designations:
        if getattr(d, "dn", None) is None or not outside(d):
            continue
        c = owner((getattr(d, "system_token", "") or "").upper())
        if c:
            by_pattern[getattr(d, "pattern", "") or ""].add(c)
    shared = {pat for pat, cs in by_pattern.items() if len(cs) >= 2}

    for d in designations:
        b = getattr(d, "bbox", None)
        if box is not None and b is not None and box[0] - 4.0 <= b[0] and b[2] <= box[2] + 4.0 \
                and box[1] - 4.0 <= b[1] and b[3] <= box[3] + 4.0:
            continue                                    # this is the legend line itself
        text = (d.text or "").upper()
        head = (d.system_token or "").upper()
        if d.dn is not None:
            # where the sheet writes no shape more than one code shares, there is no grammar to appeal to and
            # a size on the label is all the evidence there is
            if not shared or (getattr(d, "pattern", "") or "") in shared:
                c = owner(head)
                if c:
                    opens.add(c)
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

    # What another sheet of the same set already worked out about a code this sheet never uses. A plan sheet
    # draws a floor of a building, not the whole vocabulary: a set's cold water code appears on every sheet, its
    # sprinkler code on three of them. Deciding from this sheet alone that the sprinkler code is a material - it
    # opened nothing here - reads the same project differently from one sheet to the next, which is the worst
    # kind of wrong, because a refused label never becomes a pipe label that is missing.
    #
    # It only fills silence. A code this sheet did use is settled by that use, whatever another sheet made of it.
    if prior:
        for e in legend.entries:
            was = prior.get(e.code.upper())
            if e.role == "material" and was in ("system", "component"):
                e.role, e.role_from = was, "other_sheet"

    # A sheet only shows what a sheet shows. A code the legend lists under "SYSTEM SPILLVATTEN" is a system code
    # whether or not this particular page happens to carry a dimensioned label for it - and where it does not,
    # every label of that system was being refused as not naming a pipe at all. That is the same project reading
    # differently from one sheet to the next, which is the worst kind of wrong: silent, and invisible in the
    # counts, because a refused label never becomes a pipe label to be missing.
    #
    # The drawing's own grouping settles it. A heading is the sheet saying "these belong together", so a code with
    # no usage of its own takes the role its heading-mates were given by usage - and only when the heading has
    # such evidence, and only in one direction: it may promote a code the page did not use, never demote or
    # reclassify one the page did.
    by_heading: dict[str, list[LegendEntry]] = defaultdict(list)
    for e in legend.entries:
        by_heading[(e.heading or "").strip().upper()].append(e)
    if len(by_heading) < 2:
        return              # one heading over everything groups nothing, and cannot speak for anything
    for head, group in by_heading.items():
        if not head:
            continue
        evidenced = Counter(e.role for e in group if e.role in ("system", "component")
                            and e.role_from == "usage")
        if len(evidenced) != 1:
            continue        # a section holding both kinds is not a section that says which one a code is
        role, n = evidenced.most_common(1)[0]
        if 2 * n < len(group):
            continue        # A section speaks when the page has shown most of it. Two codes out of nineteen is
                            # not the section speaking: on a real sheet the section listing the sanitary fittings
                            # - floor drain, mixer, washbasin, WC, water heater - carried a dimensioned label for
                            # a shut-off valve and a slop hopper, and every fitting in it was promoted to a pipe
                            # system. The page then named a hundred pipes it does not draw, each of them a
                            # fitting, and reported every one as a pipe that never got a metre.
        for e in group:
            if e.role == "material":
                e.role = role
                e.role_from = "heading"
