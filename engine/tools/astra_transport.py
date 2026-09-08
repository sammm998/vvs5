"""The transport that puts a reading's open cases to GPT-6 Astra. Kept out of the engine on purpose.

vvs_engine/semantics/astra.py holds the rules - what may be asked, what may be answered, and how an answer is
checked. This holds only the wire: how to reach the model and how to wait for it. The engine imports none of it
and runs with no network unless a caller hands `analyze_page` a transport built here.

No key appears in this file. Where the request leaves through an agent proxy that attaches the credential,
nothing is sent from here at all; where it does not - a container running the service - the key is read from
OPENAI_API_KEY in the environment at call time and put on the wire, and never written down, logged or returned.
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


def _auth() -> list[str]:
    """The credential, if this machine is the one that has to supply it.

    Behind an agent proxy the request is authenticated after it leaves and no header belongs here. In a container
    there is no such proxy, so the key is read from the environment at the moment of the call. It is returned to
    the caller of curl and to nowhere else: never stored, never echoed into an error, never part of a result.
    """
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    return ["-H", f"Authorization: Bearer {key}"] if key else []


def available() -> tuple[bool, str]:
    """Whether a second reader can be reached from here, said plainly rather than found out by failing."""
    if os.environ.get("OPENAI_API_KEY", "").strip():
        return True, "nyckel i miljön"
    if os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"):
        return True, "proxy som fäster referensen"
    return False, "ingen OPENAI_API_KEY och ingen proxy: läsningen står på sin egen geometri"


def _curl(args: list[str], timeout: int = 90) -> dict:
    r = subprocess.run(["curl", "-sS", "--max-time", str(timeout), *_auth(), *args], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        # the key can appear in curl's own diagnostics, so only the first line of stdout is ever quoted back
        raise RuntimeError(f"icke-JSON från {API}: {(r.stdout or '')[:200] or 'inget svar'}")


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
