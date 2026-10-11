"""Pre-trade guardrails. Pure functions: every check returns (ok, reason). Order of checks follows the documented
pipeline: kill switch -> identity -> market open -> price freshness -> min odds -> duplicate -> stake -> exposure."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Signal:
    order_key: str            # deterministic id (e.g. selection_id); duplicates are refused
    event_id: str
    market_id: str
    selection: str
    engine_id: str
    probability: float
    min_odds: float
    stake_gbp: float


@dataclass(frozen=True)
class Quote:
    event_id: str
    market_id: str
    selection: str
    odds: float
    observed_at: datetime
    market_open: bool


@dataclass
class DayState:
    staked_gbp: float = 0.0
    realised_pnl_gbp: float = 0.0
    orders_by_event: dict | None = None
    orders_by_engine: dict | None = None
    submitted_keys: set | None = None
    bankroll_peak_gbp: float = 0.0
    bankroll_now_gbp: float = 0.0

    def __post_init__(self):
        self.orders_by_event = self.orders_by_event or {}
        self.orders_by_engine = self.orders_by_engine or {}
        self.submitted_keys = self.submitted_keys or set()


def check(sig: Signal, q: Quote, st: DayState, cfg: dict, now: datetime, repo: Path) -> tuple[bool, str]:
    lim = cfg["limits"]
    if (repo / cfg["kill_switch_file"]).exists():
        return False, "KILL_SWITCH"
    if (q.event_id, q.market_id, q.selection) != (sig.event_id, sig.market_id, sig.selection):
        return False, "IDENTITY_MISMATCH"
    if not q.market_open:
        return False, "MARKET_CLOSED"
    if (now - q.observed_at).total_seconds() > lim["max_price_age_seconds"]:
        return False, "STALE_PRICE"
    if q.odds < sig.min_odds * (1 - lim["max_slippage_pct"]):
        return False, "BELOW_MIN_ODDS"
    if sig.order_key in st.submitted_keys:
        return False, "DUPLICATE"
    if sig.stake_gbp <= 0 or sig.stake_gbp > lim["max_stake_gbp"]:
        return False, "STAKE_LIMIT"
    if st.staked_gbp + sig.stake_gbp > lim["daily_stake_cap_gbp"]:
        return False, "DAILY_STAKE_CAP"
    if -st.realised_pnl_gbp >= lim["daily_loss_lock_gbp"]:
        return False, "DAILY_LOSS_LOCK"
    if st.orders_by_event.get(sig.event_id, 0) >= lim["max_orders_per_event"]:
        return False, "EVENT_LIMIT"
    eng_cap = lim["max_orders_per_engine_per_day"].get(sig.engine_id, lim["default_max_orders_per_engine_per_day"])
    if st.orders_by_engine.get(sig.engine_id, 0) >= eng_cap:
        return False, "ENGINE_LIMIT"
    if st.bankroll_peak_gbp and (st.bankroll_peak_gbp - st.bankroll_now_gbp) / st.bankroll_peak_gbp >= lim["max_drawdown_pct_of_bankroll"]:
        return False, "DRAWDOWN_STOP"
    return True, "OK"
