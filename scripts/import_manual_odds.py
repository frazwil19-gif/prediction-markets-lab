#!/usr/bin/env python3
"""Validate and preview a manual odds CSV before it is used for grading.

Usage:
    python scripts/import_manual_odds.py --odds templates/manual_odds_entry.csv

Runs ingestion.manual_odds_loader + ingestion.schema_validation over
the file and prints a summary, without writing anything. Intended as a
quick sanity check after pasting prices in from a phone.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from prediction_markets_lab.ingestion.manual_odds_loader import load_manual_odds_by_market


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--odds", type=Path, required=True)
    args = parser.parse_args()

    try:
        by_market = load_manual_odds_by_market(args.odds)
    except (FileNotFoundError, ValueError) as exc:
        print(f"REJECTED: {exc}", file=sys.stderr)
        return 1

    print(f"Loaded {len(by_market)} market(s) from {args.odds}")
    for market_id, outcomes in by_market.items():
        for selection, odds in outcomes.items():
            print(f"  {market_id} / {selection}: {len(odds)} bookmaker price(s) -> {odds}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
