import hashlib
import json

import pytest

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "verify_frozen_data_hashes.py"


@pytest.fixture(scope="module")
def script_module():
    spec = spec_from_file_location("verify_frozen_data_hashes", SCRIPT_PATH)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def test_verify_frozen_data_hashes_passes_when_everything_matches(tmp_path, script_module):
    (tmp_path / "data" / "raw" / "football" / "football_data_co_uk" / "E0" / "2020_21").mkdir(parents=True)
    raw_path = tmp_path / "data" / "raw" / "football" / "football_data_co_uk" / "E0" / "2020_21" / "E0.csv"
    raw_path.write_text("Div,Date\nE0,01/08/2020\n")

    (tmp_path / "data" / "processed" / "football").mkdir(parents=True)
    proc_path = tmp_path / "data" / "processed" / "football" / "cycle_001_matches_full.csv"
    proc_path.write_text("match_id\nabc123\n")

    (tmp_path / "config").mkdir(parents=True)
    config_path = tmp_path / "config" / "football_team_aliases.yaml"
    config_path.write_text("Arsenal: [Arsenal]\n")

    freeze_record = {
        "raw_source_hashes_sha256": {"E0/2020_21/E0.csv": _sha256(raw_path.read_text())},
        "processed_artifact_hashes_sha256": {"cycle_001_matches_full.csv": _sha256(proc_path.read_text())},
        "config_hashes_sha256": {"config/football_team_aliases.yaml": _sha256(config_path.read_text())},
    }

    problems = script_module.verify_frozen_data_hashes(freeze_record, repo_root=tmp_path)
    assert problems == []


def test_verify_frozen_data_hashes_detects_a_modified_file(tmp_path, script_module):
    (tmp_path / "data" / "processed" / "football").mkdir(parents=True)
    proc_path = tmp_path / "data" / "processed" / "football" / "cycle_001_matches_full.csv"
    proc_path.write_text("match_id\nabc123\n")

    freeze_record = {
        "processed_artifact_hashes_sha256": {
            "cycle_001_matches_full.csv": _sha256("match_id\nDIFFERENT_CONTENT\n")
        },
    }

    problems = script_module.verify_frozen_data_hashes(freeze_record, repo_root=tmp_path)
    assert len(problems) == 1
    assert "HASH MISMATCH" in problems[0]


def test_verify_frozen_data_hashes_detects_a_missing_file(tmp_path, script_module):
    freeze_record = {
        "raw_source_hashes_sha256": {"E0/2020_21/E0.csv": "deadbeef"},
    }
    problems = script_module.verify_frozen_data_hashes(freeze_record, repo_root=tmp_path)
    assert len(problems) == 1
    assert "MISSING" in problems[0]


def test_verify_frozen_data_hashes_against_the_real_committed_freeze_record(script_module):
    """Integration check: run the real verifier against this repo's own
    committed freeze record and the real data files placed locally for
    Stage 3B development. If this fails, something about the local
    working copy has drifted from the frozen dataset -- see
    reports/audits/CYCLE_001_FREEZE_RECORD.json.

    Skipped when the real frozen dataset is not present in this checkout
    (e.g. a fresh clone or CI runner without the untracked data files) --
    same sentinel file and convention as
    test_stage_3b_checkpoint3_poisson.py / test_stage_3b_checkpoint4_blends.py.
    The freeze record JSON itself IS committed (it lives under
    reports/audits/), unlike the raw/processed football data it describes
    (deliberately not committed, see research/cycles/CYCLE_001/DECISION_LOG.md),
    so checking only for the freeze record's presence is not sufficient --
    it will always exist in a fresh checkout while the data it verifies
    will not."""
    matches_path = REPO_ROOT / "data" / "processed" / "football" / "cycle_001_matches_full.csv"
    freeze_record_path = REPO_ROOT / "reports" / "audits" / "CYCLE_001_FREEZE_RECORD.json"
    if not matches_path.exists() or not freeze_record_path.exists():
        pytest.skip("frozen dataset/freeze record not present in this checkout")
    with open(freeze_record_path) as f:
        freeze_record = json.load(f)
    problems = script_module.verify_frozen_data_hashes(freeze_record, repo_root=REPO_ROOT)
    assert problems == [], problems
