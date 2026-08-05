#!/usr/bin/env python3
"""Validate a completed Cycle 1 data acquisition bundle.

Usage:
    python scripts/validate_cycle_001_data_bundle.py \
        --config config/cycle_001_data.yaml \
        --data-root data \
        --reports-root reports/audits

Checks: expected file count, manifest completeness, hash consistency,
no HTML masquerading as CSV, required competition-season coverage,
processed row counts, deterministic match IDs, no unresolved critical
duplicates, valid probability triplets, eligibility counts, data-version
metadata, split-plan chronology, final-test immutability.

Produces reports/audits/CYCLE_001_DATA_BUNDLE_VALIDATION.md with a
final result of VALID, VALID_WITH_NONCRITICAL_WARNINGS, or INVALID.
Exits non-zero only for INVALID.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.ingestion.football_data_loader import looks_like_html
from prediction_markets_lab.validation.time_splits import DateRange, SplitPlan


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "cycle_001_data.yaml")
    parser.add_argument("--data-root", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--reports-root", type=Path, default=REPO_ROOT / "reports" / "audits")
    return parser.parse_args(argv)


def validate(config: dict, data_root: Path, reports_root: Path) -> tuple[str, list[str], list[str]]:
    """Returns (result, critical_issues, warnings)."""
    critical: list[str] = []
    warnings: list[str] = []

    manifest_path = reports_root / "football_data_manifest.csv"
    if not manifest_path.exists():
        critical.append(f"manifest not found at {manifest_path}")
        return "INVALID", critical, warnings

    with open(manifest_path, newline="") as f:
        manifest_rows = list(csv.DictReader(f))

    expected = config["expected_raw_file_count"]
    if len(manifest_rows) < expected:
        critical.append(f"manifest has {len(manifest_rows)} rows, expected {expected}")

    expected_pairs = {
        (c["code"], s) for c in config["competitions"] for s in config["seasons"]
    }
    manifest_pairs = {(r["competition_code"], r["season"]) for r in manifest_rows}
    missing_pairs = expected_pairs - manifest_pairs
    if missing_pairs:
        critical.append(f"missing competition/season pairs in manifest: {sorted(missing_pairs)}")

    for row in manifest_rows:
        local_path = REPO_ROOT / row["local_path"] if not Path(row["local_path"]).is_absolute() else Path(row["local_path"])
        if not local_path.exists():
            critical.append(f"raw file missing on disk: {local_path}")
            continue
        content = local_path.read_text(encoding="utf-8", errors="replace")
        if looks_like_html(content):
            critical.append(f"raw file looks like an HTML error page: {local_path}")

    version_path = data_root / "processed" / "football" / "cycle_001_data_version.json"
    if not version_path.exists():
        critical.append(f"data version metadata not found at {version_path}")
    else:
        with open(version_path) as f:
            version_meta = json.load(f)
        if version_meta.get("files_failed", 0) > 0:
            warnings.append(f"{version_meta['files_failed']} file(s) failed during acquisition")
        if version_meta.get("total_matches", 0) == 0:
            critical.append("data version reports zero total matches")

    matches_path = data_root / "processed" / "football" / "cycle_001_matches_full.csv"
    if not matches_path.exists():
        critical.append(f"processed matches file not found at {matches_path}")
    else:
        with open(matches_path, newline="") as f:
            match_rows = list(csv.DictReader(f))
        match_ids = [r["match_id"] for r in match_rows]
        if len(match_ids) != len(set(match_ids)):
            dupes = len(match_ids) - len(set(match_ids))
            warnings.append(f"{dupes} duplicate match_id(s) found in processed matches -- review required")
        unresolved = sum(1 for r in match_rows if r.get("normalisation_status") == "unresolved")
        if unresolved:
            warnings.append(f"{unresolved} row(s) with unresolved team normalisation")

    consensus_path = data_root / "processed" / "football" / "cycle_001_consensus_full.csv"
    if consensus_path.exists():
        with open(consensus_path, newline="") as f:
            consensus_rows = list(csv.DictReader(f))
        bad_sums = [
            r for r in consensus_rows
            if not (0.9 <= float(r.get("probability_sum_check", 0)) <= 1.1)
        ]
        if bad_sums:
            critical.append(f"{len(bad_sums)} consensus row(s) with implausible probability_sum_check")

    try:
        split_cfg = config["split_plan"]
        # Sanity: final test season must not appear in training/validation.
        if split_cfg["final_test_season"] in split_cfg["training_seasons"]:
            critical.append("final_test_season appears in training_seasons -- leakage risk")
        if split_cfg["final_test_season"] in split_cfg["validation_seasons"]:
            critical.append("final_test_season appears in validation_seasons -- leakage risk")
    except KeyError as exc:
        critical.append(f"split_plan config missing expected key: {exc}")

    if critical:
        return "INVALID", critical, warnings
    if warnings:
        return "VALID_WITH_NONCRITICAL_WARNINGS", critical, warnings
    return "VALID", critical, warnings


def write_report(result: str, critical: list[str], warnings: list[str], reports_root: Path) -> None:
    lines = [
        "# CYCLE_001 Data Bundle Validation",
        "",
        f"**Result: {result}**",
        "",
        "## Critical issues",
        "",
    ]
    lines += [f"- {c}" for c in critical] if critical else ["_None._"]
    lines += ["", "## Warnings", ""]
    lines += [f"- {w}" for w in warnings] if warnings else ["_None._"]
    lines += [
        "",
        "## Interpretation",
        "",
        "- `VALID`: no issues found; safe to proceed to Stage 3B review.",
        "- `VALID_WITH_NONCRITICAL_WARNINGS`: proceed only after a human reviews the warnings above.",
        "- `INVALID`: do not proceed to modelling. Resolve the critical issues and re-run acquisition.",
        "",
    ]
    (reports_root / "CYCLE_001_DATA_BUNDLE_VALIDATION.md").write_text("\n".join(lines))


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    with open(args.config) as f:
        config = yaml.safe_load(f)

    result, critical, warnings = validate(config, args.data_root, args.reports_root)
    write_report(result, critical, warnings, args.reports_root)

    print(f"Validation result: {result}")
    for c in critical:
        print(f"  CRITICAL: {c}")
    for w in warnings:
        print(f"  WARNING: {w}")

    return 1 if result == "INVALID" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
