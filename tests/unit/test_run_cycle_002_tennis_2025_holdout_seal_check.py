import hashlib
import subprocess
from pathlib import Path

import importlib.util

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_cycle_002_tennis_2025_holdout_seal_check.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("run_cycle_002_tennis_2025_holdout_seal_check", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_dataset_hash_matches(tmp_path):
    module = load_script_module()
    f = tmp_path / "data.csv"
    f.write_text("match_id,outcome\n1,1\n")
    expected = hashlib.sha256(f.read_bytes()).hexdigest()
    assert module.check_dataset_hash(path=f, expected=expected) == []


def test_check_dataset_hash_mismatch(tmp_path):
    module = load_script_module()
    f = tmp_path / "data.csv"
    f.write_text("match_id,outcome\n1,1\n")
    problems = module.check_dataset_hash(path=f, expected="0" * 64)
    assert len(problems) == 1
    assert "HASH MISMATCH" in problems[0]


def test_check_dataset_hash_missing_file(tmp_path):
    module = load_script_module()
    problems = module.check_dataset_hash(path=tmp_path / "does_not_exist.csv", expected="0" * 64)
    assert len(problems) == 1
    assert "MISSING" in problems[0]


def test_check_no_prior_2025_load_accepts_own_assertion(tmp_path):
    module = load_script_module()
    f = tmp_path / "some_script.py"
    f.write_text('SEALED_HOLDOUT_SEASON = 2025\nassert not (df["_season"] == SEALED_HOLDOUT_SEASON).any()\n')
    assert module.check_no_prior_2025_load(scripts=[f]) == []


def test_check_no_prior_2025_load_accepts_reused_loader(tmp_path):
    module = load_script_module()
    f = tmp_path / "some_other_script.py"
    f.write_text("from run_cycle_002_tennis_checkpoint_a4 import load_matches\n")
    assert module.check_no_prior_2025_load(scripts=[f]) == []


def test_check_no_prior_2025_load_flags_unverifiable_script(tmp_path):
    module = load_script_module()
    f = tmp_path / "suspicious_script.py"
    f.write_text("df = pd.read_csv('whatever.csv')\n")
    problems = module.check_no_prior_2025_load(scripts=[f])
    assert len(problems) == 1
    assert "suspicious_script.py" in problems[0]


def test_check_no_prior_2025_load_flags_missing_script(tmp_path):
    module = load_script_module()
    problems = module.check_no_prior_2025_load(scripts=[tmp_path / "nonexistent.py"])
    assert len(problems) == 1
    assert "MISSING" in problems[0]


def _init_tmp_git_repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    return tmp_path


def test_check_git_tree_clean_when_committed(tmp_path):
    module = load_script_module()
    repo = _init_tmp_git_repo(tmp_path)
    tracked_dir = repo / "research"
    tracked_dir.mkdir()
    (tracked_dir / "note.md").write_text("committed content\n")
    subprocess.run(["git", "add", "research"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    assert module.check_git_tree_clean(paths=["research"], repo_root=repo) == []


def test_check_git_tree_clean_flags_uncommitted_change(tmp_path):
    module = load_script_module()
    repo = _init_tmp_git_repo(tmp_path)
    tracked_dir = repo / "research"
    tracked_dir.mkdir()
    (tracked_dir / "note.md").write_text("committed content\n")
    subprocess.run(["git", "add", "research"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    (tracked_dir / "note.md").write_text("uncommitted edit\n")
    problems = module.check_git_tree_clean(paths=["research"], repo_root=repo)
    assert len(problems) == 1
    assert "UNCOMMITTED" in problems[0]


def test_check_git_tree_clean_ignores_paths_outside_the_given_list(tmp_path):
    module = load_script_module()
    repo = _init_tmp_git_repo(tmp_path)
    tracked_dir = repo / "research"
    tracked_dir.mkdir()
    (tracked_dir / "note.md").write_text("committed content\n")
    subprocess.run(["git", "add", "research"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    # An untracked file OUTSIDE the checked paths must not trip the check.
    (repo / "unrelated.csv").write_text("unrelated\n")
    assert module.check_git_tree_clean(paths=["research"], repo_root=repo) == []
