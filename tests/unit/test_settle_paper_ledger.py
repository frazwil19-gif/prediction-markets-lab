"""Tests for settlement.settle_paper_ledger (Production Infrastructure
Build, 2026-09-20, Section 7).
"""

from __future__ import annotations

import pytest

import prediction_markets_lab.settlement.settle_paper_ledger as settle_mod
from prediction_markets_lab.decisions.confidence import ConfidenceThresholds
from prediction_markets_lab.decisions.data_quality import DataQualityThresholds
from prediction_markets_lab.decisions.grading import GradingThresholds
from prediction_markets_lab.decisions.recommendation import PriceQuote, build_recommendation
from prediction_markets_lab.ingestion.the_odds_api_loader import TheOddsApiConfig
from prediction_markets_lab.ingestion.the_odds_api_scores import ParsedScore
from prediction_markets_lab.probability.consensus import calculate_consensus
from prediction_markets_lab.risk.staking import StakingConfig
from prediction_markets_lab.settlement.settle_paper_ledger import settle_pending_paper_bets
from prediction_markets_lab.storage.paper_ledger import (
    load_paper_bets,
    record_qualifying_candidates,
    record_qualifying_candidates_from_contract,
)


def _staking_config() -> StakingConfig:
    return StakingConfig(
        starting_bankroll_gbp=10.0,
        normal_stake_gbp=0.25,
        maximum_stake_gbp=0.50,
        maximum_daily_exposure_gbp=0.75,
        maximum_open_bets=3,
        daily_loss_stop_gbp=0.75,
        weekly_loss_stop_gbp=2.00,
    )


def _build(market_id: str, selection: str, probs: list[float], odds: float, bookmakers: int):
    consensus = calculate_consensus(probs)
    return build_recommendation(
        market_id=market_id,
        scan_timestamp="2026-09-19T09:00:00",
        event_date="2026-09-20",
        sport="football",
        competition="Premier League",
        event="Team A v Team B",
        market_type="1x2",
        selection=selection,
        consensus=consensus,
        accepted_bookmaker_count=bookmakers,
        best_price=PriceQuote(venue="Bet365", decimal_odds=odds, commission=0.0),
        quote_age_minutes=5.0,
        staking_config=_staking_config(),
        grading_thresholds=GradingThresholds(),
        confidence_thresholds=ConfidenceThresholds(),
        data_quality_thresholds=DataQualityThresholds(),
    )


def _patch_scores(monkeypatch, parsed_scores: list[ParsedScore]) -> None:
    def fake_fetch_scores_raw(sport_key, config, days_from=3):
        return "RAW_PLACEHOLDER"

    def fake_parse_scores_response(raw, sport_key):
        return parsed_scores

    monkeypatch.setattr(settle_mod, "fetch_scores_raw", fake_fetch_scores_raw)
    monkeypatch.setattr(settle_mod, "parse_scores_response", fake_parse_scores_response)


def test_settles_completed_event_and_computes_pnl(tmp_path, monkeypatch):
    ledger_path = tmp_path / "paper_bets.csv"
    strong = _build("soccer_epl-abc123-1x2", "home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    record_qualifying_candidates(ledger_path, [strong], scan_id="scan-1", created_at="2026-09-19T09:00:00")

    _patch_scores(
        monkeypatch,
        [
            ParsedScore(
                event_id="abc123",
                sport_key="soccer_epl",
                commence_time="2026-09-20T14:00:00Z",
                completed=True,
                home_team="Team A",
                away_team="Team B",
                home_score=2,
                away_score=1,
            )
        ],
    )

    summary = settle_pending_paper_bets(ledger_path, TheOddsApiConfig(), starting_bankroll_gbp=10.0)

    assert len(summary.settled_bet_ids) == 1
    rows = load_paper_bets(ledger_path)
    assert rows[0]["status"] == "settled"
    assert rows[0]["result"] == "won"
    stake = float(rows[0]["recommended_stake"])
    expected_pnl = stake * (2.20 - 1.0)
    assert float(rows[0]["actual_pnl"]) == pytest.approx(expected_pnl)
    assert float(rows[0]["paper_bankroll_after_settlement"]) == pytest.approx(10.0 + expected_pnl)


def test_not_yet_completed_event_stays_pending(tmp_path, monkeypatch):
    ledger_path = tmp_path / "paper_bets.csv"
    strong = _build("soccer_epl-abc123-1x2", "home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    record_qualifying_candidates(ledger_path, [strong], scan_id="scan-1", created_at="2026-09-19T09:00:00")

    _patch_scores(
        monkeypatch,
        [
            ParsedScore(
                event_id="abc123",
                sport_key="soccer_epl",
                commence_time="x",
                completed=False,
                home_team="Team A",
                away_team="Team B",
                home_score=None,
                away_score=None,
            )
        ],
    )

    summary = settle_pending_paper_bets(ledger_path, TheOddsApiConfig(), starting_bankroll_gbp=10.0)

    assert summary.settled_bet_ids == []
    assert "soccer_epl-abc123-1x2::home" in summary.not_yet_completed_bet_ids
    rows = load_paper_bets(ledger_path)
    assert rows[0]["status"] == "pending"


def test_contract_backfilled_bet_is_unresolvable(tmp_path):
    ledger_path = tmp_path / "paper_bets.csv"
    contract = {
        "candidates": [
            {
                "date": "2026-09-20",
                "sport": "football",
                "competition": "Premier League",
                "event": "Team A v Team B",
                "market": "1x2",
                "selection": "home",
                "bookmaker": "Bet365",
                "available_odds": 2.20,
                "estimated_probability": 0.55,
                "fair_odds": 1.818,
                "confidence": "High",
                "recommended_stake": 0.25,
                "grade": "B",
                "reason": "strong edge",
                "model_version": "v1",
            }
        ]
    }
    record_qualifying_candidates_from_contract(ledger_path, contract, scan_id="s", created_at="c")

    summary = settle_pending_paper_bets(ledger_path, TheOddsApiConfig(), starting_bankroll_gbp=10.0)

    assert len(summary.unresolvable_no_provider_id) == 1
    assert summary.settled_bet_ids == []


def test_idempotent_second_run_does_not_resettle(tmp_path, monkeypatch):
    ledger_path = tmp_path / "paper_bets.csv"
    strong = _build("soccer_epl-abc123-1x2", "home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    record_qualifying_candidates(ledger_path, [strong], scan_id="scan-1", created_at="2026-09-19T09:00:00")

    _patch_scores(
        monkeypatch,
        [
            ParsedScore(
                event_id="abc123",
                sport_key="soccer_epl",
                commence_time="x",
                completed=True,
                home_team="Team A",
                away_team="Team B",
                home_score=2,
                away_score=1,
            )
        ],
    )

    settle_pending_paper_bets(ledger_path, TheOddsApiConfig(), starting_bankroll_gbp=10.0)
    rows_after_first = load_paper_bets(ledger_path)
    first_pnl = float(rows_after_first[0]["actual_pnl"])

    second_summary = settle_pending_paper_bets(ledger_path, TheOddsApiConfig(), starting_bankroll_gbp=10.0)

    assert second_summary.settled_bet_ids == []
    rows = load_paper_bets(ledger_path)
    assert float(rows[0]["actual_pnl"]) == pytest.approx(first_pnl)


def test_event_not_found_in_scores_window(tmp_path, monkeypatch):
    ledger_path = tmp_path / "paper_bets.csv"
    strong = _build("soccer_epl-abc123-1x2", "home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    record_qualifying_candidates(ledger_path, [strong], scan_id="scan-1", created_at="2026-09-19T09:00:00")

    _patch_scores(monkeypatch, [])  # no events returned at all

    summary = settle_pending_paper_bets(ledger_path, TheOddsApiConfig(), starting_bankroll_gbp=10.0)

    assert summary.settled_bet_ids == []
    assert "soccer_epl-abc123-1x2::home" in summary.event_not_found_bet_ids


def test_skip_if_nothing_started_avoids_useless_scores_calls(tmp_path, monkeypatch):
    """V2-5 credit control: no scores call when no pending bet kicked off inside the scores window."""
    from datetime import datetime, timezone

    ledger_path = tmp_path / "paper_bets.csv"
    strong = _build("soccer_epl-abc123-1x2", "home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    record_qualifying_candidates(ledger_path, [strong], scan_id="scan-1", created_at="2026-09-19T09:00:00")
    calls: list[str] = []

    def fake_fetch(sport_key, config, days_from=3):
        calls.append(sport_key)
        return []

    monkeypatch.setattr(settle_mod, "fetch_scores_raw", fake_fetch)
    monkeypatch.setattr(settle_mod, "parse_scores_response", lambda raw, sk: [])
    before = datetime(2026, 9, 19, 12, tzinfo=timezone.utc)      # not kicked off yet
    s = settle_pending_paper_bets(ledger_path, TheOddsApiConfig(), 10.0, skip_if_nothing_started=True, now=before)
    assert calls == [] and s.skipped_sport_keys_nothing_started == ["soccer_epl"]
    long_after = datetime(2026, 9, 25, tzinfo=timezone.utc)      # outside the 3-day scores window
    settle_pending_paper_bets(ledger_path, TheOddsApiConfig(), 10.0, skip_if_nothing_started=True, now=long_after)
    assert calls == []
    inside = datetime(2026, 9, 21, tzinfo=timezone.utc)
    settle_pending_paper_bets(ledger_path, TheOddsApiConfig(), 10.0, skip_if_nothing_started=True, now=inside)
    assert calls == ["soccer_epl"]
    settle_pending_paper_bets(ledger_path, TheOddsApiConfig(), 10.0, now=before)     # default: unchanged behaviour
    assert calls == ["soccer_epl", "soccer_epl"]
