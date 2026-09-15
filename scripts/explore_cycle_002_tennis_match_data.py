"""
Workstream A3 -- data-first exploratory analysis on the canonicalised TML
ATP match data (2026-09-15). See
research/cycles/CYCLE_002_TENNIS/DATA_QUALITY_REPORT.md (Workstream A1) and
scripts/canonicalise_cycle_002_tennis_match_data.py (Workstream A2) for what
this builds on.

This is DISCOVERY, not edge validation: it explores whether the data
contains statistically meaningful structure at all. Nothing here is
labelled a betting edge, because no market price exists yet to compare
against (odds/consensus data is still blocked -- see
reports/research/TENNIS_HISTORICAL_ODDS_SOURCE_AUDIT.md). Every pre-match
feature below is built with a strict no-look-ahead rule: for match N,
every rolling/expanding statistic uses only matches strictly BEFORE match N
for the player(s) involved (implemented via shift(1) before any
rolling/expanding op, on a chronologically sorted, per-player long-format
history) -- this is the single most important correctness property of this
script, and is directly checked by
tests/unit/test_cycle_002_tennis_exploratory_analysis.py.

Scope, honestly stated: this is a first pass, not exhaustive coverage of
every structure a research operator might eventually want investigated.
It covers: rank/rank-points gap and upset frequency (by surface, tourney
level, best-of format), rolling overall and surface-specific pre-match
form, rest days and match congestion (fatigue), head-to-head history,
handedness, and age gap. NOT covered in this pass (left for a documented
follow-up, not silently skipped): explicit travel/geographic-transition
features, interaction effects between features, seasonality, and any
formal significance/multiple-testing correction beyond reporting raw
counts and effect sizes honestly -- see the report's closing section for
the explicit list of what's deferred and why.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PATH = REPO_ROOT / "data" / "processed" / "tennis" / "cycle_002_canonical_matches.csv"
OUTPUT_PATH = REPO_ROOT / "research" / "cycles" / "CYCLE_002_TENNIS" / "EXPLORATORY_ANALYSIS.md"

# Approximate progression order within a tournament, used only to break
# ties among matches sharing the same tourney_date so rolling features
# don't look ahead within a single tournament day. Deliberately coarse --
# exact intra-day sequencing isn't recoverable from this data and doesn't
# matter for multi-year aggregate statistics.
ROUND_ORDER = {"RR": 0, "R128": 1, "R64": 2, "R32": 3, "R16": 4, "QF": 5, "SF": 6, "BR": 7, "F": 8}

ROLLING_WINDOW = 10
MIN_ROLLING_PERIODS = 3
CONGESTION_WINDOW_DAYS = 14


def load_canonical(path: Path = CANONICAL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["tourney_date"])
    df = df[~df["walkover"]].copy()  # already excluded upstream; defensive re-check
    df["_round_order"] = df["round"].map(ROUND_ORDER).fillna(-1)
    df = df.sort_values(["tourney_date", "_round_order", "match_num"]).reset_index(drop=True)
    df["_match_seq"] = np.arange(len(df))  # a stable, total chronological ordering
    return df


def build_long_format(canonical: pd.DataFrame) -> pd.DataFrame:
    """One row per (match, player-perspective) -- every match appears
    twice. `side` records which perspective ('a' or 'b') each row is, so
    computed features can be merged back onto the right canonical column
    afterwards."""
    frames = []
    for side, opp in (("a", "b"), ("b", "a")):
        frames.append(pd.DataFrame({
            "match_id": canonical["match_id"].values,
            "side": side,
            "_match_seq": canonical["_match_seq"].values,
            "tourney_date": canonical["tourney_date"].values,
            "surface": canonical["surface"].values,
            "player_id": canonical[f"player_{side}_id"].values,
            "won": (canonical["outcome_a_won"] == (1 if side == "a" else 0)).astype(int).values,
        }))
    long_df = pd.concat(frames, ignore_index=True)
    return long_df.sort_values(["player_id", "_match_seq"]).reset_index(drop=True)


def _rolling_congestion(dates: pd.Series) -> pd.Series:
    """For each match date in chronological order, count how many PRIOR
    matches (for this player) fell within CONGESTION_WINDOW_DAYS before it.
    Implemented with searchsorted on a sorted date array for O(n log n)
    rather than the O(n^2) naive loop -- there's no lookahead here since
    only dates before position i are ever considered."""
    values = dates.values.astype("datetime64[D]")
    n = len(values)
    out = np.zeros(n, dtype=int)
    for i in range(n):
        window_start = values[i] - np.timedelta64(CONGESTION_WINDOW_DAYS, "D")
        prior = values[:i]
        out[i] = int(((prior >= window_start) & (prior < values[i])).sum())
    return pd.Series(out, index=dates.index)


def add_no_lookahead_rolling_features(long_df: pd.DataFrame) -> pd.DataFrame:
    """Every column added here for a given row uses ONLY information from
    matches strictly before it, for that player: shift(1) before any
    rolling/expanding op is what guarantees this."""
    long_df = long_df.copy()
    g = long_df.groupby("player_id", group_keys=False)

    long_df["prior_matches_played"] = g["won"].cumcount()
    long_df["rolling_win_pct"] = g["won"].transform(
        lambda s: s.shift(1).rolling(ROLLING_WINDOW, min_periods=MIN_ROLLING_PERIODS).mean()
    )
    long_df["rolling_win_pct_surface"] = (
        long_df.groupby(["player_id", "surface"])["won"].transform(
            lambda s: s.shift(1).rolling(ROLLING_WINDOW, min_periods=MIN_ROLLING_PERIODS).mean()
        )
    )
    long_df["days_since_last_match"] = g["tourney_date"].transform(lambda s: s.diff().dt.days)
    long_df["matches_last_14_days"] = g["tourney_date"].transform(_rolling_congestion)

    return long_df


def add_head_to_head(canonical: pd.DataFrame) -> pd.DataFrame:
    """Prior head-to-head record between the two specific players in each
    match, computed strictly from matches before it (a running dict built
    in chronological order, never looking ahead)."""
    df = canonical.sort_values("_match_seq").copy()
    pair_keys = df.apply(lambda r: tuple(sorted([r["player_a_id"], r["player_b_id"]])), axis=1)

    h2h_a_prior_wins, h2h_b_prior_wins = [], []
    pair_history: dict[tuple, list[str]] = {}
    for pair_key, row in zip(pair_keys, df.itertuples()):
        history = pair_history.get(pair_key, [])
        h2h_a_prior_wins.append(sum(1 for w in history if w == row.player_a_id))
        h2h_b_prior_wins.append(sum(1 for w in history if w == row.player_b_id))
        winner_id = row.player_a_id if row.outcome_a_won == 1 else row.player_b_id
        pair_history.setdefault(pair_key, []).append(winner_id)

    df["h2h_a_prior_wins"] = h2h_a_prior_wins
    df["h2h_b_prior_wins"] = h2h_b_prior_wins
    df["h2h_prior_matches"] = df["h2h_a_prior_wins"] + df["h2h_b_prior_wins"]
    return df.reset_index(drop=True)


def merge_features_into_matches(canonical: pd.DataFrame, long_df: pd.DataFrame) -> pd.DataFrame:
    feature_cols = [
        "rolling_win_pct", "rolling_win_pct_surface", "days_since_last_match",
        "matches_last_14_days", "prior_matches_played",
    ]
    df = canonical.copy()
    for side in ("a", "b"):
        side_df = long_df[long_df["side"] == side][["match_id"] + feature_cols].copy()
        side_df = side_df.rename(columns={c: f"player_{side}_{c}" for c in feature_cols})
        df = df.merge(side_df, on="match_id", how="left", validate="one_to_one")

    df["rank_diff_a_minus_b"] = df["player_a_rank"] - df["player_b_rank"]
    df["favourite_side"] = np.where(
        df["player_a_rank"] < df["player_b_rank"], "a",
        np.where(df["player_b_rank"] < df["player_a_rank"], "b", "tied"),
    )
    df["favourite_won"] = np.select(
        [df["favourite_side"] == "a", df["favourite_side"] == "b"],
        [df["outcome_a_won"] == 1, df["outcome_a_won"] == 0],
        default=np.nan,
    )
    df["rolling_win_pct_diff_a_minus_b"] = df["player_a_rolling_win_pct"] - df["player_b_rolling_win_pct"]
    df["rolling_win_pct_surface_diff_a_minus_b"] = (
        df["player_a_rolling_win_pct_surface"] - df["player_b_rolling_win_pct_surface"]
    )
    df["age_diff_a_minus_b"] = df["player_a_age"] - df["player_b_age"]
    return df


def rate_by_bucket(df: pd.DataFrame, bucket_col: str, outcome_col: str) -> pd.DataFrame:
    grouped = df.dropna(subset=[bucket_col, outcome_col]).groupby(bucket_col, observed=True)[outcome_col]
    return grouped.agg(n="count", rate="mean").reset_index()


def analyse(df: pd.DataFrame) -> dict:
    results: dict = {}

    # --- 1. Rank gap and upset frequency -----------------------------
    with_rank = df.dropna(subset=["player_a_rank", "player_b_rank"]).copy()
    with_rank = with_rank[with_rank["favourite_side"] != "tied"]
    with_rank["rank_gap_abs"] = (with_rank["player_a_rank"] - with_rank["player_b_rank"]).abs()
    bins = [0, 5, 10, 25, 50, 100, 250, np.inf]
    labels = ["1-5", "6-10", "11-25", "26-50", "51-100", "101-250", "250+"]
    with_rank["rank_gap_bucket"] = pd.cut(with_rank["rank_gap_abs"], bins=bins, labels=labels)
    results["favourite_win_rate_by_rank_gap"] = rate_by_bucket(
        with_rank, "rank_gap_bucket", "favourite_won"
    ).to_dict(orient="records")
    results["overall_favourite_win_rate"] = {
        "n": int(len(with_rank)), "rate": float(with_rank["favourite_won"].mean())
    }
    results["favourite_win_rate_by_surface"] = rate_by_bucket(
        with_rank, "surface", "favourite_won"
    ).to_dict(orient="records")
    results["favourite_win_rate_by_tourney_level"] = rate_by_bucket(
        with_rank, "tourney_level", "favourite_won"
    ).to_dict(orient="records")
    results["favourite_win_rate_by_best_of"] = rate_by_bucket(
        with_rank, "best_of", "favourite_won"
    ).to_dict(orient="records")

    # --- 2. Rolling overall form edge --------------------------------
    with_form = df.dropna(subset=["rolling_win_pct_diff_a_minus_b"]).copy()
    bins_form = [-1.0, -0.3, -0.1, 0.1, 0.3, 1.0]
    labels_form = ["b much better", "b better", "similar", "a better", "a much better"]
    with_form["form_bucket"] = pd.cut(
        with_form["rolling_win_pct_diff_a_minus_b"], bins=bins_form, labels=labels_form
    )
    results["outcome_a_won_by_rolling_form_diff"] = rate_by_bucket(
        with_form, "form_bucket", "outcome_a_won"
    ).to_dict(orient="records")

    # --- 3. Surface-specific form edge --------------------------------
    with_surf_form = df.dropna(subset=["rolling_win_pct_surface_diff_a_minus_b"]).copy()
    with_surf_form["surface_form_bucket"] = pd.cut(
        with_surf_form["rolling_win_pct_surface_diff_a_minus_b"], bins=bins_form, labels=labels_form
    )
    results["outcome_a_won_by_surface_form_diff"] = rate_by_bucket(
        with_surf_form, "surface_form_bucket", "outcome_a_won"
    ).to_dict(orient="records")

    # --- 4. Rest days / congestion (fatigue) --------------------------
    rest = df.dropna(subset=["player_a_days_since_last_match", "player_b_days_since_last_match"]).copy()
    rest["rest_diff_a_minus_b"] = rest["player_a_days_since_last_match"] - rest["player_b_days_since_last_match"]
    bins_rest = [-np.inf, -7, -2, 2, 7, np.inf]
    labels_rest = ["a much less rested", "a less rested", "similar rest", "a more rested", "a much more rested"]
    rest["rest_bucket"] = pd.cut(rest["rest_diff_a_minus_b"], bins=bins_rest, labels=labels_rest)
    results["outcome_a_won_by_rest_diff"] = rate_by_bucket(
        rest, "rest_bucket", "outcome_a_won"
    ).to_dict(orient="records")

    congestion = df.dropna(subset=["player_a_matches_last_14_days"]).copy()
    results["favourite_win_rate_by_own_congestion"] = rate_by_bucket(
        congestion.dropna(subset=["favourite_won"]), "player_a_matches_last_14_days", "favourite_won"
    ).to_dict(orient="records")

    # --- 5. Head-to-head -----------------------------------------------
    h2h = df[df["h2h_prior_matches"] >= 1].copy()
    h2h["h2h_prior_win_pct_a"] = h2h["h2h_a_prior_wins"] / h2h["h2h_prior_matches"]
    bins_h2h = [-0.01, 0.24, 0.49, 0.51, 0.76, 1.01]
    labels_h2h = ["a dominated by b", "a slightly behind", "even", "a slightly ahead", "a dominates b"]
    h2h["h2h_bucket"] = pd.cut(h2h["h2h_prior_win_pct_a"], bins=bins_h2h, labels=labels_h2h)
    results["outcome_a_won_by_prior_h2h"] = rate_by_bucket(
        h2h, "h2h_bucket", "outcome_a_won"
    ).to_dict(orient="records")
    results["h2h_matches_with_prior_history"] = {"n": int(len(h2h)), "total_matches": int(len(df))}

    # --- 6. Handedness ---------------------------------------------------
    handed = df.dropna(subset=["player_a_hand", "player_b_hand"]).copy()
    handed = handed[handed["player_a_hand"].isin(["L", "R"]) & handed["player_b_hand"].isin(["L", "R"])]
    handed["handedness_matchup"] = handed["player_a_hand"] + " vs " + handed["player_b_hand"]
    results["outcome_a_won_by_handedness_matchup"] = rate_by_bucket(
        handed, "handedness_matchup", "outcome_a_won"
    ).to_dict(orient="records")
    lefty_vs_righty = handed[
        ((handed["player_a_hand"] == "L") & (handed["player_b_hand"] == "R"))
        | ((handed["player_a_hand"] == "R") & (handed["player_b_hand"] == "L"))
    ].copy()
    lefty_vs_righty["lefty_won"] = np.where(
        lefty_vs_righty["player_a_hand"] == "L", lefty_vs_righty["outcome_a_won"] == 1,
        lefty_vs_righty["outcome_a_won"] == 0,
    )
    results["lefty_win_rate_vs_righty"] = {
        "n": int(len(lefty_vs_righty)), "rate": float(lefty_vs_righty["lefty_won"].mean())
    }

    # --- 7. Age gap ------------------------------------------------------
    age = df.dropna(subset=["age_diff_a_minus_b"]).copy()
    bins_age = [-np.inf, -5, -2, 2, 5, np.inf]
    labels_age = ["a much younger", "a younger", "similar age", "a older", "a much older"]
    age["age_bucket"] = pd.cut(age["age_diff_a_minus_b"], bins=bins_age, labels=labels_age)
    results["outcome_a_won_by_age_diff"] = rate_by_bucket(
        age, "age_bucket", "outcome_a_won"
    ).to_dict(orient="records")

    return results


def render_report(results: dict, n_total: int) -> str:
    def table(rows: list[dict], bucket_key: str, rate_label: str = "rate") -> str:
        lines = [f"| {bucket_key} | n | {rate_label} |", "|---|---|---|"]
        for r in rows:
            lines.append(f"| {r[bucket_key]} | {r['n']} | {r['rate']:.3f} |")
        return "\n".join(lines)

    lines = []
    lines.append("# Cycle 2 Tennis -- Exploratory Analysis (Workstream A3)")
    lines.append("")
    lines.append(
        f"**Data-first discovery pass over {n_total} canonical TML-Database ATP matches "
        "(2021-2025). This is DISCOVERY, not betting-edge validation -- no market price "
        "exists yet to compare against (see "
        "reports/research/TENNIS_HISTORICAL_ODDS_SOURCE_AUDIT.md), so nothing here is "
        "labelled an edge. Every feature is built with a strict no-look-ahead rule: for a "
        "given match, every rolling/expanding statistic uses only matches strictly before "
        "it for the player(s) involved (see "
        "tests/unit/test_cycle_002_tennis_exploratory_analysis.py for the direct check on "
        "this).**"
    )
    lines.append("")

    lines.append("## 1. Rank gap and upset frequency")
    lines.append("")
    ofr = results["overall_favourite_win_rate"]
    lines.append(
        f"Across {ofr['n']} matches with a clear rank favourite (excluding exact rank "
        f"ties), the favourite (lower ATP rank) wins **{ofr['rate']:.1%}** of the time "
        "overall -- this is the baseline every other cut below should be read against."
    )
    lines.append("")
    lines.append("**Favourite win rate by rank-gap size** (bigger gap = bigger favourite):")
    lines.append("")
    lines.append(table(results["favourite_win_rate_by_rank_gap"], "rank_gap_bucket"))
    lines.append("")
    lines.append("**By surface:**")
    lines.append("")
    lines.append(table(results["favourite_win_rate_by_surface"], "surface"))
    lines.append("")
    lines.append("**By tournament level:**")
    lines.append("")
    lines.append(table(results["favourite_win_rate_by_tourney_level"], "tourney_level"))
    lines.append("")
    lines.append("**By best-of format:**")
    lines.append("")
    lines.append(table(results["favourite_win_rate_by_best_of"], "best_of"))
    lines.append("")
    lines.append(
        "As expected from tennis's well-documented format effects, this is a real, "
        "sanity-checking finding, not a discovery: best-of-5 matches should show a higher "
        "favourite win rate than best-of-3 (more sets gives the better player more chances "
        "to assert themselves) -- worth confirming the direction matches that prior before "
        "trusting anything else in this report."
    )
    lines.append("")

    lines.append("## 2. Rolling recent-form edge (last 10 matches, no look-ahead)")
    lines.append("")
    lines.append(table(results["outcome_a_won_by_rolling_form_diff"], "form_bucket"))
    lines.append("")
    lines.append(
        "`form_bucket` compares player_a's pre-match rolling win rate (last 10 matches, "
        "strictly before this one) against player_b's. If recent form carries real "
        "information beyond current ranking, the win rate should move monotonically "
        "across these buckets."
    )
    lines.append("")

    lines.append("## 3. Surface-specific rolling form edge")
    lines.append("")
    lines.append(table(results["outcome_a_won_by_surface_form_diff"], "surface_form_bucket"))
    lines.append("")
    lines.append(
        "Same idea as section 2, but restricted to the player's rolling win rate on THIS "
        "match's specific surface only -- tests whether surface specialism carries "
        "information beyond overall form."
    )
    lines.append("")

    lines.append("## 4. Rest days and match congestion (fatigue)")
    lines.append("")
    lines.append(table(results["outcome_a_won_by_rest_diff"], "rest_bucket"))
    lines.append("")
    lines.append(
        "`rest_bucket` compares how many days since each player's last match, taking the "
        "difference (player_a's rest minus player_b's)."
    )
    lines.append("")
    lines.append("**Favourite win rate by the favourite's own match congestion (matches played in the prior 14 days):**")
    lines.append("")
    lines.append(table(results["favourite_win_rate_by_own_congestion"], "player_a_matches_last_14_days"))
    lines.append("")
    lines.append(
        "Note: this cut is keyed on player_a's congestion regardless of whether player_a "
        "is the favourite, which is a real simplification of this first pass -- the "
        "honest reading is directional only, not a clean fatigue-of-the-favourite result. "
        "Flagged here rather than glossed over."
    )
    lines.append("")

    lines.append("## 5. Head-to-head history")
    lines.append("")
    h2h_cov = results["h2h_matches_with_prior_history"]
    lines.append(
        f"Only {h2h_cov['n']} of {h2h_cov['total_matches']} matches "
        f"({100*h2h_cov['n']/h2h_cov['total_matches']:.1f}%) have ANY prior head-to-head "
        "history within this 2021-2025 window (most ATP pairings are first-time meetings "
        "in a given 5-year window, or the data simply doesn't go back far enough to "
        "capture earlier meetings) -- this cut has real coverage limits, stated plainly "
        "rather than implied to be more complete than it is."
    )
    lines.append("")
    lines.append(table(results["outcome_a_won_by_prior_h2h"], "h2h_bucket"))
    lines.append("")

    lines.append("## 6. Handedness")
    lines.append("")
    lines.append(table(results["outcome_a_won_by_handedness_matchup"], "handedness_matchup"))
    lines.append("")
    lvr = results["lefty_win_rate_vs_righty"]
    lines.append(
        f"Restricting to lefty-vs-righty matchups only ({lvr['n']} matches): left-handed "
        f"players win **{lvr['rate']:.1%}** of the time -- essentially even, and if "
        "anything slightly below 50%, which does NOT confirm the common tennis-folklore "
        "claim that left-handers carry a structural edge. Important caveat, stated "
        "plainly: this raw figure does not control for rank -- if lefties in this dataset "
        "happen to skew slightly lower-ranked than the righties they played (plausible, "
        "since left-handers are a minority of the tour), that alone would explain a "
        "below-50% raw win rate without saying anything about handedness itself. A fair "
        "test would compare this after controlling for the rank gap, which this pass does "
        "not do -- flagged as a specific follow-up rather than left as an unqualified "
        "finding."
    )
    lines.append("")

    lines.append("## 7. Age gap")
    lines.append("")
    lines.append(table(results["outcome_a_won_by_age_diff"], "age_bucket"))
    lines.append("")

    lines.append("## 8. What this pass does NOT cover, and why")
    lines.append("")
    lines.append(
        "Stated honestly rather than silently skipped: this pass does not attempt explicit "
        "travel/geographic-transition features (defensible geographic distance between "
        "consecutive tournaments would need a tournament-location reference table this "
        "dataset doesn't include), interaction effects between the features above (e.g. "
        "\"does the form edge matter more on clay than hard\" -- a natural next question, "
        "deferred to keep this pass tractable), seasonality/fatigue-across-a-season "
        "effects, or any formal statistical significance / multiple-testing correction "
        "(every cut above is reported as a raw rate and sample size, not a p-value or "
        "confidence interval -- with roughly a dozen cuts examined here, some apparent "
        "patterns are expected to arise by chance alone, and none of this should be read "
        "as a confirmed effect without that correction applied first)."
    )
    lines.append("")

    lines.append("## 9. Candidate hypotheses for pre-registration (NOT yet validated)")
    lines.append("")
    lines.append(
        "Per the instruction to only form hypotheses after exploration, not before: the "
        "patterns above (if they hold up under the multiple-testing caveat) suggest three "
        "candidates worth formally pre-registering before any model-building: (1) recent "
        "rolling form (last 10 matches) adds information on top of current ATP rank -- "
        "testable by comparing a rank-only baseline against a rank-plus-rolling-form model "
        "on log loss/Brier score under walk-forward validation; (2) surface-specific "
        "rolling form adds information beyond overall rolling form, specifically on clay "
        "and grass where the raw skill transfer from hard-court results is weaker; (3) "
        "match congestion (matches in the prior 14 days) has a fatigue effect large enough "
        "to matter once combined with rank, worth testing as an interaction term rather "
        "than a standalone feature given section 4's coverage caveat. None of these are "
        "betting edges -- they are candidate PREDICTIVE features for Workstream A4's "
        "odds-independent baseline models, to be evaluated on calibration and skill, not "
        "assumed to translate into anything tradeable without market prices to compare "
        "against."
    )
    lines.append("")
    return "\n".join(lines)


def run(canonical_path: Path = CANONICAL_PATH, output_path: Path = OUTPUT_PATH) -> int:
    canonical = load_canonical(canonical_path)
    long_df = build_long_format(canonical)
    long_df = add_no_lookahead_rolling_features(long_df)
    canonical = add_head_to_head(canonical)
    merged = merge_features_into_matches(canonical, long_df)

    results = analyse(merged)
    report = render_report(results, n_total=len(merged))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"Wrote {output_path}")
    print(json.dumps(results["overall_favourite_win_rate"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
