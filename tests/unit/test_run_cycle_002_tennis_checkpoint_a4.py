import importlib.util
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_cycle_002_tennis_checkpoint_a4.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("run_cycle_002_tennis_checkpoint_a4", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CANONICAL_COLUMNS = [
    "match_id", "walkover", "_season", "tourney_date", "round", "match_num",
    "surface", "tourney_level", "best_of", "player_a_id", "player_b_id",
    "outcome_a_won", "player_a_rank_points", "player_b_rank_points",
]


def _row(match_id, season, d, surface="Hard", tourney_level="250", best_of=3,
         a="A", b="B", outcome=1, a_points=1000.0, b_points=500.0, round_="R32", match_num=1, walkover=False):
    return {
        "match_id": match_id, "walkover": walkover, "_season": season, "tourney_date": d,
        "round": round_, "match_num": match_num, "surface": surface, "tourney_level": tourney_level,
        "best_of": best_of, "player_a_id": a, "player_b_id": b, "outcome_a_won": outcome,
        "player_a_rank_points": a_points, "player_b_rank_points": b_points,
    }


def test_load_matches_seals_out_the_sealed_holdout_season(tmp_path):
    module = load_script_module()
    csv_path = tmp_path / "canonical.csv"
    rows = [
        _row("m1", 2021, "2021-01-04"),
        _row("m2", 2024, "2024-01-04"),
        _row("m3", 2025, "2025-01-04"),
    ]
    pd.DataFrame(rows, columns=CANONICAL_COLUMNS).to_csv(csv_path, index=False)

    df = module.load_matches(csv_path)
    assert set(df["match_id"]) == {"m1", "m2"}
    assert 2025 not in df["_season"].values


def test_load_matches_excludes_walkovers_defensively(tmp_path):
    module = load_script_module()
    csv_path = tmp_path / "canonical.csv"
    rows = [
        _row("m1", 2021, "2021-01-04", walkover=False),
        _row("m2", 2021, "2021-01-05", walkover=True),
    ]
    pd.DataFrame(rows, columns=CANONICAL_COLUMNS).to_csv(csv_path, index=False)

    df = module.load_matches(csv_path)
    assert set(df["match_id"]) == {"m1"}


def test_to_elo_input_uses_correct_fields():
    module = load_script_module()
    df = pd.DataFrame([_row("m1", 2021, "2021-06-15", surface="Clay", a="playerA", b="playerB", outcome=0)])
    df["tourney_date"] = pd.to_datetime(df["tourney_date"])
    elo_input = module.to_elo_input(df.iloc[0])
    assert elo_input.match_id == "m1"
    assert elo_input.match_date == date(2021, 6, 15)
    assert elo_input.surface == "Clay"
    assert elo_input.player_a_id == "playerA"
    assert elo_input.player_b_id == "playerB"
    assert elo_input.outcome_a_won == 0


def test_to_ranking_input_treats_missing_points_as_none():
    module = load_script_module()
    df = pd.DataFrame([_row("m1", 2021, "2021-06-15", a_points=np.nan, b_points=500.0)])
    df["tourney_date"] = pd.to_datetime(df["tourney_date"])
    ranking_input = module.to_ranking_input(df.iloc[0])
    assert ranking_input.player_a_rank_points is None
    assert ranking_input.player_b_rank_points == 500.0


def _build_tiny_df():
    rows = []
    players = ["p1", "p2", "p3", "p4"]
    d = date(2021, 1, 1)
    match_num = 1
    for season in (2021, 2022, 2023, 2024):
        for i in range(6):
            a, b = players[i % 4], players[(i + 1) % 4]
            rows.append(_row(
                f"{season}_m{i}", season, f"{season}-01-{(i % 27) + 1:02d}",
                a=a, b=b, outcome=i % 2, a_points=1000.0 + i * 10, b_points=500.0 + i * 5,
                match_num=match_num,
            ))
            match_num += 1
    df = pd.DataFrame(rows, columns=CANONICAL_COLUMNS)
    df["tourney_date"] = pd.to_datetime(df["tourney_date"])
    return df


def test_run_elo_model_scores_every_match_with_a_valid_probability():
    module = load_script_module()
    df = _build_tiny_df()
    preds, best_k = module.run_elo_model(df, module.global_rating_key)
    assert set(preds.keys()) == set(df["match_id"])
    assert all(0.0 <= p <= 1.0 for p in preds.values())
    assert best_k in module.K_FACTOR_CANDIDATES


def test_run_ranking_model_only_covers_matches_with_usable_ranking():
    module = load_script_module()
    df = _build_tiny_df()
    unranked_row = df.index[df["match_id"] == "2024_m0"]
    df.loc[unranked_row, "player_a_rank_points"] = np.nan

    preds = module.run_ranking_model(df)
    assert "2024_m0" not in preds
    remaining_ids = set(df["match_id"]) - {"2024_m0"}
    assert set(preds.keys()) == remaining_ids


def test_paired_bootstrap_log_loss_delta_is_exact_for_constant_per_match_losses():
    module = load_script_module()
    # Every row has identical per-match log loss for A and for B (a
    # confident-and-correct model vs. an always-0.5 model), so resampling
    # with replacement can never change the mean -- the bootstrap CI must
    # collapse to exactly the point estimate.
    preds_a = [0.99, 0.99, 0.99, 0.99, 0.99]
    preds_b = [0.5, 0.5, 0.5, 0.5, 0.5]
    actuals = [1, 1, 1, 1, 1]
    result = module.paired_bootstrap_log_loss_delta(preds_a, preds_b, actuals, n_bootstrap=200, seed=1)

    import math
    expected_delta = -math.log(0.99) - (-math.log(0.5))
    assert result["point_delta_log_loss_a_minus_b"] == pytest.approx(expected_delta)
    assert result["ci_2_5_pct"] == pytest.approx(expected_delta)
    assert result["ci_97_5_pct"] == pytest.approx(expected_delta)
    assert result["point_delta_log_loss_a_minus_b"] < 0  # A is the better model here


def test_subgroup_table_skips_groups_smaller_than_five():
    module = load_script_module()
    rows = pd.DataFrame({
        "surface": ["Hard"] * 6 + ["Clay"] * 2,
        "p_a_win": [0.6, 0.6, 0.6, 0.4, 0.4, 0.4, 0.5, 0.5],
        "outcome_a_won": [1, 0, 1, 0, 1, 0, 1, 0],
    })
    table = module._subgroup_table(rows, "surface", "p_a_win")
    levels = {row["level"] for row in table}
    assert levels == {"Hard"}  # Clay has only 2 rows, below the n>=5 floor
