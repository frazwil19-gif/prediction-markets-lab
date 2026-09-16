"""Canonical per-match/per-player market observations (Workstream B,
market-observation pipeline, 2026-09-16), per the operator's explicit
"WORKSTREAM B -- REAL MARKET OBSERVATION PIPELINE" prompt following the
real Betfair sample audit
(research/cycles/CYCLE_002_TENNIS/WORKSTREAM_B_SAMPLE_AUDIT_REPORT.md).

This module is deliberately narrow: it defines the observation record
shape, the market-reference-probability calculation, and the mechanical
temporal-safety check every pre-match observation must pass. It does NOT
decide price-time horizons (those are chosen empirically per-run from a
real timestamp-density audit, not frozen here) and it does NOT compute
any betting threshold, EV, or edge -- this is data plumbing only.

Two probabilities are kept explicitly distinct, per the operator's
instruction:
    - raw_ltp_implied_probability = 1 / last_traded_price for ONE runner.
      With only two runners this does not sum to 1 across the market
      (the two runners' implied probabilities can and do differ from a
      clean partition -- Betfair's exchange has no fixed "overround" the
      way a bookmaker's odds do).
    - market_reference_probability = the normalised two-runner
      implied probability, q_a = (1/o_a) / (1/o_a + 1/o_b), computed from
      each runner's own last-known price at or before the same cutoff.
      This is a RESEARCH REFERENCE probability, not a claim that either
      price was actually obtainable/executable by Fraser -- BASIC tier
      has no back/lay ladder, so "executable" cannot be established here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class MarketObservation:
    """One row: one player, in one real match, at one price-time horizon.

    `snapshot_available=False` means no Betfair price update was found at
    or before `observation_timestamp` for this runner -- in that case
    `last_traded_price`, `raw_ltp_implied_probability`, and
    `price_age_seconds` are all None. Missing data is represented
    explicitly, never fabricated or interpolated.
    """

    match_id: str
    event_id: str
    market_id: str
    runner_id: int
    player_name: str
    is_player_a: bool

    scheduled_start: datetime  # the FINAL (post-revision) scheduled start
    observation_timestamp: datetime  # the query cutoff, always < scheduled_start
    horizon_label: str
    requested_horizon_minutes: float
    minutes_to_start: float

    model_probability: float
    model_fair_odds: float

    snapshot_available: bool
    last_traded_price: float | None
    raw_ltp_implied_probability: float | None
    price_age_seconds: float | None

    market_reference_probability: float | None  # None if either runner has no snapshot
    model_market_probability_delta: float | None  # None if market_reference_probability is None

    market_status: str | None
    in_play: bool | None

    outcome_won: bool | None  # filled in for reporting only; never read before this point


def market_reference_probability(price_a: float, price_b: float) -> float:
    """Normalise two runners' own last-traded prices into a two-outcome
    probability that sums to 1, per the operator's explicit instruction
    not to treat `1/price` alone as the market probability (Betfair
    last-traded prices for the two sides of a match need not imply
    probabilities that sum to 1).

    q_a = (1/price_a) / (1/price_a + 1/price_b)

    Raises:
        ValueError: if either price is not a valid decimal odds value
            (must be > 1.0 -- a price of exactly 1.0 or below is not a
            real back price and signals a parsing/data problem upstream,
            not a normal input to silently clip).
    """
    if price_a <= 1.0 or price_b <= 1.0:
        raise ValueError(
            f"decimal odds must be > 1.0 to imply a valid probability, got price_a={price_a!r}, price_b={price_b!r}"
        )
    implied_a = 1.0 / price_a
    implied_b = 1.0 / price_b
    return implied_a / (implied_a + implied_b)


def latest_price_at_or_before(
    price_series: list[tuple[datetime, float]], cutoff: datetime
) -> tuple[datetime, float] | None:
    """The most recent (timestamp, last_traded_price) pair with
    timestamp <= cutoff, or None if no such point exists.

    Never extrapolates forward and never returns a post-cutoff price --
    this is the one function responsible for temporal safety on the
    price-lookup side; `build_pre_match_observation` additionally asserts
    the cutoff itself precedes the match's scheduled start.
    """
    eligible = [(ts, price) for ts, price in price_series if ts <= cutoff]
    if not eligible:
        return None
    return max(eligible, key=lambda item: item[0])


def build_pre_match_observation(
    *,
    match_id: str,
    event_id: str,
    market_id: str,
    runner_id: int,
    player_name: str,
    is_player_a: bool,
    scheduled_start: datetime,
    horizon_label: str,
    requested_horizon_minutes: float,
    model_probability: float,
    own_price_series: list[tuple[datetime, float]],
    other_player_price_series: list[tuple[datetime, float]],
    market_status_at_cutoff: str | None,
    in_play_at_cutoff: bool | None,
    outcome_won: bool | None,
) -> MarketObservation:
    """Build one PRE-MATCH MarketObservation, at
    `scheduled_start - requested_horizon_minutes`.

    Raises:
        ValueError: if requested_horizon_minutes <= 0 (a pre-match
            observation must precede the match; a zero or negative
            horizon is a caller bug, not a valid pre-match query).
        AssertionError: mechanical proof that observation_timestamp is
            strictly before scheduled_start -- this can only fail if the
            horizon/timestamp arithmetic above is wrong, since a positive
            horizon subtracted from scheduled_start is definitionally
            earlier, but the assertion is kept as the explicit, checkable
            proof the operator asked for rather than trusting the
            arithmetic silently.
    """
    if requested_horizon_minutes <= 0:
        raise ValueError(
            f"requested_horizon_minutes must be > 0 for a pre-match observation, got {requested_horizon_minutes!r}"
        )

    observation_timestamp = scheduled_start - timedelta(minutes=requested_horizon_minutes)
    assert observation_timestamp < scheduled_start, (
        "temporal-safety violation: a pre-match observation_timestamp must be "
        "strictly before the match's final scheduled_start"
    )

    minutes_to_start = (scheduled_start - observation_timestamp).total_seconds() / 60.0

    own_point = latest_price_at_or_before(own_price_series, observation_timestamp)
    other_point = latest_price_at_or_before(other_player_price_series, observation_timestamp)

    if own_point is None:
        last_traded_price = None
        raw_ltp_implied_probability = None
        price_age_seconds = None
        snapshot_available = False
    else:
        own_ts, own_price = own_point
        last_traded_price = own_price
        raw_ltp_implied_probability = 1.0 / own_price
        price_age_seconds = (observation_timestamp - own_ts).total_seconds()
        snapshot_available = True

    market_reference_probability_value: float | None = None
    model_market_probability_delta: float | None = None
    if own_point is not None and other_point is not None:
        _, own_price = own_point
        _, other_price = other_point
        market_reference_probability_value = market_reference_probability(own_price, other_price)
        model_market_probability_delta = model_probability - market_reference_probability_value

    return MarketObservation(
        match_id=match_id,
        event_id=event_id,
        market_id=market_id,
        runner_id=runner_id,
        player_name=player_name,
        is_player_a=is_player_a,
        scheduled_start=scheduled_start,
        observation_timestamp=observation_timestamp,
        horizon_label=horizon_label,
        requested_horizon_minutes=requested_horizon_minutes,
        minutes_to_start=minutes_to_start,
        model_probability=model_probability,
        model_fair_odds=1.0 / model_probability,
        snapshot_available=snapshot_available,
        last_traded_price=last_traded_price,
        raw_ltp_implied_probability=raw_ltp_implied_probability,
        price_age_seconds=price_age_seconds,
        market_reference_probability=market_reference_probability_value,
        model_market_probability_delta=model_market_probability_delta,
        market_status=market_status_at_cutoff,
        in_play=in_play_at_cutoff,
        outcome_won=outcome_won,
    )
