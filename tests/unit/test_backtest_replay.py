from datetime import date

import pytest

from prediction_markets_lab.backtesting import replay as replay_module
from prediction_markets_lab.backtesting.frozen_strategy import load_and_freeze_current_strategy
from prediction_markets_lab.backtesting.historical_loader import HistoricalMatch
from prediction_markets_lab.validation.leakage_checks import DatedRecord, check_chronological_order


def _match(match_id, match_date, result, home_odds=2.0, draw_odds=3.5, away_odds=4.0, kickoff_hour=15):
    return HistoricalMatch(
        match_id=match_id,
        competition_code="E0",
        competition_name="Premier League",
        season="2020_21",
        match_date=match_date,
        home_team_raw="Home",
        away_team_raw="Away",
        full_time_result=result,
        bookmaker_odds={
            "B365": {"home": home_odds, "draw": draw_odds, "away": away_odds},
            "PS": {"home": home_odds * 1.02, "draw": draw_odds * 0.98, "away": away_odds * 1.01},
            "WH": {"home": home_odds * 0.99, "draw": draw_odds * 1.01, "away": away_odds * 0.98},
            "BW": {"home": home_odds * 1.01, "draw": draw_odds * 0.99, "away": away_odds * 1.02},
        },
        kickoff_iso=f"{match_date}T{kickoff_hour:02d}:00:00+00:00",
        kickoff_join_failure_reason=None,
    )


@pytest.fixture(scope="module")
def strategy():
    return load_and_freeze_current_strategy()


def test_matches_processed_in_chronological_order(strategy):
    matches = [
        _match("late", "2021-05-01", "H"),
        _match("early", "2020-08-01", "A"),
        _match("mid", "2020-12-15", "D"),
    ]
    candidates, _ = replay_module.build_candidates(matches, strategy)
    seen_order = list(dict.fromkeys(c.match_id for c in candidates))
    assert seen_order == ["early", "mid", "late"]

    # Cross-check with the project's own reusable chronology checker rather
    # than re-implementing an ordering assertion from scratch.
    dated = [
        DatedRecord(record_id=mid, record_date=date.fromisoformat(next(c.event_date for c in candidates if c.match_id == mid)))
        for mid in seen_order
    ]
    assert check_chronological_order(dated) == []


def test_result_is_not_read_before_recommendation_is_built(strategy, monkeypatch):
    call_order = []

    original_build_recommendation = replay_module.build_recommendation

    def spy_build_recommendation(*args, **kwargs):
        call_order.append("build_recommendation")
        return original_build_recommendation(*args, **kwargs)

    original_result_matcher = replay_module.actual_result_letter_matches

    def spy_result_matcher(*args, **kwargs):
        call_order.append("read_result")
        return original_result_matcher(*args, **kwargs)

    monkeypatch.setattr(replay_module, "build_recommendation", spy_build_recommendation)
    monkeypatch.setattr(replay_module, "actual_result_letter_matches", spy_result_matcher)

    matches = [_match("m1", "2020-09-12", "H")]
    replay_module.build_candidates(matches, strategy)

    # Exactly 3 outcomes x 2 calls each = 6 entries; every build_recommendation
    # for a given outcome must precede its own read_result call, and no
    # read_result may occur before the first build_recommendation exists.
    assert call_order[0] == "build_recommendation"
    build_indices = [i for i, c in enumerate(call_order) if c == "build_recommendation"]
    result_indices = [i for i, c in enumerate(call_order) if c == "read_result"]
    for result_idx in result_indices:
        assert any(b < result_idx for b in build_indices), (
            "a match result was read before any recommendation was built for that outcome"
        )


def test_best_price_drawn_only_from_accepted_bookmakers(strategy):
    # One bookmaker quotes an incomplete market (missing 'away') and offers
    # a wildly generous 'home' price -- it must never be selected as the
    # best price despite being numerically the best, because
    # compute_market_consensus rejects it outright.
    match = _match("m1", "2020-09-12", "H")
    match.bookmaker_odds["ROGUE"] = {"home": 999.0, "draw": 1.5}  # missing "away"

    candidates, _ = replay_module.build_candidates([match], strategy)
    home_candidate = next(c for c in candidates if c.selection == "home")
    assert home_candidate.venue != "ROGUE"
    assert home_candidate.decimal_odds < 999.0


def test_build_candidates_is_deterministic_across_repeated_runs(strategy):
    matches = [_match("m1", "2020-09-12", "H"), _match("m2", "2020-09-13", "A")]
    first, _ = replay_module.build_candidates(matches, strategy)
    second, _ = replay_module.build_candidates(matches, strategy)
    assert [(c.match_id, c.selection, c.consensus_probability, c.decimal_odds, c.money_decision) for c in first] == [
        (c.match_id, c.selection, c.consensus_probability, c.decimal_odds, c.money_decision) for c in second
    ]


def test_no_scan_timestamp_excludes_match_with_reason(strategy):
    match = _match("m1", "2020-09-12", "H")
    match = HistoricalMatch(**{**match.__dict__, "kickoff_iso": None, "kickoff_join_failure_reason": "test"})
    candidates, excluded = replay_module.build_candidates([match], strategy)
    assert candidates == []
    assert len(excluded) == 1
    assert excluded[0]["match_id"] == "m1"


def test_simulate_bankroll_settles_a_winning_and_losing_bet_correctly(strategy):
    from prediction_markets_lab.backtesting.replay import BacktestCandidate

    win = BacktestCandidate(
        match_id="w1", selection="home", event_date="2020-09-12", competition_code="E0",
        competition_name="Premier League", season="2020_21", home_team="A", away_team="B",
        accepted_bookmaker_count=5, consensus_probability=0.7, decimal_odds=2.0, venue="B365",
        net_ev=0.1, probability_edge_pp=5.0, confidence_label="High", data_quality_ok=True,
        research_grade="A", money_decision="BET", money_qualified=True, money_rejection_reason="",
        recommended_stake_gbp=0.25, actual_won=True, kickoff_iso="2020-09-12T15:00:00+00:00",
        scan_timestamp_iso="2020-09-12T14:00:00+00:00",
    )
    lose = BacktestCandidate(
        match_id="l1", selection="home", event_date="2020-09-13", competition_code="E0",
        competition_name="Premier League", season="2020_21", home_team="C", away_team="D",
        accepted_bookmaker_count=5, consensus_probability=0.7, decimal_odds=2.0, venue="B365",
        net_ev=0.1, probability_edge_pp=5.0, confidence_label="High", data_quality_ok=True,
        research_grade="A", money_decision="BET", money_qualified=True, money_rejection_reason="",
        recommended_stake_gbp=0.25, actual_won=False, kickoff_iso="2020-09-13T15:00:00+00:00",
        scan_timestamp_iso="2020-09-13T14:00:00+00:00",
    )
    updated, ending, exhausted, exhausted_at = replay_module.simulate_bankroll(
        [win, lose], strategy, apply_risk_gates=True
    )
    assert exhausted is False
    win_result = next(c for c in updated if c.match_id == "w1")
    lose_result = next(c for c in updated if c.match_id == "l1")
    assert win_result.net_change_gbp == pytest.approx(0.25)  # stake * (2.0 - 1)
    assert lose_result.net_change_gbp == pytest.approx(-0.25)
    starting = strategy.bankroll["starting_bankroll_gbp"]
    assert win_result.bankroll_after_gbp == pytest.approx(starting + 0.25)
    assert lose_result.bankroll_after_gbp == pytest.approx(starting)  # net zero after both
    assert ending == pytest.approx(starting)


def test_simulate_bankroll_never_lets_balance_go_negative(strategy):
    from prediction_markets_lab.backtesting.replay import BacktestCandidate

    starting = strategy.bankroll["starting_bankroll_gbp"]
    # A huge stake, larger than the whole bankroll, that loses.
    huge_loss = BacktestCandidate(
        match_id="huge", selection="home", event_date="2020-09-12", competition_code="E0",
        competition_name="Premier League", season="2020_21", home_team="A", away_team="B",
        accepted_bookmaker_count=5, consensus_probability=0.7, decimal_odds=2.0, venue="B365",
        net_ev=0.1, probability_edge_pp=5.0, confidence_label="High", data_quality_ok=True,
        research_grade="A", money_decision="BET", money_qualified=True, money_rejection_reason="",
        recommended_stake_gbp=starting * 10, actual_won=False, kickoff_iso="2020-09-12T15:00:00+00:00",
        scan_timestamp_iso="2020-09-12T14:00:00+00:00",
    )
    updated, ending, exhausted, exhausted_at = replay_module.simulate_bankroll(
        [huge_loss], strategy, apply_risk_gates=False
    )
    assert ending >= 0.0
    assert exhausted is True
    assert exhausted_at == "huge"


def test_apply_risk_gates_blocks_excess_daily_exposure(strategy):
    from prediction_markets_lab.backtesting.replay import BacktestCandidate

    max_open = strategy.bankroll["maximum_open_bets"]
    same_day_candidates = [
        BacktestCandidate(
            match_id=f"m{i}", selection="home", event_date="2020-09-12", competition_code="E0",
            competition_name="Premier League", season="2020_21", home_team="A", away_team="B",
            accepted_bookmaker_count=5, consensus_probability=0.7, decimal_odds=2.0, venue="B365",
            net_ev=0.1, probability_edge_pp=5.0, confidence_label="High", data_quality_ok=True,
            research_grade="A", money_decision="BET", money_qualified=True, money_rejection_reason="",
            recommended_stake_gbp=0.25, actual_won=False, kickoff_iso="2020-09-12T15:00:00+00:00",
            scan_timestamp_iso="2020-09-12T14:00:00+00:00",
        )
        for i in range(max_open + 3)
    ]
    updated, ending, exhausted, _ = replay_module.simulate_bankroll(
        same_day_candidates, strategy, apply_risk_gates=True
    )
    actually_staked = [c for c in updated if c.staked_gbp > 0]
    assert len(actually_staked) <= max_open
    blocked = [c for c in updated if c.risk_gate_passed is False]
    assert len(blocked) >= 1
    assert all(c.risk_gate_reason for c in blocked)


def test_candidate_count_is_preserved_through_bankroll_simulation(strategy):
    """No candidate is ever dropped by the bankroll walk, whether it was
    staked, blocked, or never money-qualified in the first place."""
    matches = [_match(f"m{i}", f"2020-09-{12+i:02d}", "H") for i in range(5)]
    candidates, _ = replay_module.build_candidates(matches, strategy)
    updated, *_ = replay_module.simulate_bankroll(candidates, strategy, apply_risk_gates=True)
    assert len(updated) == len(candidates)
    assert {(c.match_id, c.selection) for c in updated} == {(c.match_id, c.selection) for c in candidates}
