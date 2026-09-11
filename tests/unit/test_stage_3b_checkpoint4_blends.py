import csv
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_stage_3b_checkpoint4_blends_and_uncertainty.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location(
        "run_stage_3b_checkpoint4_blends_and_uncertainty", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_matches_seals_out_the_holdout_season(tmp_path):
    module = load_script_module()
    csv_path = tmp_path / "matches.csv"
    fieldnames = ["match_id", "season", "competition_code", "match_date", "full_time_result",
                  "home_team_normalised", "away_team_normalised", "eligible_consensus_model"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({"match_id": "m1", "season": "2020_21", "competition_code": "E0", "match_date": "2020-08-01",
                          "full_time_result": "H", "home_team_normalised": "Arsenal", "away_team_normalised": "Chelsea",
                          "eligible_consensus_model": "True"})
        writer.writerow({"match_id": "m2", "season": "2024_25", "competition_code": "E0", "match_date": "2024-08-01",
                          "full_time_result": "H", "home_team_normalised": "Arsenal", "away_team_normalised": "Chelsea",
                          "eligible_consensus_model": "True"})
    rows = module.load_matches(csv_path)
    assert [r["match_id"] for r in rows] == ["m1"]


def test_market_dict_for_renormalizes_to_sum_one():
    module = load_script_module()
    # Deliberately not summing to exactly 1.0, as real per-outcome median
    # consensus rows do not (see STAGE_3B_PLAN.md renormalisation note).
    row = {
        "median_fair_home_probability": "0.50",
        "median_fair_draw_probability": "0.28",
        "median_fair_away_probability": "0.24",
    }
    result = module.market_dict_for(row)
    assert result["home"] + result["draw"] + result["away"] == pytest.approx(1.0, abs=1e-9)


def test_build_goals_by_match_id_matches_real_frozen_dataset_match_ids():
    """Same join-integrity check used in checkpoints 2/3 -- this script
    has its own copy of build_goals_by_match_id (needed since the frozen
    matches CSV never carried FTHG/FTAG), so it must be verified
    independently rather than assumed identical to the other copies."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from prediction_markets_lab.normalisation.team_names import load_alias_table

    matches_path = REPO_ROOT / "data" / "processed" / "football" / "cycle_001_matches_full.csv"
    if not matches_path.exists():
        pytest.skip("frozen processed dataset not present in this checkout")

    module = load_script_module()
    alias_table = load_alias_table(REPO_ROOT / "config" / "football_team_aliases.yaml")
    goals_by_match_id = module.build_goals_by_match_id(REPO_ROOT, alias_table)

    development_match_ids = set()
    with open(matches_path) as f:
        for row in csv.DictReader(f):
            if row["season"] in module.DEVELOPMENT_SEASONS:
                development_match_ids.add(row["match_id"])

    missing = development_match_ids - set(goals_by_match_id.keys())
    assert missing == set(), f"{len(missing)} development match_id(s) failed to join: {sorted(missing)[:5]}"


def test_full_run_against_real_frozen_dataset_is_internally_consistent():
    """End-to-end regression test against the real frozen Cycle 1 dataset.

    This locks in two properties that must hold given fixed frozen data,
    a fixed predeclared weight grid, and a fixed bootstrap seed (so the
    whole computation is deterministic):

    1. Any blend combo that includes "market" as a component must not
       have a WORSE pooled log loss than market alone (the grid search
       always includes the 100%-market corner as a candidate, so the
       calibrated blend can only tie or beat pure market in-sample).
    2. elo_poisson (fundamentals-only, no market) must not be worse,
       out-of-sample, than the worse of its two individual components
       -- note it CAN beat both individually (ensembling reducing
       variance is a normal, desirable outcome), this only guards
       against a blend that is pathologically worse than either
       ingredient.

    Skipped when the real frozen dataset is not present in this
    checkout (e.g. a fresh clone without the untracked data files)."""
    matches_path = REPO_ROOT / "data" / "processed" / "football" / "cycle_001_matches_full.csv"
    freeze_record_path = REPO_ROOT / "reports" / "audits" / "CYCLE_001_FREEZE_RECORD.json"
    if not matches_path.exists() or not freeze_record_path.exists():
        pytest.skip("frozen dataset/freeze record not present in this checkout")

    module = load_script_module()
    exit_code = module.main()
    assert exit_code == 0

    metrics_path = REPO_ROOT / "data" / "interim" / "stage_3b_checkpoint4_metrics.json"
    with open(metrics_path) as f:
        summary = json.load(f)

    pooled = summary["pooled_metrics"]
    market_log_loss = pooled["market"]["log_loss"]

    for combo_name in ("market_elo", "market_poisson", "market_elo_poisson"):
        assert pooled[combo_name]["log_loss"] <= market_log_loss + 1e-9, (
            f"{combo_name} must not be worse than pure market in-sample-calibrated blend"
        )

    elo_only = pooled["elo"]["log_loss"]
    poisson_only = pooled["poisson"]["log_loss"]
    blended = pooled["elo_poisson"]["log_loss"]
    worse_component = max(elo_only, poisson_only)
    assert blended <= worse_component + 1e-9, (
        "elo_poisson blend log loss must not be worse than the worse of its two components"
    )

    # Every bootstrap CI must be well-formed regardless of which side of
    # zero it falls on.
    for name, per_metric in summary["bootstrap_results"].items():
        for key, result in per_metric.items():
            assert result["ci_lower"] <= result["ci_upper"], f"{name}.{key} has an inverted CI"
