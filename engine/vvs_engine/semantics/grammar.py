"""Drawing-local VVS designation grammar.

The engine never knows expected code VALUES. It discovers the STRUCTURE of code-like words in the current drawing:
class patterns such as  A9-A9-9  or  A9-A9-9-A9  (A = letters, 9 = digits, separators literal), their frequencies,
and which pattern position behaves like a nominal diameter. Twin-shape ambiguities left by the recognizer
(O/0, I/1, S/5, B/8, Z/2, G/6) are resolved by choosing the reading whose pattern is most frequent in this drawing.
All of this is local to one analysis job.
"""
from __future__ import annotations

import itertools
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from ..text.model import Glyph, TextRow

TWINS = {"O": "0", "0": "O", "I": "1", "1": "I", "S": "5", "5": "S", "B": "8", "8": "B", "Z": "2", "2": "Z", "G": "6", "6": "G"}
SEPARATORS = "-/+.,:()[]"
MARGIN = 0.07


def char_class(c: str) -> str:
    if c.isalpha():
        return "A"
    if c.isdigit():
        return "9"
    return c


COUNT_PREFIX_RE = re.compile(r"^(\d{1,2})[xX](.+)$")


def strip_count_prefix(word: str) -> tuple[int, str]:
    m = COUNT_PREFIX_RE.match(word)
    if m and is_code_like(m.group(2)) and any(ch in m.group(2) for ch in "-/"):
        return int(m.group(1)), m.group(2)
    return 1, word


def token_shape(tok: str) -> str:
    """Shape of a token: A<alpha-run-length>D<digit-run-length> for prefix-letters-then-digits tokens."""
    m = re.fullmatch(r"([A-Za-zÅÄÖ]*)(\d*)([A-Za-zÅÄÖ]*)", tok)
    if not m:
        return "?"
    return f"A{len(m.group(1))}D{len(m.group(2))}{'A' + str(len(m.group(3))) if m.group(3) else ''}"


def compress_pattern(word: str) -> str:
    cnt, core = strip_count_prefix(word)
    if cnt > 1:
        return "#" + compress_pattern(core)
    out = []
    for c in word:
        k = char_class(c)
        if out and out[-1] == k and k in "A9":
            continue
        out.append(k)
    return "".join(out)


def is_code_like(word: str) -> bool:
    """Structural test: letters AND digits present, only code characters, starts with a letter or a count prefix."""
    if len(word) < 2 or len(word) > 24:
        return False
    if not re.fullmatch(r"[A-Za-zÅÄÖØ0-9\-/+.,:()\[\]]+", word):
        return False
    has_a = any(c.isalpha() for c in word)
    has_d = any(c.isdigit() for c in word)
    return has_a and has_d


@dataclass
class WordReading:
    text: str
    pattern: str
    flips: int          # number of twin flips relative to the recognizer's best reading
    cost: float         # summed score deltas of flips


def word_readings(glyphs: list[Glyph]) -> list[WordReading]:
    """Enumerate alternative readings of a word over its twin-ambiguous glyphs (capped)."""
    amb = [i for i, g in enumerate(glyphs) if g.char in TWINS and any(a == TWINS[g.char] and sc <= g.score + MARGIN for a, sc in g.alternatives)]
    base = "".join(g.char for g in glyphs)
    readings = [WordReading(base, compress_pattern(base), 0, 0.0)]
    if not amb:
        return readings
    amb = amb[:5]
    for k in range(1, len(amb) + 1):
        for combo in itertools.combinations(amb, k):
            chars = [g.char for g in glyphs]
            cost = 0.0
            for i in combo:
                g = glyphs[i]
                alt = TWINS[g.char]
                sc = next(s for a, s in g.alternatives if a == alt)
                chars[i] = alt
                cost += max(0.0, sc - g.score)
            t = "".join(chars)
            readings.append(WordReading(t, compress_pattern(t), k, cost))
    return readings


@dataclass
class GrammarFamily:
    pattern: str
    count: int
    examples: list[str] = field(default_factory=list)
    numeric_positions: dict[int, int] = field(default_factory=dict)   # token index -> occurrences of pure-digit token
    dn_token_index: int | None = None
    dn_nominal_fraction: dict[int, float] = field(default_factory=dict)


class DesignationGrammar:
    """Drawing-local statistics of code-like word structures (patterns + token shapes)."""

    def __init__(self):
        self.pattern_weight: Counter = Counter()
        self.shape_weight: Counter = Counter()      # (base pattern, token index, shape) -> weight
        self.families: dict[str, GrammarFamily] = {}

    @staticmethod
    def _base(pattern: str) -> str:
        return pattern[1:] if pattern.startswith("#") else pattern

    @staticmethod
    def _admissible(r: "WordReading") -> bool:
        return is_code_like(r.text) or r.text.isdigit() or re.fullmatch(r"\d[\d.,:+\-/]*\d", r.text) is not None

    def observe(self, readings: list[WordReading]) -> None:
        """Only words whose recognizer reading (0 flips) is code-like or a pure number contribute; their
        alternative readings share the word's unit weight."""
        base_r = readings[0]
        if not self._admissible(base_r):
            return
        code = [r for r in readings if self._admissible(r)]
        w = 1.0 / len(code)
        for r in code:
            base = self._base(r.pattern)
            self.pattern_weight[base] += w
            _, core = strip_count_prefix(r.text)
            for i, tok in enumerate(split_tokens(core)):
                self.shape_weight[(base, i, token_shape(tok))] += w

    def typicality(self, r: WordReading) -> float:
        base = self._base(r.pattern)
        _, core = strip_count_prefix(r.text)
        toks = split_tokens(core)
        if not toks:
            return 0.0
        return sum(self.shape_weight.get((base, i, token_shape(t)), 0.0) for i, t in enumerate(toks)) / len(toks)

    def choose(self, readings: list[WordReading]) -> WordReading:
        """Pick the reading with the most frequent drawing-local pattern, then the most typical token shapes;
        ties -> fewer twin flips, lower cost, then text."""
        def key(r: WordReading):
            return (-self.pattern_weight.get(self._base(r.pattern), 0.0), -round(self.typicality(r), 3), r.flips, r.cost, r.text)
        code = [r for r in readings if self._admissible(r)]
        pool = code if code else readings
        return sorted(pool, key=key)[0]

    def finalize(self, words: list[str]) -> None:
        fams: dict[str, GrammarFamily] = {}
        for w in words:
            if not is_code_like(w):
                continue
            _, w = strip_count_prefix(w)
            pat = compress_pattern(w)
            f = fams.get(pat)
            if f is None:
                f = GrammarFamily(pattern=pat, count=0)
                fams[pat] = f
            f.count += 1
            if len(f.examples) < 6 and w not in f.examples:
                f.examples.append(w)
            for i, tok in enumerate(split_tokens(w)):
                if tok.isdigit():
                    f.numeric_positions[i] = f.numeric_positions.get(i, 0) + 1
        # values seen per (pattern, token index)
        values: dict[tuple[str, int], list[int]] = defaultdict(list)
        for w in words:
            if not is_code_like(w):
                continue
            _, w = strip_count_prefix(w)
            pat = compress_pattern(w)
            for i, tok in enumerate(split_tokens(w)):
                if tok.isdigit():
                    values[(pat, i)].append(int(tok))
        for f in fams.values():
            # DN token index: a pure-digit position that is numeric in (nearly) every member AND whose values
            # mostly belong to the generic nominal pipe-size series (industry knowledge, not drawing-specific)
            cands = []
            for i, n in f.numeric_positions.items():
                if n < 0.8 * f.count or i == 0:
                    continue
                vals = values.get((f.pattern, i), [])
                nominal = sum(1 for v in vals if v in NOMINAL_SIZES)
                if vals and nominal >= 0.6 * len(vals):
                    cands.append((i, nominal / len(vals)))
            if len(cands) == 1:
                f.dn_token_index = cands[0][0]
            elif len(cands) > 1:
                cands.sort(key=lambda c: (-c[1], c[0]))
                f.dn_token_index = cands[0][0] if cands[0][1] > cands[1][1] else None
            f.dn_nominal_fraction = {i: round(frac, 2) for i, frac in cands}
        self.families = fams

    def as_dict(self) -> dict:
        return {"families": [{"pattern": f.pattern, "count": f.count, "examples": f.examples,
                              "numeric_positions": f.numeric_positions, "dn_token_index": f.dn_token_index}
                             for f in sorted(self.families.values(), key=lambda x: (-x.count, x.pattern))]}


def split_tokens(word: str) -> list[str]:
    return [t for t in re.split(r"[\-/+.,:()\[\]]+", word) if t]


# Generic nominal pipe sizes (industry standard DN / copper / plastic series); used as PLAUSIBILITY evidence only.
NOMINAL_SIZES = {6, 8, 10, 12, 15, 16, 18, 20, 22, 25, 28, 32, 35, 40, 42, 50, 54, 63, 65, 75, 76, 80, 90, 100, 108,
                 110, 125, 133, 140, 150, 160, 168, 200, 219, 225, 250, 300, 315, 350, 400, 450, 500, 600, 630}


def dn_plausible(v: int) -> bool:
    return 6 <= v <= 1200
