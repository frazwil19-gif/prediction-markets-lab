"""Append-only tennis prediction ledger + separate append-only settlement file.

Predictions are never rewritten: `append_predictions` skips any prediction_id already
present and verifies that existing rows are byte-identical before and after writing.
Settlements live in their own file keyed by prediction_id (first settlement wins)."""
from __future__ import annotations

import csv
import hashlib
from dataclasses import asdict, fields
from pathlib import Path

from prediction_markets_lab.tennis_prospective.engine import TennisPrediction

PRED_FIELDS = [f.name for f in fields(TennisPrediction)]
SETTLE_FIELDS = ["prediction_id", "status", "winner", "score", "result_source", "settlement_timestamp", "correct"]
SETTLED_STATES = ("SETTLED_CORRECT", "SETTLED_INCORRECT", "VOID")


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def append_predictions(path: Path, preds: list[TennisPrediction]) -> tuple[int, int]:
    """Append new predictions; return (added, skipped_existing). Raises if an existing
    row would change (immutability guard)."""
    existing = _read(path)
    ids = {r["prediction_id"] for r in existing}
    before = path.read_bytes() if path.exists() else b""
    new = []
    for p in preds:
        if p.prediction_id in ids:
            continue
        ids.add(p.prediction_id)
        new.append(p)
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not path.exists()
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=PRED_FIELDS)
            if write_header:
                w.writeheader()
            for p in new:
                w.writerow(asdict(p))
        if not path.read_bytes().startswith(before):
            raise RuntimeError("immutability violation: existing prediction rows changed")
    return len(new), len(preds) - len(new)


def read_predictions(path: Path) -> list[dict]:
    return _read(path)


def read_settlements(path: Path) -> dict[str, dict]:
    return {r["prediction_id"]: r for r in _read(path)}


def append_settlements(path: Path, rows: list[dict]) -> int:
    done = read_settlements(path)
    new = [r for r in rows if r["prediction_id"] not in done and r["status"] in SETTLED_STATES]
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        header = not path.exists()
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SETTLE_FIELDS)
            if header:
                w.writeheader()
            for r in new:
                w.writerow({k: r.get(k, "") for k in SETTLE_FIELDS})
    return len(new)
