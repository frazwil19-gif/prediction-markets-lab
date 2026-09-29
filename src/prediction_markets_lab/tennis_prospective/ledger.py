"""Append-only tennis prediction ledger + separate append-only settlement file.

Predictions are never rewritten: `append_predictions` skips any prediction_id already
present and verifies that existing rows are byte-identical before and after writing.
Settlements live in their own file keyed by prediction_id (first settlement wins)."""
from __future__ import annotations

import csv
import hashlib
from dataclasses import asdict, fields, replace
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


def validated_upgrade_id(prediction_id: str) -> str:
    """Deterministic ID for the first VALIDATED snapshot of an event whose canonical ID is already held by a
    research-only row (protocol amendment A1, 2026-09-29: "first *valid* snapshot is canonical")."""
    return hashlib.sha256(f"{prediction_id}|FIRST_VALID_AFTER_RESEARCH".encode()).hexdigest()[:16]


def _is_validated(row: dict) -> bool:
    return str(row.get("source_validated")) in ("True", "true", "1")


def append_predictions(path: Path, preds: list[TennisPrediction]) -> tuple[int, int]:
    """Append new predictions; return (added, skipped_existing). Raises if an existing
    row would change (immutability guard).

    Canonical rule (protocol): the first *validated* snapshot before start is canonical. A research-only row
    never blocks it: if the canonical ID is held only by a research-only row, the first validated snapshot is
    appended once under `validated_upgrade_id(...)`. Existing rows are never modified; retries are idempotent."""
    existing = _read(path)
    ids = {r["prediction_id"] for r in existing}
    research_only = {r["prediction_id"] for r in existing if not _is_validated(r)}
    research_only -= {r["prediction_id"] for r in existing if _is_validated(r)}
    before = path.read_bytes() if path.exists() else b""
    new = []
    for p in preds:
        if p.prediction_id in ids:
            if not (p.source_validated and p.prediction_id in research_only):
                continue
            up = validated_upgrade_id(p.prediction_id)
            if up in ids:
                continue
            p = replace(p, prediction_id=up)
        ids.add(p.prediction_id)
        if not p.source_validated:
            research_only.add(p.prediction_id)
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
