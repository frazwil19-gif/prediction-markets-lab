"""Rebuild the paper-order ledger and the weekly/monthly paper performance report (0 credits, no manual input).

  paper_betting_v2/paper_orders.csv     one row per PAPER_BET (decision, close/CLV, settlement, flags)
  reports/paper_performance.{md,json}   7-day, 30-day and all-time windows
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from prediction_markets_lab.paper_orders import ledger as LG
from prediction_markets_lab.paper_orders import report as RP

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    now = datetime.now(timezone.utc)
    cfg = yaml.safe_load((REPO / "config/paper_mode.yaml").read_text())
    orders = LG.build(REPO, cfg, now)
    LG.write(REPO / "paper_betting_v2/paper_orders.csv", orders)
    r = RP.build(REPO, orders, cfg, now)
    (REPO / "reports/paper_performance.json").write_text(json.dumps(r, indent=1, default=str))
    (REPO / "reports/paper_performance.md").write_text(RP.render_md(r))
    print(json.dumps(r["windows"]["all"]["metrics"], default=str)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
