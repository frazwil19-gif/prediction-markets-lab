import csv
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_stage_3b_checkpoint3_poisson.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("run_stage_3b_checkpoint3_poisson", SCRIPT_PATH)
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


def test_build_goals_by_match_id_matches_real_frozen_dataset_match_ids():
    """Integration check against the real repo data: every development
    match_id produced by build_goals_by_match_id must line up exactly
    with the match_ids already in cycle_001_matches_full.csv -- if the
    match_id reconstruction here ever drifted from the acquisition
    script's own construction, this would catch it as a large 'missing'
    set rather than silently mis-joining goals to the wrong fixture."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from prediction_markets_lab.normalisation.team_names import load_alias_table

    matches_path = REPO_ROOT / "data" / "processed" / "football" / "cycle_001_matches_full.csv"
    if not matches_path.exists():
        import pytest
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
