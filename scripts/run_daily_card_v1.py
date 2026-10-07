"""Build the Daily Prediction Board + Bet Card V1 (reports/daily_card_v1.md/.json). 0 credits; reads existing outputs only."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from prediction_markets_lab.daily_card.card import run

REPO = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    c = run(REPO, REPO / "config/daily_card_v1.yaml", datetime.now(timezone.utc))
    print(c["mode"], c["summary"])
    sys.exit(0)
