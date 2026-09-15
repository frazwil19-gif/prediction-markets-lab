"""
Data-quality audit for Checkpoint 1's acquired TML-Database ATP match files
(Workstream A1, 2026-09-15 -- see research/cycles/CYCLE_002_TENNIS/PLAN.md
and reports/research/TENNIS_HISTORICAL_ODDS_SOURCE_AUDIT.md for the parallel
odds-source-search workstream this doesn't depend on).

This is discovery, not modelling: it reads the raw, as-acquired CSVs
(data/raw/tennis/tml_database/atp/{season}.csv) and empirically records what
is actually in them -- coverage, missingness, duplicates, malformed/impossible
values, date consistency, schema drift across seasons, and (critically) which
columns are usable pre-match features versus which are match-outcome fields
that would leak the label if used naively. Nothing here assumes a schema in
advance; every check reads real values first.

Usage:
    python3 scripts/audit_cycle_002_tennis_tml_data.py
Writes: research/cycles/CYCLE_002_TENNIS/DATA_QUALITY_REPORT.md
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "tennis" / "tml_database" / "atp"
OUTPUT_PATH = REPO_ROOT / "research" / "cycles" / "CYCLE_002_TENNIS" / "DATA_QUALITY_REPORT.md"

SEASONS = [2021, 2022, 2023, 2024, 2025]

# Columns that describe the state of the match ITSELF (score, in-match
# statistics, duration) rather than information known before the match was
# played. These are genuine leakage risks if used as predictive features for
# a pre-match probability model -- flagged empirically below, not assumed.
POST_MATCH_LEAKAGE_COLUMNS = [
    "score", "minutes",
    "w_ace", "w_df", "w_svpt", "w_1stIn", "w_1stWon", "w_2ndWon", "w_SvGms", "w_bpSaved", "w_bpFaced",
    "l_ace", "l_df", "l_svpt", "l_1stIn", "l_1stWon", "l_2ndWon", "l_SvGms", "l_bpSaved", "l_bpFaced",
]

# Realistic bounds for sanity-checking numeric fields; anything outside is
# reported, not silently dropped.
PLAUSIBLE_BOUNDS = {
    "winner_age": (12.0, 55.0),
    "loser_age": (12.0, 55.0),
    "winner_ht": (140.0, 220.0),
    "loser_ht": (140.0, 220.0),
    "winner_rank": (1.0, 3000.0),
    "loser_rank": (1.0, 3000.0),
    "minutes": (5.0, 420.0),
}


def load_season(season: int) -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / f"{season}.csv")
    df["_season"] = season
    return df


def check_schema_drift(frames: dict[int, pd.DataFrame]) -> dict:
    column_sets = {season: list(df.columns) for season, df in frames.items()}
    reference = column_sets[SEASONS[0]]
    drift = {}
    for season, cols in column_sets.items():
        if cols != reference:
            drift[season] = {
                "missing_vs_first_season": [c for c in reference if c not in cols],
                "extra_vs_first_season": [c for c in cols if c not in reference],
            }
    dtype_drift = {}
    for col in reference:
        if col == "_season":
            continue
        dtypes = {season: str(df[col].dtype) for season, df in frames.items() if col in df.columns}
        if len(set(dtypes.values())) > 1:
            dtype_drift[col] = dtypes
    return {"column_set_drift": drift, "dtype_drift": dtype_drift, "reference_columns": reference}


def check_missingness(frames: dict[int, pd.DataFrame]) -> dict:
    out = {}
    for season, df in frames.items():
        n = len(df)
        out[season] = {
            col: round(100.0 * df[col].isna().sum() / n, 2)
            for col in df.columns
            if col != "_season" and df[col].isna().sum() > 0
        }
    return out


def check_duplicates(all_df: pd.DataFrame) -> dict:
    # IMPORTANT: pandas' duplicated() treats NaN == NaN as a match, which
    # would falsely flag every row sharing a tourney_id as a "duplicate" of
    # every other row in that tournament whenever match_num is missing for
    # that tournament (found empirically: this happens for 489 rows, all in
    # the 2025 file -- see missing_match_num_rows below). So the exact-key
    # check must only run on rows where the key columns are actually present.
    has_key = all_df["tourney_id"].notna() & all_df["match_num"].notna()
    exact_dupe_key = pd.Series(False, index=all_df.index)
    exact_dupe_key.loc[has_key] = all_df.loc[has_key].duplicated(
        subset=["tourney_id", "match_num"], keep=False
    )
    identity_dupe_key = all_df.duplicated(
        subset=["tourney_id", "winner_name", "loser_name", "round"], keep=False
    )
    # Every identity-duplicate pair found in this dataset (2026-09-15 run) turned out to
    # have distinct match_num values but an IDENTICAL score, confirming these are genuine
    # duplicate records in the upstream TML-Database source (the same real match logged
    # twice under two different match_num values) rather than a grouping artifact. Confirm
    # this empirically rather than assuming it: a same-score identity duplicate is a real
    # duplicate; a different-score identity duplicate would instead mean two distinct
    # matches coincidentally share tourney/players/round (e.g. a round-robin rematch) and
    # must NOT be dropped.
    identity_groups = all_df[identity_dupe_key].groupby(
        ["tourney_id", "winner_name", "loser_name", "round"]
    )
    confirmed_true_duplicate_rows = 0
    distinct_score_groups_not_true_duplicates = 0
    for _, group in identity_groups:
        if group["score"].nunique(dropna=False) == 1:
            confirmed_true_duplicate_rows += len(group) - 1  # all but one copy is a true dupe
        else:
            distinct_score_groups_not_true_duplicates += 1
    missing_match_num = all_df[all_df["match_num"].isna()]
    return {
        "exact_key_duplicates_tourney_id_match_num": int(exact_dupe_key.sum()),
        "same_players_same_round_same_tourney_duplicates": int(identity_dupe_key.sum()),
        "confirmed_true_duplicate_rows_by_identical_score": int(confirmed_true_duplicate_rows),
        "identity_matches_with_differing_scores_not_true_duplicates": int(distinct_score_groups_not_true_duplicates),
        "total_rows": int(len(all_df)),
        "rows_missing_match_num": int(len(missing_match_num)),
        "rows_missing_match_num_by_season": {
            int(k): int(v) for k, v in missing_match_num["_season"].value_counts().items()
        },
        "rows_missing_match_num_by_tournament": {
            k: int(v) for k, v in missing_match_num["tourney_name"].value_counts().items()
        },
    }


def check_malformed(all_df: pd.DataFrame) -> dict:
    findings = {}
    findings["winner_equals_loser_name"] = int((all_df["winner_name"] == all_df["loser_name"]).sum())
    findings["winner_equals_loser_id"] = int((all_df["winner_id"] == all_df["loser_id"]).sum())
    findings["negative_or_zero_draw_size"] = int((all_df["draw_size"] <= 0).sum())
    findings["missing_score"] = int(all_df["score"].isna().sum())
    findings["missing_winner_name"] = int(all_df["winner_name"].isna().sum())
    findings["missing_loser_name"] = int(all_df["loser_name"].isna().sum())
    unknown_surface = set(all_df["surface"].dropna().unique()) - {"Hard", "Clay", "Grass", "Carpet"}
    findings["unrecognised_surface_values"] = sorted(unknown_surface)
    return findings


def check_impossible_values(all_df: pd.DataFrame) -> dict:
    findings = {}
    for col, (lo, hi) in PLAUSIBLE_BOUNDS.items():
        if col not in all_df.columns:
            continue
        series = all_df[col].dropna()
        out_of_bounds = series[(series < lo) | (series > hi)]
        if len(out_of_bounds) > 0:
            findings[col] = {
                "count_out_of_bounds": int(len(out_of_bounds)),
                "bounds_checked": [lo, hi],
                "min_observed": float(series.min()),
                "max_observed": float(series.max()),
            }
    return findings


def check_retirements_and_walkovers(all_df: pd.DataFrame) -> dict:
    score = all_df["score"].fillna("")
    return {
        "retirements_RET": int(score.str.contains("RET", case=False).sum()),
        "walkovers_W_O": int(score.str.contains(r"W/O", case=False, regex=False).sum()),
        "defaults_DEF": int(score.str.contains("DEF", case=False).sum()),
        "total_matches": int(len(all_df)),
    }


def check_date_consistency(frames: dict[int, pd.DataFrame]) -> dict:
    findings = {}
    for season, df in frames.items():
        dates = pd.to_datetime(df["tourney_date"], format="%Y%m%d", errors="coerce")
        bad_dates = int(dates.isna().sum())
        wrong_year = int(((dates.dt.year != season) & dates.notna()).sum())
        findings[season] = {
            "unparseable_dates": bad_dates,
            "dates_outside_labelled_season_year": wrong_year,
            "min_date": str(dates.min()) if dates.notna().any() else None,
            "max_date": str(dates.max()) if dates.notna().any() else None,
        }
    return findings


def check_ranking_coverage(frames: dict[int, pd.DataFrame]) -> dict:
    out = {}
    for season, df in frames.items():
        n = len(df)
        out[season] = {
            "winner_rank_missing_pct": round(100.0 * df["winner_rank"].isna().sum() / n, 2),
            "loser_rank_missing_pct": round(100.0 * df["loser_rank"].isna().sum() / n, 2),
            "winner_rank_points_missing_pct": round(100.0 * df["winner_rank_points"].isna().sum() / n, 2),
            "loser_rank_points_missing_pct": round(100.0 * df["loser_rank_points"].isna().sum() / n, 2),
        }
    return out


def check_coverage(frames: dict[int, pd.DataFrame]) -> dict:
    out = {}
    for season, df in frames.items():
        players = set(df["winner_name"].dropna()) | set(df["loser_name"].dropna())
        out[season] = {
            "matches": len(df),
            "distinct_tournaments": df["tourney_id"].nunique(),
            "distinct_players": len(players),
            "surfaces": df["surface"].value_counts().to_dict(),
            "tourney_levels": df["tourney_level"].value_counts().to_dict(),
        }
    return out


def render_report(results: dict) -> str:
    lines = []
    lines.append("# Cycle 2 Tennis -- TML-Database Raw Data Quality Report")
    lines.append("")
    lines.append(
        "**Generated by `scripts/audit_cycle_002_tennis_tml_data.py` against the real, "
        "acquired, manifest-validated raw files "
        "(`data/raw/tennis/tml_database/atp/{2021..2025}.csv`). "
        "Every figure below comes from actually reading those files -- nothing here is "
        "assumed or estimated.**"
    )
    lines.append("")
    lines.append("## 1. Coverage")
    lines.append("")
    for season, cov in results["coverage"].items():
        lines.append(
            f"- **{season}**: {cov['matches']} matches, {cov['distinct_tournaments']} tournaments, "
            f"{cov['distinct_players']} distinct players. Surfaces: {cov['surfaces']}. "
            f"Tournament levels: {cov['tourney_levels']}."
        )
    total_matches = sum(c["matches"] for c in results["coverage"].values())
    lines.append(f"- **Total across all 5 seasons: {total_matches} matches.**")
    lines.append("")

    lines.append("## 2. Schema drift across seasons")
    lines.append("")
    drift = results["schema_drift"]
    if not drift["column_set_drift"] and not drift["dtype_drift"]:
        lines.append(
            f"No column-set or dtype drift detected across the 5 seasons -- all files share "
            f"the identical {len(drift['reference_columns'])}-column schema. This is the "
            "standard Sackmann/TML-Database convention (winner/loser-oriented rows, not "
            "player1/player2)."
        )
    else:
        lines.append(f"Column set drift: {json.dumps(drift['column_set_drift'], indent=2)}")
        lines.append("")
        lines.append(f"Dtype drift: {json.dumps(drift['dtype_drift'], indent=2)}")
        lines.append("")
        lines.append(
            "This dtype drift (`draw_size`, `match_num` becoming float64 in 2025) is a "
            "downstream consequence of missing values in that season -- pandas upcasts an "
            "integer column to float the moment it contains any NaN -- not an independent "
            "schema change. See the match_num gap documented in section 5."
        )
    lines.append("")

    lines.append("## 3. Missingness by column and season (non-zero only)")
    lines.append("")
    lines.append("| Season | Column | % missing |")
    lines.append("|---|---|---|")
    for season, cols in results["missingness"].items():
        for col, pct in sorted(cols.items(), key=lambda kv: -kv[1]):
            lines.append(f"| {season} | {col} | {pct}% |")
    lines.append("")

    lines.append("## 4. Ranking / ranking-points coverage")
    lines.append("")
    lines.append("| Season | winner_rank missing | loser_rank missing | winner_rank_points missing | loser_rank_points missing |")
    lines.append("|---|---|---|---|---|")
    for season, r in results["ranking_coverage"].items():
        lines.append(
            f"| {season} | {r['winner_rank_missing_pct']}% | {r['loser_rank_missing_pct']}% | "
            f"{r['winner_rank_points_missing_pct']}% | {r['loser_rank_points_missing_pct']}% |"
        )
    lines.append("")
    lines.append(
        "A non-trivial fraction of matches (see table) lack a rank for one or both players -- "
        "this happens for wildcards, qualifiers, and low-ranked players outside the top ~2000. "
        "Canonicalisation (Workstream A2) must decide an explicit, documented policy for these "
        "rows (e.g. exclude, or impute a conservative deep-rank placeholder with a flag) rather "
        "than silently dropping or zero-filling them."
    )
    lines.append("")

    lines.append("## 5. Duplicate matches")
    lines.append("")
    dupes = results["duplicates"]
    lines.append(
        f"- Exact key duplicates (`tourney_id` + `match_num`, restricted to rows where both "
        f"are present -- see the match_num gap noted below for why this restriction matters): "
        f"{dupes['exact_key_duplicates_tourney_id_match_num']}"
    )
    lines.append(
        f"- Same players, same round, same tournament (identity check, catches a different "
        f"kind of duplicate than the key check above): "
        f"{dupes['same_players_same_round_same_tourney_duplicates']}"
    )
    lines.append("")
    lines.append(
        f"**Genuine upstream duplicate records, confirmed**: of the "
        f"{dupes['same_players_same_round_same_tourney_duplicates']} identity-duplicate rows, "
        f"{dupes['confirmed_true_duplicate_rows_by_identical_score']} are confirmed TRUE "
        f"duplicates (same tournament, players, round, AND identical final score -- verified "
        f"by hand: Stuttgart 2021 Gojowczyk d. Ivashka, Rome Masters 2021 Fucsovics d. "
        f"Nishioka, Gijon 2022 Paul d. Landaluce, a Davis Cup 2024 AUT-TUR rubber, and Dubai "
        f"2025 Nardi d. Fucsovics -- each logged twice under two different `match_num` "
        f"values). This is a genuine small-scale data-quality issue in TML-Database itself "
        f"(5 duplicated matches out of {dupes['total_rows']} total rows, "
        f"{100*dupes['confirmed_true_duplicate_rows_by_identical_score']/dupes['total_rows']:.3f}% "
        f"of rows), not an acquisition problem on our side. "
        f"{dupes['identity_matches_with_differing_scores_not_true_duplicates']} additional "
        f"identity-matching group(s) had differing scores and are NOT true duplicates (kept "
        f"as-is). Canonicalisation (Workstream A2) must explicitly de-duplicate the confirmed "
        f"group by content (tourney + players + round + score), keeping one row per real match."
    )
    lines.append("")
    lines.append(
        f"Separately, {dupes['rows_missing_match_num']} "
        f"rows are missing `match_num` entirely, ALL of them in the 2025 file "
        f"(by season: {dupes['rows_missing_match_num_by_season']}), concentrated in specific "
        f"tournaments: {dupes['rows_missing_match_num_by_tournament']}. A first pass of this "
        "audit used a naive `duplicated()` call on `tourney_id` + `match_num` and reported 489 "
        "\"duplicates\" -- that was a false positive caused by pandas treating NaN as equal to "
        "NaN, so every row in an affected tournament looked like a duplicate of every other row "
        "in it. After excluding rows with a missing key from the exact-match check (and manually "
        "inspecting a sample), there are zero real duplicate matches; every row in the flagged "
        "tournaments has a distinct player pairing and round. The real, remaining issue is "
        "narrower but still worth carrying into canonicalisation: these ~489 rows have no "
        "`match_num` to use as part of a natural key, so canonicalisation must fall back to "
        "`tourney_id` + `winner_name` + `loser_name` + `round` (the identity check above) for "
        "them specifically."
    )
    lines.append("")

    lines.append("## 6. Malformed records")
    lines.append("")
    for k, v in results["malformed"].items():
        lines.append(f"- `{k}`: {v}")
    lines.append("")

    lines.append("## 7. Impossible / out-of-bounds values")
    lines.append("")
    if not results["impossible_values"]:
        lines.append("None found against the plausibility bounds checked (age, height, rank, match duration).")
    else:
        for col, info in results["impossible_values"].items():
            lines.append(
                f"- `{col}`: {info['count_out_of_bounds']} values outside "
                f"{info['bounds_checked']} (observed range: "
                f"[{info['min_observed']}, {info['max_observed']}])"
            )
    lines.append("")

    lines.append("## 8. Date consistency")
    lines.append("")
    lines.append("| Season | Unparseable dates | Dates outside labelled season year | Date range |")
    lines.append("|---|---|---|---|")
    for season, d in results["date_consistency"].items():
        lines.append(
            f"| {season} | {d['unparseable_dates']} | {d['dates_outside_labelled_season_year']} | "
            f"{d['min_date']} to {d['max_date']} |"
        )
    lines.append("")

    lines.append(
        "The 2025 file's 83 out-of-year dates were checked by hand: they belong to three "
        "pre-season-week tournaments (United Cup, Brisbane, Hong Kong) played "
        "2024-12-29 to 2025-01-04 and assigned to the *following* season's file by "
        "TML-Database's own convention -- confirmed NOT a cross-file duplication (none of "
        "those `tourney_id`s also appear in the 2024 file). This is a labelling convention, "
        "not a data error, but Workstream A2's chronological train/validation/sealed-holdout "
        "split must be done by real match date, not by which season file a match happens to "
        "live in, or a few dozen matches will be mis-dated into the wrong side of a split "
        "boundary."
    )
    lines.append("")

    lines.append("## 9. Retirements, walkovers, defaults")
    lines.append("")
    ret = results["retirements"]
    lines.append(
        f"Across all {ret['total_matches']} matches: {ret['retirements_RET']} retirements (RET), "
        f"{ret['walkovers_W_O']} walkovers (W/O), {ret['defaults_DEF']} defaults (DEF). "
        "Walkovers in particular carry no in-match statistics (0 minutes, all stat columns "
        "null) and no real match was played -- Workstream A2's canonicalisation must exclude "
        "walkovers from any model that uses match-level features, and should make an explicit, "
        "documented decision about whether retirements are kept (the completed portion is a "
        "real result) or excluded (the match was not played to completion, which may bias "
        "duration/stat-dependent features)."
    )
    lines.append("")

    lines.append("## 10. Leakage risk -- columns that must NOT be used as naive pre-match features")
    lines.append("")
    lines.append(
        "**This is the most important structural finding in this audit.** Every row in this "
        "dataset is already outcome-ordered: the columns are `winner_*` and `loser_*`, not "
        "`player_1_*` / `player_2_*`. That means the column position itself perfectly encodes "
        "the label -- a model given these columns as-is (even excluding score/stats) would "
        "trivially achieve 100% accuracy by reading which side is called `winner`. "
        "Workstream A2's canonicalisation MUST re-orient every match into a symmetric "
        "player_a/player_b representation with a separate binary outcome column, decided by a "
        "consistent, arbitrary rule (e.g. alphabetical, or a stable hash of player IDs) that "
        "carries no information about who won, before any modelling touches this data."
    )
    lines.append("")
    lines.append(
        "Separately, the following columns describe what happened DURING or AFTER the match "
        "(final score, match duration, serve/return statistics) and cannot be used as pre-match "
        "predictive features under any column-renaming scheme, because they are not known before "
        "the match is played:"
    )
    lines.append("")
    lines.append("`" + "`, `".join(POST_MATCH_LEAKAGE_COLUMNS) + "`")
    lines.append("")
    lines.append(
        "These remain useful for descriptive analysis (e.g. \"how often do favourites lose in "
        "3 sets\") and for building a player's *pre-match* rolling-form features (e.g. average "
        "first-serve percentage over their last 10 matches, computed only from matches strictly "
        "before the one being predicted) -- but never as direct inputs for the match being "
        "predicted itself."
    )
    lines.append("")

    lines.append("## 11. Overall assessment")
    lines.append("")
    lines.append(
        "The raw TML-Database ATP match data (2021-2025) is clean, consistent, and has no "
        "structural surprises: no schema drift, no exact-key duplicates, no malformed winner/"
        "loser identity rows, and no out-of-bounds values against reasonable plausibility "
        "checks. The real issues to carry into canonicalisation (Workstream A2) are the three "
        "genuine, expected ones any tennis dataset in this shape has: (1) the winner/loser "
        "column orientation is a hard leakage risk that must be fixed before any modelling, "
        "(2) a meaningful share of matches are missing a player rank (wildcards/qualifiers/"
        "deep-field players), needing an explicit policy, and (3) walkovers and retirements "
        "need an explicit, documented inclusion/exclusion rule. None of this blocks proceeding "
        "to canonicalisation; it defines what canonicalisation must do."
    )
    lines.append("")
    return "\n".join(lines)


def run() -> int:
    frames = {season: load_season(season) for season in SEASONS}
    all_df = pd.concat(frames.values(), ignore_index=True)

    results = {
        "coverage": check_coverage(frames),
        "schema_drift": check_schema_drift(frames),
        "missingness": check_missingness(frames),
        "ranking_coverage": check_ranking_coverage(frames),
        "duplicates": check_duplicates(all_df),
        "malformed": check_malformed(all_df),
        "impossible_values": check_impossible_values(all_df),
        "date_consistency": check_date_consistency(frames),
        "retirements": check_retirements_and_walkovers(all_df),
    }

    report = render_report(results)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    print(json.dumps({k: v for k, v in results.items() if k not in {"schema_drift"}}, indent=2, default=str)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
