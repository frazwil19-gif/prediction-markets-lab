import csv
import importlib.util
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_stage_3b_checkpoint2_elo.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("run_stage_3b_checkpoint2_elo", SCRIPT_PATH)
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


def test_to_elo_input_uses_normalised_team_names():
    module = load_script_module()
    row = {
        "match_id": "m1", "season": "2020_21", "match_date": "2020-08-01",
        "home_team_normalised": "Wolverhampton Wanderers", "away_team_normalised": "Manchester United",
        "full_time_result": "D",
    }
    elo_input = module.to_elo_input(row)
    assert elo_input.home_team == "Wolverhampton Wanderers"
    assert elo_input.away_team == "Manchester United"
    assert elo_input.match_date == date(2020, 8, 1)
    assert elo_input.full_time_result == "D"
