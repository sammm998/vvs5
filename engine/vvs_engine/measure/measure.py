"""Measurement and quantity aggregation. Meters only with verified scale; vertical only with explicit evidence."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..pipes.ownership import OwnershipResult, PhysicalPipe, DECLARED_REASON
from .scale import ScaleResult


@dataclass
class PipeMeasure:
    pipe: PhysicalPipe
    horizontal_pdf_units: float
    horizontal_m: float | None
    vertical_m: float | None
    vertical_evidence: dict | None
    total_m: float | None
    state: str
    reasons: list[str] = field(default_factory=list)
    hatched_pdf_units: float = 0.0
    hatched_m: float | None = None      # part of the horizontal length running inside a hatched area


def measure_pipes(own: OwnershipResult, scale: ScaleResult, elevations: dict[str, list[dict]],
                  hatched_pt: dict[str, float] | None = None) -> list[PipeMeasure]:
    """elevations: anchor_id -> list of {tag, value} elevation annotations attached to the anchor's label unit.
    hatched_pt: physical_pipe_id -> length (pdf units) of the pipe inside hatched areas."""
    out: list[PipeMeasure] = []
    mpp = scale.meters_per_pt if scale.state in ("VERIFIED", "TEXT_ONLY", "BAR_ONLY", "CONFLICT", "FROM_THE_SET") \
        and scale.meters_per_pt else None
    # A sheet whose scale evidence disagrees still gets measured - the geometric bar is the better witness and
    # the reason for choosing it is recorded - but every metre that comes out of it carries the conflict, so no
    # single run can be read as confidently measured when the sheet's own scale is unsettled.
    scale_note = (f"scale_{scale.state.lower()}:{scale.reason}"
                  if scale.state not in ("VERIFIED",) and mpp is not None else None)
    for p in own.pipes:
        # hatched length is measured on drawn primitives; scale it by the bridged-gap share of the run
        factor = (p.length_pt / p.raw_length_pt) if p.raw_length_pt > 0 else 1.0
        hpt = min((hatched_pt or {}).get(p.physical_pipe_id, 0.0) * factor, p.length_pt)
        hpu = p.length_pt - hpt          # horizontal quantity = drawn length outside hatched (wall) areas
        hm = hpu * mpp if mpp is not None else None
        reasons = []
        if mpp is None:
            reasons.append("no_verified_scale")
        elif scale_note:
            reasons.append(scale_note)
        vert, vev = _vertical(p, elevations)
        total = (hm + (vert or 0.0)) if hm is not None else None
        state = "CONFIRMED" if hm is not None else "UNSUPPORTED_STYLE"
        if p.frontier_reasons:
            reasons.extend(p.frontier_reasons)
        out.append(PipeMeasure(pipe=p, horizontal_pdf_units=hpu, horizontal_m=hm, vertical_m=vert, vertical_evidence=vev,
                               total_m=total, state=state, reasons=reasons, hatched_pdf_units=hpt,
                               hatched_m=(hpt * mpp if mpp is not None else None)))
    return out


def _vertical(p: PhysicalPipe, elevations: dict[str, list[dict]]):
    """Vertical length only from explicit evidence: two elevation annotations with the same tag on the pipe's
    supporting anchors (top/bottom levels). Otherwise UNKNOWN (None).

    The unit has to come from the drawing too. A level written with a decimal separator is metres, a whole
    thousand or more is millimetres, and a bare small integer says neither - reading that as metres turns two
    levels 50 mm apart into fifty metres of pipe. A tag whose levels do not agree on one unit is not evidence,
    so the vertical stays UNKNOWN rather than being guessed at either scale.

    What this reads is the span between the highest and lowest level on the run. A pipe that goes down and up
    again passes the same levels twice and its true vertical length is larger; nothing in two levels says that
    it did, so the span is what can be defended and the rest is not claimed.
    """
    vals: dict[str, list[tuple[str, float, str | None]]] = defaultdict(list)
    for aid in p.anchor_ids:
        for e in elevations.get(aid, []):
            vals[e["tag"]].append((aid, e["value"], e.get("unit")))
    for tag, lst in sorted(vals.items()):
        uniq = sorted({v for _, v, _ in lst})
        if len(uniq) < 2:
            continue
        units = {u for _, _, u in lst}
        if len(units) != 1 or None in units:
            continue                  # the sheet did not say what these numbers are; no vertical is claimed
        unit = units.pop()
        diff = (max(uniq) - min(uniq)) / (1000.0 if unit == "mm" else 1.0)
        return round(diff, 3), {"kind": "elevation_difference_between_anchors", "tag": tag, "unit": unit,
                                "values": uniq, "anchors": sorted({a for a, _, _ in lst})}
    return None, None


def aggregate(measures: list[PipeMeasure], ambiguous_pt: dict[str, float], mpp: float | None,
              risers: dict[str, list[dict]] | None = None, label_counts: dict[str, int] | None = None,
              label_risers: dict[str, list[dict]] | None = None) -> list[dict[str, Any]]:
    """label_counts: identity key -> number of verified labels on the drawing, which is what a reader counts;
    physical_pipe_count is the number of connected runs the network resolves into, which is usually smaller."""
    rows: dict[str, dict[str, Any]] = {}
    for m in measures:
        k = m.pipe.identity.key
        r = rows.setdefault(k, {"designation": m.pipe.identity.display, "base": m.pipe.identity.base, "dn": m.pipe.identity.dn, "system": m.pipe.identity.system,
                                "physical_pipe_count": 0, "confirmed_horizontal_m": 0.0, "confirmed_vertical_m": 0.0,
                                "confirmed_total_m": 0.0, "horizontal_pdf_units": 0.0, "ambiguous_m": 0.0, "vertical_known": False,
                                "in_hatched_area_m": 0.0, "declared_m": 0.0, "state": "CONFIRMED", "pipe_ids": []})
        r["physical_pipe_count"] += 1
        if m.horizontal_m is not None and DECLARED_REASON in (m.pipe.evidence or []):
            r["declared_m"] += m.horizontal_m       # named by the sheet's written rule, not by a label
        r["horizontal_pdf_units"] += m.horizontal_pdf_units
        r["pipe_ids"].append(m.pipe.physical_pipe_id)
        if m.horizontal_m is not None:
            r["confirmed_horizontal_m"] += m.horizontal_m
            r["confirmed_total_m"] += m.horizontal_m
            r["in_hatched_area_m"] += m.hatched_m or 0.0      # excluded from the horizontal quantity
        else:
            r["state"] = "UNSUPPORTED_STYLE"
        if m.vertical_m is not None:
            r["confirmed_vertical_m"] += m.vertical_m
            r["confirmed_total_m"] += m.vertical_m
            r["vertical_known"] = True
    for k, pt in ambiguous_pt.items():
        r = rows.setdefault(k, {"designation": k.split("|DN")[0], "base": k.split("|DN")[0], "dn": _dn_from_key(k), "system": "", "physical_pipe_count": 0,
                                "confirmed_horizontal_m": 0.0, "confirmed_vertical_m": 0.0, "confirmed_total_m": 0.0,
                                "horizontal_pdf_units": 0.0, "ambiguous_m": 0.0, "vertical_known": False, "state": "AMBIGUOUS", "pipe_ids": []})
        r["ambiguous_m"] += pt * mpp if mpp else 0.0
        # geometry the reading could not give to anyone exists whether or not there is a scale to measure it in;
        # tracking it in the drawing's own units keeps a scaleless sheet from reporting the ambiguity away
        r["ambiguous_pdf_units"] = r.get("ambiguous_pdf_units", 0.0) + pt
        if r["physical_pipe_count"] == 0:
            r["state"] = "AMBIGUOUS"
    for k, n in (label_counts or {}).items():
        if k in rows:
            rows[k]["label_count"] = n
    for r in rows.values():
        r.setdefault("label_count", 0)          # a declared run has metres and no label: zero, not missing
    # Both riser readings make a row of their own. A designation the sheet writes only over a riser - a stack
    # that drops away out of the plan, drawn as a point and named with its dimension on the row below - has no
    # horizontal run to be aggregated from, and left to the measured rows alone it would not be reported at all.
    for k, lst in (label_risers or {}).items():
        r = rows.setdefault(k, _empty_row(k))
        r["riser_count_from_labels"] = len(lst)
    for k, lst in (risers or {}).items():
        r = rows.setdefault(k, _empty_row(k))
        r["riser_count"] = len(lst)
    out = []
    for k in sorted(rows):
        r = rows[k]
        r.setdefault("riser_count", 0)
        r.setdefault("riser_count_from_labels", len((label_risers or {}).get(k, [])))
        r.setdefault("label_count", (label_counts or {}).get(k, 0))
        r.setdefault("in_hatched_area_m", 0.0)
        r.setdefault("ambiguous_pdf_units", 0.0)
        if r["physical_pipe_count"] == 0 and r["ambiguous_pdf_units"] == 0 \
                and max(r["riser_count"], r["riser_count_from_labels"]) > 0:
            r["state"] = "RISER_LABELS_ONLY"
        for f in ("confirmed_horizontal_m", "confirmed_vertical_m", "confirmed_total_m", "ambiguous_m",
                  "horizontal_pdf_units", "in_hatched_area_m", "ambiguous_pdf_units"):
            r[f] = round(r[f], 3)
        r["vertical_m"] = r["confirmed_vertical_m"] if r["vertical_known"] else "UNKNOWN"
        out.append(r)
    return out


def _empty_row(k: str) -> dict[str, Any]:
    """A quantity row for a designation with nothing measured under it yet."""
    return {"designation": k.split("|DN")[0], "base": k.split("|DN")[0], "dn": _dn_from_key(k), "system": "",
            "physical_pipe_count": 0, "confirmed_horizontal_m": 0.0, "confirmed_vertical_m": 0.0,
            "confirmed_total_m": 0.0, "horizontal_pdf_units": 0.0, "ambiguous_m": 0.0, "vertical_known": False,
            "in_hatched_area_m": 0.0, "state": "CONFIRMED", "pipe_ids": []}


def _dn_from_key(k: str):
    t = k.split("|DN")[-1]
    return int(t) if t.isdigit() else None
