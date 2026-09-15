"""
Checkpoint 1's canonicalisation step for the acquired TML-Database ATP
match data (Workstream A2, 2026-09-15 -- see
research/cycles/CYCLE_002_TENNIS/DATA_QUALITY_REPORT.md for the audit this
directly implements the recommendations of).

What this does, and why, driven entirely by the audit's real findings:

1. Re-orients every match from winner/loser columns into a symmetric
   player_a/player_b representation with a separate outcome_a_won column.
   This is the audit's #1 finding: raw winner_*/loser_* columns encode the
   label in the column name itself, which is a hard leakage risk for any
   model. The a/b assignment is decided by a rule that carries ZERO
   information about who won: player_a is whichever of the two player IDs
   sorts first lexicographically. Player IDs are opaque database codes with
   no relationship to who wins a match, so this is safe and, crucially,
   deterministic and reproducible run to run.

2. Removes the 5 confirmed true duplicate matches found in the audit
   (identical tournament/players/round/score, logged twice under different
   match_num values in the upstream source) -- keeping the first occurrence,
   logging the rest as excluded with reason "duplicate_of_upstream_source".

3. Excludes walkovers from the canonical modelling-ready dataset (no real
   match was played; every stat column is null) -- logged as excluded with
   reason "walkover", never silently dropped without a trace.

4. Keeps retirements IN the canonical dataset (a real, if incomplete, match
   was played and has a real winner) but flags them explicitly via
   `retired` so downstream modelling can make its own informed choice
   about whether to include them, rather than that choice being made
   silently here.

5. Never imputes a missing rank. Rows with a missing player_a_rank or
   player_b_rank keep it as null and get an explicit
   player_a_rank_missing / player_b_rank_missing boolean flag -- fabricating
   a plausible-looking rank number would be exactly the kind of invented
   data this project's standing rules prohibit.

6. Builds a deterministic match_id from (tourney_id, match_num, round) when
   match_num is present, and falls back to a stable hash of
   (tourney_id, sorted player ids, round, score) for the ~489 rows (all in
   the 2025 file, per the audit) where match_num is missing -- flagged via
   match_id_derived_without_match_num so this is traceable, not hidden.

Outputs (all under data/processed/tennis/):
- cycle_002_canonical_matches.csv    -- the canonical, modelling-ready rows
- cycle_002_canonicalisation_exclusions.csv -- every excluded raw row + why
- cycle_002_canonicalisation_version.json   -- provenance and counts

Every raw column is preserved in the canonical output (renamed to its a_/b_
canonical name where applicable) -- nothing is deleted, only re-labelled,
flagged, or (for excluded rows) set aside with a documented reason.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "tennis" / "tml_database" / "atp"
OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "tennis"

SEASONS = [2021, 2022, 2023, 2024, 2025]

CANONICALISATION_VERSION = "tennis_cycle_002_canonical_v0.1.0"

# Player/match attributes known BEFORE the match is played -- safe to use
# as pre-match predictive features once rolled up into pre-match form
# (never used as-is for the match they describe, since e.g. rank is the
# rank entering that tournament, which is legitimately known in advance).
PRE_MATCH_ATTRIBUTE_SUFFIXES = [
    "id", "seed", "entry", "name", "hand", "ht", "ioc", "age", "rank", "rank_points",
]

# Attributes that describe what happened DURING/AFTER the match -- kept in
# the canonical output (nothing is deleted) but explicitly labelled as
# leakage risk in the version metadata, per the audit's finding #1.
POST_MATCH_STAT_SUFFIXES = [
    "ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced",
]

MATCH_LEVEL_COLUMNS = [
    "tourney_id", "tourney_name", "surface", "draw_size", "tourney_level", "indoor",
    "tourney_date", "match_num", "score", "best_of", "round", "minutes",
]


@dataclass
class CanonicalisationCounts:
    total_raw_rows: int = 0
    excluded_walkovers: int = 0
    excluded_upstream_duplicates: int = 0
    retirements_kept_and_flagged: int = 0
    rows_missing_match_num_handled_via_fallback_key: int = 0
    canonical_rows_written: int = 0
    rank_a_missing: int = 0
    rank_b_missing: int = 0
    exclusion_reasons: dict = field(default_factory=dict)


def load_raw(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    frames = []
    for season in SEASONS:
        df = pd.read_csv(raw_dir / f"{season}.csv")
        df["_season"] = season
        df["_source_row_index"] = df.index
        df["_source_file"] = f"{season}.csv"
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def mark_upstream_duplicates(df: pd.DataFrame) -> pd.Series:
    """Returns a boolean Series: True for the SECOND (and later) occurrence
    of a confirmed true duplicate (same tourney/players/round/score) --
    the first occurrence is kept, later ones are marked for exclusion.
    Mirrors the audit's manual verification exactly: a same-score identity
    match is a real duplicate; a different-score one is not touched."""
    key_cols = ["tourney_id", "winner_name", "loser_name", "round", "score"]
    is_dupe_of_earlier = df.duplicated(subset=key_cols, keep="first")
    return is_dupe_of_earlier


def build_match_id(row: pd.Series) -> tuple[str, bool]:
    """Deterministic match_id. Uses the real match_num when present (the
    normal, reliable case); falls back to a content hash for the ~489 rows
    (2025 file only, per the audit) where match_num is missing, so every
    row still gets a stable, reproducible id rather than a silently
    dropped or arbitrarily-numbered one."""
    if pd.notna(row["match_num"]):
        return f"{row['tourney_id']}:{int(row['match_num'])}", False
    fallback_key = "|".join(
        str(row[c]) for c in ["tourney_id", "winner_id", "loser_id", "round", "score"]
    )
    digest = hashlib.sha256(fallback_key.encode("utf-8")).hexdigest()[:16]
    return f"{row['tourney_id']}:nomatchnum:{digest}", True


def canonicalise_row(row: pd.Series) -> dict:
    winner_id, loser_id = str(row["winner_id"]), str(row["loser_id"])
    # The a/b assignment rule: whichever player ID sorts first lexically is
    # "a". Player IDs are opaque database codes -- this carries no
    # information whatsoever about who won.
    if winner_id <= loser_id:
        a_prefix, b_prefix, a_is_winner = "winner", "loser", True
    else:
        a_prefix, b_prefix, a_is_winner = "loser", "winner", False

    match_id, derived_without_match_num = build_match_id(row)

    out = {"match_id": match_id, "match_id_derived_without_match_num": derived_without_match_num}
    for c in MATCH_LEVEL_COLUMNS:
        out[c] = row[c]
    out["_season"] = row["_season"]
    out["_source_row_index"] = row["_source_row_index"]
    out["_source_file"] = row["_source_file"]

    for suffix in PRE_MATCH_ATTRIBUTE_SUFFIXES:
        out[f"player_a_{suffix}"] = row[f"{a_prefix}_{suffix}"]
        out[f"player_b_{suffix}"] = row[f"{b_prefix}_{suffix}"]
    for suffix in POST_MATCH_STAT_SUFFIXES:
        a_col = "w" if a_prefix == "winner" else "l"
        b_col = "w" if b_prefix == "winner" else "l"
        out[f"player_a_{suffix}_POST_MATCH_LEAKAGE"] = row[f"{a_col}_{suffix}"]
        out[f"player_b_{suffix}_POST_MATCH_LEAKAGE"] = row[f"{b_col}_{suffix}"]

    out["outcome_a_won"] = int(a_is_winner)
    out["player_a_rank_missing"] = bool(pd.isna(out["player_a_rank"]))
    out["player_b_rank_missing"] = bool(pd.isna(out["player_b_rank"]))

    score_str = str(row["score"]) if pd.notna(row["score"]) else ""
    out["walkover"] = "W/O" in score_str.upper()
    out["retired"] = "RET" in score_str.upper()
    out["defaulted"] = "DEF" in score_str.upper()

    return out


def run(raw_dir: Path = RAW_DIR, output_dir: Path = OUTPUT_DIR) -> int:
    # NOTE (2026-09-15): raw_dir/output_dir are real, honoured parameters --
    # not hardcoded REPO_ROOT constants used directly inside run() -- on
    # purpose. A hardcoded-path version of exactly this pattern in
    # run_cycle_002_tennis_data_acquisition.py silently ignored its own
    # --output-root/--reports-root CLI overrides and caused a real test run
    # to delete real acquired data (see that script's "FIX (2026-09-15)"
    # comment and commit 679cf74). This script is written to never repeat
    # that mistake: every test must be able to point both directories at a
    # tmp_path and know execution will never touch real repo state.
    raw = load_raw(raw_dir)
    counts = CanonicalisationCounts(total_raw_rows=len(raw))

    exclusion_rows = []

    is_upstream_dupe = mark_upstream_duplicates(raw)
    counts.excluded_upstream_duplicates = int(is_upstream_dupe.sum())
    for _, row in raw[is_upstream_dupe].iterrows():
        exclusion_rows.append({
            "tourney_id": row["tourney_id"], "match_num": row["match_num"],
            "winner_name": row["winner_name"], "loser_name": row["loser_name"],
            "round": row["round"], "_season": row["_season"],
            "reason": "duplicate_of_upstream_source",
        })

    working = raw[~is_upstream_dupe].copy()

    canonical_records = [canonicalise_row(row) for _, row in working.iterrows()]
    canonical_df = pd.DataFrame(canonical_records)

    is_walkover = canonical_df["walkover"]
    counts.excluded_walkovers = int(is_walkover.sum())
    for _, row in canonical_df[is_walkover].iterrows():
        exclusion_rows.append({
            "tourney_id": row["tourney_id"], "match_num": row["match_num"],
            "winner_name": None, "loser_name": None,
            "round": row["round"], "_season": row["_season"],
            "reason": "walkover",
        })
    canonical_df = canonical_df[~is_walkover].reset_index(drop=True)

    counts.retirements_kept_and_flagged = int(canonical_df["retired"].sum())
    counts.rows_missing_match_num_handled_via_fallback_key = int(
        canonical_df["match_id_derived_without_match_num"].sum()
    )
    counts.rank_a_missing = int(canonical_df["player_a_rank_missing"].sum())
    counts.rank_b_missing = int(canonical_df["player_b_rank_missing"].sum())
    counts.canonical_rows_written = len(canonical_df)
    counts.exclusion_reasons = pd.Series(
        [r["reason"] for r in exclusion_rows]
    ).value_counts().to_dict() if exclusion_rows else {}

    assert canonical_df["match_id"].is_unique, "match_id must be unique after canonicalisation"
    assert set(canonical_df["outcome_a_won"].unique()) <= {0, 1}
    assert counts.canonical_rows_written + counts.excluded_walkovers + counts.excluded_upstream_duplicates == counts.total_raw_rows

    output_dir.mkdir(parents=True, exist_ok=True)
    canonical_path = output_dir / "cycle_002_canonical_matches.csv"
    canonical_df.to_csv(canonical_path, index=False)

    exclusions_path = output_dir / "cycle_002_canonicalisation_exclusions.csv"
    exclusion_columns = ["tourney_id", "match_num", "winner_name", "loser_name", "round", "_season", "reason"]
    # Always write a real header, even with zero excluded rows -- an empty
    # exclusion_rows list would otherwise produce a completely empty file
    # (pd.DataFrame([]) has no columns), which downstream code reading this
    # file with pd.read_csv would fail on with EmptyDataError. A clean run
    # with nothing excluded is a real, expected outcome and must still
    # produce a valid, readable (header-only) CSV.
    pd.DataFrame(exclusion_rows, columns=exclusion_columns).to_csv(exclusions_path, index=False)

    version_path = output_dir / "cycle_002_canonicalisation_version.json"
    version = {
        "canonicalisation_version": CANONICALISATION_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(raw_dir),
        "counts": {
            "total_raw_rows": counts.total_raw_rows,
            "excluded_walkovers": counts.excluded_walkovers,
            "excluded_upstream_duplicates": counts.excluded_upstream_duplicates,
            "canonical_rows_written": counts.canonical_rows_written,
            "retirements_kept_and_flagged": counts.retirements_kept_and_flagged,
            "rows_missing_match_num_handled_via_fallback_key": counts.rows_missing_match_num_handled_via_fallback_key,
            "player_a_rank_missing": counts.rank_a_missing,
            "player_b_rank_missing": counts.rank_b_missing,
        },
        "decisions": {
            "a_b_assignment_rule": "player_a = whichever of winner_id/loser_id sorts first lexicographically -- carries no information about who won",
            "walkovers": "excluded from canonical dataset (no real match played, all stats null); logged in exclusions file",
            "retirements": "kept in canonical dataset, flagged via `retired` column -- a real (if incomplete) match with a real winner",
            "upstream_duplicates": "5 confirmed true duplicates (identical tourney/players/round/score under different match_num) -- first occurrence kept, rest excluded and logged",
            "missing_rank": "never imputed -- kept null, flagged via player_a_rank_missing/player_b_rank_missing",
            "post_match_stat_columns": "preserved but suffixed _POST_MATCH_LEAKAGE -- must never be used as a feature for predicting the match they belong to",
        },
        "post_match_leakage_columns": [
            f"player_{side}_{suffix}_POST_MATCH_LEAKAGE"
            for side in ("a", "b") for suffix in POST_MATCH_STAT_SUFFIXES
        ],
    }
    with open(version_path, "w") as f:
        json.dump(version, f, indent=2, sort_keys=True)

    print(f"Wrote {canonical_path} ({counts.canonical_rows_written} rows)")
    print(f"Wrote {exclusions_path} ({len(exclusion_rows)} rows)")
    print(f"Wrote {version_path}")
    print(json.dumps(version["counts"], indent=2))
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    cli_args = parser.parse_args()
    raise SystemExit(run(raw_dir=cli_args.raw_dir, output_dir=cli_args.output_dir))
