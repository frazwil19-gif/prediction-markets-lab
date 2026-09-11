#!/usr/bin/env python3
"""Validate a completed Cycle 2 (Tennis) raw-acquisition bundle.

Modelled on scripts/validate_cycle_001_data_bundle.py's role (a final
integrity gate run after acquisition, before any downstream script is
allowed to treat the bundle as trustworthy), adapted for two content
shapes (text CSV vs. binary xlsx) instead of one.

Checks:
  - the manifest exists and has the expected number of rows;
  - every file the manifest references exists on disk and its sha256
    matches the manifest;
  - no acquired CSV file is empty or looks like an HTML error page;
  - the data-version record exists and its `summary.files_failed` is 0.

Exits non-zero on any check failure.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main() -> int:
    config = load_config(REPO_ROOT / "config" / "cycle_002_tennis_data.yaml")
    manifest_path = REPO_ROOT / config["output_paths"]["manifest_path"]
    data_version_path = REPO_ROOT / config["output_paths"]["data_version_path"]
    output_root = REPO_ROOT / "data"

    failures: list[str] = []

    if not manifest_path.exists():
        print(f"FAIL: manifest not found at {manifest_path}")
        return 1

    with open(manifest_path, newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        failures.append("manifest has zero rows")

    for row in rows:
        file_path = output_root / "raw" / row["raw_relative_path"]
        if not file_path.exists():
            failures.append(f"missing file referenced by manifest: {file_path}")
            continue
        content = file_path.read_bytes()
        if len(content) == 0:
            failures.append(f"empty file: {file_path}")
            continue
        actual_digest = hashlib.sha256(content).hexdigest()
        if actual_digest != row["sha256"]:
            failures.append(
                f"hash mismatch for {file_path}: manifest={row['sha256']} actual={actual_digest}"
            )
        if row.get("content_mode") == "bytes":
            if content[:4] != b"PK\x03\x04":
                failures.append(f"expected a zip-based xlsx file but magic number is missing: {file_path}")
        else:
            if content.lstrip()[:1] == b"<":
                failures.append(f"file looks like an HTML error page, not CSV: {file_path}")

    if not data_version_path.exists():
        failures.append(f"data-version record not found at {data_version_path}")
    else:
        with open(data_version_path) as f:
            data_version = json.load(f)
        if data_version.get("summary", {}).get("files_failed", 1) != 0:
            failures.append(
                f"data-version record reports files_failed="
                f"{data_version.get('summary', {}).get('files_failed')} (expected 0)"
            )

    if failures:
        print(f"VALIDATION FAILED ({len(failures)} issue(s)):")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"OK: {len(rows)} manifest rows validated, all hashes match, no HTML error pages found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
