"""Odds API tennis parsing + frozen probability engine (source hierarchy) for the
tennis Prediction Board. Pure functions; no I/O."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from prediction_markets_lab.research import margin_removal_methods as mrm

ENGINE_VERSION = "1"
EXCHANGE_KEY = "betfair_ex_uk"
MAX_QUOTE_AGE = timedelta(hours=6)
MIN_CONSENSUS_BOOKS = 3
PROBABILITY_BANDS = (
    (0.50, 0.55, "50-54.9%"), (0.55, 0.60, "55-59.9%"), (0.60, 0.65, "60-64.9%"), (0.65, 0.70, "65-69.9%"),
    (0.70, 0.75, "70-74.9%"), (0.75, 0.80, "75-79.9%"), (0.80, 0.85, "80-84.9%"), (0.85, 0.90, "85-89.9%"),
    (0.90, 0.95, "90-94.9%"), (0.95, 1.0000001, "95%+"),
)
VALID_SOURCES = ("EXCHANGE_MID", "EXCHANGE_BACK")
RESEARCH_ONLY_SOURCES = ("BOOKMAKER_CONSENSUS",)


def tour_of(sport_key: str) -> str | None:
    if sport_key.startswith("tennis_atp_"):
        return "ATP"
    if sport_key.startswith("tennis_wta_"):
        return "WTA"
    return None


def engine_id_for(tour: str) -> str:
    return {"ATP": "atp_match_winner.betfair_market", "WTA": "wta_match_winner.betfair_market"}[tour]


def band_of(p: float) -> str:
    for lo, hi, lab in PROBABILITY_BANDS:
        if lo <= p < hi:
            return lab
    return "<50%"


def _parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class TennisEventQuotes:
    event_id: str
    sport_key: str
    sport_title: str
    tour: str
    commence_time: datetime
    player_a: str  # provider home_team (orientation fixed by the provider, never by outcome)
    player_b: str
    exchange_back: dict[str, float] = field(default_factory=dict)
    exchange_lay: dict[str, float] = field(default_factory=dict)
    exchange_last_update: datetime | None = None
    bookmaker_h2h: dict[str, tuple[float, float]] = field(default_factory=dict)  # book -> (odds a, odds b)
    bookmaker_last_update: dict[str, datetime] = field(default_factory=dict)


def parse_tennis_odds(raw: Any, sport_key: str) -> list[TennisEventQuotes]:
    """Parse a /v4/sports/{tennis key}/odds response. Events with missing players or
    unparseable times are skipped (never guessed)."""
    tour = tour_of(sport_key)
    if tour is None:
        raise ValueError(f"not a tennis sport key: {sport_key!r}")
    if not isinstance(raw, list):
        raise ValueError("odds response must be a list of events")
    out = []
    for ev in raw:
        try:
            a, b = ev["home_team"], ev["away_team"]
            ct = _parse_ts(ev["commence_time"])
        except (KeyError, TypeError, ValueError):
            continue
        if not a or not b or a == b or ct is None:
            continue
        q = TennisEventQuotes(event_id=str(ev.get("id")), sport_key=sport_key, sport_title=ev.get("sport_title", ""),
                              tour=tour, commence_time=ct, player_a=a, player_b=b)
        for bk in ev.get("bookmakers", []) or []:
            key = bk.get("key")
            for mk in bk.get("markets", []) or []:
                prices = {o.get("name"): o.get("price") for o in mk.get("outcomes", []) or []}
                if set(prices) != {a, b} or any((not isinstance(v, (int, float))) or v <= 1.0 for v in prices.values()):
                    continue
                lu = _parse_ts(mk.get("last_update") or bk.get("last_update"))
                if key == EXCHANGE_KEY and mk.get("key") == "h2h":
                    q.exchange_back = {"a": float(prices[a]), "b": float(prices[b])}
                    q.exchange_last_update = lu
                elif key == EXCHANGE_KEY and mk.get("key") == "h2h_lay":
                    q.exchange_lay = {"a": float(prices[a]), "b": float(prices[b])}
                elif mk.get("key") == "h2h" and key != EXCHANGE_KEY:
                    q.bookmaker_h2h[key] = (float(prices[a]), float(prices[b]))
                    if lu:
                        q.bookmaker_last_update[key] = lu
        out.append(q)
    return out


@dataclass(frozen=True)
class TennisPrediction:
    prediction_id: str
    engine_id: str
    engine_version: str
    tour: str
    sport_key: str
    tournament: str
    event_id: str
    player_a: str
    player_b: str
    commence_time: str
    prediction_timestamp: str
    source: str  # EXCHANGE_MID / EXCHANGE_BACK / BOOKMAKER_CONSENSUS
    source_validated: bool
    raw_prices: str  # compact provenance string
    p_a: float
    p_b: float
    predicted_winner: str
    predicted_probability: float
    probability_band: str
    multi_research_eligible: bool
    status: str = "PREDICTED"


def make_prediction_id(engine_id: str, version: str, event_id: str) -> str:
    return hashlib.sha256(f"{engine_id}@{version}|{event_id}".encode()).hexdigest()[:16]


def predict(q: TennisEventQuotes, now: datetime) -> TennisPrediction | None:
    """Apply the frozen source hierarchy. Returns None (DATA_INVALID) when no
    eligible source exists or the event has already started."""
    if now >= q.commence_time:
        return None
    fresh_ex = q.exchange_last_update is None or (now - q.exchange_last_update) <= MAX_QUOTE_AGE
    source, pa, raw = None, None, ""
    if q.exchange_back and q.exchange_lay and fresh_ex:
        mid_a = (q.exchange_back["a"] + q.exchange_lay["a"]) / 2
        mid_b = (q.exchange_back["b"] + q.exchange_lay["b"]) / 2
        pa = mrm.multiplicative([mid_a, mid_b])[0]
        source = "EXCHANGE_MID"
        raw = f"ex_back={q.exchange_back['a']}/{q.exchange_back['b']};ex_lay={q.exchange_lay['a']}/{q.exchange_lay['b']}"
    elif q.exchange_back and fresh_ex:
        pa = mrm.multiplicative([q.exchange_back["a"], q.exchange_back["b"]])[0]
        source = "EXCHANGE_BACK"
        raw = f"ex_back={q.exchange_back['a']}/{q.exchange_back['b']}"
    else:
        books = {k: v for k, v in q.bookmaker_h2h.items()
                 if k not in q.bookmaker_last_update or (now - q.bookmaker_last_update[k]) <= MAX_QUOTE_AGE}
        if len(books) >= MIN_CONSENSUS_BOOKS:
            pa = mrm.consensus([list(v) for v in books.values()], "multiplicative")[0]
            source = "BOOKMAKER_CONSENSUS"
            raw = ";".join(f"{k}={v[0]}/{v[1]}" for k, v in sorted(books.items()))
    if source is None:
        return None
    pb = 1.0 - pa
    winner, pw = (q.player_a, pa) if pa >= pb else (q.player_b, pb)
    validated = source in VALID_SOURCES
    eid = engine_id_for(q.tour)
    return TennisPrediction(
        prediction_id=make_prediction_id(eid, ENGINE_VERSION, q.event_id), engine_id=eid, engine_version=ENGINE_VERSION,
        tour=q.tour, sport_key=q.sport_key, tournament=q.sport_title, event_id=q.event_id,
        player_a=q.player_a, player_b=q.player_b, commence_time=q.commence_time.isoformat(),
        prediction_timestamp=now.isoformat(), source=source, source_validated=validated, raw_prices=raw,
        p_a=round(pa, 6), p_b=round(pb, 6), predicted_winner=winner, predicted_probability=round(pw, 6),
        probability_band=band_of(pw),
        # research flag only (no multis are built): validated source AND at least 80%
        multi_research_eligible=bool(validated and pw >= 0.80),
    )
