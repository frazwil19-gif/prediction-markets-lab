"""Candidate evaluation and reason-coded decisions (V2-6, rule_version from config).

An accurate prediction is not automatically an attractive bet: P and the price are judged separately, and every
failed gate is recorded (not just the first).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

from prediction_markets_lab.bet_selection_v2.prices import PriceSnapshot, ts
from prediction_markets_lab.ev.expected_value import break_even_probability, net_expected_value

CONFIG_PATH = Path(__file__).resolve().parents[3] / "config/bet_selection_v2.yaml"

PAPER_BET, WATCH, MULTI, REJECT = "PAPER_BET", "WATCH", "MULTI_RESEARCH_ELIGIBLE", "REJECT"
DECISIONS = (PAPER_BET, MULTI, WATCH, REJECT)


def load_config(path: Path = CONFIG_PATH) -> dict:
    cfg = yaml.safe_load(path.read_text())
    if cfg.get("real_money_enabled"):
        raise ValueError("real_money_enabled must stay false in the V2-6 paper layer")
    if cfg.get("multi", {}).get("same_event_allowed"):
        raise ValueError("same-event multis must stay disabled")
    return cfg


@dataclass
class Candidate:
    prediction_id: str
    sport: str
    engine_id: str
    engine_status: str
    event_key: str
    event_name: str
    event_start: str
    market: str
    selection: str
    probability: float           # probability USED for the decision (same snapshot as the price)
    fair_odds: float
    prediction_valid: bool
    evaluated_at: str
    minutes_to_event: float
    source: str = ""
    is_exchange: bool = False
    commission: float | None = None
    decimal_odds: float | None = None
    price_observed_at: str = ""
    price_age_minutes: float | None = None
    break_even_probability: float | None = None
    gross_ev: float | None = None
    net_ev: float | None = None
    value_reference: str = ""
    price_origin: str = ""
    ledger_probability: float | None = None   # frozen first-snapshot P from the prediction ledger (calibration record)
    decision: str = REJECT
    reasons: list[str] = field(default_factory=list)

    def row(self) -> dict:
        d = asdict(self)
        d["reasons"] = "|".join(self.reasons)
        return d


def commission_for(source: str, cfg: dict) -> tuple[bool, float | None]:
    """(is_exchange, commission). Unknown exchange commission -> None (the candidate is rejected, never assumed 0)."""
    s = source.lower()
    exch = s in [k.lower() for k in cfg["exchange_keys"]]
    if not exch:
        return False, 0.0
    return True, cfg["commission"].get(s)


def value_reference(sport: str, source: str) -> str:
    if sport == "tennis":
        return "SELF_SOURCE_EXCHANGE (EV<=0 by construction)" if source == "betfair_ex_uk" else "INDEPENDENT_EXCHANGE_MID"
    return "INCLUSIVE_CONSENSUS"


def _price_candidate(pred: dict, snap: PriceSnapshot | None, cfg: dict, now: datetime) -> Candidate:
    start = ts(pred["event_start"])
    p = float(pred["estimated_probability"])
    c = Candidate(prediction_id=pred["prediction_id"], sport=pred["sport"], engine_id=pred["engine_id"],
                  engine_status=pred["engine_status"], event_key=pred["event_key"], event_name=pred["event_name"],
                  event_start=pred["event_start"], market=pred["market"], selection=pred["selection"], probability=p,
                  fair_odds=1.0 / p, prediction_valid=str(pred.get("prediction_valid")) == "True",
                  evaluated_at=now.isoformat(), minutes_to_event=round((start - now).total_seconds() / 60, 1))
    if not c.prediction_valid:
        c.reasons.append("PREDICTION_NOT_VALID")
    if now >= start:
        c.reasons.append("EVENT_STARTED")
    if snap is None:
        c.reasons.append("NO_EXECUTABLE_PRICE")
        return c
    c.ledger_probability = p
    if snap.p_same_snapshot is None:
        c.reasons.append("PROBABILITY_NOT_SAME_SNAPSHOT")
    else:
        p = float(snap.p_same_snapshot)
        c.probability, c.fair_odds = p, 1.0 / p
    exch, comm = commission_for(snap.source, cfg)
    c.source, c.is_exchange, c.commission, c.decimal_odds = snap.source, exch, comm, snap.decimal_odds
    c.price_observed_at, c.price_origin = snap.observed_at.isoformat(), snap.origin
    c.price_age_minutes = round((now - snap.quote_at).total_seconds() / 60, 1)
    c.value_reference = value_reference(c.sport, snap.source)
    if snap.observed_at >= start:
        c.reasons.append("PRICE_AT_OR_AFTER_START")
    if c.price_age_minutes > cfg["decision_gates"]["paper_bet"]["max_price_age_minutes"]:
        c.reasons.append("PRICE_STALE")
    if comm is None:
        c.reasons.append("COMMISSION_UNKNOWN")
        return c
    if not 0 < p < 1:
        c.reasons.append("PROBABILITY_OUT_OF_RANGE")
        return c
    c.break_even_probability = break_even_probability(snap.decimal_odds, comm)
    c.gross_ev = p * snap.decimal_odds - 1.0
    c.net_ev = net_expected_value(p, snap.decimal_odds, comm)
    return c


HARD = {"PROBABILITY_NOT_SAME_SNAPSHOT", "PREDICTION_NOT_VALID", "EVENT_STARTED", "NO_EXECUTABLE_PRICE", "PRICE_AT_OR_AFTER_START", "PRICE_STALE",
        "COMMISSION_UNKNOWN", "PROBABILITY_OUT_OF_RANGE", "NET_EV_NOT_POSITIVE", "P_BELOW_FLOOR", "ENGINE_STATUS_INELIGIBLE"}


def decide(c: Candidate, cfg: dict) -> Candidate:
    g = cfg["decision_gates"]
    pb, w, m = g["paper_bet"], g["watch"], g["multi_research"]
    if c.net_ev is not None and c.net_ev <= w["min_net_ev_exclusive"]:
        c.reasons.append("NET_EV_NOT_POSITIVE")
    if c.probability < pb["min_probability"]:
        c.reasons.append("P_BELOW_FLOOR")
    if c.engine_status not in w["engine_statuses"]:
        c.reasons.append("ENGINE_STATUS_INELIGIBLE")
    if HARD & set(c.reasons):
        c.decision = REJECT
        return c
    soft = []
    if c.net_ev < pb["min_net_ev"]:
        soft.append("NET_EV_BELOW_PAPER_GATE")
    if c.decimal_odds < pb["min_decimal_odds"]:
        soft.append("ODDS_BELOW_PAYOUT_FLOOR")
    if c.minutes_to_event > pb["max_hours_to_event"] * 60:
        soft.append("OUTSIDE_EVENT_HORIZON")
    if c.engine_status not in pb["engine_statuses"]:
        soft.append("ENGINE_NOT_VALIDATED_FOR_PAPER_BET")
    c.reasons += soft
    if not soft:
        c.decision = PAPER_BET
        c.reasons.append("ALL_PAPER_GATES_PASSED")
    elif c.probability >= m["min_probability"] and c.engine_status in m["engine_statuses"]:
        c.decision = MULTI
    else:
        c.decision = WATCH
    return c


def evaluate_prediction(pred: dict, snaps: list[PriceSnapshot], cfg: dict, now: datetime) -> tuple[Candidate, list[Candidate]]:
    """Evaluate every executable snapshot; the decision uses the best fresh, computable net-EV candidate.
    Returns (decided candidate, all evaluated candidates)."""
    cands = [_price_candidate(pred, s, cfg, now) for s in snaps] or [_price_candidate(pred, None, cfg, now)]
    usable = [c for c in cands if c.net_ev is not None
              and not ({"PRICE_STALE", "PRICE_AT_OR_AFTER_START", "PROBABILITY_NOT_SAME_SNAPSHOT"} & set(c.reasons))]
    if usable:   # bsv2-2: only the LATEST snapshot's quotes (quotes that coexist); never the best across times
        latest = max(c.price_observed_at for c in usable)
        usable = [c for c in usable if c.price_observed_at == latest]
    if usable:
        best = max(usable, key=lambda c: (c.net_ev, c.price_observed_at))
    else:
        best = max(cands, key=lambda c: (c.net_ev is not None, c.price_observed_at))
    best = decide(best, cfg)
    if best.decision == REJECT and "NET_EV_NOT_POSITIVE" in best.reasons:
        hard_other = HARD - {"NET_EV_NOT_POSITIVE"}
        m = cfg["decision_gates"]["multi_research"]
        if not (hard_other & set(best.reasons)) and best.probability >= m["min_probability"] \
                and best.engine_status in m["engine_statuses"]:
            best.decision = MULTI  # strong prediction, poor price: kept for multi research only
    return best, cands
