import csv
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_stage_3b_checkpoint6_holdout_evaluation.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location(
        "run_stage_3b_checkpoint6_holdout_evaluation", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_matches_including_holdout_does_include_the_holdout_season(tmp_path):
    """UNIQUE to Checkpoint 6: this is the one script that must NOT seal
    out 2024_25 -- every other Stage 3B script's own seal test asserts
    the opposite. This test locks in that this script's inclusion of the
    holdout is deliberate, not an accidental copy-paste of the seal
    guard from another checkpoint script."""
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
    rows = module.load_matches_including_holdout(csv_path)
    assert {r["match_id"] for r in rows} == {"m1", "m2"}


def test_apply_verdict_rubric_strong_signal_when_ci_entirely_below_zero():
    module = load_script_module()
    verdict = module.apply_verdict_rubric("elo_poisson", best_delta=-0.02, best_ci_lower=-0.03, best_ci_upper=-0.01)
    assert verdict == "STRONG SIGNAL"


def test_apply_verdict_rubric_market_dominates_when_ci_entirely_above_zero():
    module = load_script_module()
    verdict = module.apply_verdict_rubric("elo_poisson", best_delta=0.03, best_ci_lower=0.01, best_ci_upper=0.05)
    assert verdict == "MARKET DOMINATES / NULL RESULT"


def test_apply_verdict_rubric_weak_uncertain_when_ci_straddles_zero():
    module = load_script_module()
    verdict = module.apply_verdict_rubric("elo_poisson", best_delta=-0.01, best_ci_lower=-0.02, best_ci_upper=0.005)
    assert verdict == "WEAK-UNCERTAIN SIGNAL"


def test_apply_verdict_rubric_weak_uncertain_when_point_estimate_tiny():
    module = load_script_module()
    verdict = module.apply_verdict_rubric("elo_poisson", best_delta=0.002, best_ci_lower=-0.01, best_ci_upper=0.01)
    assert verdict == "WEAK-UNCERTAIN SIGNAL"


def test_full_holdout_run_against_real_frozen_dataset():
    """The actual Checkpoint 6 run. Skipped when the real frozen dataset
    is not present in this checkout (e.g. CI without the untracked data
    files). When present, this really does open the sealed 2024/25
    season -- that is the point of this script and this test."""
    matches_path = REPO_ROOT / "data" / "processed" / "football" / "cycle_001_matches_full.csv"
    freeze_record_path = REPO_ROOT / "reports" / "audits" / "CYCLE_001_FREEZE_RECORD.json"
    protocol_freeze_path = REPO_ROOT / "reports" / "audits" / "STAGE_3B_PRE_HOLDOUT_FREEZE.json"
    if not matches_path.exists() or not freeze_record_path.exists() or not protocol_freeze_path.exists():
        pytest.skip("frozen dataset/freeze records not present in this checkout")

    module = load_script_module()
    exit_code = module.main()
    assert exit_code == 0

    metrics_path = REPO_ROOT / "data" / "interim" / "stage_3b_checkpoint6_holdout_metrics.json"
    with open(metrics_path) as f:
        summary = json.load(f)

    with open(protocol_freeze_path) as f:
        protocol_freeze_record = json.load(f)
    expected_n = protocol_freeze_record["predeclared_holdout_coverage"]["common_sample_n"]
    assert summary["common_sample_n"] == expected_n

    assert summary["verdict"] in (
        "STRONG SIGNAL", "WEAK-UNCERTAIN SIGNAL", "MARKET DOMINATES / NULL RESULT", "INVALID",
    )
    for name, per_metric in summary["bootstrap_results"].items():
        for key, result in per_metric.items():
            assert result["ci_lower"] <= result["ci_upper"], f"{name}.{key} has an inverted CI"
