#!/usr/bin/env python3
"""Write reports/latest_performance.json from the paper-bet ledger (Section 8).

Usage:
    python scripts/generate_performance_report.py

Machine-readable only, by design (Section 8: "ChatGPT must NEVER need to
reproduce the engine's calculations") -- ChatGPT reads this file directly
rather than recomputing win rate/ROI/Brier/etc. from the raw ledger.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from prediction_markets_lab.performance.paper_performance import build_performance_report
from prediction_markets_lab.storage.paper_ledger import load_paper_bets

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    bankroll_cfg = yaml.safe_load((REPO_ROOT / "config" / "bankroll.yaml").read_text())
    ledger_path = REPO_ROOT / "paper_ledger" / "paper_bets.csv"
    rows = load_paper_bets(ledger_path)

    report = build_performance_report(rows, starting_bankroll_gbp=bankroll_cfg["starting_bankroll_gbp"])

    out_path = REPO_ROOT / "reports" / "latest_performance.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    print(f"Performance report written to {out_path}")
    print(json.dumps(report["overall"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
