import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_cycle_002_tennis_2025_holdout.py"
A4_PATH = REPO_ROOT / "scripts" / "run_cycle_002_tennis_checkpoint_a4.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("run_cycle_002_tennis_2025_holdout", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_a4_module():
    spec = importlib.util.spec_from_file_location("run_cycle_002_tennis_checkpoint_a4", A4_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COLUMNS = [
    "match_id", "tourney_id", "tourney_name", "surface", "tourney_level", "tourney_date",
    "match_num", "best_of", "round", "_season", "player_a_id", "player_b_id",
    "player_a_rank_points", "player_b_rank_points", "outcome_a_won", "walkover",
]


def _synthetic_canonical_csv(tmp_path, seasons=(2021, 2022, 2023, 2024, 2025), n_per_season=80, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    match_id = 0
    n_players = 24
    player_strength = rng.normal(0, 1, n_players)  # fixed latent strength per player id
    for season in seasons:
        for i in range(n_per_season):
            a, b = rng.choice(n_players, size=2, replace=False)
            match_id += 1
            # Outcome driven by latent strength so Elo has real signal to learn.
            logit = 0.9 * (player_strength[a] - player_strength[b])
            p = 1.0 / (1.0 + np.exp(-logit))
            outcome = int(rng.uniform() < p)
            rows.append({
                "match_id": f"m{match_id}",
                "tourney_id": f"t{season}",
                "tourney_name": "Synthetic Open",
                "surface": "Hard" if i % 2 == 0 else "Clay",
                "tourney_level": "A",
                "tourney_date": pd.Timestamp(f"{season}-01-01") + pd.Timedelta(days=i % 300),
                "match_num": i,
                "best_of": 3,
                "round": "R32",
                "_season": season,
                "player_a_id": f"p{a}",
                "player_b_id": f"p{b}",
                "player_a_rank_points": float(1000 + 200 * player_strength[a] + rng.normal(0, 20)),
                "player_b_rank_points": float(1000 + 200 * player_strength[b] + rng.normal(0, 20)),
                "outcome_a_won": outcome,
                "walkover": False,
            })
    df = pd.DataFrame(rows, columns=COLUMNS)
    path = tmp_path / "synthetic_canonical.csv"
    df.to_csv(path, index=False)
    return path


def test_build_rank_gap_bucket_flags_only_usable_rows():
    module = load_script_module()
    rows = pd.DataFrame({
        "match_id": ["m1", "m2", "m3"],
        "player_a_rank_points": [1000.0, np.nan, 500.0],
        "player_b_rank_points": [500.0, 800.0, 1000.0],
    })
    out = module.build_rank_gap_bucket(rows, ranking_pred_ids={"m1", "m3"}, n_buckets=2)
    assert out["_usable_rank_mask"].tolist() == [True, False, True]
    assert np.isnan(out.loc[1, "_rank_gap_abs"])


def test_build_common_sample_intersects_both_models_and_holdout():
    module = load_script_module()
    holdout_lookup = pd.DataFrame(
        {"outcome_a_won": [1, 0, 1]}, index=pd.Index(["m1", "m2", "m3"], name="match_id")
    )
    global_preds = {"m1": 0.6, "m2": 0.4, "m3": 0.7, "m_not_in_holdout": 0.9}
    ranking_preds = {"m1": 0.55, "m3": 0.65}  # m2 unranked -- absent
    common = module.build_common_sample(global_preds, ranking_preds, holdout_lookup)
    assert sorted(common["match_id"].tolist()) == ["m1", "m3"]
    assert set(common.columns) >= {"global_elo_p_a_win", "ranking_baseline_p_a_win", "outcome_a_won"}


def test_end_to_end_synthetic_run_produces_a_verdict_and_refuses_rerun(tmp_path, monkeypatch):
    module = load_script_module()
    csv_path = _synthetic_canonical_csv(tmp_path)

    report_path = tmp_path / "HOLDOUT_REPORT.md"
    predictions_path = tmp_path / "predictions.csv"
    metrics_path = tmp_path / "metrics.json"
    monkeypatch.setattr(module, "REPORT_PATH", report_path)
    monkeypatch.setattr(module, "PREDICTIONS_PATH", predictions_path)
    monkeypatch.setattr(module, "METRICS_PATH", metrics_path)

    a4 = load_a4_module()
    monkeypatch.setattr(a4, "CANONICAL_PATH", csv_path)

    # Patch _load_module so main() loads OUR a4 (pointed at the synthetic CSV)
    # instead of re-loading the real module fresh (which would reset CANONICAL_PATH).
    monkeypatch.setattr(module, "_load_module", lambda path, name: a4)

    # This synthetic dataset has no reason to calibrate to Tennis Cycle 1's
    # real frozen k_factor (32.0, derived from the REAL training data) --
    # derive what IT calibrates to and treat that as "frozen" for this
    # smoke test, so the k_factor-consistency guard is exercised (see the
    # dedicated mismatch test below) without being conflated with it here.
    probe_df = module.load_matches_including_holdout(a4)
    _, expected_k = a4.run_elo_model(probe_df, a4.global_rating_key)
    monkeypatch.setattr(module, "FROZEN_K_FACTOR", expected_k)

    exit_code = module.main([])
    assert exit_code == 0
    assert report_path.exists()
    text = report_path.read_text()
    assert "# VERDICT:" in text
    assert any(f"# VERDICT: {v}" in text for v in ("PASS", "PARTIAL", "FAIL"))

    # One-shot guard: re-running without --allow-rerun must refuse and leave the report alone.
    original_mtime = report_path.stat().st_mtime
    exit_code_rerun = module.main([])
    assert exit_code_rerun == 1
    assert report_path.stat().st_mtime == original_mtime

    # --allow-rerun explicitly permits it.
    exit_code_forced = module.main(["--allow-rerun"])
    assert exit_code_forced == 0


def test_refuses_to_proceed_if_rederived_k_factor_disagrees_with_frozen_value(tmp_path, monkeypatch):
    module = load_script_module()
    csv_path = _synthetic_canonical_csv(tmp_path)
    monkeypatch.setattr(module, "REPORT_PATH", tmp_path / "HOLDOUT_REPORT.md")
    monkeypatch.setattr(module, "PREDICTIONS_PATH", tmp_path / "predictions.csv")
    monkeypatch.setattr(module, "METRICS_PATH", tmp_path / "metrics.json")
    monkeypatch.setattr(module, "FROZEN_K_FACTOR", -1.0)  # guaranteed to disagree

    a4 = load_a4_module()
    monkeypatch.setattr(a4, "CANONICAL_PATH", csv_path)
    monkeypatch.setattr(module, "_load_module", lambda path, name: a4)

    exit_code = module.main([])
    assert exit_code == 1
    assert not (tmp_path / "HOLDOUT_REPORT.md").exists()
