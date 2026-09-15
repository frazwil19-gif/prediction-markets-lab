"""
Tests for scripts/explore_cycle_002_tennis_match_data.py (Workstream A3).

The single most important property this file checks is NO LOOK-AHEAD: every
rolling/expanding pre-match feature must be computable using only
information from matches strictly before the one it's attached to. A
leakage bug here would silently make the whole exploratory analysis (and
anything built on top of it later) worthless, so this gets direct,
hand-verified coverage rather than just an end-to-end smoke test.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "explore_cycle_002_tennis_match_data.py"


@pytest.fixture()
def script_module():
    spec = importlib.util.spec_from_file_location(
        "explore_cycle_002_tennis_match_data", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    del sys.modules[spec.name]


def _canonical_row(**overrides) -> dict:
    base = {
        "match_id": "m1", "match_id_derived_without_match_num": False,
        "tourney_id": "2024-001", "tourney_name": "Testville", "surface": "Hard",
        "draw_size": 32, "tourney_level": "250", "indoor": "O",
        "tourney_date": "2024-01-01", "match_num": 1, "score": "6-4 6-3",
        "best_of": 3, "round": "R32", "minutes": 90.0, "_season": 2024,
        "_source_row_index": 0, "_source_file": "2024.csv",
        "player_a_id": "AAA1", "player_b_id": "ZZZ9",
        "player_a_seed": None, "player_b_seed": None,
        "player_a_entry": None, "player_b_entry": None,
        "player_a_name": "Alice", "player_b_name": "Zoe",
        "player_a_hand": "R", "player_b_hand": "L",
        "player_a_ht": 180.0, "player_b_ht": 175.0,
        "player_a_ioc": "USA", "player_b_ioc": "GBR",
        "player_a_age": 25.0, "player_b_age": 27.0,
        "player_a_rank": 10.0, "player_b_rank": 20.0,
        "player_a_rank_points": 2000.0, "player_b_rank_points": 1500.0,
        "outcome_a_won": 1,
        "player_a_rank_missing": False, "player_b_rank_missing": False,
        "walkover": False, "retired": False, "defaulted": False,
    }
    base.update(overrides)
    return base


def _write_canonical_csv(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def test_rolling_win_pct_uses_only_strictly_prior_matches(script_module):
    """Player X: win, win, loss, win across 4 dated matches. At the 4th
    match, rolling_win_pct must reflect exactly the first 3 (2/3 = 0.667),
    NEVER including the 4th match's own outcome."""
    canonical = pd.DataFrame([
        _canonical_row(match_id="m1", match_num=1, tourney_date="2024-01-01",
                       player_a_id="X", player_b_id="P1", outcome_a_won=1),
        _canonical_row(match_id="m2", match_num=2, tourney_date="2024-01-08",
                       player_a_id="X", player_b_id="P2", outcome_a_won=1),
        _canonical_row(match_id="m3", match_num=3, tourney_date="2024-01-15",
                       player_a_id="X", player_b_id="P3", outcome_a_won=0),
        _canonical_row(match_id="m4", match_num=4, tourney_date="2024-01-22",
                       player_a_id="X", player_b_id="P4", outcome_a_won=1),
    ])
    canonical["tourney_date"] = pd.to_datetime(canonical["tourney_date"])
    canonical["_round_order"] = 0
    canonical = canonical.sort_values(["tourney_date", "_round_order", "match_num"]).reset_index(drop=True)
    canonical["_match_seq"] = np.arange(len(canonical))

    long_df = script_module.build_long_format(canonical)
    long_df = script_module.add_no_lookahead_rolling_features(long_df)

    x_rows = long_df[long_df["player_id"] == "X"].sort_values("_match_seq")
    # min_periods=3 means at least 3 STRICTLY PRIOR matches are required.
    # Match 1: 0 prior matches -> NaN. Match 2: 1 prior -> NaN.
    assert pd.isna(x_rows.iloc[0]["rolling_win_pct"])
    assert pd.isna(x_rows.iloc[1]["rolling_win_pct"])
    # Match 3: only 2 prior matches (win, win) -- still below min_periods=3 -> NaN.
    # This is itself a no-look-ahead check: if the code wrongly counted the
    # CURRENT match as one of the 3 required periods, this would incorrectly
    # produce a value here instead of NaN.
    assert pd.isna(x_rows.iloc[2]["rolling_win_pct"])
    # Match 4: exactly 3 prior matches (win, win, loss) -> 2/3.
    assert x_rows.iloc[3]["rolling_win_pct"] == pytest.approx(2 / 3)


def test_head_to_head_uses_only_strictly_prior_meetings(script_module):
    """Same two players meet 3 times; A wins the 1st, B wins the 2nd. At
    the 3rd meeting, h2h_a_prior_wins/h2h_b_prior_wins must be exactly
    1 and 1 -- never counting the 3rd match itself."""
    canonical = pd.DataFrame([
        _canonical_row(match_id="m1", match_num=1, tourney_date="2024-01-01",
                       player_a_id="A", player_b_id="B", outcome_a_won=1),
        _canonical_row(match_id="m2", match_num=2, tourney_date="2024-02-01",
                       player_a_id="B", player_b_id="A", outcome_a_won=1),  # B wins
        _canonical_row(match_id="m3", match_num=3, tourney_date="2024-03-01",
                       player_a_id="A", player_b_id="B", outcome_a_won=0),  # B wins again
    ])
    canonical["tourney_date"] = pd.to_datetime(canonical["tourney_date"])
    canonical["_round_order"] = 0
    canonical = canonical.sort_values(["tourney_date", "_round_order", "match_num"]).reset_index(drop=True)
    canonical["_match_seq"] = np.arange(len(canonical))

    with_h2h = script_module.add_head_to_head(canonical)

    m1 = with_h2h[with_h2h["match_id"] == "m1"].iloc[0]
    assert m1["h2h_prior_matches"] == 0

    m2 = with_h2h[with_h2h["match_id"] == "m2"].iloc[0]
    assert m2["h2h_prior_matches"] == 1
    assert m2["h2h_a_prior_wins"] == 0  # player_a here is B, who has 0 prior wins
    assert m2["h2h_b_prior_wins"] == 1  # player_b here is A, who won match 1

    m3 = with_h2h[with_h2h["match_id"] == "m3"].iloc[0]
    assert m3["h2h_prior_matches"] == 2
    assert m3["h2h_a_prior_wins"] == 1  # A (player_a in m3) won match 1
    assert m3["h2h_b_prior_wins"] == 1  # B (player_b in m3) won match 2


def test_days_since_last_match_is_a_real_gap_not_lookahead(script_module):
    canonical = pd.DataFrame([
        _canonical_row(match_id="m1", match_num=1, tourney_date="2024-01-01",
                       player_a_id="X", player_b_id="P1"),
        _canonical_row(match_id="m2", match_num=2, tourney_date="2024-01-11",
                       player_a_id="X", player_b_id="P2"),
    ])
    canonical["tourney_date"] = pd.to_datetime(canonical["tourney_date"])
    canonical["_round_order"] = 0
    canonical = canonical.sort_values(["tourney_date", "_round_order", "match_num"]).reset_index(drop=True)
    canonical["_match_seq"] = np.arange(len(canonical))

    long_df = script_module.build_long_format(canonical)
    long_df = script_module.add_no_lookahead_rolling_features(long_df)
    x_rows = long_df[long_df["player_id"] == "X"].sort_values("_match_seq")

    assert pd.isna(x_rows.iloc[0]["days_since_last_match"])  # no prior match
    assert x_rows.iloc[1]["days_since_last_match"] == 10.0


def test_favourite_side_and_favourite_won(script_module):
    canonical = pd.DataFrame([
        _canonical_row(match_id="m1", player_a_rank=5.0, player_b_rank=50.0, outcome_a_won=1),
        _canonical_row(match_id="m2", player_a_rank=50.0, player_b_rank=5.0, outcome_a_won=1),
        _canonical_row(match_id="m3", player_a_rank=10.0, player_b_rank=10.0, outcome_a_won=1),
    ])
    canonical["tourney_date"] = pd.to_datetime(canonical["tourney_date"])
    canonical["_round_order"] = 0
    canonical = canonical.sort_values(["tourney_date", "_round_order", "match_num"]).reset_index(drop=True)
    canonical["_match_seq"] = np.arange(len(canonical))

    long_df = script_module.build_long_format(canonical)
    long_df = script_module.add_no_lookahead_rolling_features(long_df)
    canonical = script_module.add_head_to_head(canonical)
    merged = script_module.merge_features_into_matches(canonical, long_df)

    m1 = merged[merged["match_id"] == "m1"].iloc[0]
    assert m1["favourite_side"] == "a"  # lower rank = favourite
    assert bool(m1["favourite_won"]) is True  # a is favourite and a won

    m2 = merged[merged["match_id"] == "m2"].iloc[0]
    assert m2["favourite_side"] == "b"  # b has the lower rank here
    assert bool(m2["favourite_won"]) is False  # b is favourite but a won

    m3 = merged[merged["match_id"] == "m3"].iloc[0]
    assert m3["favourite_side"] == "tied"


def test_walkovers_excluded_before_analysis(script_module):
    canonical = pd.DataFrame([
        _canonical_row(match_id="m1", walkover=False),
        _canonical_row(match_id="m2", walkover=True),
    ])
    canonical["tourney_date"] = pd.to_datetime(canonical["tourney_date"])
    loaded = canonical.copy()
    loaded["_round_order"] = loaded["round"].map(script_module.ROUND_ORDER).fillna(-1)
    loaded = loaded.sort_values(["tourney_date", "_round_order", "match_num"]).reset_index(drop=True)
    loaded["_match_seq"] = np.arange(len(loaded))
    assert not loaded[loaded["walkover"]].empty  # sanity: the walkover row is really there

    # load_canonical() itself is the thing that must exclude walkovers.
    tmp_csv = Path("/tmp/_test_canonical_walkover_check.csv")
    canonical.to_csv(tmp_csv, index=False)
    try:
        result = script_module.load_canonical(tmp_csv)
        assert len(result) == 1
        assert result.iloc[0]["match_id"] == "m1"
    finally:
        tmp_csv.unlink(missing_ok=True)


def test_never_writes_outside_the_given_output_path(script_module, tmp_path):
    """Guards against a repeat of the exact real-data-loss pattern found in
    run_cycle_002_tennis_data_acquisition.py earlier the same day (commit
    679cf74): this script must only ever write to the output_path it was
    explicitly given."""
    real_report_path = REPO_ROOT / "research" / "cycles" / "CYCLE_002_TENNIS" / "EXPLORATORY_ANALYSIS.md"
    real_mtime_before = real_report_path.stat().st_mtime if real_report_path.exists() else None

    rows = [
        _canonical_row(match_id=f"m{i}", match_num=i, tourney_date=f"2024-01-{i:02d}",
                       player_a_id="X", player_b_id=f"P{i}", outcome_a_won=i % 2)
        for i in range(1, 6)
    ]
    canonical_path = tmp_path / "canonical.csv"
    _write_canonical_csv(canonical_path, rows)
    output_path = tmp_path / "report.md"

    exit_code = script_module.run(canonical_path=canonical_path, output_path=output_path)

    real_mtime_after = real_report_path.stat().st_mtime if real_report_path.exists() else None
    assert exit_code == 0
    assert output_path.exists()
    assert real_mtime_before == real_mtime_after, (
        "exploratory analysis touched the real repo's output file during a test run"
    )
