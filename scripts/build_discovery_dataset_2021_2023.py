"""Build the 2021-2023 discovery dataset (Workstream B Phase 2, Task #21,
2026-09-16).

One row per successfully-linked, priceable 2021-2023 ATP match, combining:
  - the FROZEN Global Elo probability (k_factor=32.0, unmodified since
    Tennis Cycle 1 -- reuses run_cycle_002_tennis_checkpoint_a4.run_elo_model
    unchanged, calibrated on match OUTCOMES only, never on market prices,
    per the standing "Elo must never be retuned using market results" rule)
  - the frozen ranking-baseline probability (same module, unchanged)
  - the market-reference probability at 4 horizons (24h/6h/1h/30min),
    reusing the tested `build_pre_match_observation` unchanged
  - pre-match, leakage-safe form/rest/congestion covariates computed from
    STRICTLY PRIOR matches only (via a per-player shifted rolling window)
  - all covariates needed for the 13 pre-registered discovery families

This script is data assembly ONLY. It appends `outcome_a_won` as a plain
column for Task #22's use but computes, prints, or inspects no
outcome-linked statistic anywhere in this file -- no win rate, no
model-market-delta-vs-outcome relationship, nothing. Every printed number
below is a data-availability count, not a result.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

REPO_ROOT = Path.home() / "mnt" / "prediction-markets-lab"
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.normalisation.tennis_betfair_linkage import (  # noqa: E402
    names_are_equivalent,
)
from prediction_markets_lab.research.market_observation import (  # noqa: E402
    build_pre_match_observation,
)

CANONICAL_PATH = REPO_ROOT / "data" / "processed" / "tennis" / "cycle_002_canonical_matches.csv"
LINKAGE_PATH = REPO_ROOT / "data" / "interim" / "workstream_b_2021_2025_linkage.csv"
INDEX_DIR = Path.home() / "betfair_2021_2025_index"
OUT_PATH = REPO_ROOT / "data" / "interim" / "workstream_b_2021_2023_discovery_dataset.csv"

DISCOVERY_YEARS = {2021, 2022, 2023}
MARKET_HORIZONS_MINUTES = {"24h": 24 * 60, "6h": 6 * 60, "1h": 60, "30min": 30}
PRIMARY_HORIZON = "30min"  # per WORKSTREAM_B_PRICE_COVERAGE_AUDIT.md section 6
FRESH_CAP = lambda minutes: max(2 * minutes * 60, 3600)
FORM_WINDOW = 10  # trailing matches for recent-form
REST_CONGESTION_WINDOW_DAYS = 14


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_canonical_2021_2023(a4) -> pd.DataFrame:
    df = pd.read_csv(CANONICAL_PATH, dtype={"tourney_date": str})
    df = df[~df["walkover"]].copy()
    df["_season_int"] = df["tourney_date"].str[:4].astype(int)
    df = df[df["_season_int"].isin(DISCOVERY_YEARS)].copy()
    df["tourney_date_dt"] = pd.to_datetime(df["tourney_date"], format="%Y%m%d")
    df["tourney_date"] = df["tourney_date_dt"]  # a4.to_elo_input expects a Timestamp here
    df["_round_order"] = df["round"].map(a4.ROUND_ORDER).fillna(-1)
    df = df.sort_values(["tourney_date_dt", "_round_order", "match_num"]).reset_index(drop=True)
    # a4.run_elo_model/run_ranking_model both expect a `_season` column
    # (matching TRAINING_SEASONS) -- since every row here IS 2021-2023,
    # every row is "training" for the purpose of that function's internal
    # calibration split, which is exactly correct: 2021-2023 IS the
    # frozen model's original calibration window.
    df["_season"] = df["_season_int"]
    return df


def compute_elo_and_ranking(a4, df: pd.DataFrame) -> tuple[dict, dict, float]:
    elo_preds, k = a4.run_elo_model(df, a4.global_rating_key)
    if k != 32.0:
        raise RuntimeError(f"re-derived k_factor {k} != frozen 32.0 -- STOP, do not proceed")
    ranking_preds = a4.run_ranking_model(df)
    return elo_preds, ranking_preds, k


def compute_form_rest_congestion(df: pd.DataFrame) -> pd.DataFrame:
    """Leakage-safe, per-player rolling form/surface-form/rest/congestion,
    computed ONLY from each player's STRICTLY PRIOR matches (via .shift(1)
    before any rolling window) in tourney_date order. Long-format table:
    one row per (match, player-slot), matches with each canonical row via
    (match_id, is_a)."""
    long_rows = []
    for _, row in df.iterrows():
        for is_a, pid, other_id in ((True, row["player_a_id"], row["player_b_id"]),
                                     (False, row["player_b_id"], row["player_a_id"])):
            won = bool(row["outcome_a_won"]) if is_a else (not bool(row["outcome_a_won"]))
            long_rows.append({
                "match_id": row["match_id"], "is_a": is_a, "player_id": pid,
                "tourney_date_dt": row["tourney_date_dt"], "surface": row["surface"],
                "match_num": row["match_num"], "_round_order": row["_round_order"], "won": float(won),
            })
    long_df = pd.DataFrame(long_rows)
    long_df = long_df.sort_values(["player_id", "tourney_date_dt", "_round_order", "match_num"]).reset_index(drop=True)

    out_form, out_surface_form, out_rest, out_congestion = [], [], [], []
    for player_id, grp in long_df.groupby("player_id", sort=False):
        grp = grp.sort_values(["tourney_date_dt", "_round_order", "match_num"])
        won_shifted = grp["won"].shift(1)
        recent_form = won_shifted.rolling(FORM_WINDOW, min_periods=3).mean()

        # surface form: rolling mean of `won`, shifted, WITHIN each surface group
        surf_form = pd.Series(index=grp.index, dtype=float)
        for surface, sgrp in grp.groupby("surface"):
            sgrp_sorted = sgrp.sort_values(["tourney_date_dt", "_round_order", "match_num"])
            sw = sgrp_sorted["won"].shift(1).rolling(FORM_WINDOW, min_periods=3).mean()
            surf_form.loc[sgrp_sorted.index] = sw.values

        prev_date = grp["tourney_date_dt"].shift(1)
        rest_days = (grp["tourney_date_dt"] - prev_date).dt.days

        # congestion: count of this player's OTHER matches with
        # tourney_date within the trailing REST_CONGESTION_WINDOW_DAYS
        # days (strictly before this match's date) -- O(n^2) per player
        # but player match counts over 3 years are small (dozens-hundreds).
        dates = grp["tourney_date_dt"].values
        congestion = []
        for i in range(len(dates)):
            cutoff_lo = dates[i] - pd.Timedelta(days=REST_CONGESTION_WINDOW_DAYS)
            cnt = ((dates[:i] >= cutoff_lo) & (dates[:i] < dates[i])).sum()
            congestion.append(int(cnt))

        for idx, rf, sf, rd, cg in zip(grp.index, recent_form.values, surf_form.values, rest_days.values, congestion):
            out_form.append((idx, rf))
            out_surface_form.append((idx, sf))
            out_rest.append((idx, rd))
            out_congestion.append((idx, cg))

    for name, vals in [("recent_form", out_form), ("surface_form", out_surface_form),
                        ("rest_days", out_rest), ("matches_last_14d", out_congestion)]:
        s = pd.Series(dict(vals))
        long_df[name] = long_df.index.map(s)

    # pivot back to one row per match: player_a_* and player_b_* columns
    a_side = long_df[long_df["is_a"]].set_index("match_id")[["recent_form", "surface_form", "rest_days", "matches_last_14d"]]
    b_side = long_df[~long_df["is_a"]].set_index("match_id")[["recent_form", "surface_form", "rest_days", "matches_last_14d"]]
    a_side.columns = [f"player_a_{c}" for c in a_side.columns]
    b_side.columns = [f"player_b_{c}" for c in b_side.columns]
    return a_side.join(b_side, how="outer")


def load_usable_market_rows() -> dict:
    dataset = ds.dataset(
        sorted(INDEX_DIR.glob("markets_2021_*.parquet"))
        + sorted(INDEX_DIR.glob("markets_2022_*.parquet"))
        + sorted(INDEX_DIR.glob("markets_2023_*.parquet")),
        format="parquet",
    )
    table = dataset.to_table(columns=[
        "market_id", "event_id", "market_type", "final_market_time",
        "runner_ids", "runner_names", "n_price_points",
        "price_runner_ids", "price_ltp", "price_epoch_ms",
    ])
    df = table.to_pandas()
    df = df[(df["market_type"] == "MATCH_ODDS") & (df["n_price_points"] > 0)]
    return {row.market_id: row for row in df.itertuples(index=False)}


def build_price_series(row) -> dict[int, list[tuple[datetime, float]]]:
    series: dict[int, list] = {}
    for rid, ltp, ep in zip(row.price_runner_ids, row.price_ltp, row.price_epoch_ms):
        if ep is None or ltp is None:
            continue
        series.setdefault(int(rid), []).append((datetime.fromtimestamp(ep / 1000.0, tz=timezone.utc), float(ltp)))
    for rid in series:
        series[rid].sort(key=lambda t: t[0])
    return series


def main():
    a4 = _load_module(REPO_ROOT / "scripts" / "run_cycle_002_tennis_checkpoint_a4.py", "a4")

    canonical = load_canonical_2021_2023(a4)
    print(f"Loaded {len(canonical)} 2021-2023 canonical matches (all, not just MATCHED)")

    elo_preds, ranking_preds, k = compute_elo_and_ranking(a4, canonical)
    print(f"Elo: {len(elo_preds)} predictions, k_factor={k} (frozen, confirmed)")
    print(f"Ranking baseline: {len(ranking_preds)} predictions (usable-ranking rows only)")

    form_df = compute_form_rest_congestion(canonical)
    print(f"Form/rest/congestion computed for {len(form_df)} matches")

    linkage = pd.read_csv(LINKAGE_PATH, dtype={"tml_match_id": str, "matched_market_id": str})
    matched = linkage[linkage["linkage_status"] == "MATCHED"].copy()
    matched["_year"] = matched["tml_match_date"].str[:4].astype(int)
    matched = matched[matched["_year"].isin(DISCOVERY_YEARS)]
    print(f"MATCHED links in 2021-2023: {len(matched)}")

    market_by_id = load_usable_market_rows()
    print(f"Loaded {len(market_by_id)} usable 2021-2023 MATCH_ODDS markets")

    canonical_by_id = canonical.set_index("match_id")

    rows = []
    skipped = {"no_canonical": 0, "no_market": 0, "no_final_time": 0, "runner_map_failed": 0}

    for i, link_row in enumerate(matched.itertuples(index=False)):
        mid = link_row.tml_match_id
        if mid not in canonical_by_id.index:
            skipped["no_canonical"] += 1
            continue
        crow = canonical_by_id.loc[mid]
        mrow = market_by_id.get(link_row.matched_market_id)
        if mrow is None:
            skipped["no_market"] += 1
            continue
        try:
            scheduled_start = datetime.fromisoformat(mrow.final_market_time)
        except (ValueError, TypeError):
            skipped["no_final_time"] += 1
            continue

        names = list(mrow.runner_names)
        rids = list(mrow.runner_ids)
        if len(names) != 2 or len(rids) != 2:
            skipped["runner_map_failed"] += 1
            continue
        sel_a = sel_b = None
        for rid, name in zip(rids, names):
            if name is None:
                continue
            if names_are_equivalent(link_row.player_a_name, name):
                sel_a = int(rid)
            elif names_are_equivalent(link_row.player_b_name, name):
                sel_b = int(rid)
        if sel_a is None or sel_b is None:
            skipped["runner_map_failed"] += 1
            continue

        price_series = build_price_series(mrow)
        series_a = price_series.get(sel_a, [])
        series_b = price_series.get(sel_b, [])

        rec = {
            "match_id": mid,
            "tourney_id": crow["tourney_id"],
            "tourney_date": crow["tourney_date"],
            "year": crow["_season_int"],
            "surface": crow["surface"],
            "tourney_level": crow["tourney_level"],
            "best_of": crow["best_of"],
            "round": crow["round"],
            "player_a_id": crow["player_a_id"], "player_a_name": crow["player_a_name"],
            "player_b_id": crow["player_b_id"], "player_b_name": crow["player_b_name"],
            "player_a_rank": crow["player_a_rank"], "player_b_rank": crow["player_b_rank"],
            "rank_gap_b_minus_a": (crow["player_b_rank"] - crow["player_a_rank"])
                if pd.notna(crow["player_a_rank"]) and pd.notna(crow["player_b_rank"]) else None,
            "elo_prob_a": elo_preds.get(mid),
            "ranking_prob_a": ranking_preds.get(mid),
        }
        if rec["elo_prob_a"] is not None and rec["ranking_prob_a"] is not None:
            rec["elo_vs_ranking_delta"] = rec["elo_prob_a"] - rec["ranking_prob_a"]
        else:
            rec["elo_vs_ranking_delta"] = None

        if mid in form_df.index:
            for c in form_df.columns:
                rec[c] = form_df.loc[mid, c]
        else:
            for c in ["player_a_recent_form", "player_a_surface_form", "player_a_rest_days", "player_a_matches_last_14d",
                      "player_b_recent_form", "player_b_surface_form", "player_b_rest_days", "player_b_matches_last_14d"]:
                rec[c] = None

        for label, minutes in MARKET_HORIZONS_MINUTES.items():
            obs_a = build_pre_match_observation(
                match_id=mid, event_id=str(mrow.event_id), market_id=link_row.matched_market_id,
                runner_id=sel_a, player_name=link_row.player_a_name, is_player_a=True,
                scheduled_start=scheduled_start, horizon_label=label, requested_horizon_minutes=float(minutes),
                model_probability=rec["elo_prob_a"] if rec["elo_prob_a"] is not None else 0.5,
                own_price_series=series_a, other_player_price_series=series_b,
                market_status_at_cutoff=None, in_play_at_cutoff=False, outcome_won=None,
            )
            obs_b = build_pre_match_observation(
                match_id=mid, event_id=str(mrow.event_id), market_id=link_row.matched_market_id,
                runner_id=sel_b, player_name=link_row.player_b_name, is_player_a=False,
                scheduled_start=scheduled_start, horizon_label=label, requested_horizon_minutes=float(minutes),
                model_probability=1 - rec["elo_prob_a"] if rec["elo_prob_a"] is not None else 0.5,
                own_price_series=series_b, other_player_price_series=series_a,
                market_status_at_cutoff=None, in_play_at_cutoff=False, outcome_won=None,
            )
            fresh = (
                obs_a.snapshot_available and obs_b.snapshot_available
                and obs_a.price_age_seconds is not None and obs_b.price_age_seconds is not None
                and max(obs_a.price_age_seconds, obs_b.price_age_seconds) <= FRESH_CAP(minutes)
            )
            rec[f"market_prob_a_{label}"] = obs_a.market_reference_probability if fresh else None
            rec[f"market_priced_fresh_{label}"] = fresh

        rec["outcome_a_won"] = bool(crow["outcome_a_won"])
        rows.append(rec)

        if i % 2000 == 0:
            print(f"...{i}/{len(matched)} matches assembled", flush=True)

    print(f"Skipped: {skipped}")

    out_df = pd.DataFrame(rows)

    # Derived primary-horizon fields (30min, per the frozen coverage audit choice)
    prim = PRIMARY_HORIZON
    out_df["model_market_delta_30min"] = out_df["elo_prob_a"] - out_df[f"market_prob_a_{prim}"]
    out_df["price_movement_6h_to_30min"] = out_df[f"market_prob_a_{prim}"] - out_df["market_prob_a_6h"]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUT_PATH, index=False)
    print(f"\nWrote {len(out_df)} rows, {len(out_df.columns)} columns to {OUT_PATH}")

    print("\n=== Data-availability counts (NOT outcome statistics) ===")
    print(f"N rows (MATCHED, 2021-2023): {len(out_df)}")
    print(f"N with elo_prob_a: {out_df['elo_prob_a'].notna().sum()}")
    print(f"N with ranking_prob_a: {out_df['ranking_prob_a'].notna().sum()}")
    print(f"N with elo_vs_ranking_delta: {out_df['elo_vs_ranking_delta'].notna().sum()}")
    for label in MARKET_HORIZONS_MINUTES:
        print(f"N with market_prob_a_{label} (fresh): {out_df[f'market_prob_a_{label}'].notna().sum()}")
    print(f"N with model_market_delta_30min: {out_df['model_market_delta_30min'].notna().sum()}")
    print(f"N with price_movement_6h_to_30min: {out_df['price_movement_6h_to_30min'].notna().sum()}")
    print(f"N with player_a_recent_form: {out_df['player_a_recent_form'].notna().sum()}")
    print(f"N with player_a_surface_form: {out_df['player_a_surface_form'].notna().sum()}")
    print(f"N with rank_gap_b_minus_a: {out_df['rank_gap_b_minus_a'].notna().sum()}")
    print(f"\nYear distribution:\n{out_df['year'].value_counts().sort_index()}")


if __name__ == "__main__":
    main()
