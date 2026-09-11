import csv
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_stage_3b_checkpoint1_baselines.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("run_stage_3b_checkpoint1_baselines", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_matches_csv(path, rows):
    fieldnames = ["match_id", "season", "competition_code", "match_date", "full_time_result", "eligible_consensus_model"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_load_matches_seals_out_the_holdout_season(tmp_path):
    module = load_script_module()
    csv_path = tmp_path / "matches.csv"
    _write_matches_csv(csv_path, [
        {"match_id": "m1", "season": "2020_21", "competition_code": "E0", "match_date": "2020-08-01", "full_time_result": "H", "eligible_consensus_model": "True"},
        {"match_id": "m2", "season": "2024_25", "competition_code": "E0", "match_date": "2024-08-01", "full_time_result": "H", "eligible_consensus_model": "True"},
    ])
    rows = module.load_matches(csv_path)
    assert [r["match_id"] for r in rows] == ["m1"]
    assert all(r["season"] != "2024_25" for r in rows)


def test_load_matches_keeps_all_development_seasons(tmp_path):
    module = load_script_module()
    csv_path = tmp_path / "matches.csv"
    _write_matches_csv(csv_path, [
        {"match_id": f"m{i}", "season": season, "competition_code": "E0", "match_date": "2020-08-01", "full_time_result": "H", "eligible_consensus_model": "True"}
        for i, season in enumerate(module.DEVELOPMENT_SEASONS)
    ])
    rows = module.load_matches(csv_path)
    assert len(rows) == len(module.DEVELOPMENT_SEASONS)


def test_load_closing_consensus_excludes_opening_rows(tmp_path):
    module = load_script_module()
    csv_path = tmp_path / "consensus.csv"
    fieldnames = ["match_id", "price_timing", "median_fair_home_probability", "median_fair_draw_probability", "median_fair_away_probability"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({"match_id": "m1", "price_timing": "opening", "median_fair_home_probability": "0.5", "median_fair_draw_probability": "0.3", "median_fair_away_probability": "0.2"})
        writer.writerow({"match_id": "m1", "price_timing": "closing", "median_fair_home_probability": "0.4", "median_fair_draw_probability": "0.35", "median_fair_away_probability": "0.25"})
    result = module.load_closing_consensus(csv_path)
    assert list(result.keys()) == ["m1"]
    assert result["m1"]["price_timing"] == "closing"
