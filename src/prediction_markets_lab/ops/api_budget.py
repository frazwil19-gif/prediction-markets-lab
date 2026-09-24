"""Per-consumer Odds API credit guard (additive; config/api_budget.json).

A consumer may spend `cost` credits only if (a) its own spend this calendar month (UTC), computed from its
credit log's `x_requests_last` column, stays within its monthly cap, and (b) the account's remaining credits
after the call stay at or above max(global reserve, consumer min_remaining). Optional consumers carry higher
floors, so they stop before core ones.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    reason: str
    month_spend: int
    monthly_cap: int
    floor: int


def load_budget(path: Path) -> dict:
    return json.loads(path.read_text())


def month_spend(credit_log: Path, now: datetime) -> int:
    """Sum of credits charged (x_requests_last) in the log for now's UTC calendar month."""
    if not credit_log.exists():
        return 0
    prefix = now.strftime("%Y-%m")
    total = 0
    with credit_log.open(newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("timestamp_utc") or "").startswith(prefix):
                try:
                    total += int(row.get("x_requests_last") or 0)
                except ValueError:
                    continue
    return total


def check(budget: dict, consumer: str, spent: int, remaining: int, cost: int = 1) -> BudgetDecision:
    c = budget["consumers"][consumer]
    cap = int(c["monthly_cap"])
    floor = max(int(budget["global_reserve_remaining"]), int(c.get("min_remaining", 0)))
    if spent + cost > cap:
        return BudgetDecision(False, f"monthly cap {cap} reached ({spent} spent)", spent, cap, floor)
    if remaining - cost < floor:
        return BudgetDecision(False, f"remaining {remaining} would fall below floor {floor}", spent, cap, floor)
    return BudgetDecision(True, "ok", spent, cap, floor)
