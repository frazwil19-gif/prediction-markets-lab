"""Write reports/qualified_capacity.{json,md} (monitoring only; 0 API calls). See daily_card/capacity.py."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from prediction_markets_lab.daily_card import capacity as Q

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    cfg = yaml.safe_load((REPO / "config/qualified_capacity.yaml").read_text())
    r = Q.build(REPO, cfg, datetime.now(timezone.utc))
    (REPO / "reports/qualified_capacity.json").write_text(json.dumps(r, indent=1))
    (REPO / "reports/qualified_capacity.md").write_text(Q.render_md(r))
    print(json.dumps(r["expected_vs_realised"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
