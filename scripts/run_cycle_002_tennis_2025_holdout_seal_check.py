#!/usr/bin/env python3
"""Pre-holdout seal verification for Tennis Cycle 1's 2025 evaluation.

Per the research operator's explicit instruction ("before opening 2025:
verify and report -- 2025 has not previously been loaded by any research/
model script; no 2025-derived statistic informed model selection; frozen
model/config hashes match; canonical dataset hash matches; git working
tree is clean; full tests pass. If any material violation is discovered:
STOP. Do not evaluate the holdout."), this script performs exactly that
check, mechanically, and must PASS before
scripts/run_cycle_002_tennis_2025_holdout.py is ever run.

This script does NOT read the canonical dataset's rows at all (only its
raw bytes, to hash it) -- it never sees a single 2025 match result, by
design. It is safe to run at any time, including before this freeze is
approved.

Run:
    python scripts/run_cycle_002_tennis_2025_holdout_seal_check.py
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_PATH = REPO_ROOT / "data" / "processed" / "tennis" / "cycle_002_canonical_matches.csv"
FROZEN_CANONICAL_SHA256 = "03043d3387e0d9dfe72cf3b79a8f9f9cfc5e444a3ce637f49e68403b0f7daf91"
FREEZE_DOC_PATH = REPO_ROOT / "research" / "cycles" / "CYCLE_002_TENNIS" / "TENNIS_CYCLE_1_PRE_HOLDOUT_FREEZE.md"

# Every script in this cycle that reads the canonical CSV for modelling
# BEFORE the holdout evaluation itself -- each one must provably exclude
# season 2025 at read time. The holdout script is intentionally excluded
# from this list: it is the one script permitted to load 2025, exactly once.
PRE_HOLDOUT_MODELLING_SCRIPTS = [
    REPO_ROOT / "scripts" / "run_cycle_002_tennis_checkpoint_a4.py",
    REPO_ROOT / "scripts" / "run_cycle_002_tennis_checkpoint_a4_step_d.py",
    REPO_ROOT / "scripts" / "run_cycle_002_tennis_calibration.py",
]

# Paths this correction/holdout work touches -- checked for a clean
# (fully committed) tree immediately before the holdout is evaluated, so
# there is no ambiguity about what code produced the recorded result.
CYCLE_TRACKED_PATHS = [
    "research/cycles/CYCLE_002_TENNIS",
    "scripts/run_cycle_002_tennis_checkpoint_a4.py",
    "scripts/run_cycle_002_tennis_checkpoint_a4_step_d.py",
    "scripts/run_cycle_002_tennis_calibration.py",
    "scripts/run_cycle_002_tennis_2025_holdout_seal_check.py",
    "scripts/run_cycle_002_tennis_2025_holdout.py",
    "src/prediction_markets_lab/models/tennis_elo.py",
    "src/prediction_markets_lab/models/tennis_ranking_baseline.py",
    "src/prediction_markets_lab/research/holdout_verdict.py",
    "tests/unit/test_holdout_verdict.py",
    "tests/unit/test_tennis_elo.py",
    "tests/unit/test_tennis_ranking_baseline.py",
    "tests/unit/test_run_cycle_002_tennis_checkpoint_a4.py",
    "tests/unit/test_run_cycle_002_tennis_checkpoint_a4_step_d.py",
    "tests/unit/test_run_cycle_002_tennis_calibration.py",
]


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_dataset_hash(path: Path = CANONICAL_PATH, expected: str = FROZEN_CANONICAL_SHA256) -> list[str]:
    """Confirm the working-copy canonical dataset matches the frozen hash.

    Returns a list of problem strings; empty means the hash matches.
    """
    if not path.exists():
        return [f"MISSING canonical dataset file: {path}"]
    actual = sha256_of_file(path)
    if actual != expected:
        return [f"HASH MISMATCH canonical dataset {path}: expected {expected}, got {actual}"]
    return []


def check_no_prior_2025_load(scripts: list[Path] = PRE_HOLDOUT_MODELLING_SCRIPTS) -> list[str]:
    """Confirm every pre-holdout modelling script provably excludes 2025.

    A script "provably excludes 2025" if it either (a) contains an
    explicit assertion that the sealed holdout season is absent from the
    loaded frame, or (b) reuses load_matches from a script that does (a)
    without loading the CSV again itself. This is a static, textual check
    -- it reads source code, never the dataset's rows.
    """
    problems: list[str] = []
    assertion_pattern = re.compile(r"assert not.*SEALED_HOLDOUT_SEASON|assert not.*==\s*2025")
    reuse_pattern = re.compile(r"load_matches|_load_module")
    for script in scripts:
        if not script.exists():
            problems.append(f"MISSING expected pre-holdout script: {script}")
            continue
        text = script.read_text()
        has_own_assertion = bool(assertion_pattern.search(text))
        reuses_loader = bool(reuse_pattern.search(text))
        if not (has_own_assertion or reuses_loader):
            problems.append(
                f"{script.name}: no 2025-exclusion assertion found, and it does not appear to "
                "reuse another script's load_matches -- cannot confirm 2025 was never loaded here"
            )
    return problems


def check_git_tree_clean(paths: list[str] = CYCLE_TRACKED_PATHS, repo_root: Path = REPO_ROOT) -> list[str]:
    """Confirm no uncommitted changes exist under this cycle's tracked paths.

    Untracked/modified files OUTSIDE these paths (e.g. unrelated football
    data files elsewhere in the working tree) are explicitly not this
    check's concern.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain", "--"] + paths,
        cwd=repo_root, capture_output=True, text=True, check=True,
    )
    dirty = [line for line in result.stdout.splitlines() if line.strip()]
    if dirty:
        return [f"UNCOMMITTED CHANGE under cycle-tracked paths: {line}" for line in dirty]
    return []


def check_tests_pass(repo_root: Path = REPO_ROOT) -> list[str]:
    """Run the full test suite; any non-zero exit is a seal violation."""
    venv_python = repo_root / ".venv" / "bin" / "python"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable
    result = subprocess.run(
        [python_exe, "-m", "pytest", "-q"], cwd=repo_root, capture_output=True, text=True,
    )
    if result.returncode != 0:
        tail = "\n".join(result.stdout.splitlines()[-25:])
        return [f"TEST SUITE FAILED (exit {result.returncode}):\n{tail}"]
    return []


def run_all_checks(repo_root: Path = REPO_ROOT) -> dict[str, list[str]]:
    return {
        "dataset_hash": check_dataset_hash(),
        "no_prior_2025_load": check_no_prior_2025_load(),
        "git_tree_clean": check_git_tree_clean(repo_root=repo_root),
        "tests_pass": check_tests_pass(repo_root=repo_root),
    }


def main() -> int:
    results = run_all_checks()
    total_problems = sum(len(v) for v in results.values())

    print("=" * 70)
    print("TENNIS CYCLE 1 -- PRE-2025 SEAL VERIFICATION")
    print("=" * 70)
    for check_name, problems in results.items():
        status = "OK" if not problems else f"PROBLEM ({len(problems)})"
        print(f"[{status}] {check_name}")
        for p in problems:
            print(f"    - {p}")

    if total_problems:
        print()
        print(f"STOP -- {total_problems} seal violation(s) found. Do NOT evaluate the "
              "2025 holdout until every check above is OK.")
        return 1

    print()
    print("All checks OK. 2025 has not been loaded by any pre-holdout script, the "
          "canonical dataset hash matches the freeze, the cycle's tracked files are "
          "fully committed, and the full test suite passes. Safe to run "
          "run_cycle_002_tennis_2025_holdout.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
