"""Immutable paper singles, price snapshots and settlements (V2-6).

- selections.csv   append-only; selection_id = sha256(rule_version|prediction_id)[:16]; frozen P/odds/source/snapshot time.
- price_snapshots.csv append-only record of every evaluated real price (later snapshots never touch a selection).
- settlements.csv  append-only, keyed by selection_id; joins the platform's verified settlement; first settlement wins.
Every append verifies the existing bytes are an unchanged prefix (raises on mutation). No selection can be written
for an event that has started, or from a price observed at/after the start.
"""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime
from pathlib import Path

from prediction_markets_lab.bet_selection_v2.evaluate import PAPER_BET, Candidate
from prediction_markets_lab.bet_selection_v2.prices import ts

SELECTION_FIELDS = ["selection_id", "rule_version", "prediction_id", "sport", "engine_id", "engine_status", "event_key",
                    "event_name", "event_start", "market", "selection", "probability", "fair_odds", "decimal_odds",
                    "source", "is_exchange", "commission", "price_observed_at", "price_age_minutes", "decision_at",
                    "minutes_to_event", "break_even_probability", "net_ev", "value_reference", "decision", "reasons",
                    "stake_units"]
SNAPSHOT_FIELDS = ["snapshot_id", "prediction_id", "source", "decimal_odds", "price_observed_at", "evaluated_at",
                   "minutes_to_event", "net_ev", "decision", "origin"]
SETTLEMENT_FIELDS = ["selection_id", "prediction_id", "status", "result", "settled_at", "settlement_source",
                     "pnl_units", "rule_version"]


def _h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def selection_id(rule_version: str, prediction_id: str) -> str:
    return _h(f"{rule_version}|{prediction_id}")


def snapshot_id(c: Candidate) -> str:
    return _h(f"{c.prediction_id}|{c.source}|{c.decimal_odds}|{c.price_observed_at}")


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _append(path: Path, fields: list[str], key: str, rows: list[dict]) -> int:
    existing = {r[key] for r in read_rows(path)}
    before = path.read_bytes() if path.exists() else b""
    new = []
    for r in rows:
        if r[key] in existing:
            continue
        existing.add(r[key])
        new.append(r)
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        header = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            if header:
                w.writeheader()
            w.writerows(new)
        if not path.read_bytes().startswith(before):
            raise RuntimeError(f"immutability violation in {path}")
    return len(new)


def selection_row(c: Candidate, rule_version: str, stake_units: float, now: datetime) -> dict:
    return {"selection_id": selection_id(rule_version, c.prediction_id), "rule_version": rule_version,
            "prediction_id": c.prediction_id, "sport": c.sport, "engine_id": c.engine_id, "engine_status": c.engine_status,
            "event_key": c.event_key, "event_name": c.event_name, "event_start": c.event_start, "market": c.market,
            "selection": c.selection, "probability": c.probability, "fair_odds": c.fair_odds, "decimal_odds": c.decimal_odds,
            "source": c.source, "is_exchange": c.is_exchange, "commission": c.commission,
            "price_observed_at": c.price_observed_at, "price_age_minutes": c.price_age_minutes, "decision_at": now.isoformat(),
            "minutes_to_event": c.minutes_to_event, "break_even_probability": c.break_even_probability, "net_ev": c.net_ev,
            "value_reference": c.value_reference, "decision": c.decision,
            "reasons": "|".join(c.reasons + ([f"LEDGER_P={c.ledger_probability:.6f}"] if c.ledger_probability is not None else [])),
            "stake_units": stake_units}


def record_selections(path: Path, decided: list[Candidate], rule_version: str, stake_units: float, now: datetime,
                      exclude_prediction_ids: set[str] | None = None) -> int:
    """exclude_prediction_ids: predictions already carrying a valid selection under an earlier rule version
    (no duplicate exposure on one event)."""
    rows = []
    for c in decided:
        if c.decision != PAPER_BET or c.prediction_id in (exclude_prediction_ids or set()):
            continue
        start = ts(c.event_start)
        if now >= start or ts(c.price_observed_at) >= start:   # never a post-start selection (no backfilling)
            continue
        rows.append(selection_row(c, rule_version, stake_units, now))
    return _append(path, SELECTION_FIELDS, "selection_id", rows)


def record_snapshots(path: Path, cands: list[Candidate], decided_ids: dict[str, str]) -> int:
    rows = [{"snapshot_id": snapshot_id(c), "prediction_id": c.prediction_id, "source": c.source,
             "decimal_odds": c.decimal_odds, "price_observed_at": c.price_observed_at, "evaluated_at": c.evaluated_at,
             "minutes_to_event": c.minutes_to_event, "net_ev": c.net_ev, "decision": decided_ids.get(c.prediction_id, ""),
             "origin": c.price_origin} for c in cands if c.decimal_odds is not None]
    return _append(path, SNAPSHOT_FIELDS, "snapshot_id", rows)


def pnl_units(status: str, odds: float, commission: float, stake: float) -> float:
    if status == "WON":
        return stake * (odds - 1.0) * (1.0 - commission)
    if status == "LOST":
        return -stake
    return 0.0


def settle(selections: list[dict], platform_settlements: dict[str, dict], done: set[str], now: datetime) -> list[dict]:
    """Settle from the platform's verified results. Fail closed: anything but correct in {0,1} (or VOID) stays pending."""
    out = []
    for s in selections:
        if s["selection_id"] in done:
            continue
        ps = platform_settlements.get(s["prediction_id"])
        if not ps:
            continue
        st, corr = str(ps.get("settlement_status", "")).upper(), str(ps.get("correct", ""))
        if st == "VOID":
            status = "VOID"
        elif st == "SETTLED" and corr in ("0", "1"):
            status = "WON" if corr == "1" else "LOST"
        else:
            continue  # ambiguous / pending review: never guessed
        comm = float(s["commission"] or 0.0)
        out.append({"selection_id": s["selection_id"], "prediction_id": s["prediction_id"], "status": status,
                    "result": ps.get("result", ""), "settled_at": now.isoformat(),
                    "settlement_source": ps.get("settlement_source", ""),
                    "pnl_units": round(pnl_units(status, float(s["decimal_odds"]), comm, float(s["stake_units"])), 6),
                    "rule_version": s["rule_version"]})
    return out


def append_settlements(path: Path, rows: list[dict]) -> int:
    return _append(path, SETTLEMENT_FIELDS, "selection_id", rows)
