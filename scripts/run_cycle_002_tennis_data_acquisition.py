#!/usr/bin/env python3
"""One-command orchestrator for Cycle 2 (Tennis) RAW data acquisition.

Usage:
    python scripts/run_cycle_002_tennis_data_acquisition.py \
        --config config/cycle_002_tennis_data.yaml \
        --output-root data \
        --reports-root reports/audits

Scope of this script, deliberately narrower than Cycle 1's single
mega-orchestrator (which also built bookmaker triplets, team
normalisation, and consensus in the same run): paced download (with
retry/backoff) of Tennismylife/TML-Database ATP match files and
Tennis-data.co.uk odds files -> manifest -> per-source-family schema
inventory (empirically recording the actual CSV header columns found,
the same "discover, don't assume" philosophy Cycle 1 used for
bookmaker-column prefixes) -> data-version metadata -> validation.

PIVOT NOTE (2026-09-11): this script originally targeted Jeff
Sackmann's tennis_atp/tennis_wta GitHub repos directly. Confirmed via
`git ls-remote` and the GitHub API, from a real GitHub Actions runner,
that both repos no longer exist at that path. Replaced with
Tennismylife/TML-Database, an actively-maintained continuation of
Sackmann's work verified against real fetched content before
switching -- see config/cycle_002_tennis_data.yaml's top-of-file note.
WTA and the separate rankings/player-bio files are dropped in this
pivot: TML-Database embeds rank/age/hand/height/country per match row,
and no actively-maintained free WTA source was found.

It deliberately does NOT do player-name normalisation, odds parsing
into probabilities, or consensus construction -- that cross-source
entity-resolution problem (TML-Database's full names vs.
Tennis-data.co.uk's "Djokovic N."-style name strings) is Checkpoint 2,
not acquisition. See config/cycle_002_tennis_data.yaml's top-of-file
note and research/cycles/CYCLE_002_TENNIS/PLAN.md.

This script requires real network access to raw.githubusercontent.com
and tennis-data.co.uk. As of 2026-09-11, both the cloud research
sandbox and this project's own development machine are proxy-blocked
from these hosts -- it is designed to run via
.github/workflows/cycle_002_tennis_data_acquisition.yml, mirroring the
Cycle 1 acquisition workflow's phone-triggerable pattern (see
docs/PHONE_ONLY_DATA_ACQUISITION.md).

Exits non-zero if any critical requirement fails (a source unavailable
after retries, or a file that looks like an HTML error page).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.ingestion.tennis_data_loader import (
    AcquisitionConfig,
    HttpClient,
    fetch_one_bytes,
    fetch_one_text,
    tennis_data_co_uk_url,
    tml_database_match_file_url,
    write_raw_file_atomic_bytes,
    write_raw_file_atomic_text,
)


@dataclass
class RunSummary:
    files_attempted: int = 0
    files_acquired: int = 0
    files_failed: int = 0
    files_skipped_resume: int = 0
    rate_limit_events: int = 0


@dataclass
class AcquisitionTarget:
    source_family: str  # "tml_database_match" | "tennis_data_co_uk"
    content_mode: str  # "text" | "bytes"
    tour_code: str  # "ATP" | "WTA"
    season: str | None  # None for player/ranking files (not per-season)
    url: str
    raw_relative_path: Path  # relative to <output-root>/raw/


def load_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "cycle_002_tennis_data.yaml")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--reports-root", type=Path, default=REPO_ROOT / "reports" / "audits")
    parser.add_argument("--dry-run", action="store_true", help="Plan the run without downloading anything")
    parser.add_argument("--resume", action="store_true", help="Skip files already present on disk without re-fetching")
    parser.add_argument(
        "--force-redownload",
        action="store_true",
        help="Overwrite an existing raw file even if its hash differs from the freshly-fetched content",
    )
    parser.add_argument("--tour", action="append", choices=["ATP", "WTA"], help="Restrict to specific tour(s)")
    parser.add_argument("--season", action="append", help="Restrict to specific season(s), e.g. 2024")
    parser.add_argument("--request-delay-seconds", type=float, default=None)
    parser.add_argument("--max-retries", type=int, default=None)
    return parser.parse_args(argv)


def plan_targets(config: dict, tour_filter, season_filter) -> list[AcquisitionTarget]:
    """Build the flat list of files to acquire.

    PIVOT NOTE (2026-09-11): previously built two extra target families
    per tour (sackmann_ranking, sackmann_player) alongside a
    per-tour/per-season sackmann_match target, keyed off a
    tour-code -> repo-key mapping (sackmann_atp / sackmann_wta) that no
    longer applies now that Jeff Sackmann's tennis_atp/tennis_wta repos
    are gone. Tennismylife/TML-Database's schema embeds rank/age/hand/
    height/country directly in each per-season match file, so the
    ranking/player target families are removed entirely rather than
    re-pointed -- there is nothing left for them to fetch. Tours now
    comes straight from config (ATP only for this phase; see
    config/cycle_002_tennis_data.yaml's top-of-file note on the WTA
    descope), so no tour-code -> slug mapping helper is needed either.
    """
    tours = [t["code"] for t in config["tours"]]
    seasons = config["seasons"]
    if tour_filter:
        tours = [t for t in tours if t in tour_filter]
    if season_filter:
        seasons = [s for s in seasons if s in season_filter]

    sources = config["sources"]
    targets: list[AcquisitionTarget] = []

    for tour_code in tours:
        tml = sources["tml_database_atp"]
        filename_template = config["tml_database_match_files"]["filename_template"]

        for season in seasons:
            url = tml_database_match_file_url(tml["base_url"], filename_template, season)
            targets.append(AcquisitionTarget(
                source_family="tml_database_match", content_mode="text", tour_code=tour_code, season=season, url=url,
                raw_relative_path=Path("tennis") / "tml_database" / tour_code.lower() / filename_template.format(season=season),
            ))

        tdcu = sources["tennis_data_co_uk"]
        for season in seasons:
            url = tennis_data_co_uk_url(
                tdcu["base_url"], tour_code, season, tdcu["men_path_template"], tdcu["women_path_template"]
            )
            targets.append(AcquisitionTarget(
                source_family="tennis_data_co_uk", content_mode="bytes", tour_code=tour_code, season=season, url=url,
                raw_relative_path=Path("tennis") / "tennis_data_co_uk" / tour_code / f"{season}.xlsx",
            ))

    return targets


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    config = load_config(args.config)

    acquisition_cfg = AcquisitionConfig(
        user_agent=config["sources"]["user_agent"],
        delay_between_requests_seconds=(
            args.request_delay_seconds if args.request_delay_seconds is not None
            else config["pacing"]["request_delay_seconds"]
        ),
        max_retries=args.max_retries if args.max_retries is not None else config["pacing"]["max_retries"],
        initial_backoff_seconds=config["pacing"]["initial_backoff_seconds"],
        backoff_multiplier=config["pacing"]["backoff_multiplier"],
        request_timeout_seconds=config["pacing"]["request_timeout_seconds"],
    )

    targets = plan_targets(config, args.tour, args.season)
    summary = RunSummary(files_attempted=len(targets))

    print(f"Planned targets ({len(targets)}):")
    for t in targets:
        print(f"  [{t.source_family}/{t.content_mode}] {t.tour_code} {t.season or ''} <- {t.url}")

    if args.dry_run:
        print("\n--dry-run: no downloads performed.")
        return 0

    if len(targets) != config["expected_raw_file_count"] and not (args.tour or args.season):
        print(
            f"WARNING: planned target count ({len(targets)}) does not match "
            f"expected_raw_file_count ({config['expected_raw_file_count']}) in config -- "
            "check config/cycle_002_tennis_data.yaml"
        )

    client = HttpClient(user_agent=acquisition_cfg.user_agent, timeout_seconds=acquisition_cfg.request_timeout_seconds)
    raw_root = args.output_root / "raw"
    manifest_rows: list[dict] = []
    schema_inventory: dict[str, dict] = {}

    for i, target in enumerate(targets):
        dest_path = raw_root / target.raw_relative_path
        source_key = f"{target.source_family}:{target.tour_code}:{target.season or 'all'}"

        if args.resume and dest_path.exists():
            print(f"[{source_key}] already present -- skipping (--resume)")
            summary.files_skipped_resume += 1
            # A pre-existing file at --resume time could be either a real
            # earlier automated fetch, or a file placed here by
            # scripts/import_manual_tennis_data_co_uk_files.py (the
            # manual-download fallback for when Tennis-data.co.uk's TLS
            # handshake can't be made to work at all). Both are legitimate
            # and both get a manifest row; "resumed_existing_file" is the
            # honest label for provenance -- it does not claim this run
            # fetched the bytes itself, only that it found and recorded
            # them. See scripts/import_manual_tennis_data_co_uk_files.py's
            # module docstring for the full fallback rationale.
            acquisition_method = "resumed_existing_file"
            if target.content_mode == "text":
                content = dest_path.read_text(encoding="utf-8")
            else:
                content = dest_path.read_bytes()
        else:
            acquisition_method = "automated_fetch"
            if i > 0:
                time.sleep(acquisition_cfg.delay_between_requests_seconds)
            print(f"[{source_key}] fetching...")
            if target.content_mode == "text":
                result = fetch_one_text(source_key, target.url, acquisition_cfg, client)
            else:
                result = fetch_one_bytes(source_key, target.url, acquisition_cfg, client)
            summary.rate_limit_events += result.rate_limited_count
            if not result.success:
                print(f"[{source_key}] FAILED: {result.error_message}")
                summary.files_failed += 1
                continue
            content = result.raw_text if target.content_mode == "text" else result.raw_bytes
            try:
                if target.content_mode == "text":
                    write_raw_file_atomic_text(dest_path, content)
                else:
                    write_raw_file_atomic_bytes(dest_path, content)
            except FileExistsError as exc:
                if not args.force_redownload:
                    print(f"[{source_key}] REFUSED overwrite: {exc}")
                    summary.files_failed += 1
                    continue
                if target.content_mode == "text":
                    dest_path.write_text(content, encoding="utf-8")
                else:
                    dest_path.write_bytes(content)
            summary.files_acquired += 1

        digest = hashlib.sha256(content.encode("utf-8") if target.content_mode == "text" else content).hexdigest()
        byte_size = len(content.encode("utf-8")) if target.content_mode == "text" else len(content)
        manifest_rows.append({
            "source_family": target.source_family,
            "content_mode": target.content_mode,
            "tour_code": target.tour_code,
            "season": target.season or "",
            "url": target.url,
            "raw_relative_path": str(target.raw_relative_path),
            "acquisition_method": acquisition_method,
            "sha256": digest,
            "bytes": byte_size,
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })

        # Empirical schema inventory: only meaningful for text CSV
        # sources here -- the xlsx odds files need a real spreadsheet
        # reader (openpyxl or similar), which is Checkpoint 2's concern,
        # not duplicated in this acquisition-only script.
        if target.content_mode == "text":
            first_line = content.split("\n", 1)[0]
            header_columns = next(csv.reader([first_line]))
            # Keyed by filename stem, not just tour+season -- multiple
            # ranking files share the same (tour, season=None) pair, and
            # collapsing them to one key would silently drop all but
            # the last-processed ranking file's header.
            inventory_key = f"{target.tour_code}:{target.season or target.raw_relative_path.stem}"
            schema_inventory.setdefault(target.source_family, {})[inventory_key] = header_columns

    reports_root = args.reports_root
    reports_root.mkdir(parents=True, exist_ok=True)

    manifest_path = REPO_ROOT / config["output_paths"]["manifest_path"]
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", newline="") as f:
        if manifest_rows:
            writer = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()))
            writer.writeheader()
            writer.writerows(manifest_rows)

    schema_inventory_path = reports_root / "tennis_data_schema_inventory.json"
    with open(schema_inventory_path, "w") as f:
        json.dump(schema_inventory, f, indent=2, sort_keys=True)

    data_version_path = REPO_ROOT / config["output_paths"]["data_version_path"]
    data_version_path.parent.mkdir(parents=True, exist_ok=True)
    data_version = {
        "data_version": f"cycle_002_tennis_v0.1.0-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "acquisition_scope": (
            "raw acquisition only -- no player-name matching, no odds parsing, "
            "no consensus construction (deferred to Checkpoint 2)"
        ),
        "schema_version": config["schema"]["canonical_schema_version"],
        "sources": ["tml_database_atp", "tennis_data_co_uk"],
        "match_data_license": config["licensing"]["match_data_license"],
        "match_data_attribution": config["licensing"]["match_data_attribution"],
        "seasons": config["seasons"],
        "summary": asdict(summary),
    }
    with open(data_version_path, "w") as f:
        json.dump(data_version, f, indent=2, sort_keys=True)

    print(f"\nSummary: {summary}")

    if summary.files_failed > 0:
        print(f"CRITICAL: {summary.files_failed} file(s) failed to acquire.")
        return 1
    return 0


def main() -> int:
    return run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
