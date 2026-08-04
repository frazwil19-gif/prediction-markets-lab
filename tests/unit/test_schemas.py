import pytest
from pydantic import ValidationError

from prediction_markets_lab.storage.schemas import BetRecord, MarketRecord, ResultRecord


def test_market_record_valid_construction():
    record = MarketRecord(
        market_id="M-FB-001",
        scan_timestamp="2026-08-03T12:00:00+00:00",
        event_date="2026-08-04",
        sport="football",
        competition="Premier League",
        event="Arsenal vs Chelsea",
        market_type="pre_match_1x2",
        selection="home",
        bookmaker_count=5,
        consensus_probability=0.47,
        exchange="Smarkets",
        exchange_odds=2.20,
        exchange_implied_probability=0.4545,
        commission=0.02,
        probability_edge=1.5,
        gross_ev=0.05,
        net_ev=0.03,
        grade="B",
    )
    assert record.market_id == "M-FB-001"


def test_market_record_rejects_invalid_probability():
    with pytest.raises(ValidationError):
        MarketRecord(
            market_id="M-FB-001",
            scan_timestamp="2026-08-03T12:00:00+00:00",
            event_date="2026-08-04",
            sport="football",
            competition="Premier League",
            event="Arsenal vs Chelsea",
            market_type="pre_match_1x2",
            selection="home",
            bookmaker_count=5,
            consensus_probability=1.5,  # invalid: must be < 1.0
            exchange="Smarkets",
            exchange_odds=2.20,
            exchange_implied_probability=0.4545,
            commission=0.02,
            probability_edge=1.5,
            gross_ev=0.05,
            net_ev=0.03,
            grade="B",
        )


def test_market_record_rejects_invalid_sport():
    with pytest.raises(ValidationError):
        MarketRecord(
            market_id="M-FB-001",
            scan_timestamp="2026-08-03T12:00:00+00:00",
            event_date="2026-08-04",
            sport="rugby",  # not a recognised Sport literal
            competition="Premier League",
            event="Arsenal vs Chelsea",
            market_type="pre_match_1x2",
            selection="home",
            bookmaker_count=5,
            consensus_probability=0.47,
            exchange="Smarkets",
            exchange_odds=2.20,
            exchange_implied_probability=0.4545,
            commission=0.02,
            probability_edge=1.5,
            gross_ev=0.05,
            net_ev=0.03,
            grade="B",
        )


def test_result_record_defaults():
    record = ResultRecord(
        market_id="M-FB-001",
        event="Arsenal vs Chelsea",
        settlement_date="2026-08-04",
        winning_outcome="home",
    )
    assert record.settlement_status == "settled"


def test_bet_record_requires_positive_stake():
    with pytest.raises(ValidationError):
        BetRecord(
            bet_id="B-0001",
            market_id="M-FB-001",
            bet_timestamp="2026-08-03T12:00:00+00:00",
            sport="football",
            competition="Premier League",
            event="Arsenal vs Chelsea",
            market="pre_match_1x2",
            selection="home",
            venue="Smarkets",
            requested_odds=2.20,
            matched_odds=2.20,
            stake=0.0,  # invalid: must be > 0
            estimated_probability=0.5,
            implied_probability=0.45,
            net_ev_at_entry=0.03,
            grade="A",
            bankroll_before=10.0,
            liability=0.0,
        )
