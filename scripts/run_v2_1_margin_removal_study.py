"""Phase V2-1 Workstream A -- margin-removal calibration study (pre-registered in
research/platform_v2/calibration/MARGIN_REMOVAL_PROTOCOL.md).

Football 1X2 (development 2020/21-2022/23, validation 2023/24-2024/25, least-exposed
confirmation 2025/26) and tennis DEVELOPMENT years 2021-2023 only. Tennis 2024-2025 is
NOT read here -- it is opened once by run_v2_1_tennis_holdout.py.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from prediction_markets_lab.performance.binary_classification import fit_calibration_intercept_slope
from prediction_markets_lab.research import margin_removal_methods as mrm
from prediction_markets_lab.research import probability_reliability as rel

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/calibration"
SEED = 20260923
PRIMARY_BOOKS = ("B365", "BW", "PS")
PERIODS = {"development": ("2020_21", "2021_22", "2022_23"), "validation": ("2023_24", "2024_25"),
           "confirmation_2025_26": ("2025_26",)}
RESULT_IDX = {"H": 0, "D": 1, "A": 2}
DEV_TENNIS_YEARS = (2021, 2022, 2023)


def football_panels() -> tuple[dict, dict]:
    """Return {panel_name: DataFrame(match_id, season, outcome_idx, books=list of [h,d,a])}."""
    b = pd.read_csv(REPO / "data/processed/football/cycle_001_bookmaker_markets_full.csv")
    mt = pd.read_csv(REPO / "data/processed/football/cycle_001_matches_full.csv",
                     usecols=["match_id", "season", "full_time_result"])
    mt = mt[mt.full_time_result.isin(RESULT_IDX)]
    panels: dict[str, list] = {"primary_closing_B365_BW_PS": [], "all_books_closing": [], "all_books_opening": []}
    grp = {k: g for k, g in b.dropna(subset=["home_odds", "draw_odds", "away_odds"]).groupby(["match_id", "price_timing"])}
    for r in mt.itertuples():
        for timing, name in (("closing", "all_books_closing"), ("opening", "all_books_opening")):
            g = grp.get((r.match_id, timing))
            if g is None or len(g) < 3:
                continue
            books = g[["home_odds", "draw_odds", "away_odds"]].to_numpy().tolist()
            panels[name].append((r.match_id, r.season, RESULT_IDX[r.full_time_result], books))
            if timing == "closing":
                prim = g[g.bookmaker.isin(PRIMARY_BOOKS)]
                if len(prim) == 3:
                    panels["primary_closing_B365_BW_PS"].append(
                        (r.match_id, r.season, RESULT_IDX[r.full_time_result],
                         prim[["home_odds", "draw_odds", "away_odds"]].to_numpy().tolist()))
    # 2025/26 from raw files (never processed before) -- same three books, closing
    for code in ("E0", "E1", "SC0"):
        with open(REPO / f"data/raw/football/football_data_co_uk/{code}/2025_26/{code}.csv", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row.get("FTR") not in RESULT_IDX:
                    continue
                try:
                    books = [[float(row[f"{bk}C{o}"]) for o in "HDA"] for bk in PRIMARY_BOOKS]
                except (KeyError, ValueError):
                    continue
                if any(x <= 1.0 for bk in books for x in bk):
                    continue
                mid = f"{code}_2025_26_{row['Date']}_{row['HomeTeam']}_{row['AwayTeam']}"
                panels["primary_closing_B365_BW_PS"].append((mid, "2025_26", RESULT_IDX[row["FTR"]], books))
    return {k: pd.DataFrame(v, columns=["match_id", "season", "outcome", "books"]) for k, v in panels.items()}, {}


def evaluate(prob_rows: list[list[float]], outcomes: list[int]) -> tuple[dict, np.ndarray, list, list]:
    ll = rel.multiclass_log_loss(prob_rows, outcomes)
    br = rel.multiclass_brier(prob_rows, outcomes)
    flat_p = [p for r in prob_rows for p in r]
    flat_y = [int(j == o) for r, o in zip(prob_rows, outcomes) for j in range(len(r))]
    inter, slope = fit_calibration_intercept_slope(flat_p, flat_y)
    fp, fy = np.array(flat_p), np.array(flat_y)
    bins = np.clip((fp * 10).astype(int), 0, 9)
    ece = sum(abs(fy[bins == i].mean() - fp[bins == i].mean()) * (bins == i).sum() for i in range(10) if (bins == i).any()) / len(fp)
    picks = [rel.top_pick(r) for r in prob_rows]
    pick_p = [p for _, p in picks]
    pick_w = [int(i == o) for (i, _), o in zip(picks, outcomes)]
    return ({"n": len(outcomes), "log_loss": float(ll.mean()), "brier": float(br.mean()),
             "cal_intercept": inter, "cal_slope": slope, "ece": float(ece),
             "top_pick_accuracy": float(np.mean(pick_w)), "mean_top_pick_p": float(np.mean(pick_p))},
            ll, pick_p, pick_w)


def run_block(label: str, data: dict[str, tuple[list, list]], results: list, bands: list, thresholds: list, boot: list) -> None:
    """data: period -> (per-method prob rows dict, outcomes)."""
    for period, (by_method, outcomes) in data.items():
        lls = {}
        for meth in mrm.METHODS:
            m, ll, pp, pw = evaluate(by_method[meth], outcomes)
            lls[meth] = ll
            results.append({"market": label, "period": period, "method": meth, **m})
            bands += [{"market": label, "period": period, "method": meth, **x} for x in rel.band_table(pp, pw)]
            thresholds += [{"market": label, "period": period, "method": meth, **x} for x in rel.threshold_table(pp, pw)]
        for meth in mrm.METHODS[1:]:
            d, lo, hi = rel.paired_bootstrap_ci(lls[meth], lls["multiplicative"], seed=SEED)
            boot.append({"market": label, "period": period, "method": meth, "vs": "multiplicative",
                         "log_loss_diff": d, "ci95_low": lo, "ci95_high": hi, "excludes_zero": lo > 0 or hi < 0,
                         "n": len(outcomes)})


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    panels, _ = football_panels()
    results, bands, thresholds, boot = [], [], [], []
    for pname, df in panels.items():
        data = {}
        for period, seasons in PERIODS.items():
            sub = df[df.season.isin(seasons)]
            if sub.empty:
                continue
            by_m = {meth: [mrm.consensus(bk, meth) for bk in sub.books] for meth in mrm.METHODS}
            data[period] = (by_m, sub.outcome.tolist())
        run_block(f"football_1x2::{pname}", data, results, bands, thresholds, boot)
    t = pd.read_csv(REPO / "data/interim/v2_tennis_market_dataset.csv")
    t = t[t.year.isin(DEV_TENNIS_YEARS)]  # 2024-2025 deliberately excluded
    data = {"development_2021_2023": (
        {meth: [[p, 1 - p] for p in t[f"p_a_market_{meth}"]] for meth in mrm.METHODS},
        [0 if w == 1 else 1 for w in t.outcome_a_won])}
    run_block("tennis_atp_winner::betfair_ltp_30min", data, results, bands, thresholds, boot)
    pd.DataFrame(results).to_csv(OUT / "MARGIN_REMOVAL_RESULTS.csv", index=False)
    pd.DataFrame(bands).to_csv(OUT / "HIGH_PROBABILITY_CALIBRATION.csv", index=False)
    pd.DataFrame(thresholds).to_csv(OUT / "HIGH_PROBABILITY_THRESHOLDS.csv", index=False)
    pd.DataFrame(boot).to_csv(OUT / "MARGIN_REMOVAL_BOOTSTRAP.csv", index=False)
    (OUT / "PANEL_SIZES.json").write_text(json.dumps({k: {s: int((v.season == s).sum()) for s in sorted(v.season.unique())}
                                                       for k, v in panels.items()}, indent=1))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(results).round(5).to_string())
    print(pd.DataFrame(boot).round(5).to_string())


if __name__ == "__main__":
    main()
