"""Tests for scripts/run_cycle_001_data_acquisition.py.

Per project instructions, no real network calls are made -- this
exercises config loading, target planning, and dry-run behaviour
directly by importing the script as a module. Full end-to-end download
behaviour is covered indirectly by ingestion.football_data_loader's own
mocked-HTTP tests.
"""

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_cycle_001_data_acquisition.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("run_cycle_001_data_acquisition", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script_module():
    return load_script_module()


def test_config_file_loads_and_has_required_keys(script_module):
    config = script_module.load_config(REPO_ROOT / "config" / "cycle_001_data.yaml")
    assert "source" in config
    assert "competitions" in config
    assert "seasons" in config
    assert config["expected_raw_file_count"] == 15


def test_plan_targets_full_matrix(script_module):
    config = script_module.load_config(REPO_ROOT / "config" / "cycle_001_data.yaml")
    targets = script_module.plan_targets(config, None, None)
    assert len(targets) == 15
    assert ("E0", "2024_25") in targets
    assert ("SC0", "2020_21") in targets


def test_plan_targets_competition_filter(script_module):
    config = script_module.load_config(REPO_ROOT / "config" / "cycle_001_data.yaml")
    targets = script_module.plan_targets(config, ["E0"], None)
    assert len(targets) == 5
    assert all(c == "E0" for c, s in targets)


def test_plan_targets_season_filter(script_module):
    config = script_module.load_config(REPO_ROOT / "config" / "cycle_001_data.yaml")
    targets = script_module.plan_targets(config, None, ["2024_25"])
    assert len(targets) == 3
    assert all(s == "2024_25" for c, s in targets)


def test_plan_targets_both_filters(script_module):
    config = script_module.load_config(REPO_ROOT / "config" / "cycle_001_data.yaml")
    targets = script_module.plan_targets(config, ["E1"], ["2022_23"])
    assert targets == [("E1", "2022_23")]


def test_dry_run_exits_zero_without_network(script_module):
    exit_code = script_module.run(["--dry-run"])
    assert exit_code == 0


def test_dry_run_with_filters_exits_zero(script_module, capsys):
    exit_code = script_module.run(["--dry-run", "--competition", "SC0", "--season", "2024_25"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "SC0 2024_25" in captured.out
    assert "Planned targets (1)" in captured.out


def test_run_summary_dataclass_defaults(script_module):
    summary = script_module.RunSummary()
    assert summary.files_attempted == 0
    assert summary.critical_failure is None


def test_acquisition_config_yaml_split_plan_chronological():
    """The provisional split plan in config must itself be chronologically
    sane (training seasons before validation before test), even though
    it is not yet backed by real acquired row counts."""
    with open(REPO_ROOT / "config" / "cycle_001_data.yaml") as f:
        config = yaml.safe_load(f)
    split = config["split_plan"]
    assert split["final_test_season"] == "2024_25"
    assert split["final_test_season"] not in split["training_seasons"]
    assert split["final_test_season"] not in split["validation_seasons"]
