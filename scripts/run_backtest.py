#!/usr/bin/env python3
"""Run the frozen-V1 1X2 historical backtest (BACKTEST PHASE 1, 2026-09-22).

Reuses backtesting.frozen_strategy / backtesting.historical_loader /
backtesting.replay / backtesting.report end to end. See
research/backtesting/BACKTEST_DATA_FEASIBILITY_AUDIT.md and
LEAKAGE_AUDIT.md for what this run does and does not represent (a
closing-snapshot PROXY of the live daily-scan design, not an exact
replay -- see those documents before trusting any number this prints).

Usage:
    python scripts/run_backtest.py --price-timing closing --run-id 2026-09-22-phase1-primary
    python scripts/run_backtest.py --price-timing opening --run-id 2026-09-22-phase1-secondary-opening
    python scripts/run_backtest.py --price-timing closing --no-risk-gates --run-id 2026-09-22-phase1-no-risk-gates
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.backtesting.frozen_strategy import load_and_freeze_current_strategy
from prediction_markets_lab.backtesting.replay import run_replay
from prediction_markets_lab.backtesting.report import write_backtest_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--price-timing", choices=["opening", "closing"], default="closing")
    parser.add_argument("--run-id", required=True, help="Unique identifier for this run's output directory")
    parser.add_argument(
        "--no-risk-gates",
        action="store_true",
        help="Disable risk.decision_gates exposure/loss-lock enforcement (matches what the live "
        "automated scan currently permits, which does not wire these gates in -- see the "
        "run's manifest.json for the disclosure this flag controls).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "backtests",
        help="Root directory for backtest outputs (default: backtests/)",
    )
    args = parser.parse_args()

    strategy = load_and_freeze_current_strategy()
    print(f"Frozen strategy: {strategy.strategy_name} (config_hash={strategy.config_hash})", file=sys.stderr)

    run = run_replay(args.price_timing, apply_risk_gates=not args.no_risk_gates, strategy=strategy)

    dataset_description = (
        f"Cycle 1 1X2 (E0/E1/SC0, 2020/21-2025/26), {args.price_timing} snapshot -- "
        f"data/processed/football/cycle_001_{{matches,bookmaker_markets}}_full.csv"
    )
    written = write_backtest_outputs(run, args.run_id, dataset_description, args.out)

    print(f"\nBacktest complete: {len(run.candidates)} candidates, "
          f"{sum(1 for c in run.candidates if c.money_qualified)} money-qualified, "
          f"{sum(1 for c in run.candidates if c.staked_gbp > 0)} staked.", file=sys.stderr)
    print(f"Ending bankroll: £{run.ending_bankroll_gbp:.2f} (started £{run.starting_bankroll_gbp:.2f})",
          file=sys.stderr)
    if run.bankroll_exhausted:
        print(f"WARNING: bankroll was exhausted at match {run.bankroll_exhausted_at_match_id}", file=sys.stderr)
    print("\nOutputs written:", file=sys.stderr)
    for kind, path in written.items():
        print(f"  {kind}: {path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
