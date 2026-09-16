"""Price-coverage / selection-bias audit of the frozen 2021-2025 MATCHED
Betfair<->TML linkage (Workstream B, Phase 2 gate, Task #20, 2026-09-16).

Per the operator's instruction: "Report N_total/N_linked/N_with_required_
prices/N_final_analysis and coverage%/exclusion% by year, surface,
tournament level, favourite-underdog, price band, and horizon, to check
whether the thinner price coverage found in Phase 1 (vs January's sample)
is random or concentrated in particular match types."

Deliberately does NOT read outcome_a_won anywhere and does NOT compute any
model-vs-market disagreement statistic -- this is a coverage/missingness
audit only, run before the 2021-2023 discovery dataset is built (Task #21).
favourite/underdog is determined from pre-match ATP ranking (player_a_rank
vs player_b_rank), never from price or outcome. price_band uses each
market's own CLOSING (last available) price -- a structural fact about how
lopsided the market ended up, not a claim about pre-match coverage, kept
deliberately separate from the horizon-coverage question itself.

Reuses the tested `build_pre_match_observation` / `latest_price_at_or_
before` functions from `research/market_observation.py` unchanged, exactly
like the January 2026 pipeline script, for one runner-pair per MATCHED
match at each of 7 candidate horizons.
"""

from __future__ import annotations

import sys
from collections import defaultdict
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

INDEX_DIR = Path.home() / "betfair_2021_2025_index"
CANONICAL_PATH = REPO_ROOT / "data" / "processed" / "tennis" / "cycle_002_canonical_matches.csv"
LINKAGE_PATH = REPO_ROOT / "data" / "interim" / "workstream_b_2021_2025_linkage.csv"
OUT_ROWS_PATH = REPO_ROOT / "data" / "interim" / "workstream_b_price_coverage_audit_rows.csv"

CANDIDATE_HORIZONS_MINUTES = {
    "24h": 24 * 60, "12h": 12 * 60, "6h": 6 * 60, "3h": 3 * 60,
    "1h": 60, "30min": 30, "10min": 10,
}

PRICE_BANDS = [(0.50, 0.55), (0.55, 0.65), (0.65, 0.75), (0.75, 0.85), (0.85, 0.95), (0.95, 1.01)]


def price_band_for(favourite_prob: float) -> str:
    for lo, hi in PRICE_BANDS:
        if lo <= favourite_prob < hi:
            return f"[{lo:.2f},{hi:.2f})"
    return "other"


def load_market_rows() -> pd.DataFrame:
    dataset = ds.dataset(sorted(INDEX_DIR.glob("markets_*.parquet")), format="parquet")
    table = dataset.to_table(columns=[
        "market_id", "event_id", "market_type", "final_market_time",
        "runner_ids", "runner_names", "n_price_points",
        "price_runner_ids", "price_ltp", "price_epoch_ms",
    ])
    df = table.to_pandas()
    return df[(df["market_type"] == "MATCH_ODDS") & (df["n_price_points"] > 0)].copy()


def build_price_series(row) -> dict[int, list[tuple[datetime, float]]]:
    series: dict[int, list[tuple[datetime, float]]] = defaultdict(list)
    rids = row.price_runner_ids
    ltps = row.price_ltp
    epochs = row.price_epoch_ms
    for rid, ltp, ep in zip(rids, ltps, epochs):
        if ep is None or ltp is None:
            continue
        series[int(rid)].append((datetime.fromtimestamp(ep / 1000.0, tz=timezone.utc), float(ltp)))
    for rid in series:
        series[rid].sort(key=lambda t: t[0])
    return series


def main():
    linkage = pd.read_csv(LINKAGE_PATH, dtype={"tml_match_id": str, "matched_market_id": str})
    matched = linkage[linkage["linkage_status"] == "MATCHED"].copy()
    n_total = len(linkage)
    n_linked = len(matched)
    print(f"N_total={n_total}  N_linked(MATCHED)={n_linked} ({100*n_linked/n_total:.2f}%)")

    canonical = pd.read_csv(CANONICAL_PATH, dtype={"tourney_date": str}).set_index("match_id")

    market_df = load_market_rows()
    market_by_id = {row.market_id: row for row in market_df.itertuples(index=False)}
    print(f"Loaded {len(market_by_id)} usable MATCH_ODDS markets for lookup")

    records = []
    skipped_no_market = 0
    skipped_no_final_time = 0
    skipped_runner_map = 0

    for i, row in enumerate(matched.itertuples(index=False)):
        if row.tml_match_id not in canonical.index:
            continue
        crow = canonical.loc[row.tml_match_id]
        mrow = market_by_id.get(row.matched_market_id)
        if mrow is None:
            skipped_no_market += 1
            continue
        try:
            scheduled_start = datetime.fromisoformat(mrow.final_market_time)
        except (ValueError, TypeError):
            skipped_no_final_time += 1
            continue

        names = list(mrow.runner_names)
        rids = list(mrow.runner_ids)
        if len(names) != 2 or len(rids) != 2:
            skipped_runner_map += 1
            continue
        sel_a = sel_b = None
        for rid, name in zip(rids, names):
            if name is None:
                continue
            if names_are_equivalent(row.player_a_name, name):
                sel_a = int(rid)
            elif names_are_equivalent(row.player_b_name, name):
                sel_b = int(rid)
        if sel_a is None or sel_b is None:
            skipped_runner_map += 1
            continue

        price_series = build_price_series(mrow)
        series_a = price_series.get(sel_a, [])
        series_b = price_series.get(sel_b, [])

        # Closing (last-known) price band -- structural, not outcome-based:
        # which side the market ultimately favoured, used only to check
        # whether coverage differs by how lopsided the match was priced.
        favourite_prob_close = None
        if series_a and series_b:
            close_a = series_a[-1][1]
            close_b = series_b[-1][1]
            if close_a > 1.0 and close_b > 1.0:
                q_a = (1.0 / close_a) / (1.0 / close_a + 1.0 / close_b)
                favourite_prob_close = max(q_a, 1.0 - q_a)

        # favourite/underdog by pre-match ATP ranking only (never price/outcome)
        rank_a, rank_b = crow.get("player_a_rank"), crow.get("player_b_rank")
        if pd.notna(rank_a) and pd.notna(rank_b):
            fav_by_rank = "player_a" if rank_a < rank_b else ("player_b" if rank_b < rank_a else "tied")
        else:
            fav_by_rank = "unknown"

        base = {
            "tml_match_id": row.tml_match_id,
            "year": crow["tourney_date"][:4],
            "surface": crow.get("surface"),
            "tourney_level": crow.get("tourney_level"),
            "favourite_by_rank": fav_by_rank,
            "price_band_close": price_band_for(favourite_prob_close) if favourite_prob_close is not None else "unknown",
        }

        for label, minutes in CANDIDATE_HORIZONS_MINUTES.items():
            obs_a = build_pre_match_observation(
                match_id=row.tml_match_id, event_id=str(mrow.event_id), market_id=row.matched_market_id,
                runner_id=sel_a, player_name=row.player_a_name, is_player_a=True,
                scheduled_start=scheduled_start, horizon_label=label, requested_horizon_minutes=float(minutes),
                model_probability=0.5, own_price_series=series_a, other_player_price_series=series_b,
                market_status_at_cutoff=None, in_play_at_cutoff=False, outcome_won=None,
            )
            obs_b = build_pre_match_observation(
                match_id=row.tml_match_id, event_id=str(mrow.event_id), market_id=row.matched_market_id,
                runner_id=sel_b, player_name=row.player_b_name, is_player_a=False,
                scheduled_start=scheduled_start, horizon_label=label, requested_horizon_minutes=float(minutes),
                model_probability=0.5, own_price_series=series_b, other_player_price_series=series_a,
                market_status_at_cutoff=None, in_play_at_cutoff=False, outcome_won=None,
            )
            both_priced = obs_a.snapshot_available and obs_b.snapshot_available
            max_age = None
            if obs_a.price_age_seconds is not None and obs_b.price_age_seconds is not None:
                max_age = max(obs_a.price_age_seconds, obs_b.price_age_seconds)
            rec = dict(base)
            rec["horizon"] = label
            rec["both_sides_priced"] = both_priced
            rec["max_price_age_seconds"] = max_age
            # "Fresh" coverage: both sides priced AND neither snapshot is
            # staler than the horizon itself by more than a 2x margin --
            # i.e. the snapshot genuinely reflects trading reasonably close
            # to this horizon, not a days-old ante-post price that happens
            # to predate the cutoff. This is a materially different (and
            # more decision-relevant) bar than "any price ever recorded".
            fresh_cap_seconds = max(2 * minutes * 60, 3600)
            rec["fresh_priced"] = bool(both_priced and max_age is not None and max_age <= fresh_cap_seconds)
            records.append(rec)

        if i % 2000 == 0:
            print(f"...{i}/{len(matched)} matches processed", flush=True)

    print(f"Skipped: no_market={skipped_no_market} no_final_time={skipped_no_final_time} runner_map_failed={skipped_runner_map}")

    df = pd.DataFrame(records)
    df.to_csv(OUT_ROWS_PATH, index=False)
    print(f"Wrote {len(df)} (match x horizon) rows to {OUT_ROWS_PATH}")

    n_matches_audited = df["tml_match_id"].nunique()
    print(f"\nN_total={n_total}  N_linked={n_linked}  N_audited_for_coverage={n_matches_audited}")

    print("\n=== Coverage % by horizon: RAW (any price at/before cutoff) vs FRESH (staleness-capped) ===")
    for label in CANDIDATE_HORIZONS_MINUTES:
        sub = df[df["horizon"] == label]
        raw_cov = 100 * sub["both_sides_priced"].mean()
        fresh_cov = 100 * sub["fresh_priced"].mean()
        median_age = sub.loc[sub["both_sides_priced"], "max_price_age_seconds"].median()
        print(f"  {label:>5}: raw={raw_cov:.1f}%  fresh={fresh_cov:.1f}%  "
              f"median_age_when_priced={median_age/3600:.2f}h  (n={len(sub)})")

    print("\n=== FRESH coverage % by year x horizon ===")
    pivot_year = df.pivot_table(index="year", columns="horizon", values="fresh_priced", aggfunc="mean") * 100
    print(pivot_year[list(CANDIDATE_HORIZONS_MINUTES.keys())].round(1))

    # Choose the best-covered horizon empirically using the FRESH (decision-
    # relevant) definition, same empirical discipline as the Jan pipeline
    # but not fooled by stale ante-post prices satisfying the raw definition.
    overall_cov = {label: 100 * df[df["horizon"] == label]["fresh_priced"].mean() for label in CANDIDATE_HORIZONS_MINUTES}
    best_label = max(overall_cov, key=lambda l: overall_cov[l])
    print(f"\nBest-covered candidate horizon (by FRESH coverage): {best_label} ({overall_cov[best_label]:.1f}%)")

    best_df = df[df["horizon"] == best_label]
    n_final_analysis = int(best_df["fresh_priced"].sum())
    print(f"N_final_analysis at horizon={best_label}: {n_final_analysis} / {n_matches_audited} "
          f"({100*n_final_analysis/n_matches_audited:.2f}%)  "
          f"(exclusion% = {100*(1 - n_final_analysis/n_matches_audited):.2f}%)")

    for dim in ["surface", "tourney_level", "favourite_by_rank", "price_band_close"]:
        print(f"\n=== FRESH coverage % at {best_label} by {dim} ===")
        g = best_df.groupby(dim)["fresh_priced"].agg(["mean", "count"])
        g["mean"] = (g["mean"] * 100).round(1)
        print(g.sort_values("count", ascending=False))

    print(f"\n=== N by year (audited matches) ===")
    print(best_df.groupby("year").size())


if __name__ == "__main__":
    main()
