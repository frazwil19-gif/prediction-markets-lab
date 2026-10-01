"""V2-15: NBA Stage A uncertainty evidence from the EXISTING sealed-holdout band table (no fitting, no new data).

Source: research/platform_v2/nba/NBA_PROBABILITY_BANDS.csv, period SEALED_HOLDOUT_2024_26, estimator `market`
(the frozen engine; closing average odds). 5pp bands are pooled into the same coarse bands as tennis/football
(50-65, 65-80, 80+). One row per game, so effective N = games. sigma = pooled Wilson 95% half-width / 1.96: the sampling
precision of the historical calibration evidence. It EXCLUDES the bias of the live early-snapshot (~17-21h before tip)
estimator, which is unmeasured and tested prospectively from 20 Oct 2026.
Output: research/platform_v2/v2_15_nba/NBA_SIGMA_EVIDENCE.json (same schema as FOOTBALL_SIGMA_EVIDENCE.json)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from prediction_markets_lab.research.probability_reliability import wilson

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "research/platform_v2/nba/NBA_PROBABILITY_BANDS.csv"
OUT = REPO / "research/platform_v2/v2_15_nba/NBA_SIGMA_EVIDENCE.json"
COARSE = ((0.50, 0.65, "50-65%", ("50-54.9%", "55-59.9%", "60-64.9%")),
          (0.65, 0.80, "65-80%", ("65-69.9%", "70-74.9%", "75-79.9%")),
          (0.80, 1.0, "80%+", ("80-84.9%", "85-89.9%", "90-94.9%", "95%+")))


def main() -> int:
    with SRC.open() as f:
        rows = {r["band"]: r for r in csv.DictReader(f) if r["period"] == "SEALED_HOLDOUT_2024_26" and r["estimator"] == "market"}
    bands = []
    for lo, hi, lab, parts in COARSE:
        n = sum(int(rows[b]["n"]) for b in parts)
        k = sum(int(rows[b]["actual_wins"]) for b in parts)
        mp = sum(float(rows[b]["mean_predicted"]) * int(rows[b]["n"]) for b in parts) / n
        w = wilson(k, n)
        bands.append({"band": lab, "lo": lo, "hi": hi, "rows": n, "effective_n_matches": n, "mean_pred": mp, "actual": k / n,
                      "wilson95": list(w), "wilson_half_width_over_1_96": (w[1] - w[0]) / (2 * 1.96),
                      "sigma_clustered_se": (w[1] - w[0]) / (2 * 1.96)})
    out = {"source": str(SRC.relative_to(REPO)), "estimator": "nba_moneyline.market v1 (average closing odds, proportional)",
           "period": "SEALED_HOLDOUT_2024_26 (n=2,629 games; opened once)", "exposed_data": True,
           "sigma_method": "pooled Wilson 95% half-width / 1.96 (one row per game; field name kept for schema parity)",
           "excludes": "live early-snapshot (~17-21h before tip) estimator bias (unmeasured; prospective test)",
           "bands": [b["band"] for b in bands], "markets": {"moneyline": bands}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    for b in bands:
        print(b["band"], b["rows"], round(b["mean_pred"], 4), round(b["actual"], 4), round(b["sigma_clustered_se"], 5))
    return 0


if __name__ == "__main__":
    sys.exit(main())
