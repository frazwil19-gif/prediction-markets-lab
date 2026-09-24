"""Append-only CSV ledgers with an immutability guard (existing bytes must be unchanged after every write)."""
from __future__ import annotations

import csv
from pathlib import Path


class LedgerIntegrityError(RuntimeError):
    pass


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_unique(path: Path, rows: list[dict], fieldnames: list[str], key: str = "prediction_id") -> tuple[int, int]:
    """Append rows whose key is new; first write wins. Returns (added, skipped). Never rewrites existing rows."""
    before = path.read_bytes() if path.exists() else b""
    if before:
        with path.open(newline="", encoding="utf-8") as f:
            header = next(csv.reader(f))
        if header != fieldnames:
            raise LedgerIntegrityError(f"{path}: header differs from the canonical schema")
    seen = {r[key] for r in read_rows(path)}
    new = []
    for r in rows:
        if r[key] in seen:
            continue
        seen.add(r[key])
        new.append(r)
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="raise")
            if not before:
                w.writeheader()
            w.writerows(new)
        if path.read_bytes()[: len(before)] != before:
            raise LedgerIntegrityError(f"{path}: existing rows changed during append")
    return len(new), len(rows) - len(new)
