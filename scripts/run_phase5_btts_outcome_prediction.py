"""Phase 5 -- Football BTTS outcome-prediction cycle (2026-09-22).

Usage:
    python scripts/run_phase5_btts_outcome_prediction.py --stage development
    python scripts/run_phase5_btts_outcome_prediction.py --stage holdout

The development stage never reads 2024/25 outcomes into any fitted model or
report. The holdout stage refuses to run unless HOLDOUT_PROTOCOL.json exists and
matches the SHA-256 recorded in HOLDOUT_PROTOCOL.sha256, and refuses to run a
second time if HOLDOUT_RESULTS.json already exists (single-opening guard).

Reads only data/processed/football/cycle_002_discovery_features.csv. Fetches
nothing, modifies no production file.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from prediction_markets_lab.performance.binary_classification import (
    binary_auc,
    binary_brier_score,
    binary_log_loss,
    binary_log_loss_single,
    fit_calibration_intercept_slope,
)
from prediction_markets_lab.performance.bootstrap import paired_bootstrap_mean_diff
from prediction_markets_lab.research import btts_outcome_prediction as B

REPO = Path(__file__).resolve().parents[1]
FEATURES = REPO / "data" / "processed" / "football" / "cycle_002_discovery_features.csv"
OUT = REPO / "research" / "btts_outcome_prediction"
DATASET_OUT = REPO / "data" / "processed" / "football" / "phase5_btts_canonical_dataset.csv"
PROTOCOL = OUT / "HOLDOUT_PROTOCOL.json"
PROTOCOL_HASH = OUT / "HOLDOUT_PROTOCOL.sha256"
HOLDOUT_RESULTS = OUT / "HOLDOUT_RESULTS.json"
BOOTSTRAP_SEED = 20260922
BOOTSTRAP_RESAMPLES = 2000
ERROR_ANALYSIS_THRESHOLD = 0.60


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def load() -> list[B.BttsMatch]:
    with open(FEATURES, newline="", encoding="utf-8") as f:
        return B.build_btts_dataset(csv.DictReader(f))


def metrics(preds: list[B.Prediction]) -> dict:
    if not preds:
        return {"n": 0}
    p = [x.p_yes for x in preds]
    y = [x.actual for x in preds]
    tp = B.top_prediction_summary(preds)
    yes_ok = sum(1 for x in preds if x.p_yes > 0.5 and x.actual == 1)
    no_ok = sum(1 for x in preds if x.p_yes <= 0.5 and x.actual == 0)
    n_yes, n_no = sum(y), len(y) - sum(y)
    try:
        inter, slope = fit_calibration_intercept_slope(p, y)
    except ValueError:  # e.g. a constant-probability model (naive within one season): slope undefined
        inter, slope = None, None
    dec = B.decile_calibration(preds)
    ece = sum(abs(r["gap_pp"]) * r["n"] for r in dec if r["n"]) / len(preds) / 100
    return {
        "n": len(preds),
        "base_rate_yes": n_yes / len(y),
        "mean_predicted_yes": sum(p) / len(p),
        "log_loss": binary_log_loss(p, y),
        "brier": binary_brier_score(p, y),
        "auc": binary_auc(p, y),
        "accuracy": tp["accuracy"],
        "balanced_accuracy": 0.5 * (yes_ok / n_yes + no_ok / n_no),
        "calibration_intercept": inter,
        "calibration_slope": slope,
        "ece_decile": ece,
        "min_p_yes": min(p),
        "max_p_yes": max(p),
        "share_top_pick_ge_0_60": sum(1 for q in p if max(q, 1 - q) >= 0.60) / len(p),
    }


def model_table(preds: dict[str, list[B.Prediction]], partition: str) -> list[dict]:
    return [{"partition": partition, "model": k, "fitted_parameters": B.MODEL_FITTED_PARAMETERS[k], **metrics(v)}
            for k, v in preds.items()]


def bootstrap_vs(preds_common: dict[str, list[B.Prediction]], ref: str) -> list[dict]:
    ref_ll = [binary_log_loss_single(x.p_yes, x.actual) for x in preds_common[ref]]
    rows = []
    for k, v in preds_common.items():
        if k == ref:
            continue
        ll = [binary_log_loss_single(x.p_yes, x.actual) for x in v]
        r = paired_bootstrap_mean_diff(ll, ref_ll, seed=BOOTSTRAP_SEED, n_resamples=BOOTSTRAP_RESAMPLES)
        rows.append({"model": k, "reference": ref, "log_loss_diff_vs_reference": r.point_estimate,
                     "ci95_low": r.ci_lower, "ci95_high": r.ci_upper, "excludes_zero": r.excludes_zero, "n": r.n})
    return rows


def select_estimator(preds_common: dict[str, list[B.Prediction]]) -> tuple[str, list[dict]]:
    """Pre-registered rule (PRE_REGISTRATION.md)."""
    ll = {k: binary_log_loss([x.p_yes for x in v], [x.actual for x in v]) for k, v in preds_common.items()}
    winner = min(ll, key=ll.get)
    boot = bootstrap_vs(preds_common, winner)
    simpler = [r for r in boot if not r["excludes_zero"]
               and B.MODEL_FITTED_PARAMETERS[r["model"]] < B.MODEL_FITTED_PARAMETERS[winner]]
    if simpler:
        simpler.sort(key=lambda r: (B.MODEL_FITTED_PARAMETERS[r["model"]], r["log_loss_diff_vs_reference"]))
        return simpler[0]["model"], boot
    return winner, boot


def band_rows(preds: dict[str, list[B.Prediction]], partition: str) -> list[dict]:
    rows = []
    for k, v in preds.items():
        for side in ("YES", "NO"):
            for r in B.probability_band_report(v, side):
                rows.append({"partition": partition, "model": k, **r})
    return rows


def high_rows(preds: dict[str, list[B.Prediction]], partition: str) -> list[dict]:
    return [{"partition": partition, "model": k, **r} for k, v in preds.items() for r in B.high_probability_report(v)]


def calib_rows(preds: dict[str, list[B.Prediction]], partition: str) -> list[dict]:
    return [{"partition": partition, "model": k, **r} for k, v in preds.items() for r in B.decile_calibration(v)]


def top_breakdown(preds: list[B.Prediction], partition: str, model: str) -> list[dict]:
    rows = [{"partition": partition, "model": model, "group": "ALL", **B.top_prediction_summary(preds)}]
    for key in ("season", "competition"):
        for g in sorted({getattr(p, key) for p in preds}):
            rows.append({"partition": partition, "model": model, "group": f"{key}={g}",
                         **B.top_prediction_summary([p for p in preds if getattr(p, key) == g])})
    return rows


DISCOVERY_EXTRA = (
    "p_poisson", "p_market_implied_closing", "lambda_poisson_home", "lambda_poisson_away", "lambda_poisson_min",
    "lambda_market_home", "lambda_market_away", "lambda_market_min",
    "market_1x2_closing_draw_probability", "market_ou25_closing_source_avg_over_probability", "abs_elo_gap",
    "home_failed_to_score_rate_l10", "away_failed_to_score_rate_l10",
    "home_team_overall_last10_goal_diff_volatility", "away_team_overall_last10_goal_diff_volatility",
)


def feature_value(m: B.BttsMatch, f: str) -> float | None:
    if f in m.features:
        return m.features[f]
    if f == "p_poisson":
        return m.p_poisson
    if f == "p_market_implied_closing":
        return m.p_market_implied_closing
    if f.startswith("lambda_poisson"):
        lp = m.lambda_poisson
        return None if lp is None else {"home": lp[0], "away": lp[1], "min": min(lp)}[f.rsplit("_", 1)[1]]
    if f.startswith("lambda_market"):
        lp = m.lambda_market_closing
        return None if lp is None else {"home": lp[0], "away": lp[1], "min": min(lp)}[f.rsplit("_", 1)[1]]
    v = m.context.get(f)
    return None if v is None or isinstance(v, bool) else float(v)


def discovery(matches: list[B.BttsMatch], seasons: tuple[str, ...]) -> dict[str, dict]:
    sub = [m for m in matches if m.season in seasons]
    out = {}
    for f in tuple(B.DATA_FEATURES) + DISCOVERY_EXTRA:
        pairs = [(feature_value(m, f), m.target) for m in sub]
        pairs = [(v, t) for v, t in pairs if v is not None]
        yes = [v for v, t in pairs if t == 1]
        no = [v for v, t in pairs if t == 0]
        out[f] = {
            "n": len(pairs), "mean_yes": sum(yes) / len(yes) if yes else None,
            "mean_no": sum(no) / len(no) if no else None, "cohens_d": B.cohens_d(yes, no),
            "univariate_auc": B.univariate_auc([v for v, _ in pairs], [t for _, t in pairs]),
        }
    return out


def error_analysis(matches: list[B.BttsMatch], preds: list[B.Prediction]) -> dict:
    by_id = {m.match_id: m for m in matches}
    sel = []
    for p in preds:
        side, prob = B.top_pick(p.p_yes)
        if prob >= ERROR_ANALYSIS_THRESHOLD:
            sel.append((p, side, int((side == "YES") == (p.actual == 1))))
    res: dict = {"threshold": ERROR_ANALYSIS_THRESHOLD, "n": len(sel),
                 "correct": sum(c for *_, c in sel), "by_characteristic": {}}
    def split(name: str, fn) -> None:
        groups: dict[str, list[int]] = {}
        for p, side, c in sel:
            g = fn(by_id[p.match_id], side)
            groups.setdefault(str(g), []).append(c)
        res["by_characteristic"][name] = {
            g: {"n": len(v), "accuracy": sum(v) / len(v), "wilson95": B.wilson_interval(sum(v), len(v))}
            for g, v in sorted(groups.items())
        }
    split("pick_side", lambda m, s: s)
    split("competition", lambda m, s: m.competition)
    split("season", lambda m, s: m.season)
    split("season_stage", lambda m, s: "early(<=6)" if m.context["season_match_number"] <= 6 else "later(>6)")
    split("history_depth", lambda m, s: "thin(<10)" if m.context["min_history_matches"] < 10 else "full(10)")
    split("new_to_competition", lambda m, s: bool(m.context["home_new_to_competition"]) or bool(m.context["away_new_to_competition"]))
    gaps = sorted(m.context["abs_elo_gap"] for m in matches if m.context.get("abs_elo_gap") is not None)
    q = gaps[int(len(gaps) * 0.75)] if gaps else 0.0
    split("elo_mismatch_top_quartile", lambda m, s: (m.context.get("abs_elo_gap") or 0) >= q)
    vols = sorted(v for m in matches for v in [m.context.get("home_team_overall_last10_goal_diff_volatility")] if v is not None)
    vq = vols[int(len(vols) * 0.75)] if vols else 0.0
    split("home_volatility_top_quartile", lambda m, s: (m.context.get("home_team_overall_last10_goal_diff_volatility") or 0) >= vq)
    res["thresholds_used"] = {"abs_elo_gap_q75": q, "home_goal_diff_volatility_q75": vq}
    return res


def dataset_rows(matches: list[B.BttsMatch]) -> list[dict]:
    rows = []
    for m in matches:
        r = {"match_id": m.match_id, "season": m.season, "match_date": m.match_date.isoformat(),
             "competition": m.competition, "home_team": m.home_team, "away_team": m.away_team,
             "btts_yes": m.target, "home_goals": m.home_goals, "away_goals": m.away_goals}
        r.update({f: m.features.get(f) for f in B.DATA_FEATURES})
        r.update({k: v for k, v in m.context.items()})
        r["lambda_poisson_home"], r["lambda_poisson_away"] = m.lambda_poisson or (None, None)
        r["p_btts_poisson"] = m.p_poisson
        r["lambda_market_closing_home"], r["lambda_market_closing_away"] = m.lambda_market_closing or (None, None)
        r["p_btts_market_implied_closing"] = m.p_market_implied_closing
        r["p_btts_market_implied_opening"] = m.p_market_implied_opening
        rows.append(r)
    return rows


def run_development() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    matches = load()
    write_csv(DATASET_OUT, dataset_rows(matches))
    dev_matches = [m for m in matches if m.season != B.HOLDOUT_SEASON]  # holdout outcomes never enter this stage

    disc = discovery(dev_matches, B.DISCOVERY_SEASONS)
    val = discovery(dev_matches, (B.VALIDATION_SEASON,))
    disc_rows, stab_rows = [], []
    for f, d in disc.items():
        disc_rows.append({"feature": f, "partition": "discovery_2020_21-2022_23", **d})
        v = val[f]
        dd, vd = d["cohens_d"], v["cohens_d"]
        verdict = "INSUFFICIENT_DATA" if dd is None or vd is None else (
            "STABLE" if (dd > 0) == (vd > 0) and abs(vd) >= 0.5 * abs(dd) else
            ("SIGN_FLIP" if (dd > 0) != (vd > 0) and min(abs(dd), abs(vd)) > 0.02 else "WEAKENED"))
        stab_rows.append({"feature": f, "discovery_d": dd, "validation_2023_24_d": vd,
                          "discovery_auc": d["univariate_auc"], "validation_auc": v["univariate_auc"],
                          "stability": verdict})
    disc_rows.sort(key=lambda r: -abs(r["cohens_d"] or 0))
    write_csv(OUT / "OUTCOME_DISCOVERY.csv", disc_rows)
    write_csv(OUT / "FEATURE_STABILITY.csv", stab_rows)

    all_keys = B.MODEL_KEYS + B.SENSITIVITY_MODEL_KEYS
    pooled = B.run_expanding_walk_forward(dev_matches, B.DEVELOPMENT_EVAL_SEASONS, all_keys)
    common = B.restrict_to_common({k: pooled[k] for k in B.MODEL_KEYS})
    common_all = B.restrict_to_common(pooled)
    validation = {k: [p for p in v if p.season == B.VALIDATION_SEASON] for k, v in common_all.items()}
    selected, boot = select_estimator(common)

    comp_rows = (model_table(pooled, "dev_pooled_own_coverage") + model_table(common_all, "dev_pooled_common")
                 + model_table(validation, "validation_2023_24_common"))
    for s in B.DEVELOPMENT_EVAL_SEASONS:
        comp_rows += model_table({k: [p for p in v if p.season == s] for k, v in common_all.items()}, f"season_{s}_common")
    write_csv(OUT / "MODEL_COMPARISON.csv", comp_rows)
    write_csv(OUT / "DEV_BOOTSTRAP_VS_BEST.csv", boot)
    write_csv(OUT / "CALIBRATION.csv", calib_rows(common_all, "dev_pooled_common"))
    write_csv(OUT / "PROBABILITY_BANDS.csv", band_rows(common_all, "dev_pooled_common"))
    write_csv(OUT / "HIGH_PROBABILITY_ANALYSIS.csv", high_rows(common_all, "dev_pooled_common"))
    top = []
    for k, v in common_all.items():
        top += top_breakdown(v, "dev_pooled_common", k)
    write_csv(OUT / "TOP_PREDICTION_PERFORMANCE.csv", top)
    ea = {k: error_analysis(dev_matches, common_all[k]) for k in (selected, "data_logit", "market_implied_poisson")}
    write_csv(OUT / "predictions_development.csv",
              [{"model": k, **p.__dict__} for k, v in common_all.items() for p in v])
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_matches_total": len(matches), "n_matches_development": len(dev_matches),
        "base_rate_by_season": {s: sum(m.target for m in matches if m.season == s) / sum(1 for m in matches if m.season == s)
                                 for s in B.SEASONS_IN_ORDER if s != B.HOLDOUT_SEASON},
        "selected_estimator": selected, "selection_rule": "PRE_REGISTRATION.md",
        "dev_common_n": len(next(iter(common.values()))),
        "dev_metrics_common": {k: metrics(v) for k, v in common_all.items()},
        "validation_metrics_common": {k: metrics(v) for k, v in validation.items()},
        "bootstrap_vs_best": boot, "error_analysis": ea,
        "config": B.DEFAULT_CONFIG.__dict__,
    }
    (OUT / "DEV_RESULTS.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps({"selected": selected, "dev": summary["dev_metrics_common"],
                      "val": summary["validation_metrics_common"], "boot": boot}, indent=1, default=str))


def run_holdout() -> None:
    if HOLDOUT_RESULTS.exists():
        sys.exit("REFUSED: holdout already opened once (HOLDOUT_RESULTS.json exists).")
    if not PROTOCOL.exists() or not PROTOCOL_HASH.exists():
        sys.exit("REFUSED: frozen HOLDOUT_PROTOCOL.json + .sha256 required before opening holdout.")
    digest = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    if digest != PROTOCOL_HASH.read_text().split()[0]:
        sys.exit("REFUSED: HOLDOUT_PROTOCOL.json does not match its frozen hash.")
    protocol = json.loads(PROTOCOL.read_text())
    selected = protocol["selected_estimator"]
    matches = load()
    all_keys = B.MODEL_KEYS + B.SENSITIVITY_MODEL_KEYS
    preds = B.run_expanding_walk_forward(matches, (B.HOLDOUT_SEASON,), all_keys)
    common = B.restrict_to_common(preds)
    boot = bootstrap_vs(common, selected)
    filters = {}
    by_id = {m.match_id: m for m in matches}
    for flt in protocol.get("reliability_filters_to_test", []):
        name, field, op, val = flt["name"], flt["context_field"], flt["op"], flt["value"]
        def keep(p: B.Prediction) -> bool:
            m = by_id[p.match_id]
            v = m.context.get(field) if field in m.context else getattr(m, field, None)
            if v is None:
                return False
            return {">": v > val, "<=": v <= val, "==": v == val, "!=": v != val}[op] if op != ">" else v > val
        base = [p for p in common[selected] if B.top_pick(p.p_yes)[1] >= ERROR_ANALYSIS_THRESHOLD]
        kept = [p for p in base if keep(p)]
        dropped = [p for p in base if not keep(p)]
        acc = lambda ps: (sum(int((B.top_pick(p.p_yes)[0] == "YES") == (p.actual == 1)) for p in ps) / len(ps)) if ps else None
        filters[name] = {"definition": flt, "n_base": len(base), "acc_base": acc(base),
                         "n_kept": len(kept), "acc_kept": acc(kept), "n_dropped": len(dropped), "acc_dropped": acc(dropped)}
    result = {
        "opened_at": datetime.now(timezone.utc).isoformat(), "protocol_sha256": digest,
        "selected_estimator": selected, "n": len(common[selected]),
        "base_rate_yes": sum(p.actual for p in common[selected]) / len(common[selected]),
        "metrics": {k: metrics(v) for k, v in common.items()},
        "bootstrap_vs_selected": boot, "reliability_filters": filters,
        "error_analysis_selected": error_analysis(matches, common[selected]),
    }
    HOLDOUT_RESULTS.write_text(json.dumps(result, indent=1, default=str))
    write_csv(OUT / "HOLDOUT_PROBABILITY_BANDS.csv", band_rows(common, "holdout_2024_25"))
    write_csv(OUT / "HOLDOUT_HIGH_PROBABILITY.csv", high_rows(common, "holdout_2024_25"))
    write_csv(OUT / "HOLDOUT_CALIBRATION.csv", calib_rows(common, "holdout_2024_25"))
    top = []
    for k, v in common.items():
        top += top_breakdown(v, "holdout_2024_25", k)
    write_csv(OUT / "HOLDOUT_TOP_PREDICTION.csv", top)
    write_csv(OUT / "predictions_holdout.csv", [{"model": k, **p.__dict__} for k, v in common.items() for p in v])
    print(json.dumps({k: result[k] for k in ("selected_estimator", "n", "base_rate_yes", "metrics", "bootstrap_vs_selected", "reliability_filters")}, indent=1, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("development", "holdout"), required=True)
    a = ap.parse_args()
    run_development() if a.stage == "development" else run_holdout()
