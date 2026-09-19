"""Tests for storage.paper_ledger (Track B live paper-bet ledger, 2026-09-19)."""

from __future__ import annotations

import csv

import pytest

from prediction_markets_lab.decisions.confidence import ConfidenceThresholds
from prediction_markets_lab.decisions.data_quality import DataQualityThresholds
from prediction_markets_lab.decisions.grading import GradingThresholds
from prediction_markets_lab.decisions.recommendation import PriceQuote, build_recommendation
from prediction_markets_lab.probability.consensus import calculate_consensus
from prediction_markets_lab.risk.staking import StakingConfig
from prediction_markets_lab.storage.paper_ledger import (
    _FIELDS,
    load_paper_bets,
    record_qualifying_candidates,
    record_qualifying_candidates_from_contract,
    settle_paper_bet,
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


def test_record_qualifying_candidates_only_records_grade_b_or_better(tmp_path):
    strong = _build("M-1", "home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    reject = _build("M-2", "away", [1 / 1.80] * 4, 1.80, 4)
    ledger_path = tmp_path / "paper_bets.csv"

    recorded, skipped = record_qualifying_candidates(
        ledger_path, [strong, reject], scan_id="scan-1", created_at="2026-09-19T09:00:00"
    )

    assert len(recorded) == 1
    assert skipped == []
    rows = load_paper_bets(ledger_path)
    assert len(rows) == 1
    assert rows[0]["selection"] == "home"
    assert rows[0]["grade"] in ("A+", "A")
    assert rows[0]["status"] == "pending"


def test_record_qualifying_candidates_skips_already_recorded_duplicate(tmp_path):
    strong = _build("M-1", "home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    ledger_path = tmp_path / "paper_bets.csv"

    first_recorded, first_skipped = record_qualifying_candidates(
        ledger_path, [strong], scan_id="scan-1", created_at="2026-09-19T09:00:00"
    )
    second_recorded, second_skipped = record_qualifying_candidates(
        ledger_path, [strong], scan_id="scan-2", created_at="2026-09-19T09:05:00"
    )

    assert len(first_recorded) == 1
    assert first_skipped == []
    assert second_recorded == []
    assert second_skipped == first_recorded
    # Still only one row -- no duplicate, no overwrite.
    rows = load_paper_bets(ledger_path)
    assert len(rows) == 1
    assert rows[0]["scan_id"] == "scan-1"  # untouched by the second scan


def test_record_qualifying_candidates_writes_every_ledger_field(tmp_path):
    strong = _build("M-1", "home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    ledger_path = tmp_path / "paper_bets.csv"
    record_qualifying_candidates(ledger_path, [strong], scan_id="scan-1", created_at="2026-09-19T09:00:00")

    with open(ledger_path, newline="") as f:
        header = next(csv.reader(f))
    assert header == _FIELDS


def test_settle_paper_bet_updates_only_settlement_fields(tmp_path):
    strong = _build("M-1", "home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    ledger_path = tmp_path / "paper_bets.csv"
    recorded, _ = record_qualifying_candidates(
        ledger_path, [strong], scan_id="scan-1", created_at="2026-09-19T09:00:00"
    )
    bet_id = recorded[0]
    before = load_paper_bets(ledger_path)[0]

    settle_paper_bet(
        ledger_path,
        bet_id=bet_id,
        result="won",
        closing_odds_if_available="2.15",
        actual_pnl="1.20",
        paper_bankroll_after_settlement="11.20",
    )

    after = load_paper_bets(ledger_path)[0]
    assert after["status"] == "settled"
    assert after["result"] == "won"
    assert after["closing_odds_if_available"] == "2.15"
    assert after["actual_pnl"] == "1.20"
    assert after["paper_bankroll_after_settlement"] == "11.20"
    # Every non-settlement field is untouched.
    for field in _FIELDS:
        if field in ("status", "result", "closing_odds_if_available", "actual_pnl", "paper_bankroll_after_settlement"):
            continue
        assert before[field] == after[field], f"field {field} changed during settlement"


def test_settle_paper_bet_raises_for_unknown_bet_id(tmp_path):
    ledger_path = tmp_path / "paper_bets.csv"
    strong = _build("M-1", "home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    record_qualifying_candidates(ledger_path, [strong], scan_id="scan-1", created_at="2026-09-19T09:00:00")

    with pytest.raises(KeyError):
        settle_paper_bet(
            ledger_path,
            bet_id="does-not-exist",
            result="won",
            closing_odds_if_available="",
            actual_pnl="0",
            paper_bankroll_after_settlement="10",
        )


def test_load_paper_bets_returns_empty_list_for_missing_file(tmp_path):
    assert load_paper_bets(tmp_path / "does_not_exist.csv") == []


def _sample_contract(grade: str = "B") -> dict:
    return {
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
                "grade": grade,
                "reason": "strong edge",
                "model_version": "daily-engine-v1.1.0-odds-api",
            }
        ]
    }


def test_record_qualifying_candidates_from_contract_records_qualifying_grade(tmp_path):
    ledger_path = tmp_path / "paper_bets.csv"
    recorded, skipped = record_qualifying_candidates_from_contract(
        ledger_path, _sample_contract("A+"), scan_id="scan-1", created_at="2026-09-19T09:00:00"
    )
    assert len(recorded) == 1
    assert skipped == []
    rows = load_paper_bets(ledger_path)
    assert rows[0]["event"] == "Team A v Team B"
    assert rows[0]["grade"] == "A+"


def test_record_qualifying_candidates_from_contract_skips_reject_grade(tmp_path):
    ledger_path = tmp_path / "paper_bets.csv"
    recorded, skipped = record_qualifying_candidates_from_contract(
        ledger_path, _sample_contract("Reject"), scan_id="scan-1", created_at="2026-09-19T09:00:00"
    )
    assert recorded == []
    assert skipped == []
    assert load_paper_bets(ledger_path) == []


def test_record_qualifying_candidates_from_contract_skips_existing_duplicate(tmp_path):
    ledger_path = tmp_path / "paper_bets.csv"
    contract = _sample_contract("B")
    record_qualifying_candidates_from_contract(
        ledger_path, contract, scan_id="scan-1", created_at="2026-09-19T09:00:00"
    )
    recorded, skipped = record_qualifying_candidates_from_contract(
        ledger_path, contract, scan_id="scan-2", created_at="2026-09-19T09:05:00"
    )
    assert recorded == []
    assert len(skipped) == 1
    assert len(load_paper_bets(ledger_path)) == 1
