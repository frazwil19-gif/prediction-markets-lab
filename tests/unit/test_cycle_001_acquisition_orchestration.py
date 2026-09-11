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


def test_resume_skips_network_when_file_already_present(script_module, tmp_path, monkeypatch):
    """--resume must skip re-downloading a file that already exists on
    disk, and must not require any network call to do so."""
    raw_dir = tmp_path / "raw" / "football" / "football_data_co_uk" / "E0" / "2024_25"
    raw_dir.mkdir(parents=True)
    (raw_dir / "E0.csv").write_text("Div,Date,HomeTeam,AwayTeam,FTR\nE0,16/08/2024,A,B,H\n")

    def _should_not_be_called(*args, **kwargs):
        raise AssertionError("fetch_one must not be called when --resume finds an existing file")

    monkeypatch.setattr(script_module, "fetch_one", _should_not_be_called)

    exit_code = script_module.run([
        "--resume", "--competition", "E0", "--season", "2024_25",
        "--output-root", str(tmp_path), "--reports-root", str(tmp_path / "reports"),
    ])
    assert exit_code == 0


def test_expected_file_count_gate_uses_planned_targets_not_global_total(script_module, tmp_path, monkeypatch):
    """A filtered, single-file run must gate on its OWN planned target
    count (1), not the global 15-file expectation -- otherwise every
    filtered/partial run would spuriously fail this gate."""
    raw_dir = tmp_path / "raw" / "football" / "football_data_co_uk" / "E0" / "2024_25"
    raw_dir.mkdir(parents=True)
    (raw_dir / "E0.csv").write_text("Div,Date,HomeTeam,AwayTeam,FTR\nE0,16/08/2024,A,B,H\n")

    exit_code = script_module.run([
        "--resume", "--competition", "E0", "--season", "2024_25",
        "--output-root", str(tmp_path), "--reports-root", str(tmp_path / "reports"),
    ])
    assert exit_code == 0  # 1 of 1 planned targets satisfied via resume


def test_expected_file_count_gate_fails_when_targets_missing(script_module, tmp_path, monkeypatch):
    """If a planned target has neither an existing file nor a successful
    fetch, the run must exit non-zero. The HTTP layer is mocked so this
    test never makes a real network call."""
    import urllib.error

    class FailingClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, url):
            raise urllib.error.URLError("mocked network failure -- no live calls in tests")

    monkeypatch.setattr(script_module, "HttpClient", FailingClient)

    exit_code = script_module.run([
        "--competition", "E0", "--season", "2024_25",
        "--request-delay-seconds", "0", "--max-retries", "0",
        "--output-root", str(tmp_path), "--reports-root", str(tmp_path / "reports"),
    ])
    assert exit_code == 1


def test_workflow_is_workflow_dispatch_only():
    """The GitHub Actions workflow must never run on push or a schedule
    -- only a manual trigger, per the architecture-freeze justification
    (a bounded, manually-triggered research job, not continuous CI)."""
    workflow_path = REPO_ROOT / ".github" / "workflows" / "cycle_001_data_acquisition.yml"
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)
    triggers = workflow.get(True, workflow.get("on"))
    assert list(triggers.keys()) == ["workflow_dispatch"]


def test_workflow_requires_no_secrets():
    workflow_path = REPO_ROOT / ".github" / "workflows" / "cycle_001_data_acquisition.yml"
    content = workflow_path.read_text()
    assert "secrets." not in content


def test_workflow_does_not_reference_any_paid_api_or_betting_execution():
    workflow_path = REPO_ROOT / ".github" / "workflows" / "cycle_001_data_acquisition.yml"
    content = workflow_path.read_text().lower()
    for forbidden in ("smarkets", "betfair api", "place_bet", "execute_trade", "paid_api"):
        assert forbidden not in content


def test_no_betting_execution_code_exists_in_models_directory():
    """Superseded 2026-09-11 (Stage 3B accepted -- see
    research/cycles/CYCLE_001/STAGE_3B_PLAN.md and
    reports/audits/CURRENT_STATE_AUDIT.md Update 4): this test used to
    require football_elo.py/football_poisson.py to remain unimplemented
    PLACEHOLDER files during Stage 3A. Stage 3A is now frozen (GO) and
    Stage 3B (probability-model validation, explicitly authorised by
    the project directive) is underway, so real Elo/Poisson model code
    is expected and correct in this directory now.

    What remains genuinely out of scope at every stage until a much
    later, explicitly-authorised one (per project instructions and the
    Stage 3B directive section 26/27: no staking, no EV thresholds, no
    live execution yet) is any actual bet-placement/execution code --
    that invariant is what this test now checks, rather than the
    now-obsolete "no model code at all" rule."""
    models_dir = REPO_ROOT / "src" / "prediction_markets_lab" / "models"
    forbidden = ("place_bet", "execute_trade", "smarkets", "betfair api", "paid_api")
    for path in sorted(models_dir.glob("*.py")):
        content_lower = path.read_text().lower()
        for term in forbidden:
            assert term not in content_lower, f"{path} must not contain live-execution code ({term!r} found)"


def test_default_raw_output_path_matches_workflow_upload_glob(script_module):
    """Regression test for the Cycle 1 raw-files provenance bug: the
    acquisition script's default raw-file destination must live under
    the same 'data/raw/football/...' tree that the GitHub Actions
    workflow's 'Upload raw source files' step globs, and under the
    'data/raw/' tree that is git-ignored for genuine downloads (see
    research/cycles/CYCLE_001/DECISION_LOG.md). Previously the script
    wrote real downloads to data/football/football_data_co_uk/... (no
    'raw' segment), so the workflow's data/raw/football/** glob only
    ever picked up the pre-existing EXCERPT_VALIDATION_ONLY stub files
    and never the genuine downloaded season files."""
    args = script_module.parse_args(["--dry-run"])
    raw_root = args.output_root / "raw" / "football" / "football_data_co_uk"
    assert str(raw_root).endswith("data/raw/football/football_data_co_uk")

    workflow_path = REPO_ROOT / ".github" / "workflows" / "cycle_001_data_acquisition.yml"
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)
    upload_steps = [
        step for step in workflow["jobs"]["acquire"]["steps"]
        if step.get("name") == "Upload raw source files"
    ]
    assert len(upload_steps) == 1
    glob_path = upload_steps[0]["with"]["path"]
    assert glob_path == "data/raw/football/**"
