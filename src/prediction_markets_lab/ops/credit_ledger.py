"""Shared Odds API credit ledger (V2-14, Credit Plan A accounting).

Every paid call and every call SKIPPED by a fixtures-first gate is appended to status/credit_ledger.csv, so actual
spend and gate savings can be compared with the projections in research/platform_v2/v2_13_october/CREDIT_AUDIT.md.
Append-only; never affects a decision.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ["timestamp_utc", "consumer", "call", "outcome", "credits_charged", "credits_saved_estimate",
          "x_requests_used", "x_requests_remaining", "reason"]
PAID, SKIPPED_GATE, SKIPPED_FLOOR = "PAID", "SKIPPED_FIXTURE_GATE", "SKIPPED_CREDIT_FLOOR"


def append(path: Path, consumer: str, call: str, outcome: str, credits_charged: int | None,
           credits_saved_estimate: int, headers: dict | None = None, reason: str = "",
           now: datetime | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    h = headers or {}
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"timestamp_utc": (now or datetime.now(timezone.utc)).isoformat(), "consumer": consumer, "call": call,
                    "outcome": outcome, "credits_charged": "" if credits_charged is None else credits_charged,
                    "credits_saved_estimate": credits_saved_estimate, "x_requests_used": h.get("x-requests-used", ""),
                    "x_requests_remaining": h.get("x-requests-remaining", ""), "reason": reason})


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
