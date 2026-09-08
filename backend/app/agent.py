"""The agent that works against a finished reading.

The division the whole thing rests on: the model decides what to ask, the engine decides what the answer is.
Every number the agent says comes out of a tool call into the measuring pipeline's own artifacts, so an answer in
the chat and an answer in the takeoff table cannot disagree. The model never sees geometry it could invent from -
it sees the names of tools and the results they return.

A turn is bounded: at most a handful of tool rounds, and the tools are read-only. Changing the drawing goes
through the correction log, which is versioned and can be undone; nothing here writes.
"""
from __future__ import annotations

import json
from typing import Any

MAX_ROUNDS = 6
MAX_RESULT_CHARS = 6000


def _clip(obj: Any) -> str:
    s = json.dumps(obj, ensure_ascii=False)
    return s if len(s) <= MAX_RESULT_CHARS else s[:MAX_RESULT_CHARS] + " …(avkortat)"


def run_turn(model, ask, question: str, selection: dict | None = None,
             history: list[dict] | None = None) -> dict:
    """One question, answered through the tools. Returns the words, the calls made and what to light up."""
    from vvs_engine.agent import tools as T

    lines = [question.strip()]
    if selection:
        ids = selection.get("pipe_ids") or []
        box = selection.get("bbox")
        page = selection.get("page")
        bits = []
        if ids:
            bits.append(f"markerade rör: {', '.join(ids[:40])}")
        if box:
            bits.append(f"markerat område: [{', '.join(str(round(float(v), 1)) for v in box)}]")
        if page is not None:
            bits.append(f"sida: {page}")
        if bits:
            lines.append("\n[Användarens markering] " + "; ".join(bits))

    messages: list[dict] = list(history or [])
    messages.append({"role": "user", "content": "\n".join(lines)})

    used: list[dict] = []
    for _ in range(MAX_ROUNDS):
        out = ask(messages, T.schemas())
        calls = out.get("calls") or []
        if not calls:
            return {"svar": out.get("text") or "", "verktyg": used, "markera": _highlights(used)}
        for c in calls:
            try:
                args = json.loads(c.get("arguments") or "{}")
            except Exception:
                args = {}
            result = T.run(c.get("name") or "", model, args)
            used.append({"namn": c.get("name"), "argument": args, "resultat": result})
            messages.append({"type": "function_call", "call_id": c.get("call_id"),
                             "name": c.get("name"), "arguments": c.get("arguments") or "{}"})
            messages.append({"type": "function_call_output", "call_id": c.get("call_id"),
                             "output": _clip(result)})
    return {"svar": "Jag kom inte fram till ett svar inom det antal steg en fråga får ta. "
                    "Smalna av frågan, eller markera det du menar i ritningen.",
            "verktyg": used, "markera": _highlights(used)}


def _highlights(used: list[dict]) -> dict:
    """Everything the answer rests on, so a claim on screen can be pointed at on the sheet."""
    pipe_ids: list[str] = []
    boxes: list[list[float]] = []
    for u in used:
        r = u.get("resultat") or {}
        for key in ("ror", "stracker", "vag"):
            for row in (r.get(key) or []):
                if isinstance(row, dict) and row.get("pipe_id"):
                    pipe_ids.append(row["pipe_id"])
                    if row.get("bbox"):
                        boxes.append(row["bbox"])
        for row in (r.get("beteckningar") or []):
            if isinstance(row, dict) and row.get("bbox"):
                boxes.append(row["bbox"])
        if r.get("pipe_id"):
            pipe_ids.append(r["pipe_id"])
        for row in (r.get("granser") or []) + (r.get("andar") or []) + (r.get("stallen") or []):
            if isinstance(row, dict) and row.get("bbox"):
                boxes.append(row["bbox"])
    seen: set[str] = set()
    ids = [i for i in pipe_ids if not (i in seen or seen.add(i))]
    return {"ror_id": ids[:400], "rutor": boxes[:400]}
