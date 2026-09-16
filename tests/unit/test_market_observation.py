from datetime import datetime, timezone

import pytest

from prediction_markets_lab.research.market_observation import (
    build_pre_match_observation,
    latest_price_at_or_before,
    market_reference_probability,
)


def _dt(hour, minute=0):
    return datetime(2026, 1, 6, hour, minute, tzinfo=timezone.utc)


# --- market_reference_probability ---

def test_market_reference_probability_normalises_two_prices():
    # implied: 1/1.5 = 0.6667, 1/3.0 = 0.3333, sum = 1.0 exactly here
    q = market_reference_probability(1.5, 3.0)
    assert q == pytest.approx(2.0 / 3.0)


def test_market_reference_probability_does_not_assume_prices_already_sum_to_one():
    # implied: 1/1.5=0.6667, 1/2.5=0.4, sum=1.0667 -- overround-like case,
    # confirming this function actually normalises rather than just
    # returning 1/price_a unchanged: 0.6667/1.0667 = 0.625, not 0.6667.
    q = market_reference_probability(1.5, 2.5)
    assert q == pytest.approx(0.625, abs=1e-3)
    assert q != pytest.approx(1.0 / 1.5)


def test_market_reference_probability_rejects_invalid_odds():
    with pytest.raises(ValueError):
        market_reference_probability(1.0, 2.0)
    with pytest.raises(ValueError):
        market_reference_probability(2.0, 0.5)


# --- latest_price_at_or_before ---

def test_latest_price_at_or_before_picks_most_recent_eligible_point():
    series = [(_dt(10), 2.0), (_dt(12), 1.8), (_dt(14), 1.5)]
    assert latest_price_at_or_before(series, _dt(13)) == (_dt(12), 1.8)


def test_latest_price_at_or_before_never_returns_a_future_price():
    series = [(_dt(10), 2.0), (_dt(20), 1.1)]
    # cutoff strictly before the only-later point -- must not leak it
    result = latest_price_at_or_before(series, _dt(11))
    assert result == (_dt(10), 2.0)


def test_latest_price_at_or_before_none_when_nothing_eligible():
    series = [(_dt(10), 2.0)]
    assert latest_price_at_or_before(series, _dt(9)) is None


# --- build_pre_match_observation: temporal safety ---

def test_rejects_non_positive_horizon():
    with pytest.raises(ValueError):
        build_pre_match_observation(
            match_id="m1", event_id="e1", market_id="1.1", runner_id=1,
            player_name="Player One", is_player_a=True,
            scheduled_start=_dt(14), horizon_label="bad", requested_horizon_minutes=0,
            model_probability=0.6, own_price_series=[], other_player_price_series=[],
            market_status_at_cutoff="OPEN", in_play_at_cutoff=False, outcome_won=None,
        )


def test_observation_timestamp_is_always_strictly_before_scheduled_start():
    obs = build_pre_match_observation(
        match_id="m1", event_id="e1", market_id="1.1", runner_id=1,
        player_name="Player One", is_player_a=True,
        scheduled_start=_dt(14), horizon_label="1h", requested_horizon_minutes=60,
        model_probability=0.6, own_price_series=[(_dt(10), 2.0)],
        other_player_price_series=[(_dt(10), 2.0)],
        market_status_at_cutoff="OPEN", in_play_at_cutoff=False, outcome_won=None,
    )
    assert obs.observation_timestamp < obs.scheduled_start
    assert obs.observation_timestamp == _dt(13)
    assert obs.minutes_to_start == pytest.approx(60.0)


def test_post_start_prices_never_leak_into_a_pre_match_observation():
    """A price update recorded AFTER the observation cutoff (even if still
    before the match's real start) must never be used -- this is the
    mechanical proof of no post-cutoff leakage."""
    own_series = [(_dt(10), 2.0), (_dt(13, 30), 1.2)]  # 13:30 is after our 13:00 cutoff
    obs = build_pre_match_observation(
        match_id="m1", event_id="e1", market_id="1.1", runner_id=1,
        player_name="Player One", is_player_a=True,
        scheduled_start=_dt(14), horizon_label="1h", requested_horizon_minutes=60,
        model_probability=0.6, own_price_series=own_series,
        other_player_price_series=[(_dt(10), 2.0)],
        market_status_at_cutoff="OPEN", in_play_at_cutoff=False, outcome_won=None,
    )
    assert obs.last_traded_price == 2.0  # NOT 1.2 -- that update is post-cutoff


def test_missing_snapshot_is_represented_explicitly_not_fabricated():
    obs = build_pre_match_observation(
        match_id="m1", event_id="e1", market_id="1.1", runner_id=1,
        player_name="Player One", is_player_a=True,
        scheduled_start=_dt(14), horizon_label="24h", requested_horizon_minutes=24 * 60,
        model_probability=0.6, own_price_series=[], other_player_price_series=[],
        market_status_at_cutoff=None, in_play_at_cutoff=None, outcome_won=None,
    )
    assert obs.snapshot_available is False
    assert obs.last_traded_price is None
    assert obs.raw_ltp_implied_probability is None
    assert obs.price_age_seconds is None
    assert obs.market_reference_probability is None
    assert obs.model_market_probability_delta is None


def test_market_reference_probability_is_none_when_only_one_side_has_a_snapshot():
    obs = build_pre_match_observation(
        match_id="m1", event_id="e1", market_id="1.1", runner_id=1,
        player_name="Player One", is_player_a=True,
        scheduled_start=_dt(14), horizon_label="1h", requested_horizon_minutes=60,
        model_probability=0.6, own_price_series=[(_dt(10), 2.0)],
        other_player_price_series=[],  # other side never traded before cutoff
        market_status_at_cutoff="OPEN", in_play_at_cutoff=False, outcome_won=None,
    )
    assert obs.snapshot_available is True
    assert obs.last_traded_price == 2.0
    assert obs.market_reference_probability is None
    assert obs.model_market_probability_delta is None


def test_price_age_seconds_reflects_staleness():
    obs = build_pre_match_observation(
        match_id="m1", event_id="e1", market_id="1.1", runner_id=1,
        player_name="Player One", is_player_a=True,
        scheduled_start=_dt(14), horizon_label="1h", requested_horizon_minutes=60,
        model_probability=0.6, own_price_series=[(_dt(9), 2.0)],  # 4 hours stale at the 13:00 cutoff
        other_player_price_series=[(_dt(9), 2.0)],
        market_status_at_cutoff="OPEN", in_play_at_cutoff=False, outcome_won=None,
    )
    assert obs.price_age_seconds == pytest.approx(4 * 3600.0)


def test_full_observation_computes_model_market_delta_correctly():
    obs = build_pre_match_observation(
        match_id="m1", event_id="e1", market_id="1.1", runner_id=1,
        player_name="Player One", is_player_a=True,
        scheduled_start=_dt(14), horizon_label="1h", requested_horizon_minutes=60,
        model_probability=0.70,
        own_price_series=[(_dt(12), 1.5)], other_player_price_series=[(_dt(12), 3.0)],
        market_status_at_cutoff="OPEN", in_play_at_cutoff=False, outcome_won=True,
    )
    expected_market_ref = market_reference_probability(1.5, 3.0)
    assert obs.market_reference_probability == pytest.approx(expected_market_ref)
    assert obs.model_market_probability_delta == pytest.approx(0.70 - expected_market_ref)
    assert obs.model_fair_odds == pytest.approx(1.0 / 0.70)
    assert obs.outcome_won is True
