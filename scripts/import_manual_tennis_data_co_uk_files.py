#!/usr/bin/env python3
"""Manual-download fallback importer for Tennis-data.co.uk odds files.

Why this exists: Tennis-data.co.uk has repeatedly failed TLS handshakes
from every automated environment tried so far (a GitHub Actions runner,
this project's own web-fetch tooling, and a plain browser-style check),
with `[SSL: TLSV1_ALERT_INTERNAL_ERROR]` and inconsistent 503s. Per
explicit instruction: allow one final sensible automated compatibility
attempt (see tennis_data_loader.build_legacy_tolerant_ssl_context), and
if that still fails, stop engineering around it rather than burning
further sessions on TLS tweaks, and design the simplest safe fallback
instead -- a human downloads the handful of files a real browser can
get in seconds, and this script ingests them with the same provenance
guarantees (hashing, idempotent atomic writes, no silent overwrites) an
automated fetch would have provided.

Usage (after manually downloading the ATP .xlsx files from
tennis-data.co.uk in a real browser -- the site itself is not blocking
browsers, only automated clients so far):

    python scripts/import_manual_tennis_data_co_uk_files.py \
        --source-dir ~/Downloads/tennis_data_co_uk \
        --config config/cycle_002_tennis_data.yaml \
        --output-root data

Expects one file per configured season, named exactly as
tennis-data.co.uk itself names them when downloaded in a browser
(`{season}.xlsx`, e.g. `2023.xlsx`) -- the same convention
config/cycle_002_tennis_data.yaml's `men_path_template` already
encodes, so no separate renaming step should be needed after a plain
"Save As" from the site.

This script does NOT run the acquisition pipeline itself. It only
places validated files at the exact raw path
scripts/run_cycle_002_tennis_data_acquisition.py's plan_targets()
expects, so that a subsequent `--resume` run of that script picks them
up, records them in the manifest with `acquisition_method =
resumed_existing_file` (the honest label -- this run didn't fetch the
bytes, it found and recorded them), and folds them into the same
schema-inventory / data-version / validation machinery an automated
fetch would have gone through. Nothing downstream needs to know or
care that these particular bytes arrived via a human and a browser
instead of urllib.

Validation performed before any file is accepted (mirrors
tennis_data_loader.fetch_one_bytes's own checks, since a manually
downloaded file deserves exactly the same scrutiny an automated fetch
would have gotten, not less):
  - the file exists and is non-empty;
  - it starts with the real xlsx ZIP magic number (rejects an HTML
    error page saved with a misleading .xlsx extension, or a
    half-finished/corrupted download);
  - if a file already exists at the destination with DIFFERENT
    content, the write is refused rather than silently overwritten
    (write_raw_file_atomic_bytes's existing idempotency guarantee).

Exits non-zero if any configured season's file is missing or invalid,
mirroring this project's "loud failure, no silent gaps" philosophy for
raw acquisition.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.ingestion.tennis_data_loader import (
    XLSX_ZIP_MAGIC,
    compute_sha256_bytes,
    looks_like_html_bytes,
    write_raw_file_atomic_bytes,
)


def load_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-dir", type=Path, required=True, help="Directory containing manually downloaded .xlsx files")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "cycle_002_tennis_data.yaml")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--tour", action="append", choices=["ATP", "WTA"], help="Restrict to specific tour(s)")
    parser.add_argument("--season", action="append", help="Restrict to specific season(s), e.g. 2024")
    parser.add_argument(
        "--force-redownload",
        action="store_true",
        help="Overwrite an existing raw file even if its hash differs from the source-dir file",
    )
    return parser.parse_args(argv)


def validate_xlsx_bytes(content: bytes, filename: str) -> str | None:
    """Return an error message if `content` is not acceptable as a real
    xlsx payload, or None if it passes. Mirrors
    tennis_data_loader.fetch_one_bytes's own checks."""
    if not content:
        return f"{filename} is empty"
    if content[:4] != XLSX_ZIP_MAGIC:
        if looks_like_html_bytes(content):
            return f"{filename} looks like an HTML error page, not an xlsx file -- rejected"
        return f"{filename} does not start with the xlsx ZIP magic number ({XLSX_ZIP_MAGIC!r}) -- rejected"
    return None


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    config = load_config(args.config)

    tours = [t["code"] for t in config["tours"]]
    seasons = config["seasons"]
    if args.tour:
        tours = [t for t in tours if t in args.tour]
    if args.season:
        seasons = [s for s in seasons if s in args.season]

    raw_root = args.output_root / "raw"
    imported = 0
    skipped_already_present = 0
    failed = 0

    for tour_code in tours:
        for season in seasons:
            source_key = f"tennis_data_co_uk:{tour_code}:{season}"
            source_path = args.source_dir / f"{season}.xlsx"
            dest_path = raw_root / "tennis" / "tennis_data_co_uk" / tour_code / f"{season}.xlsx"

            if not source_path.exists():
                print(f"[{source_key}] MISSING: expected a manually downloaded file at {source_path}")
                failed += 1
                continue

            content = source_path.read_bytes()
            error = validate_xlsx_bytes(content, source_path.name)
            if error is not None:
                print(f"[{source_key}] REJECTED: {error}")
                failed += 1
                continue

            try:
                already_present = dest_path.exists()
                write_raw_file_atomic_bytes(dest_path, content)
                if already_present:
                    print(f"[{source_key}] already present with identical content -- left as-is: {dest_path}")
                    skipped_already_present += 1
                else:
                    print(f"[{source_key}] imported ({len(content)} bytes, sha256={compute_sha256_bytes(content)[:12]}...): {dest_path}")
                    imported += 1
            except FileExistsError as exc:
                if not args.force_redownload:
                    print(f"[{source_key}] REFUSED overwrite (existing file differs from source-dir file): {exc}")
                    failed += 1
                    continue
                dest_path.write_bytes(content)
                print(f"[{source_key}] force-overwritten: {dest_path}")
                imported += 1

    print(
        f"\nSummary: imported={imported}, already_present={skipped_already_present}, "
        f"failed_or_missing={failed}"
    )

    if failed > 0:
        print(
            "\nCRITICAL: one or more expected files were missing or invalid. "
            "Manually download the remaining Tennis-data.co.uk .xlsx files "
            "(one per season, ATP men's path) into --source-dir and re-run."
        )
        return 1

    print(
        "\nNext step: run scripts/run_cycle_002_tennis_data_acquisition.py "
        "with --resume so it picks these files up, records them in the "
        "manifest (acquisition_method=resumed_existing_file), and runs the "
        "schema-inventory / data-version / validation steps exactly as it "
        "would for an automated fetch."
    )
    return 0


def main() -> int:
    return run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
