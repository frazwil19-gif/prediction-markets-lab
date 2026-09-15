"""
Tests for scripts/canonicalise_cycle_002_tennis_match_data.py -- the
Workstream A2 canonicalisation step built directly from
research/cycles/CYCLE_002_TENNIS/DATA_QUALITY_REPORT.md's findings.

Uses entirely synthetic season CSVs written to tmp_path and passed via
--raw-dir/--output-dir equivalents (raw_dir=/output_dir= kwargs on run()
directly) -- this script never touches real repo paths during a test,
by design (see the script's own 2026-09-15 NOTE on why that matters).
"""
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "canonicalise_cycle_002_tennis_match_data.py"

RAW_COLUMNS = [
    "tourney_id", "tourney_name", "surface", "draw_size", "tourney_level", "indoor",
    "tourney_date", "match_num",
    "winner_id", "winner_seed", "winner_entry", "winner_name", "winner_hand", "winner_ht",
    "winner_ioc", "winner_age", "winner_rank", "winner_rank_points",
    "loser_id", "loser_seed", "loser_entry", "loser_name", "loser_hand", "loser_ht",
    "loser_ioc", "loser_age", "loser_rank", "loser_rank_points",
    "score", "best_of", "round", "minutes",
    "w_ace", "w_df", "w_svpt", "w_1stIn", "w_1stWon", "w_2ndWon", "w_SvGms", "w_bpSaved", "w_bpFaced",
    "l_ace", "l_df", "l_svpt", "l_1stIn", "l_1stWon", "l_2ndWon", "l_SvGms", "l_bpSaved", "l_bpFaced",
]


def _row(**overrides) -> dict:
    base = {c: None for c in RAW_COLUMNS}
    base.update({
        "tourney_id": "2024-001", "tourney_name": "Testville", "surface": "Hard",
        "draw_size": 32, "tourney_level": "250", "indoor": "O",
        "tourney_date": 20240101, "match_num": 1,
        "winner_id": "AAA1", "winner_seed": None, "winner_entry": None,
        "winner_name": "Alice Alpha", "winner_hand": "R", "winner_ht": 180.0,
        "winner_ioc": "USA", "winner_age": 25.0, "winner_rank": 10.0, "winner_rank_points": 2000.0,
        "loser_id": "ZZZ9", "loser_seed": None, "loser_entry": None,
        "loser_name": "Zoe Zulu", "loser_hand": "L", "loser_ht": 175.0,
        "loser_ioc": "GBR", "loser_age": 27.0, "loser_rank": 20.0, "loser_rank_points": 1500.0,
        "score": "6-4 6-3", "best_of": 3, "round": "R32", "minutes": 90.0,
        "w_ace": 5.0, "w_df": 1.0, "w_svpt": 60.0, "w_1stIn": 40.0, "w_1stWon": 30.0,
        "w_2ndWon": 10.0, "w_SvGms": 9.0, "w_bpSaved": 2.0, "w_bpFaced": 3.0,
        "l_ace": 3.0, "l_df": 2.0, "l_svpt": 58.0, "l_1stIn": 35.0, "l_1stWon": 25.0,
        "l_2ndWon": 12.0, "l_SvGms": 8.0, "l_bpSaved": 1.0, "l_bpFaced": 4.0,
    })
    base.update(overrides)
    return base


def _write_season_csv(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows, columns=RAW_COLUMNS).to_csv(path, index=False)


@pytest.fixture()
def script_module():
    spec = importlib.util.spec_from_file_location(
        "canonicalise_cycle_002_tennis_match_data", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    del sys.modules[spec.name]


def _run_with_rows(script_module, tmp_path, rows_by_season: dict[int, list[dict]]):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    for season, rows in rows_by_season.items():
        _write_season_csv(raw_dir / f"{season}.csv", rows)
    # Fill in any seasons the script expects but the test didn't provide,
    # with an empty (header-only) file, since SEASONS is a fixed module
    # constant listing all 5 years.
    for season in script_module.SEASONS:
        if season not in rows_by_season:
            _write_season_csv(raw_dir / f"{season}.csv", [])
    output_dir = tmp_path / "out"
    exit_code = script_module.run(raw_dir=raw_dir, output_dir=output_dir)
    return exit_code, output_dir


def test_ab_assignment_carries_no_outcome_information(script_module, tmp_path):
    """player_a is decided purely by lexicographic order of the two player
    IDs -- verify directly against the documented rule, both when the
    lexicographically-first player wins and when they lose."""
    rows = [
        _row(match_num=1, winner_id="AAA1", loser_id="ZZZ9",
             winner_name="Alice Alpha", loser_name="Zoe Zulu"),  # a (AAA1) wins
        _row(match_num=2, winner_id="ZZZ9", loser_id="AAA1",
             winner_name="Zoe Zulu", loser_name="Alice Alpha",  # b (AAA1) loses this time
             score="7-5 4-6 6-2"),  # deliberately a different score too, so this
             # isn't coincidentally caught by the same-score duplicate check --
             # it's a genuinely different match (see test below for that check).
    ]
    exit_code, output_dir = _run_with_rows(script_module, tmp_path, {2024: rows})
    df = pd.read_csv(output_dir / "cycle_002_canonical_matches.csv")
    assert exit_code == 0
    assert len(df) == 2

    row1 = df[df["match_num"] == 1].iloc[0]
    assert row1["player_a_id"] == "AAA1"  # AAA1 sorts first lexically
    assert row1["outcome_a_won"] == 1  # AAA1 was the winner

    row2 = df[df["match_num"] == 2].iloc[0]
    assert row2["player_a_id"] == "AAA1"  # still AAA1, regardless of who won
    assert row2["outcome_a_won"] == 0  # AAA1 lost this one


def test_walkover_excluded_and_logged(script_module, tmp_path):
    rows = [
        _row(match_num=1, score="6-4 6-3"),
        _row(match_num=2, score="W/O", minutes=None, w_ace=None, w_df=None, w_svpt=None,
             w_1stIn=None, w_1stWon=None, w_2ndWon=None, w_SvGms=None, w_bpSaved=None, w_bpFaced=None,
             l_ace=None, l_df=None, l_svpt=None, l_1stIn=None, l_1stWon=None, l_2ndWon=None,
             l_SvGms=None, l_bpSaved=None, l_bpFaced=None),
    ]
    exit_code, output_dir = _run_with_rows(script_module, tmp_path, {2024: rows})
    canonical = pd.read_csv(output_dir / "cycle_002_canonical_matches.csv")
    exclusions = pd.read_csv(output_dir / "cycle_002_canonicalisation_exclusions.csv")

    assert exit_code == 0
    assert len(canonical) == 1  # only the real match survives
    assert canonical.iloc[0]["match_num"] == 1
    assert len(exclusions) == 1
    assert exclusions.iloc[0]["reason"] == "walkover"
    assert exclusions.iloc[0]["match_num"] == 2


def test_retirement_kept_and_flagged_not_excluded(script_module, tmp_path):
    rows = [_row(match_num=1, score="6-4 3-0 RET")]
    exit_code, output_dir = _run_with_rows(script_module, tmp_path, {2024: rows})
    canonical = pd.read_csv(output_dir / "cycle_002_canonical_matches.csv")
    exclusions = pd.read_csv(output_dir / "cycle_002_canonicalisation_exclusions.csv")

    assert exit_code == 0
    assert len(canonical) == 1
    assert bool(canonical.iloc[0]["retired"]) is True
    assert len(exclusions) == 0


def test_confirmed_upstream_duplicate_deduplicated_and_logged(script_module, tmp_path):
    """Same tourney/players/round/score under two different match_num
    values -- exactly the pattern found for real in the audit -- must be
    de-duplicated, keeping the first occurrence."""
    rows = [
        _row(match_num=5, score="6-4 6-3"),
        _row(match_num=13, score="6-4 6-3"),  # same players/round/score as match_num=5
    ]
    exit_code, output_dir = _run_with_rows(script_module, tmp_path, {2024: rows})
    canonical = pd.read_csv(output_dir / "cycle_002_canonical_matches.csv")
    exclusions = pd.read_csv(output_dir / "cycle_002_canonicalisation_exclusions.csv")

    assert exit_code == 0
    assert len(canonical) == 1
    assert canonical.iloc[0]["match_num"] == 5  # first occurrence kept
    assert len(exclusions) == 1
    assert exclusions.iloc[0]["reason"] == "duplicate_of_upstream_source"
    assert exclusions.iloc[0]["match_num"] == 13


def test_same_players_different_score_not_treated_as_duplicate(script_module, tmp_path):
    """A different score for the same players/round/tournament (e.g. a
    genuine round-robin rematch) must NOT be removed -- only an identical
    score is a confirmed duplicate."""
    rows = [
        _row(match_num=1, score="6-4 6-3"),
        _row(match_num=2, score="7-5 6-2"),  # different score -> not a duplicate
    ]
    exit_code, output_dir = _run_with_rows(script_module, tmp_path, {2024: rows})
    canonical = pd.read_csv(output_dir / "cycle_002_canonical_matches.csv")
    assert exit_code == 0
    assert len(canonical) == 2


def test_missing_rank_never_imputed_only_flagged(script_module, tmp_path):
    rows = [_row(match_num=1, winner_rank=None, winner_rank_points=None)]
    exit_code, output_dir = _run_with_rows(script_module, tmp_path, {2024: rows})
    canonical = pd.read_csv(output_dir / "cycle_002_canonical_matches.csv")
    row = canonical.iloc[0]

    assert exit_code == 0
    # winner_id "AAA1" < loser_id "ZZZ9" lexically, so winner is player_a.
    assert pd.isna(row["player_a_rank"])
    assert bool(row["player_a_rank_missing"]) is True
    assert bool(row["player_b_rank_missing"]) is False


def test_missing_match_num_gets_deterministic_fallback_id(script_module, tmp_path):
    """Mirrors the real 2025-file gap found in the audit: a row with no
    match_num must still get a stable, unique match_id, flagged as derived
    without one."""
    rows = [_row(match_num=None, score="6-4 6-3")]
    exit_code, output_dir = _run_with_rows(script_module, tmp_path, {2024: rows})
    canonical = pd.read_csv(output_dir / "cycle_002_canonical_matches.csv")
    row = canonical.iloc[0]

    assert exit_code == 0
    assert bool(row["match_id_derived_without_match_num"]) is True
    assert isinstance(row["match_id"], str) and len(row["match_id"]) > 0


def test_post_match_stat_columns_are_clearly_labelled_as_leakage(script_module, tmp_path):
    rows = [_row(match_num=1)]
    exit_code, output_dir = _run_with_rows(script_module, tmp_path, {2024: rows})
    canonical = pd.read_csv(output_dir / "cycle_002_canonical_matches.csv")
    version = json.loads((output_dir / "cycle_002_canonicalisation_version.json").read_text())

    assert exit_code == 0
    leakage_cols = [c for c in canonical.columns if c.endswith("_POST_MATCH_LEAKAGE")]
    assert len(leakage_cols) == 18  # 9 stat suffixes x 2 players
    assert set(leakage_cols) == set(version["post_match_leakage_columns"])
    # And the pre-match attributes must NOT carry that suffix.
    assert "player_a_rank" in canonical.columns
    assert "player_a_rank_POST_MATCH_LEAKAGE" not in canonical.columns


def test_match_id_always_unique(script_module, tmp_path):
    rows = [
        _row(match_num=1, winner_id="AAA1", loser_id="BBB2",
             winner_name="Player One", loser_name="Player Two"),
        _row(match_num=2, winner_id="CCC3", loser_id="DDD4",
             winner_name="Player Three", loser_name="Player Four"),
        _row(match_num=None, winner_id="EEE5", loser_id="FFF6",
             winner_name="Player Five", loser_name="Player Six", score="1-6 6-1 6-0"),
    ]
    exit_code, output_dir = _run_with_rows(script_module, tmp_path, {2024: rows})
    canonical = pd.read_csv(output_dir / "cycle_002_canonical_matches.csv")
    assert exit_code == 0
    assert canonical["match_id"].is_unique
    assert len(canonical) == 3


def test_never_writes_outside_the_given_output_dir(script_module, tmp_path):
    """Guards directly against a repeat of the exact real-data-loss bug
    found in run_cycle_002_tennis_data_acquisition.py earlier the same day
    (commit 679cf74): this script must only ever write under the output_dir
    it was explicitly given, never to a REPO_ROOT-relative default."""
    rows = [_row(match_num=1)]
    real_canonical_path = REPO_ROOT / "data" / "processed" / "tennis" / "cycle_002_canonical_matches.csv"
    real_mtime_before = real_canonical_path.stat().st_mtime if real_canonical_path.exists() else None

    _run_with_rows(script_module, tmp_path, {2024: rows})

    real_mtime_after = real_canonical_path.stat().st_mtime if real_canonical_path.exists() else None
    assert real_mtime_before == real_mtime_after, (
        "canonicalisation touched the real repo's output file during a test run"
    )
