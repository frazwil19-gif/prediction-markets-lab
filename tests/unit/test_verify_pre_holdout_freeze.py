import hashlib
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "verify_pre_holdout_freeze.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("verify_pre_holdout_freeze", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verify_passes_for_an_unmodified_document(tmp_path):
    module = load_script_module()
    doc_path = tmp_path / "protocol.md"
    doc_path.write_text("frozen protocol content\n")
    freeze_record = {
        "protocol_document_path": "protocol.md",
        "protocol_document_sha256": hashlib.sha256(doc_path.read_bytes()).hexdigest(),
    }
    problems = module.verify_pre_holdout_freeze(freeze_record, repo_root=tmp_path)
    assert problems == []


def test_verify_fails_when_document_has_changed(tmp_path):
    module = load_script_module()
    doc_path = tmp_path / "protocol.md"
    doc_path.write_text("original content\n")
    original_hash = hashlib.sha256(doc_path.read_bytes()).hexdigest()
    doc_path.write_text("someone edited the frozen protocol after the fact\n")

    freeze_record = {
        "protocol_document_path": "protocol.md",
        "protocol_document_sha256": original_hash,
    }
    problems = module.verify_pre_holdout_freeze(freeze_record, repo_root=tmp_path)
    assert len(problems) == 1
    assert "hash mismatch" in problems[0]


def test_verify_fails_when_document_missing(tmp_path):
    module = load_script_module()
    freeze_record = {
        "protocol_document_path": "does_not_exist.md",
        "protocol_document_sha256": "irrelevant",
    }
    problems = module.verify_pre_holdout_freeze(freeze_record, repo_root=tmp_path)
    assert len(problems) == 1
    assert "missing" in problems[0]


def test_real_committed_freeze_record_verifies_against_the_real_repo():
    """Integration check: the actual committed FINAL_HOLDOUT_PROTOCOL.md
    must match the hash recorded in the actual committed
    STAGE_3B_PRE_HOLDOUT_FREEZE.json -- this is the same check Checkpoint 6
    itself will run before opening the holdout."""
    module = load_script_module()
    freeze_record_path = REPO_ROOT / "reports" / "audits" / "STAGE_3B_PRE_HOLDOUT_FREEZE.json"
    with open(freeze_record_path) as f:
        freeze_record = json.load(f)
    problems = module.verify_pre_holdout_freeze(freeze_record, repo_root=REPO_ROOT)
    assert problems == []


def test_main_exits_zero_against_the_real_repo():
    module = load_script_module()
    assert module.main() == 0
