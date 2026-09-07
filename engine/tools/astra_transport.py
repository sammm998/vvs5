"""The transport that puts a reading's open cases to GPT-6 Astra. Kept out of the engine on purpose.

vvs_engine/semantics/astra.py holds the rules - what may be asked, what may be answered, and how an answer is
checked. This holds only the wire: how to reach the model and how to wait for it. The engine imports none of it
and runs with no network unless a caller hands `analyze_page` a transport built here.

No key appears here. The agent proxy attaches the credential after the request leaves the machine.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from typing import Callable

API = "https://api.openai.com/v1/responses"
MODEL = os.environ.get("VVS_SECOND_READER_MODEL", "gpt-6-astra")
# reasoning tokens count against this, and a bounded multiple-choice question needs far less room than a review
MAX_OUTPUT_TOKENS = 4000
POLL_SECONDS, POLL_ROUNDS = 5, 60

SYSTEM = ("Du läser VVS-ritningar. Du får ett fall som den geometriska läsningen inte kunde avgöra, tillsammans "
          "med de kandidater ritningen faktiskt erbjuder. Välj en av dem eller svara OKLART. Hitta aldrig på "
          "geometri, koordinater, dimensioner eller beteckningar som inte står i frågan.")


def _curl(args: list[str], timeout: int = 90) -> dict:
    r = subprocess.run(["curl", "-sS", "--max-time", str(timeout), *args], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        raise RuntimeError(f"icke-JSON från {API}: {(r.stdout or r.stderr)[:200]}")


def transport(effort: str = "low") -> Callable:
    """A callable for analyze_page(second_reader=...). Raising is safe: the case simply stays ambiguous."""
    def ask(q) -> str:
        body = {"model": MODEL, "instructions": SYSTEM, "input": q.as_prompt(),
                "max_output_tokens": MAX_OUTPUT_TOKENS, "reasoning": {"effort": effort}, "background": True}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(body, fh)
            path = fh.name
        try:
            d = _curl([API, "-H", "Content-Type: application/json", "-d", f"@{path}"])
            if d.get("error"):
                raise RuntimeError(str(d["error"])[:200])
            rid = d["id"]
            for _ in range(POLL_ROUNDS):
                if d.get("status") in ("completed", "failed", "incomplete"):
                    break
                time.sleep(POLL_SECONDS)
                d = _curl([f"{API}/{rid}"], timeout=60)
            return "".join(c.get("text", "")
                           for o in d.get("output", []) for c in (o.get("content") or [])
                           if c.get("type") == "output_text")
        finally:
            os.unlink(path)
    return ask


def vision_transport(effort: str = "low") -> Callable:
    """A callable for review.vision.look(ask=...). Images go up; only words come back.

    Nothing this returns can become geometry - vision.look has no way to write into a reading - so the only
    risk here is cost and latency, not a wrong metre.
    """
    import base64

    def ask(prompt: str, images: list[bytes]) -> str:
        content: list[dict] = [{"type": "input_text", "text": prompt}]
        for png in images:
            content.append({"type": "input_image",
                            "image_url": "data:image/png;base64," + base64.b64encode(png).decode()})
        body = {"model": MODEL, "input": [{"role": "user", "content": content}],
                "max_output_tokens": 8000, "reasoning": {"effort": effort}, "background": True}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(body, fh)
            path = fh.name
        try:
            d = _curl([API, "-H", "Content-Type: application/json", "-d", f"@{path}"], timeout=180)
            if d.get("error"):
                raise RuntimeError(str(d["error"])[:200])
            rid = d["id"]
            for _ in range(POLL_ROUNDS):
                if d.get("status") in ("completed", "failed", "incomplete"):
                    break
                time.sleep(POLL_SECONDS)
                d = _curl([f"{API}/{rid}"], timeout=60)
            return "".join(c.get("text", "")
                           for o in d.get("output", []) for c in (o.get("content") or [])
                           if c.get("type") == "output_text")
        finally:
            os.unlink(path)
    return ask
