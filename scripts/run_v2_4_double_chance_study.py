"""Phase V2-4 Football Double Chance study on EXPOSED data (pre-registered:
research/platform_v2/double_chance/DC_PROTOCOL.md). Does NOT read 2026/27 (sealed)."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_v2_1_margin_removal_study import PERIODS, football_panels  # noqa: E402

from prediction_markets_lab.performance.binary_classification import (  # noqa: E402
    binary_auc, binary_brier_score, binary_log_loss, fit_calibration_intercept_slope)
from prediction_markets_lab.research import margin_removal_methods as mrm  # noqa: E402
from prediction_markets_lab.research import probability_reliability as rel  # noqa: E402
from prediction_markets_lab.research.double_chance import (  # noqa: E402
    DC_LABELS, best_selection, dc_outcomes, dc_probabilities)

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/double_chance"
SEED, N_BOOT, Z995 = 20260924, 1000, 2.807033768343811
THRESHOLDS = (0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
GATE_PERIODS = ("validation", "confirmation_2025_26")


def competition_of(match_ids: pd.Series) -> pd.Series:
    m = pd.read_csv(REPO / "data/processed/football/cycle_001_matches_full.csv", usecols=["match_id", "competition_code"])
    lut = dict(zip(m.match_id, m.competition_code))
    return match_ids.map(lambda x: lut.get(x, str(x).split("_")[0]))


def frame(df: pd.DataFrame, method: str) -> pd.DataFrame:
    p = np.array([mrm.consensus(b, method) for b in df.books])
    p = p / p.sum(1, keepdims=True)
    dc, won = dc_probabilities(p), dc_outcomes(df.outcome.to_numpy())
    bi, bp = best_selection(dc)
    out = pd.DataFrame({"match_id": df.match_id.values, "season": df.season.values, "comp": competition_of(df.match_id).values,
                        "best_type": [DC_LABELS[i] for i in bi], "best_p": bp, "best_won": won[np.arange(len(bi)), bi]})
    for j, lab in enumerate(DC_LABELS):
        out[f"p_{lab}"], out[f"w_{lab}"] = dc[:, j], won[:, j]
    return out


def events(f: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    p = np.concatenate([f[f"p_{l}"].to_numpy() for l in DC_LABELS])
    w = np.concatenate([f[f"w_{l}"].to_numpy() for l in DC_LABELS])
    g = np.tile(np.arange(len(f)), 3)
    return p, w, g


def calib(p: np.ndarray, w: np.ndarray, g: np.ndarray, rng: np.random.Generator) -> dict:
    a, b = fit_calibration_intercept_slope(p.tolist(), w.tolist())
    n = g.max() + 1
    idx_by = [[] for _ in range(n)]
    for k, gi in enumerate(g):
        idx_by[gi].append(k)
    idx_by = [np.array(x) for x in idx_by]
    slopes = []
    for _ in range(N_BOOT):
        take = np.concatenate([idx_by[i] for i in rng.integers(0, n, n)])
        slopes.append(fit_calibration_intercept_slope(p[take].tolist(), w[take].tolist())[1])
    lo, hi = np.percentile(slopes, [2.5, 97.5])
    return {"intercept": a, "slope": b, "slope_ci95": [float(lo), float(hi)], "slope_ci_includes_1": bool(lo <= 1 <= hi)}


def band_check(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        if r["n"] >= 200:
            lo, hi = rel.wilson(r["actual_wins"], r["n"], Z995)
            out.append({"band": r["band"], "n": r["n"], "mean_pred": r["mean_predicted"], "actual": r["actual_rate"],
                        "w995": [lo, hi], "inside": bool(lo <= r["mean_predicted"] <= hi)})
    return out


def main() -> None:
    panels, _ = football_panels()
    rng = np.random.default_rng(SEED)
    res: dict = {"protocol": "DC_PROTOCOL.md", "exposed_data": True, "periods": {}, "sensitivity": {}}
    thr_rows, band_rows, split_rows = [], [], []
    prim = frame(panels["primary_closing_B365_BW_PS"], "multiplicative")
    prim.to_csv(OUT / "DC_PRIMARY_PANEL_DERIVED.csv", index=False)
    for period, seasons in {**PERIODS, "all": tuple(sorted(prim.season.unique()))}.items():
        f = prim[prim.season.isin(seasons)]
        p, w, g = events(f)
        r = {"matches": len(f), "events": len(p), "log_loss": binary_log_loss(p.tolist(), w.tolist()),
             "brier": binary_brier_score(p.tolist(), w.tolist()), "auc": binary_auc(p.tolist(), w.tolist())}
        if period != "all":
            r["calibration_all_events"] = calib(p, w, g, rng)
        for view, (pp, ww) in {"all_events": (p, w), "best_selection": (f.best_p.to_numpy(), f.best_won.to_numpy())}.items():
            bt = rel.band_table(pp, ww)
            r[f"bands_n200_check_{view}"] = band_check(bt)
            band_rows += [{"period": period, "view": view, **x} for x in bt]
            tt = rel.threshold_table(pp, ww, THRESHOLDS)
            for x in tt:
                x["share_of_matches"] = x["n"] / len(f)
                x["wilson995"] = list(rel.wilson(x["actual_wins"], x["n"], Z995))
            thr_rows += [{"period": period, "view": view, **x} for x in tt]
        res["periods"][period] = r
    # splits: league x season, and selection type, at >=80 (best selection)
    for (comp, season), f in prim.groupby(["comp", "season"]):
        k = f.best_p >= 0.8
        split_rows.append({"split": "league_season", "comp": comp, "season": season, "matches": len(f), "n_ge80": int(k.sum()),
                           "share_ge80": k.mean(), "mean_pred": f.best_p[k].mean(), "actual": f.best_won[k].mean()})
    for season, f in prim.groupby("season"):
        k = f.best_p >= 0.8
        split_rows.append({"split": "season", "comp": "ALL", "season": season, "matches": len(f), "n_ge80": int(k.sum()),
                           "share_ge80": k.mean(), "mean_pred": f.best_p[k].mean(), "actual": f.best_won[k].mean()})
    for typ, f in prim.groupby("best_type"):
        for lab, k in (("all", f.best_p >= 0), ("ge80", f.best_p >= 0.8), ("ge90", f.best_p >= 0.9)):
            split_rows.append({"split": f"type_{lab}", "comp": typ, "season": "all", "matches": len(f), "n_ge80": int(k.sum()),
                               "share_ge80": k.sum() / len(prim), "mean_pred": f.best_p[k].mean(), "actual": f.best_won[k].mean()})
    # sensitivity: other panels / methods at the headline thresholds (best selection, all seasons)
    for pname, meth in (("primary_closing_B365_BW_PS", "odds_ratio"), ("primary_closing_B365_BW_PS", "shin"),
                        ("all_books_closing", "multiplicative"), ("all_books_opening", "multiplicative")):
        f = frame(panels[pname], meth)
        res["sensitivity"][f"{pname}::{meth}"] = {
            str(t): {"n": int((f.best_p >= t).sum()), "share": float((f.best_p >= t).mean()),
                     "mean_pred": float(f.best_p[f.best_p >= t].mean()), "actual": float(f.best_won[f.best_p >= t].mean())}
            for t in (0.8, 0.9)}
    # gate
    g = {}
    for per in GATE_PERIODS:
        r = res["periods"][per]
        g[per] = {"slope_ci_includes_1": r["calibration_all_events"]["slope_ci_includes_1"],
                  "bands_ok_all_events": all(x["inside"] for x in r["bands_n200_check_all_events"]),
                  "bands_ok_best_selection": all(x["inside"] for x in r["bands_n200_check_best_selection"])}
    seas = [s for per in GATE_PERIODS for s in PERIODS[per]]
    share_ok = all(x["share_ge80"] >= 0.15 for x in split_rows if x["split"] == "season" and x["season"] in seas)
    c1 = all(v["slope_ci_includes_1"] for v in g.values())
    c2 = all(v["bands_ok_all_events"] and v["bands_ok_best_selection"] for v in g.values())
    grade = "A" if (c1 and c2 and share_ok) else ("B" if (c1 != c2) else ("C" if not (c1 or c2) else "B"))
    res["gate"] = {"per_period": g, "ge80_share_ok_every_gate_season": share_ok, "slope_criterion": c1,
                   "band_criterion": c2, "grade": grade, "qualifier": "exposed data; sealed 2026/27 + prospective required"}
    (OUT / "DC_RESULTS.json").write_text(json.dumps(res, indent=1, default=float))
    for name, rows in (("DC_THRESHOLDS.csv", thr_rows), ("DC_BANDS.csv", band_rows), ("DC_SPLITS.csv", split_rows)):
        with (OUT / name).open("w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            wr.writeheader()
            wr.writerows(rows)
    print(json.dumps(res["gate"], indent=1))


if __name__ == "__main__":
    main()
