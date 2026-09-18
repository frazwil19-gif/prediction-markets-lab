#!/usr/bin/env python3
"""V1 Daily Engine scan: bookmaker odds + current best price -> Daily Bet Card.

This is the operational entry point for the Daily Probability Engine V1
(see docs/DAILY_ENGINE_V1_LOCK_AND_IMPLEMENTATION_ROADMAP.md). It is the
successor to scripts/generate_daily_shortlist.py's ad hoc composition:
every candidate now goes through decisions.recommendation.build_recommendation,
which itself calls the tested consensus/EV/confidence/data-quality/
liquidity/grading/staking modules.

Usage:
    python scripts/run_daily_scan.py \\
        --odds templates/manual_odds_entry.csv \\
        --best-price templates/exchange_price_entry.csv \\
        --quote-age-minutes 5

Input files:
    --odds        A CSV matching templates/manual_odds_entry.csv: every
                  bookmaker's full outcome set for every market_id, plus
                  the market's sport/competition/event/event_date/
                  market_type/scan_timestamp (read once per market_id via
                  ingestion.manual_odds_loader.load_manual_odds_market_metadata).
    --best-price  A CSV matching templates/exchange_price_entry.csv: the
                  single best currently-obtainable price per
                  (market_id, selection), from any bookmaker or exchange
                  (see ingestion.exchange_price_loader -- despite the
                  filename, the `exchange` column accepts any venue name,
                  per storage.schemas.Exchange's 2026-09-18 generalisation).

V1 market scope: 1X2 ("1x2") and Over/Under 2.5 goals ("over_under_2_5").
Asian Handicap uses the same consensus method in principle but needs
exact-line matching between the consensus market_id and the best-price
quote, which this script does not yet automate -- see the roadmap doc's
NEEDS BUILDING bucket. A market_id whose market_type is not in
EXPECTED_OUTCOMES is skipped with a warning, not silently mis-priced.

Reads config/bankroll.yaml, config/thresholds.yaml (grading, data_quality,
confidence sections) -- nothing is hard-coded, per project coding
standards.

Writes:
    - A Daily Bet Card (plain text) to --out (default reports/daily/).
    - A full candidate log (every graded candidate, all grades) to
      data/processed/daily_cards/<date>_candidates.csv, for future
      calibration/performance analysis against settled results -- see
      the roadmap doc's result-logging section. This does NOT write to
      data/processed/bets.csv; only bets Fraser actually places should
      ever be logged there (via the existing manual workflow feeding
      scripts/settle_results.py), so an unplaced candidate is never
      mistaken for a real bet.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

from prediction_markets_lab.decisions.confidence import ConfidenceThresholds
from prediction_markets_lab.decisions.data_quality import DataQualityThresholds
from prediction_markets_lab.decisions.grading import GradingThresholds
from prediction_markets_lab.decisions.recommendation import (
    PriceQuote,
    RecommendationResult,
    build_recommendation,
)
from prediction_markets_lab.ingestion.exchange_price_loader import (
    best_price_for_selection,
    load_exchange_prices,
)
from prediction_markets_lab.ingestion.manual_odds_loader import (
    load_manual_odds_by_bookmaker,
    load_manual_odds_market_metadata,
)
from prediction_markets_lab.probability.market_pipeline import compute_market_consensus
from prediction_markets_lab.reports.daily_bet_card import DailyBetCardContext, render_daily_bet_card
from prediction_markets_lab.risk.staking import StakingConfig
from prediction_markets_lab.storage.csv_store import append_record

REPO_ROOT = Path(__file__).resolve().parent.parent

# V1 market scope -- see module docstring. Extending this to a new market
# family is the correct way to add one (per project engineering standards:
# no magic numbers, configuration/registry-driven), not writing a parallel
# script.
EXPECTED_OUTCOMES: dict[str, list[str]] = {
    "1x2": ["home", "draw", "away"],
    "over_under_2_5": ["over", "under"],
}


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def build_staking_config() -> StakingConfig:
    cfg = load_yaml(REPO_ROOT / "config" / "bankroll.yaml")
    return StakingConfig(
        starting_bankroll_gbp=cfg["starting_bankroll_gbp"],
        normal_stake_gbp=cfg["normal_stake_gbp"],
        maximum_stake_gbp=cfg["maximum_stake_gbp"],
        maximum_daily_exposure_gbp=cfg["maximum_daily_exposure_gbp"],
        maximum_open_bets=cfg["maximum_open_bets"],
        daily_loss_stop_gbp=cfg["daily_loss_stop_gbp"],
        weekly_loss_stop_gbp=cfg["weekly_loss_stop_gbp"],
    )


def build_grading_thresholds(t: dict) -> GradingThresholds:
    return GradingThresholds(
        a_plus_min_net_ev=t["grade_a_plus"]["min_net_ev"],
        a_plus_min_edge_pp=t["grade_a_plus"]["min_probability_edge_pp"],
        a_plus_min_bookmakers=t["grade_a_plus"]["min_bookmaker_count"],
        a_min_net_ev=t["grade_a"]["min_net_ev"],
        a_min_edge_pp=t["grade_a"]["min_probability_edge_pp"],
        a_min_bookmakers=t["grade_a"]["min_bookmaker_count"],
        b_min_net_ev=t["grade_b"]["min_net_ev"],
        c_min_net_ev=t["grade_c"]["min_net_ev"],
    )


def build_confidence_thresholds(t: dict) -> ConfidenceThresholds:
    c = t["confidence"]
    return ConfidenceThresholds(
        high_min_bookmakers=c["high_min_bookmakers"],
        high_max_std_dev=c["high_max_std_dev"],
        medium_min_bookmakers=c["medium_min_bookmakers"],
        medium_max_std_dev=c["medium_max_std_dev"],
    )


def build_data_quality_thresholds(t: dict) -> DataQualityThresholds:
    d = t["data_quality"]
    return DataQualityThresholds(
        min_bookmakers=d["min_bookmakers"],
        max_quote_age_minutes=d["max_quote_age_minutes"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--odds", type=Path, required=True, help="Manual bookmaker odds CSV path")
    parser.add_argument("--best-price", type=Path, required=True, help="Best-available-price CSV path")
    parser.add_argument(
        "--quote-age-minutes",
        type=float,
        default=5.0,
        help="Minutes since prices were entered, applied uniformly to this scan (default 5.0)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "reports" / "daily",
        help="Directory to write the Daily Bet Card into",
    )
    parser.add_argument(
        "--run-label",
        default="",
        help="Optional label appended to output filenames (e.g. 'dryrun')",
    )
    args = parser.parse_args()

    thresholds = load_yaml(REPO_ROOT / "config" / "thresholds.yaml")
    staking_config = build_staking_config()
    grading_thresholds = build_grading_thresholds(thresholds)
    confidence_thresholds = build_confidence_thresholds(thresholds)
    data_quality_thresholds = build_data_quality_thresholds(thresholds)

    bookmaker_odds_by_market = load_manual_odds_by_bookmaker(args.odds)
    market_metadata = load_manual_odds_market_metadata(args.odds)
    best_prices = load_exchange_prices(args.best_price)

    recommendations: list[RecommendationResult] = []
    system_warnings: list[str] = []
    fixtures_seen: set[str] = set()

    for market_id, bookmaker_odds in bookmaker_odds_by_market.items():
        meta = market_metadata.get(market_id, {})
        market_type = meta.get("market_type", "")
        expected_outcomes = EXPECTED_OUTCOMES.get(market_type)
        if expected_outcomes is None:
            system_warnings.append(
                f"market {market_id} skipped -- market_type {market_type!r} is not yet "
                f"wired into run_daily_scan.py (supported: {sorted(EXPECTED_OUTCOMES)})"
            )
            continue

        fixtures_seen.add(meta.get("event", market_id))

        try:
            market_result = compute_market_consensus(market_id, bookmaker_odds, expected_outcomes)
        except ValueError as exc:
            system_warnings.append(f"market {market_id} rejected -- {exc}")
            continue

        for rejected in market_result.rejected_bookmakers:
            system_warnings.append(
                f"{rejected.bookmaker} excluded from {market_id} consensus -- {rejected.reason}"
            )

        for selection, consensus in market_result.consensus_by_outcome.items():
            best = best_price_for_selection(best_prices, market_id, selection)
            if best is None:
                system_warnings.append(
                    f"no best-price quote for {market_id}/{selection} -- candidate skipped"
                )
                continue

            price_quote = PriceQuote(
                venue=best.exchange,
                decimal_odds=best.decimal_odds,
                commission=best.commission,
                available_size_gbp=best.available_size_gbp if best.available_size_gbp > 0 else None,
            )

            result = build_recommendation(
                market_id=market_id,
                scan_timestamp=meta.get("scan_timestamp", datetime.now().isoformat()),
                event_date=meta.get("event_date", date.today().isoformat()),
                sport=meta.get("sport", "football"),
                competition=meta.get("competition", ""),
                event=meta.get("event", market_id),
                market_type=market_type,
                selection=selection,
                consensus=consensus,
                accepted_bookmaker_count=market_result.accepted_bookmaker_count,
                best_price=price_quote,
                quote_age_minutes=args.quote_age_minutes,
                staking_config=staking_config,
                grading_thresholds=grading_thresholds,
                confidence_thresholds=confidence_thresholds,
                data_quality_thresholds=data_quality_thresholds,
            )
            recommendations.append(result)

    context = DailyBetCardContext(
        generated_at=datetime.now(),
        bankroll_gbp=staking_config.starting_bankroll_gbp,
        fixtures_scanned=len(fixtures_seen),
        markets_scanned=len(bookmaker_odds_by_market),
    )
    card_text = render_daily_bet_card(context, recommendations, system_warnings)

    args.out.mkdir(parents=True, exist_ok=True)
    suffix = f"_{args.run_label}" if args.run_label else ""
    card_path = args.out / f"{date.today().isoformat()}{suffix}_daily_bet_card.txt"
    card_path.write_text(card_text)
    print(card_text)
    print(f"Daily Bet Card written to {card_path}", file=sys.stderr)

    candidates_path = (
        REPO_ROOT
        / "data"
        / "processed"
        / "daily_cards"
        / f"{date.today().isoformat()}{suffix}_candidates.csv"
    )
    for rec in recommendations:
        append_record(candidates_path, rec.market_record)
    print(f"{len(recommendations)} candidate(s) logged to {candidates_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
