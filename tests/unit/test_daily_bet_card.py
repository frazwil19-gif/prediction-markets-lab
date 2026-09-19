"""Tests for reports.daily_bet_card (Daily Engine V1 build, 2026-09-18;
JSON/CSV/MD contract additions, 2026-09-19)."""

from __future__ import annotations

import csv
import json
from datetime import datetime

from prediction_markets_lab.decisions.confidence import ConfidenceThresholds
from prediction_markets_lab.decisions.data_quality import DataQualityThresholds
from prediction_markets_lab.decisions.grading import GradingThresholds
from prediction_markets_lab.decisions.recommendation import PriceQuote, build_recommendation
from prediction_markets_lab.probability.consensus import calculate_consensus
from prediction_markets_lab.reports.daily_bet_card import (
    _CSV_FIELDS,
    ENGINE_VERSION,
    DailyBetCardContext,
    build_daily_bet_card_contract,
    render_daily_bet_card,
    write_daily_bet_card_outputs,
)
from prediction_markets_lab.risk.staking import StakingConfig


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


def _build(selection: str, probs: list[float], odds: float, bookmakers: int):
    consensus = calculate_consensus(probs)
    return build_recommendation(
        market_id=f"TEST-{selection}",
        scan_timestamp="2026-09-18T09:00:00",
        event_date="2026-09-18",
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


def test_card_contains_header_and_ranked_selection():
    strong = _build("home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 18, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    text = render_daily_bet_card(context, [strong])
    assert "DAILY BET CARD" in text
    assert "RANKED SELECTIONS" in text
    assert "OPTIONAL MULTI" in text
    assert "REJECT / WATCH SUMMARY" in text
    assert "home" in text
    assert f"£{10.0:.2f}" in text


def test_reject_candidate_appears_only_in_watch_summary_not_ranked():
    reject = _build("away", [1 / 1.80] * 4, 1.80, 4)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 18, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    text = render_daily_bet_card(context, [reject])
    ranked_section = text.split("RANKED SELECTIONS")[1].split("OPTIONAL MULTI")[0]
    assert "away" not in ranked_section
    watch_section = text.split("REJECT / WATCH SUMMARY")[1]
    assert "away" in watch_section


def test_no_qualifying_candidates_says_so_explicitly():
    reject = _build("away", [1 / 1.80] * 4, 1.80, 4)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 18, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    text = render_daily_bet_card(context, [reject])
    assert "no candidate cleared Grade B or better" in text


def test_system_warnings_are_rendered_when_present():
    reject = _build("away", [1 / 1.80] * 4, 1.80, 4)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 18, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    text = render_daily_bet_card(context, [reject], system_warnings=["test warning"])
    assert "System warnings:" in text
    assert "test warning" in text


# ---------------------------------------------------------------------------
# JSON/CSV/MD contract (2026-09-19 build)
# ---------------------------------------------------------------------------


def test_contract_has_all_required_card_level_fields():
    strong = _build("home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 19, 9, 0), bankroll_gbp=10.0, fixtures_scanned=2, markets_scanned=3
    )
    contract = build_daily_bet_card_contract(context, [strong], system_warnings=["a warning"])

    for field in (
        "run_timestamp",
        "data_timestamp",
        "engine_version",
        "bankroll_gbp",
        "fixtures_scanned",
        "markets_scanned",
        "candidates_analysed",
        "grade_counts",
        "recommended_total_exposure_gbp",
        "optional_multi",
        "candidates",
        "system_warnings",
    ):
        assert field in contract

    assert contract["fixtures_scanned"] == 2
    assert contract["markets_scanned"] == 3
    assert contract["candidates_analysed"] == 1
    assert contract["optional_multi"] is None
    assert contract["system_warnings"] == ["a warning"]
    assert contract["grade_counts"]["A+"] + contract["grade_counts"]["A"] == 1


def test_contract_candidate_row_has_all_required_fields_and_no_fabricated_context():
    strong = _build("home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 19, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    contract = build_daily_bet_card_contract(context, [strong])
    row = contract["candidates"][0]

    for field in _CSV_FIELDS:
        assert field in row

    assert row["selection"] == "home"
    assert row["market"] == "1x2"
    assert row["bookmaker"] == "Bet365"
    assert row["grade"] in ("A+", "A")
    # No automated context source exists yet -- must stay empty, not guessed.
    assert row["current_context"] == ""


def test_contract_engine_version_defaults_to_module_constant():
    strong = _build("home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 19, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    contract = build_daily_bet_card_contract(context, [strong])
    assert contract["engine_version"] == ENGINE_VERSION
    assert contract["candidates"][0]["model_version"] == ENGINE_VERSION


def test_contract_data_timestamp_defaults_to_generated_at_when_not_given():
    strong = _build("home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 19, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    contract = build_daily_bet_card_contract(context, [strong])
    assert contract["data_timestamp"] == contract["run_timestamp"]


def test_contract_data_timestamp_uses_explicit_value_when_given():
    strong = _build("home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 19, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    contract = build_daily_bet_card_contract(
        context, [strong], data_timestamp="2026-09-19T07:30:00"
    )
    assert contract["data_timestamp"] == "2026-09-19T07:30:00"


def test_write_daily_bet_card_outputs_writes_all_three_files(tmp_path):
    strong = _build("home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 19, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    contract = build_daily_bet_card_contract(context, [strong])
    markdown_text = render_daily_bet_card(context, [strong])
    out_dir = tmp_path / "2026-09-19"

    paths = write_daily_bet_card_outputs(out_dir, contract, markdown_text)

    assert paths["json"].exists()
    assert paths["csv"].exists()
    assert paths["md"].exists()

    loaded = json.loads(paths["json"].read_text())
    assert loaded["candidates_analysed"] == 1

    with open(paths["csv"], newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["selection"] == "home"
    assert list(rows[0].keys()) == _CSV_FIELDS

    assert "DAILY BET CARD" in paths["md"].read_text()


def test_write_daily_bet_card_outputs_creates_missing_directory(tmp_path):
    strong = _build("home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 19, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=1
    )
    contract = build_daily_bet_card_contract(context, [strong])
    nested = tmp_path / "does" / "not" / "exist" / "yet"

    paths = write_daily_bet_card_outputs(nested, contract, "some markdown")

    assert nested.exists()
    assert paths["json"].parent == nested


def test_contract_candidates_are_grade_ranked_same_as_markdown():
    strong = _build("home", [0.60, 0.61, 0.59, 0.60, 0.60], 2.20, 5)
    reject = _build("away", [1 / 1.80] * 4, 1.80, 4)
    context = DailyBetCardContext(
        generated_at=datetime(2026, 9, 19, 9, 0), bankroll_gbp=10.0, fixtures_scanned=1, markets_scanned=2
    )
    contract = build_daily_bet_card_contract(context, [reject, strong])
    grades = [c["grade"] for c in contract["candidates"]]
    # Best grade first, matching the markdown's ranking.
    assert grades[0] in ("A+", "A")
    assert grades[-1] in ("C", "Reject")
