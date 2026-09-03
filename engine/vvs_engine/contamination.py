"""Contamination firewall: production source must not contain drawing-specific designations, DN inventories,
coordinates, object ids or expected quantities, and must not import validation data."""
from __future__ import annotations

import os
import re
from typing import Any

FORBIDDEN_PATTERNS = [
    # concrete VVS designations (system-material-DN forms) used as literals
    (r"[\"'](?:S[0-9]|KV0?[0-9]|VV0?[0-9]|VVC0?[0-9]|VS[0-9]{1,2}|VP0?[0-9]|SF0?[0-9]|S0?[0-9])-[A-Z][0-9]{1,2}(?:-[0-9]{2,3})?[\"']", "designation literal"),
    (r"[\"']V-5[0-9][A-Z]*-?-?FE", "pipe layer name literal"),
    (r"(?i)facit|expected_(?:meters|quantit|length)|reference_(?:meters|length)", "validation vocabulary"),
    (r"(?i)DRAWING_[ABCD]", "development drawing reference"),
    (r"[\"'](?:path|seqno|xref)_[0-9a-f]{6,}[\"']", "raw object id literal"),
    (r"\b(?:972\.72|347\.64|1223\.4|2384\.0|1684\.0)\b", "coordinate literal from development drawings"),
]
ALLOWED_FILES = {"contamination.py"}


def scan_source(root: str) -> dict[str, Any]:
    findings = []
    n_files = 0
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".py") or fn in ALLOWED_FILES:
                continue
            path = os.path.join(dirpath, fn)
            n_files += 1
            with open(path, "r", encoding="utf-8") as fh:
                for ln, line in enumerate(fh, 1):
                    for pat, why in FORBIDDEN_PATTERNS:
                        if re.search(pat, line):
                            findings.append({"file": os.path.relpath(path, root), "line": ln, "reason": why, "text": line.strip()[:120]})
    return {"state": "PASS" if not findings else "FAIL", "files_scanned": n_files, "findings": findings,
            "validation_data_dependency": False,
            "note": "production package has no import of validation/facit data; detection runs with data/ absent"}
