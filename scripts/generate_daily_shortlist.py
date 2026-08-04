#!/usr/bin/env python3
"""Generate a daily shortlist and report from manual odds/exchange CSVs.

Usage:
    python scripts/generate_daily_shortlist.py \\
        --odds templates/manual_odds_entry.csv \\
        --exchange templates/exchange_price_entry.csv \\
        --outcomes home draw away

CORRECTED (previous version used raw implied-probability "consensus"
without ever removing bookmaker margin — see git history / CHANGELOG
for details). This version performs proper per-bookmaker margin
removal before aggregating across bookmakers, via
probability.market_pipeline.compute_market_consensus, and rejects any
bookmaker that did not quote a complete outcome set for the market
rather than silently treating partial odds as valid.

Reads config/bankroll.yaml, config/thresholds.yaml and
config/commissions.yaml for its settings rather than hard-coding
anything, per project coding standards.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

from prediction_markets_lab.decisions.grading import (
    GradingInput,
    GradingThresholds,
    grade_opportunity,
)
from prediction_markets_lab.ev.expected_value import evaluate
from prediction_markets_lab.ingestion.exchange_price_loader import (
    best_price_for_selection,
    load_exchange_prices,
)
from prediction_markets_lab.ingestion.manual_odds_loader import load_manual_odds_by_bookmaker
from prediction_markets_lab.probability.market_pipeline import compute_market_consensus
from prediction_markets_lab.reports.daily_report import (
    DailyReportContext,
    generate_daily_report,
)
from prediction_markets_lab.risk.staking import StakingConfig, recommended_stake_gbp
from prediction_markets_lab.storage.schemas import MarketRecord

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def build_staking_config() -> StakingConfig:
    bankroll_cfg = load_yaml(REPO_ROOT / "config" / "bankroll.yaml")
    return StakingConfig(
        starting_bankroll_gbp=bankroll_cfg["starting_bankroll_gbp"],
        normal_stake_gbp=bankroll_cfg["normal_stake_gbp"],
        maximum_stake_gbp=bankroll_cfg["maximum_stake_gbp"],
        maximum_daily_exposure_gbp=bankroll_cfg["maximum_daily_exposure_gbp"],
        maximum_open_bets=bankroll_cfg["maximum_open_bets"],
        daily_loss_stop_gbp=bankroll_cfg["daily_loss_stop_gbp"],
        weekly_loss_stop_gbp=bankroll_cfg["weekly_loss_stop_gbp"],
    )


def build_grading_thresholds() -> GradingThresholds:
    t = load_yaml(REPO_ROOT / "config" / "thresholds.yaml")
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--odds", type=Path, required=True, help="Manual odds CSV path")
    parser.add_argument("--exchange", type=Path, required=True, help="Exchange price CSV path")
    parser.add_argument(
        "--outcomes",
        nargs="+",
        required=True,
        help="Full list of expected outcomes for the market type, e.g. "
        "--outcomes home draw away (football 1X2) or "
        "--outcomes player_a player_b (tennis match winner)",
    )
    parser.add_argument(
        "--sport",
        default="football",
        choices=["football", "tennis"],
        help="Sport to tag opportunities with (Stage 2 supports one sport per run)",
    )
    parser.add_argument(
        "--competition", default="", help="Competition name to tag opportunities with"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "reports" / "daily",
        help="Directory to write the report into",
    )
    args = parser.parse_args()

    manual_odds = load_manual_odds_by_bookmaker(args.odds)
    exchange_prices = load_exchange_prices(args.exchange)
    staking_config = build_staking_config()
    grading_thresholds = build_grading_thresholds()

    opportunities: list[MarketRecord] = []
    stakes: dict[str, float] = {}
    actions: list[str] = []

    for market_id, bookmaker_odds in manual_odds.items():
        try:
            market_result = compute_market_consensus(
                market_id, bookmaker_odds, expected_outcomes=args.outcomes
            )
        except ValueError as exc:
            print(f"REJECTED market {market_id}: {exc}", file=sys.stderr)
            continue

        for bookmaker in market_result.rejected_bookmakers:
            print(
                f"  note: {bookmaker.bookmaker} excluded from {market_id} "
                f"consensus — {bookmaker.reason}",
                file=sys.stderr,
            )

        for selection, consensus in market_result.consensus_by_outcome.items():
            best_exchange = best_price_for_selection(exchange_prices, market_id, selection)
            if best_exchange is None:
                continue

            ev_result = evaluate(
                probability=consensus.consensus_probability,
                decimal_odds=best_exchange.decimal_odds,
                commission=best_exchange.commission,
            )

            evidence = GradingInput(
                net_ev=ev_result.net_ev,
                probability_edge_pp=ev_result.probability_edge_pp,
                bookmaker_count=consensus.bookmaker_count,
                data_quality_ok=True,
                no_material_info_risk=True,
                exchange_price_current=True,
                market_rules_match=True,
                liquidity_adequate=best_exchange.available_size_gbp > 0,
            )
            grading_result = grade_opportunity(evidence, grading_thresholds)
            stake = recommended_stake_gbp(grading_result.grade, staking_config)

            record = MarketRecord(
                market_id=market_id,
                scan_timestamp=date.today().isoformat(),
                event_date=date.today().isoformat(),
                sport=args.sport,
                competition=args.competition,
                event=market_id,
                market_type="pre_match",
                selection=selection,
                bookmaker_count=consensus.bookmaker_count,
                consensus_probability=consensus.consensus_probability,
                consensus_mean=consensus.mean,
                consensus_median=consensus.median,
                consensus_std=consensus.std_dev,
                exchange=best_exchange.exchange,
                exchange_odds=best_exchange.decimal_odds,
                exchange_implied_probability=ev_result.exchange_implied_probability,
                commission=best_exchange.commission,
                probability_edge=ev_result.probability_edge_pp,
                gross_ev=ev_result.gross_ev,
                net_ev=ev_result.net_ev,
                grade=grading_result.grade,
                decision=grading_result.reason,
                rejection_reason=grading_result.reason if grading_result.grade == "Reject" else "",
            )
            opportunities.append(record)
            stakes[market_id] = stake

            if stake > 0:
                actions.append(
                    f"BET: {market_id} {selection} @ {best_exchange.decimal_odds} "
                    f"{best_exchange.exchange}, £{stake:.2f}"
                )
            elif grading_result.grade == "B":
                actions.append(f"PAPER TRADE: {market_id} {selection}")
            elif grading_result.grade == "C":
                actions.append(f"WATCH: {market_id} {selection}")

    if not actions:
        actions = ["NO BETS TODAY"]

    context = DailyReportContext(
        report_date=date.today(),
        markets_scanned=len(opportunities),
        football_markets=len(opportunities) if args.sport == "football" else 0,
        tennis_markets=len(opportunities) if args.sport == "tennis" else 0,
        current_bankroll_gbp=staking_config.starting_bankroll_gbp,
        current_exposure_gbp=sum(stakes.values()),
    )
    report = generate_daily_report(context, opportunities, stakes, actions)

    args.out.mkdir(parents=True, exist_ok=True)
    out_path = args.out / f"{date.today().isoformat()}.md"
    out_path.write_text(report)
    print(f"Report written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
