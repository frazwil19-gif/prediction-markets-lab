#!/usr/bin/env python3
"""Verify the Stage 3B pre-holdout freeze record before Checkpoint 6 runs.

Mirrors scripts/verify_frozen_data_hashes.py's pattern for the raw/
processed data, but for research/cycles/CYCLE_001/results/FINAL_HOLDOUT_PROTOCOL.md
itself: the holdout protocol must not have changed since it was
pre-registered in reports/audits/STAGE_3B_PRE_HOLDOUT_FREEZE.json. Any
Checkpoint 6 script must call verify_pre_holdout_freeze() and refuse to
proceed on any mismatch, exactly as every Stage 3B script already does for
the underlying data via verify_frozen_data_hashes().
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def sha256_of_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_pre_holdout_freeze(freeze_record: dict, repo_root: Path = REPO_ROOT) -> list[str]:
    """Check the live protocol document's hash against the freeze record.

    Args:
        freeze_record: parsed contents of
            reports/audits/STAGE_3B_PRE_HOLDOUT_FREEZE.json.
        repo_root: repository root the protocol_document_path is relative to.

    Returns:
        A list of human-readable problem descriptions. Empty if the live
        protocol document's SHA-256 matches the frozen hash exactly.
    """
    problems: list[str] = []
    doc_path = repo_root / freeze_record["protocol_document_path"]
    if not doc_path.exists():
        problems.append(f"protocol document missing: {doc_path}")
        return problems

    actual_hash = sha256_of_file(doc_path)
    expected_hash = freeze_record["protocol_document_sha256"]
    if actual_hash != expected_hash:
        problems.append(
            f"protocol document hash mismatch for {doc_path}: "
            f"expected {expected_hash}, got {actual_hash} -- "
            "the holdout protocol has changed since pre-registration"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    freeze_record_path = REPO_ROOT / "reports" / "audits" / "STAGE_3B_PRE_HOLDOUT_FREEZE.json"
    with open(freeze_record_path) as f:
        freeze_record = json.load(f)
    problems = verify_pre_holdout_freeze(freeze_record, repo_root=REPO_ROOT)
    if problems:
        print("STOP -- pre-holdout freeze verification failed:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"Pre-holdout freeze verified OK ({freeze_record['freeze_name']}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
