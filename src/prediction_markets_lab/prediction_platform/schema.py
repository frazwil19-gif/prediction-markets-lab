"""Canonical cross-sport prediction contract (V2-5)."""
from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass, fields
from datetime import datetime

from prediction_markets_lab.research.probability_reliability import V2_BANDS

THRESHOLDS: tuple[float, ...] = (0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
HIGH_P = 0.80


@dataclass(frozen=True)
class Prediction:
    prediction_id: str
    engine_id: str
    engine_version: str
    sport: str
    competition: str
    event_id: str | None          # provider id when one exists
    event_key: str                # deterministic identity used by this platform
    event_name: str
    event_start: str              # ISO UTC
    market: str
    selection: str
    estimated_probability: float
    fair_odds: float
    probability_band: str
    probability_source: str
    historical_support: str
    engine_status: str
    data_quality: str
    current_context_status: str
    configured_scan_time: str | None
    actual_workflow_start: str | None
    prediction_timestamp: str
    minutes_to_event: float
    live_price: float | None
    live_price_source: str | None
    paper_status: str             # PAPER / RESEARCH_ONLY_SOURCE
    prediction_valid: bool
    single_eligible: bool         # pre-filter only; the Money Card remains the authority
    single_ineligible_reason: str | None
    multi_research_eligible: bool
    snapshot_rule: str
    origin: str
    origin_prediction_id: str | None


PREDICTION_FIELDS: list[str] = [f.name for f in fields(Prediction)]
SETTLEMENT_FIELDS: list[str] = ["prediction_id", "settlement_status", "result", "correct", "settlement_timestamp",
                                "settlement_source", "mapping_status"]
SETTLEMENT_STATES: tuple[str, ...] = ("SETTLED", "VOID")


def band_of(p: float) -> str:
    for lo, hi, lab in V2_BANDS:
        if lo <= p < hi:
            return lab
    return "<50%"


def fair_odds(p: float) -> float:
    if not 0.0 < p < 1.0:
        raise ValueError(f"probability out of bounds: {p}")
    return 1.0 / p


def make_prediction_id(engine_id: str, version: str, event_key: str, market: str, selection: str) -> str:
    """Deterministic: identical event/market/selection/engine@version always gives the same id (retry-safe)."""
    return hashlib.sha256(f"{engine_id}@{version}|{event_key}|{market}|{selection}".encode()).hexdigest()[:16]


def validate(p: Prediction) -> list[str]:
    errs = []
    if not (isinstance(p.estimated_probability, float) and 0.0 < p.estimated_probability < 1.0):
        errs.append("probability out of (0,1)")
    elif not math.isclose(p.fair_odds, 1.0 / p.estimated_probability, rel_tol=1e-9):
        errs.append("fair_odds != 1/p")
    elif p.probability_band != band_of(p.estimated_probability):
        errs.append("band mismatch")
    if p.minutes_to_event <= 0:
        errs.append("prediction not before event start")
    for ts in (p.event_start, p.prediction_timestamp):
        try:
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            errs.append(f"bad timestamp {ts!r}")
    if not p.prediction_id or not p.engine_id or not p.engine_version:
        errs.append("missing identity")
    return errs


def to_row(p: Prediction) -> dict:
    d = asdict(p)
    return {k: ("" if v is None else v) for k, v in d.items()}
