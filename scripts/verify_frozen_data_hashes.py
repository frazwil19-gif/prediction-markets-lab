#!/usr/bin/env python3
"""Verify the local working-copy data files match the frozen Stage 3A
provenance record before any Stage 3B modelling reads them.

Per the Stage 3B directive: "read the freeze record programmatically.
Verify hashes before modelling. If hashes do not match: STOP. Do not
silently continue on modified data."

Usage:
    python scripts/verify_frozen_data_hashes.py
    python scripts/verify_frozen_data_hashes.py --freeze-record path/to/other_record.json
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FREEZE_RECORD = REPO_ROOT / "reports" / "audits" / "CYCLE_001_FREEZE_RECORD.json"


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_frozen_data_hashes(freeze_record: dict, repo_root: Path = REPO_ROOT) -> list[str]:
    """Check every hashed file in a freeze record against the working copy.

    Args:
        freeze_record: the parsed contents of a CYCLE_001_FREEZE_RECORD.json-style file.
        repo_root: repository root that raw/processed/config paths are relative to.

    Returns:
        A list of human-readable mismatch/missing-file messages. Empty
        list means every hashed file is present and matches exactly.
    """
    problems: list[str] = []

    for rel, expected in freeze_record.get("raw_source_hashes_sha256", {}).items():
        path = repo_root / "data" / "raw" / "football" / "football_data_co_uk" / rel
        if not path.exists():
            problems.append(f"MISSING raw source file: {path}")
            continue
        actual = sha256_of_file(path)
        if actual != expected:
            problems.append(f"HASH MISMATCH raw source file {path}: expected {expected}, got {actual}")

    processed_dir = repo_root / "data" / "processed" / "football"
    for name, expected in freeze_record.get("processed_artifact_hashes_sha256", {}).items():
        path = processed_dir / name
        if not path.exists():
            problems.append(f"MISSING processed artifact: {path}")
            continue
        actual = sha256_of_file(path)
        if actual != expected:
            problems.append(f"HASH MISMATCH processed artifact {path}: expected {expected}, got {actual}")

    for rel, expected in freeze_record.get("config_hashes_sha256", {}).items():
        path = repo_root / rel
        if not path.exists():
            problems.append(f"MISSING config file: {path}")
            continue
        actual = sha256_of_file(path)
        if actual != expected:
            problems.append(f"HASH MISMATCH config file {path}: expected {expected}, got {actual}")

    return problems


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-record", type=Path, default=DEFAULT_FREEZE_RECORD)
    args = parser.parse_args(argv)

    import json

    with open(args.freeze_record) as f:
        freeze_record = json.load(f)

    problems = verify_frozen_data_hashes(freeze_record, repo_root=REPO_ROOT)

    if problems:
        print(f"STOP -- {len(problems)} hash mismatch(es)/missing file(s) against "
              f"{args.freeze_record}:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"All hashes verified against {args.freeze_record} (data_version "
          f"{freeze_record.get('data_version', '?')}) -- safe to proceed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
