"""Tests for scripts/validate_cycle_001_data_bundle.py."""

import csv
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_cycle_001_data_bundle.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("validate_cycle_001_data_bundle", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def minimal_config():
    return {
        "expected_raw_file_count": 1,
        "competitions": [{"code": "E0", "name": "Premier League"}],
        "seasons": ["2024_25"],
        "split_plan": {
            "training_seasons": ["2020_21"],
            "validation_seasons": ["2023_24"],
            "final_test_season": "2024_25",
        },
    }


def write_manifest(reports_root: Path, rows):
    reports_root.mkdir(parents=True, exist_ok=True)
    with open(reports_root / "football_data_manifest.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_missing_manifest_is_invalid(tmp_path: Path):
    module = load_script_module()
    result, critical, warnings = module.validate(minimal_config(), tmp_path, tmp_path / "reports")
    assert result == "INVALID"
    assert any("manifest not found" in c for c in critical)


def test_missing_raw_file_is_invalid(tmp_path: Path):
    module = load_script_module()
    reports_root = tmp_path / "reports"
    write_manifest(reports_root, [{
        "competition_code": "E0", "season": "2024_25", "local_path": "does/not/exist.csv",
    }])
    result, critical, warnings = module.validate(minimal_config(), tmp_path, reports_root)
    assert result == "INVALID"
    assert any("raw file missing" in c for c in critical)


def test_html_error_page_detected_as_invalid(tmp_path: Path):
    module = load_script_module()
    reports_root = tmp_path / "reports"
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True)
    html_path = raw_dir / "E0.csv"
    html_path.write_text("<!DOCTYPE html><html><body>429 error</body></html>")
    write_manifest(reports_root, [{
        "competition_code": "E0", "season": "2024_25", "local_path": str(html_path),
    }])
    result, critical, warnings = module.validate(minimal_config(), tmp_path, reports_root)
    assert result == "INVALID"
    assert any("HTML error page" in c for c in critical)


def test_missing_competition_season_pair_is_invalid(tmp_path: Path):
    module = load_script_module()
    reports_root = tmp_path / "reports"
    config = minimal_config()
    config["expected_raw_file_count"] = 2
    config["seasons"] = ["2023_24", "2024_25"]
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True)
    csv_path = raw_dir / "E0.csv"
    csv_path.write_text("Div,Date\nE0,01/01/2024\n")
    write_manifest(reports_root, [{
        "competition_code": "E0", "season": "2024_25", "local_path": str(csv_path),
    }])
    result, critical, warnings = module.validate(config, tmp_path, reports_root)
    assert result == "INVALID"
    assert any("missing competition/season pairs" in c for c in critical)


def test_leakage_in_split_plan_detected(tmp_path: Path):
    module = load_script_module()
    reports_root = tmp_path / "reports"
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True)
    csv_path = raw_dir / "E0.csv"
    csv_path.write_text("Div,Date\nE0,01/01/2024\n")
    write_manifest(reports_root, [{
        "competition_code": "E0", "season": "2024_25", "local_path": str(csv_path),
    }])

    version_dir = tmp_path / "processed" / "football"
    version_dir.mkdir(parents=True)
    (version_dir / "cycle_001_data_version.json").write_text(json.dumps({"total_matches": 1, "files_failed": 0}))
    (version_dir / "cycle_001_matches_full.csv").write_text("match_id,normalisation_status\nabc123,resolved\n")

    bad_config = minimal_config()
    bad_config["split_plan"]["final_test_season"] = "2020_21"  # collides with training

    result, critical, warnings = module.validate(bad_config, tmp_path, reports_root)
    assert result == "INVALID"
    assert any("leakage risk" in c for c in critical)


def test_fully_valid_bundle_returns_valid(tmp_path: Path):
    module = load_script_module()
    reports_root = tmp_path / "reports"
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True)
    csv_path = raw_dir / "E0.csv"
    csv_path.write_text("Div,Date\nE0,01/01/2024\n")
    write_manifest(reports_root, [{
        "competition_code": "E0", "season": "2024_25", "local_path": str(csv_path),
    }])

    version_dir = tmp_path / "processed" / "football"
    version_dir.mkdir(parents=True)
    (version_dir / "cycle_001_data_version.json").write_text(json.dumps({"total_matches": 10, "files_failed": 0}))
    (version_dir / "cycle_001_matches_full.csv").write_text(
        "match_id,normalisation_status\nabc123,resolved\ndef456,resolved\n"
    )
    (version_dir / "cycle_001_consensus_full.csv").write_text(
        "match_id,probability_sum_check\nabc123,0.998\ndef456,1.002\n"
    )

    result, critical, warnings = module.validate(minimal_config(), tmp_path, reports_root)
    assert result == "VALID"
    assert critical == []
    assert warnings == []


def test_write_report_produces_expected_file(tmp_path: Path):
    module = load_script_module()
    module.write_report("VALID", [], [], tmp_path)
    report = (tmp_path / "CYCLE_001_DATA_BUNDLE_VALIDATION.md").read_text()
    assert "**Result: VALID**" in report
    assert "_None._" in report
