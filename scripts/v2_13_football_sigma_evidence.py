"""V2-13: football Stage A uncertainty evidence from EXISTING historical calibration bands (no fitting, no new data).

Source sample: research/platform_v2/double_chance/DC_PRIMARY_PANEL_DERIVED.csv (V2-4; 5,897 E0/E1/SC0 matches,
2020/21-2025/26, B365/BW/PS CLOSING odds, per-book multiplicative de-vig, mean consensus, renormalised). 1X2 outcome
probabilities are recovered exactly from the DC sums: P(H)=1-P(X2), P(D)=1-P(12), P(A)=1-P(1X).

Per market and coarse probability band (the same bands as the tennis V2-7 sigma) it reports rows, effective N (distinct
matches), mean predicted, realised rate, Wilson 95% and a match-clustered bootstrap SE of the realised rate. The Stage A
sigma for a band is that clustered SE: the sampling precision of the historical calibration evidence. It is NOT an
estimate of the live 24-48h estimator's bias (unmeasured; see the pre-registration). All data are exposed.
Output: research/platform_v2/v2_13_football/FOOTBALL_SIGMA_EVIDENCE.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from prediction_markets_lab.research.probability_reliability import wilson

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "research/platform_v2/double_chance/DC_PRIMARY_PANEL_DERIVED.csv"
OUT = REPO / "research/platform_v2/v2_13_football/FOOTBALL_SIGMA_EVIDENCE.json"
BANDS = ((0.0, 0.50, "<50%"), (0.50, 0.65, "50-65%"), (0.65, 0.80, "65-80%"), (0.80, 1.0000001, "80%+"))
SEED, N_BOOT = 20261001, 1000


def long_rows(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """One row per (match, selection): market 1x2 (H/D/A) and double_chance (1X/X2/12)."""
    h_won = (df.w_1X == 1) & (df.w_12 == 1)
    d_won = (df.w_1X == 1) & (df.w_X2 == 1)
    a_won = (df.w_X2 == 1) & (df.w_12 == 1)
    x12 = pd.concat([pd.DataFrame({"match_id": df.match_id, "p": 1 - df.p_X2, "y": h_won.astype(int)}),
                     pd.DataFrame({"match_id": df.match_id, "p": 1 - df.p_12, "y": d_won.astype(int)}),
                     pd.DataFrame({"match_id": df.match_id, "p": 1 - df.p_1X, "y": a_won.astype(int)})])
    dc = pd.concat([pd.DataFrame({"match_id": df.match_id, "p": df[f"p_{s}"], "y": df[f"w_{s}"]}) for s in ("1X", "X2", "12")])
    return {"1x2": x12.reset_index(drop=True), "double_chance": dc.reset_index(drop=True)}


def clustered_se(rows: pd.DataFrame, rng: np.random.Generator) -> float:
    by = rows.groupby("match_id").y.agg(["sum", "count"])
    s, c = by["sum"].to_numpy(), by["count"].to_numpy()
    n = len(by)
    draws = rng.integers(0, n, size=(N_BOOT, n))
    rates = s[draws].sum(1) / c[draws].sum(1)
    return float(rates.std(ddof=1))


def main() -> int:
    df = pd.read_csv(SRC)
    # internal consistency: each match's three outcomes must be exactly one of H/D/A
    rows = long_rows(df)
    chk = rows["1x2"].groupby("match_id").y.sum()
    assert (chk == 1).all(), "1X2 outcomes not exclusive"
    rng = np.random.default_rng(SEED)
    out = {"source": str(SRC.relative_to(REPO)), "estimator": "closing B365/BW/PS, multiplicative de-vig, mean, renormalised",
           "seasons": sorted(df.season.unique().tolist()), "matches": int(len(df)), "exposed_data": True,
           "sigma_method": "match-clustered bootstrap SE of the band's realised rate (1000 resamples, seed fixed)",
           "excludes": "live 24-48h median-of-UK-books estimator bias (unmeasured; prospective test)",
           "bands": [b[2] for b in BANDS], "markets": {}}
    for market, r in rows.items():
        out["markets"][market] = []
        for lo, hi, lab in BANDS:
            m = r[(r.p >= lo) & (r.p < hi)]
            k, n = int(m.y.sum()), len(m)
            w = wilson(k, n)
            out["markets"][market].append({
                "band": lab, "lo": lo, "hi": min(hi, 1.0), "rows": n, "effective_n_matches": int(m.match_id.nunique()),
                "mean_pred": float(m.p.mean()), "actual": float(m.y.mean()), "wilson95": list(w),
                "wilson_half_width_over_1_96": float((w[1] - w[0]) / (2 * 1.96)),
                "sigma_clustered_se": clustered_se(m, rng)})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    for mk, bs in out["markets"].items():
        for b in bs:
            print(mk, b["band"], b["rows"], b["effective_n_matches"], round(b["mean_pred"], 4), round(b["actual"], 4),
                  round(b["sigma_clustered_se"], 5), round(b["wilson_half_width_over_1_96"], 5))
    return 0


if __name__ == "__main__":
    sys.exit(main())
