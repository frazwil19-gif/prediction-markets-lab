"""Brokers. PaperBroker simulates a full fill at the quoted price. LIVE is refused by construction."""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from prediction_markets_lab.execution.guards import DayState, Quote, Signal, check


class LiveExecutionDisabled(RuntimeError):
    """Raised for any attempt to execute with real money. There is no live adapter in this codebase (2026-10-11)."""


@dataclass
class Fill:
    order_key: str
    status: str          # FILLED | REJECTED
    reason: str
    odds: float | None
    stake_gbp: float
    environment: str
    at: str


class PaperBroker:
    environment = "PAPER"

    def submit(self, sig: Signal, q: Quote, now: datetime) -> Fill:
        return Fill(sig.order_key, "FILLED", "SIMULATED_FULL_FILL", q.odds, sig.stake_gbp, self.environment, now.isoformat())


def broker_for(cfg: dict):
    if cfg.get("environment") != "PAPER":
        raise LiveExecutionDisabled("LIVE environment requested but no live broker exists; see AUTOMATION_ARCHITECTURE.md gate")
    return PaperBroker()


AUDIT_FIELDS = ["order_key", "status", "reason", "odds", "stake_gbp", "environment", "at"]


def execute(sig: Signal, q: Quote, st: DayState, cfg: dict, now: datetime, repo: Path, audit: Path) -> Fill:
    """Pipeline: guards -> broker -> state update -> audit log. Every attempt (filled or rejected) is logged."""
    broker = broker_for(cfg)
    ok, reason = check(sig, q, st, cfg, now, repo)
    fill = broker.submit(sig, q, now) if ok else Fill(sig.order_key, "REJECTED", reason, None, 0.0, broker.environment, now.isoformat())
    if fill.status == "FILLED":
        st.submitted_keys.add(sig.order_key)
        st.staked_gbp += sig.stake_gbp
        st.orders_by_event[sig.event_id] = st.orders_by_event.get(sig.event_id, 0) + 1
        st.orders_by_engine[sig.engine_id] = st.orders_by_engine.get(sig.engine_id, 0) + 1
    audit.parent.mkdir(parents=True, exist_ok=True)
    new = not audit.exists()
    with audit.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=AUDIT_FIELDS)
        if new:
            w.writeheader()
        w.writerow(asdict(fill))
    return fill
