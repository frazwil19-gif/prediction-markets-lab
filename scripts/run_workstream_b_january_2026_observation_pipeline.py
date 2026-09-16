#!/usr/bin/env python3
"""WORKSTREAM B -- real market-observation pipeline for January 2026.

Per the operator's "WORKSTREAM B -- REAL MARKET OBSERVATION PIPELINE"
prompt (2026-09-16), following the real Betfair sample audit
(research/cycles/CYCLE_002_TENNIS/WORKSTREAM_B_SAMPLE_AUDIT_REPORT.md).

**January 2026 is a PIPELINE-VALIDATION / EXPLORATORY dataset, not
evidence of a betting edge.** N=137. This script builds the observation
pipeline, audits real timestamp density, and runs a bounded descriptive
Elo-vs-market analysis. It does NOT choose a betting threshold and does
NOT promote any relationship it finds -- any interesting pattern is
recorded as a candidate hypothesis requiring fresh validation, per the
operator's explicit instruction.

Global Elo is the FROZEN Tennis Cycle 1 candidate (k_factor=32.0, no
calibration, no added features) -- this script extends its chronological
rating simulation forward through January 2026 using a4.run_elo_model
UNCHANGED (same function, same training-season calibration, just fed a
longer chronologically-ordered dataframe), exactly mirroring how
run_cycle_002_tennis_2025_holdout.py extended it through 2025. The
k_factor consistency assertion below is the same guard used there.

This script depends on Fraser's real Betfair BASIC sample being present
on his machine at ~/Downloads/BASIC (mounted here at ~/mnt/BASIC via the
device bridge) -- it cannot run standalone in CI/a fresh checkout, and
is not intended to (this is a one-off research analysis script, not a
reusable ingestion step; anything worth keeping reusable was factored
into src/prediction_markets_lab/research/market_observation.py and
covered by tests there instead).

Run:
    python scripts/run_workstream_b_january_2026_observation_pipeline.py
"""
from __future__ import annotations

import bz2
import importlib.util
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.ingestion.betfair_historical_schema import (  # noqa: E402
    latest_singles_event_candidates,
    parse_market_change_line,
)
from prediction_markets_lab.normalisation.tennis_betfair_linkage import (  # noqa: E402
    TMLMatchRecord,
    classify_all,
)
from prediction_markets_lab.research.market_observation import (  # noqa: E402
    build_pre_match_observation,
)

RAW_2026_PATH = REPO_ROOT / "data" / "raw" / "tennis" / "tml_database" / "atp" / "2026.csv"
CANONICAL_2026_PATH = (
    REPO_ROOT / "data" / "processed" / "tennis" / "workstream_b_canonical_matches_2026_partial.csv"
)
BETFAIR_JAN_ROOT = Path(os.path.expanduser("~/mnt/BASIC/2026/Jan"))
REPORT_PATH = (
    REPO_ROOT / "research" / "cycles" / "CYCLE_002_TENNIS" / "WORKSTREAM_B_JANUARY_2026_OBSERVATION_REPORT.md"
)
OBSERVATIONS_PATH = REPO_ROOT / "data" / "interim" / "workstream_b_january_2026_observations.csv"

FROZEN_K_FACTOR = 32.0

# Candidate horizons to AUDIT (not to freeze) -- per the operator's
# explicit instruction, the actual horizons used for analysis are chosen
# from what the density audit below shows, not pre-committed here.
CANDIDATE_HORIZONS_MINUTES = {
    "24h": 24 * 60, "12h": 12 * 60, "6h": 6 * 60, "3h": 3 * 60,
    "1h": 60, "30min": 30, "10min": 10,
}


def _load_module(path: Path, name: str):
    # sys.modules registration is needed here (unlike the other scripts'
    # identical-looking helper) because this is the first script to
    # dynamically load canonicalise_cycle_002_tennis_match_data.py, whose
    # own @dataclass definition needs its module registered in
    # sys.modules to resolve type hints on Python 3.11 -- discovered by
    # a real ImportError/AttributeError while building this pipeline.
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def canonicalise_2026(canon) -> pd.DataFrame:
    """Canonicalise the raw 2026 TML rows using the SAME frozen
    canonicalise_row/mark_upstream_duplicates logic as the 2021-2025
    canonical dataset -- reused unchanged, never duplicated. Written to
    its own file, NEVER to the frozen cycle_002_canonical_matches.csv."""
    raw = pd.read_csv(RAW_2026_PATH)
    raw["_season"] = 2026
    raw["_source_row_index"] = raw.index
    raw["_source_file"] = "2026.csv"
    is_dupe = canon.mark_upstream_duplicates(raw)
    working = raw[~is_dupe].copy()
    records = [canon.canonicalise_row(row) for _, row in working.iterrows()]
    df = pd.DataFrame(records)
    df = df[~df["walkover"]].reset_index(drop=True)
    df["tourney_date"] = pd.to_datetime(df["tourney_date"], format="%Y%m%d")
    CANONICAL_2026_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CANONICAL_2026_PATH, index=False)
    return df


def run_forward_elo(a4, holdout_mod, canonical_2026: pd.DataFrame) -> tuple[dict, float]:
    """Extend the frozen Global Elo simulation from 2021-2025 through
    January 2026, using a4.run_elo_model completely UNCHANGED. k_factor
    is recalibrated on the same 2021-2023 training rows only (unaffected
    by how much data follows) as a consistency check that it still equals
    the frozen 32.0 -- this is not re-tuning, it's the same guard used in
    run_cycle_002_tennis_2025_holdout.py."""
    df_2021_2025 = holdout_mod.load_matches_including_holdout(a4)
    combined = pd.concat([df_2021_2025, canonical_2026], ignore_index=True)
    combined["_round_order"] = combined["round"].map(a4.ROUND_ORDER).fillna(-1)
    combined = combined.sort_values(["tourney_date", "_round_order", "match_num"]).reset_index(drop=True)
    preds, k = a4.run_elo_model(combined, a4.global_rating_key)
    if k != FROZEN_K_FACTOR:
        raise RuntimeError(f"re-derived k_factor {k} != frozen {FROZEN_K_FACTOR} -- STOP, do not proceed")
    return preds, k


def scan_betfair_january_market_files() -> dict[str, Path]:
    market_files: dict[str, Path] = {}
    for day in sorted(os.listdir(BETFAIR_JAN_ROOT), key=lambda x: int(x)):
        ddir = BETFAIR_JAN_ROOT / day
        for ev in os.listdir(ddir):
            edir = ddir / ev
            for fn in os.listdir(edir):
                if fn.startswith("1.") and fn.endswith(".bz2"):
                    market_files[fn[:-4]] = edir / fn
    return market_files


def load_market_messages(path: Path) -> list:
    with bz2.open(path, "rt") as fh:
        lines = [line.strip() for line in fh if line.strip()]
    messages = []
    for line in lines:
        messages.extend(parse_market_change_line(line))
    return messages


def extract_market_facts(messages: list):
    """From one market's full message history: the FINAL scheduled start
    (last non-null marketDefinition.market_time -- the post-revision,
    authoritative one, per the real date-drift discovery in the sample
    audit), the final runner id->name map, and per-selection (timestamp,
    ltp) price series plus a (timestamp, status, in_play) definition
    timeline."""
    final_market_time = None
    final_runners: dict[int, str] = {}
    price_series: dict[int, list[tuple[datetime, float]]] = {}
    definition_timeline: list[tuple[datetime, str | None, bool | None]] = []

    for msg in messages:
        if msg.market_definition is not None:
            md = msg.market_definition
            if md.market_time is not None:
                final_market_time = md.market_time
            for runner in md.runners:
                if runner.name is not None:
                    final_runners[runner.selection_id] = runner.name
            if msg.published_at is not None:
                definition_timeline.append((msg.published_at, md.status, None))
        for rc in msg.runner_changes:
            if rc.last_traded_price is not None and msg.published_at is not None:
                price_series.setdefault(rc.selection_id, []).append((msg.published_at, rc.last_traded_price))

    for sel_id in price_series:
        price_series[sel_id].sort(key=lambda item: item[0])
    definition_timeline.sort(key=lambda item: item[0])

    return final_market_time, final_runners, price_series, definition_timeline


def status_at_or_before(timeline, cutoff):
    eligible = [t for t in timeline if t[0] <= cutoff]
    if not eligible:
        return None
    return max(eligible, key=lambda t: t[0])[1]


def main() -> int:
    a4 = _load_module(REPO_ROOT / "scripts" / "run_cycle_002_tennis_checkpoint_a4.py", "a4")
    holdout_mod = _load_module(REPO_ROOT / "scripts" / "run_cycle_002_tennis_2025_holdout.py", "holdout_mod")
    canon = _load_module(REPO_ROOT / "scripts" / "canonicalise_cycle_002_tennis_match_data.py", "canon")

    canonical_2026 = canonicalise_2026(canon)
    print(f"Canonicalised {len(canonical_2026)} January 2026 ATP matches.")

    elo_preds, k = run_forward_elo(a4, holdout_mod, canonical_2026)
    print(f"Forward Elo simulation OK, k_factor confirmed = {k}")

    tml_matches = [
        TMLMatchRecord(
            match_id=row["match_id"], match_date=row["tourney_date"].date(),
            player_a_name=row["player_a_name"], player_b_name=row["player_b_name"],
        )
        for _, row in canonical_2026.iterrows()
    ]

    market_files = scan_betfair_january_market_files()
    print(f"Scanning {len(market_files)} real per-market files for January 2026 candidates...")
    all_messages_by_market = {mid: load_market_messages(path) for mid, path in market_files.items()}
    candidates_by_market = {}
    for mid, messages in all_messages_by_market.items():
        cands = latest_singles_event_candidates(messages)
        candidates_by_market.update(cands)
    candidates = list(candidates_by_market.values())
    print(f"Real Match Odds singles candidates: {len(candidates)}")

    results = classify_all(tml_matches, candidates)
    print(f"MATCHED={len(results['MATCHED'])} AMBIGUOUS={len(results['AMBIGUOUS'])} UNMATCHED={len(results['UNMATCHED'])}")

    canonical_by_id = {row["match_id"]: row for _, row in canonical_2026.iterrows()}

    # --- timestamp-density audit (data-driven, before any threshold choice) ---
    density_counts = {label: 0 for label in CANDIDATE_HORIZONS_MINUTES}
    stale_over_1h_counts = {label: 0 for label in CANDIDATE_HORIZONS_MINUTES}
    missing_ltp_matches = 0
    n_matched_with_final_time = 0

    observations = []
    hypothesis_rows = []

    for result in results["MATCHED"]:
        match_id = result.tml_match_id
        market_id = result.matched_market_id
        canonical_row = canonical_by_id[match_id]
        messages = all_messages_by_market[market_id]
        final_market_time, final_runners, price_series, definition_timeline = extract_market_facts(messages)
        if final_market_time is None:
            continue
        n_matched_with_final_time += 1

        # Map selection_id -> is_player_a via name matching against the canonical row.
        from prediction_markets_lab.normalisation.tennis_betfair_linkage import names_are_equivalent

        sel_a = sel_b = None
        for sel_id, name in final_runners.items():
            if names_are_equivalent(canonical_row["player_a_name"], name):
                sel_a = sel_id
            elif names_are_equivalent(canonical_row["player_b_name"], name):
                sel_b = sel_id
        if sel_a is None or sel_b is None:
            continue  # wrong-runner-mapping guard: skip rather than guess

        p_a = elo_preds.get(match_id)
        if p_a is None:
            continue
        outcome_a_won = bool(canonical_row["outcome_a_won"])

        series_a = price_series.get(sel_a, [])
        series_b = price_series.get(sel_b, [])
        if not series_a and not series_b:
            missing_ltp_matches += 1

        for label, minutes in CANDIDATE_HORIZONS_MINUTES.items():
            for is_a, sel_id, own_series, other_series, name, model_p in (
                (True, sel_a, series_a, series_b, canonical_row["player_a_name"], p_a),
                (False, sel_b, series_b, series_a, canonical_row["player_b_name"], 1.0 - p_a),
            ):
                cutoff_status = status_at_or_before(definition_timeline, final_market_time)
                obs = build_pre_match_observation(
                    match_id=match_id, event_id=result.matched_market_id, market_id=market_id,
                    runner_id=sel_id, player_name=name, is_player_a=is_a,
                    scheduled_start=final_market_time, horizon_label=label,
                    requested_horizon_minutes=float(minutes), model_probability=model_p,
                    own_price_series=own_series, other_player_price_series=other_series,
                    market_status_at_cutoff=cutoff_status, in_play_at_cutoff=False,
                    outcome_won=outcome_a_won if is_a else (not outcome_a_won),
                )
                observations.append(obs)
                if obs.snapshot_available:
                    density_counts[label] += 1
                    if obs.price_age_seconds is not None and obs.price_age_seconds > 3600:
                        stale_over_1h_counts[label] += 1

    n_matched = len(results["MATCHED"])
    density_report = {
        label: {
            "coverage_pct": round(100.0 * density_counts[label] / max(n_matched * 2, 1), 1),
            "stale_over_1h_pct_of_available": round(
                100.0 * stale_over_1h_counts[label] / max(density_counts[label], 1), 1
            ),
        }
        for label in CANDIDATE_HORIZONS_MINUTES
    }

    # --- descriptive Elo-vs-market analysis at the best-covered practical horizon ---
    best_label = max(density_report, key=lambda lbl: density_report[lbl]["coverage_pct"])
    analysis_rows = [
        o for o in observations
        if o.horizon_label == best_label and o.snapshot_available and o.market_reference_probability is not None
    ]
    deltas = [o.model_market_probability_delta for o in analysis_rows]
    outcomes = [o.outcome_won for o in analysis_rows]

    bins = [(-1.0, -0.10), (-0.10, -0.03), (-0.03, 0.03), (0.03, 0.10), (0.10, 1.0)]
    bin_stats = []
    for lo, hi in bins:
        in_bin = [(d, w) for d, w in zip(deltas, outcomes) if lo <= d < hi]
        if in_bin:
            win_rate = sum(1 for _, w in in_bin if w) / len(in_bin)
        else:
            win_rate = None
        bin_stats.append({"delta_range": f"[{lo:+.2f}, {hi:+.2f})", "n": len(in_bin), "outcome_rate": win_rate})

    delta_mean = statistics.mean(deltas) if deltas else None
    delta_stdev = statistics.stdev(deltas) if len(deltas) > 1 else None

    print(f"\nBest-covered horizon for analysis: {best_label} ({density_report[best_label]['coverage_pct']}% coverage)")
    print(f"Observations with both a model prob and a market reference prob: {len(analysis_rows)}")
    print(f"Mean model-market delta: {delta_mean}, stdev: {delta_stdev}")
    for row in bin_stats:
        print(row)

    # --- write outputs ---
    OBSERVATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    obs_df = pd.DataFrame([
        {
            "match_id": o.match_id, "market_id": o.market_id, "runner_id": o.runner_id,
            "player_name": o.player_name, "is_player_a": o.is_player_a,
            "scheduled_start": o.scheduled_start, "observation_timestamp": o.observation_timestamp,
            "horizon_label": o.horizon_label, "minutes_to_start": o.minutes_to_start,
            "model_probability": o.model_probability, "model_fair_odds": o.model_fair_odds,
            "snapshot_available": o.snapshot_available, "last_traded_price": o.last_traded_price,
            "raw_ltp_implied_probability": o.raw_ltp_implied_probability,
            "price_age_seconds": o.price_age_seconds,
            "market_reference_probability": o.market_reference_probability,
            "model_market_probability_delta": o.model_market_probability_delta,
            "market_status": o.market_status, "outcome_won": o.outcome_won,
        }
        for o in observations
    ])
    obs_df.to_csv(OBSERVATIONS_PATH, index=False)

    summary = {
        "n_tml_matches": len(tml_matches),
        "n_matched": n_matched,
        "n_ambiguous": len(results["AMBIGUOUS"]),
        "n_unmatched": len(results["UNMATCHED"]),
        "n_matched_with_final_market_time": n_matched_with_final_time,
        "n_missing_ltp_entirely": missing_ltp_matches,
        "n_observations_built": len(observations),
        "density_report": density_report,
        "best_covered_horizon": best_label,
        "n_analysis_rows": len(analysis_rows),
        "delta_mean": delta_mean,
        "delta_stdev": delta_stdev,
        "bin_stats": bin_stats,
    }
    metrics_path = REPO_ROOT / "data" / "interim" / "workstream_b_january_2026_observation_summary.json"
    with open(metrics_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    # --- per-horizon coverage / disagreement-magnitude summary (real,
    # reproducible from obs_df -- answers "does coverage/disagreement
    # change with horizon" without pre-supposing an answer) ---
    horizon_order = list(CANDIDATE_HORIZONS_MINUTES.keys())
    per_horizon = []
    for label in horizon_order:
        sub = obs_df[obs_df["horizon_label"] == label]
        sub_valid = sub[sub["market_reference_probability"].notna()]
        per_horizon.append({
            "horizon_label": label,
            "coverage_pct": round(100.0 * sub["snapshot_available"].mean(), 1) if len(sub) else None,
            "n_with_both_sides_priced": int(len(sub_valid)),
            "mean_abs_delta": round(sub_valid["model_market_probability_delta"].abs().mean(), 4) if len(sub_valid) else None,
        })
    summary["per_horizon_summary"] = per_horizon

    sub_30 = obs_df[(obs_df["horizon_label"] == "30min") & (obs_df["is_player_a"])]
    summary["naive_calibration_30min_player_a"] = {
        "n": int(len(sub_30)),
        "mean_model_probability": round(sub_30["model_probability"].mean(), 4) if len(sub_30) else None,
        "actual_outcome_rate": round(sub_30["outcome_won"].mean(), 4) if len(sub_30) else None,
    }
    stale_sub = obs_df[(obs_df["horizon_label"] == "30min") & (obs_df["snapshot_available"])]
    summary["price_staleness_seconds_30min_horizon"] = {
        "n": int(len(stale_sub)),
        "median": round(stale_sub["price_age_seconds"].median(), 1) if len(stale_sub) else None,
        "p75": round(stale_sub["price_age_seconds"].quantile(0.75), 1) if len(stale_sub) else None,
        "max": round(stale_sub["price_age_seconds"].max(), 1) if len(stale_sub) else None,
    }
    with open(metrics_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\nWrote {len(observations)} observations to {OBSERVATIONS_PATH}")
    print(f"Wrote summary to {metrics_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
