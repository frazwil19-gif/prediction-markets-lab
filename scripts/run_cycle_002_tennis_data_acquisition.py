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

Exits non-zero if a REQUIRED source family fails (a source unavailable
after retries, or a file that looks like an HTML error page).
config/cycle_002_tennis_data.yaml's optional_source_families lists
source families that may fail without failing the run -- currently
just tennis_data_co_uk, confirmed broken server-side (a fatal TLS
alert) against every real client tried as of 2026-09-15. An optional
failure is still fully recorded (manifest, data-version summary,
printed warning) -- "optional" means "does not block the run," never
"silently dropped" or "faked as present."
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
    # files_failed counts REQUIRED-source-family failures only -- the
    # hard gate this script's exit code and
    # validate_cycle_002_tennis_data_bundle.py both key off. A failure
    # in an optional_source_families family (see
    # config/cycle_002_tennis_data.yaml) is tracked separately in
    # files_failed_optional and never fails the run: it is a real,
    # honestly-recorded gap (never silently dropped, never fabricated
    # as present), just not one that should block progress on the
    # required sources that did succeed. failed_optional_source_keys
    # names exactly which targets failed, for anyone auditing the run.
    files_failed: int = 0
    files_failed_optional: int = 0
    files_skipped_resume: int = 0
    rate_limit_events: int = 0
    failed_optional_source_keys: list[str] = None

    def __post_init__(self) -> None:
        if self.failed_optional_source_keys is None:
            self.failed_optional_source_keys = []


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
    parser.add_argument(
        "--optional-max-retries", type=int, default=None,
        help=(
            "Retries specifically for optional-source-family targets (see "
            "config/cycle_002_tennis_data.yaml's optional_source_families). "
            "Deliberately independent of --max-retries: the acquisition workflow "
            "always passes an explicit --max-retries (its workflow_dispatch input "
            "has a default value, so the flag is never actually omitted), which "
            "would otherwise silently defeat pacing.optional_source_max_retries's "
            "fast-fail behaviour on every real run -- see PLAN.md's 2026-09-15 "
            "diagnostic notes for the run this bug was caught on. Defaults to "
            "config's pacing.optional_source_max_retries; pass this explicitly "
            "only to deliberately give a known-broken optional source a longer, "
            "uniform retry budget for a specific diagnostic pass."
        ),
    )
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
    # A source family already confirmed broken (see
    # config/cycle_002_tennis_data.yaml's optional_source_families
    # note) gets its own, much smaller retry budget rather than the
    # full one -- see that config's pacing.optional_source_max_retries
    # comment for the reasoning. This is deliberately controlled by its
    # OWN CLI flag (--optional-max-retries), not by --max-retries: the
    # acquisition workflow's "Build acquisition command" step always
    # appends --max-retries with its workflow_dispatch input's current
    # value (that input has a default, so the flag is never actually
    # omitted), so gating this on "--max-retries wasn't passed" silently
    # never applied on any real run -- caught on the 2026-09-15 run that
    # still took ~12 minutes instead of the intended ~2. See PLAN.md.
    optional_source_families = set(config.get("optional_source_families", []))
    optional_max_retries = (
        args.optional_max_retries if args.optional_max_retries is not None
        else config["pacing"].get("optional_source_max_retries", acquisition_cfg.max_retries)
    )
    optional_acquisition_cfg = AcquisitionConfig(
        user_agent=acquisition_cfg.user_agent,
        delay_between_requests_seconds=acquisition_cfg.delay_between_requests_seconds,
        max_retries=optional_max_retries,
        initial_backoff_seconds=acquisition_cfg.initial_backoff_seconds,
        backoff_multiplier=acquisition_cfg.backoff_multiplier,
        request_timeout_seconds=acquisition_cfg.request_timeout_seconds,
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
            is_optional = target.source_family in optional_source_families
            target_cfg = optional_acquisition_cfg if is_optional else acquisition_cfg
            if i > 0:
                time.sleep(target_cfg.delay_between_requests_seconds)
            print(f"[{source_key}] fetching...")
            if target.content_mode == "text":
                result = fetch_one_text(source_key, target.url, target_cfg, client)
            else:
                result = fetch_one_bytes(source_key, target.url, target_cfg, client)
            summary.rate_limit_events += result.rate_limited_count
            if not result.success:
                if is_optional:
                    print(f"[{source_key}] FAILED (optional source, not blocking the run): {result.error_message}")
                    summary.files_failed_optional += 1
                    summary.failed_optional_source_keys.append(source_key)
                else:
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
                    if is_optional:
                        print(f"[{source_key}] REFUSED overwrite (optional source, not blocking the run): {exc}")
                        summary.files_failed_optional += 1
                        summary.failed_optional_source_keys.append(source_key)
                    else:
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

    # FIX (2026-09-15): these two paths used to be hardcoded as
    # REPO_ROOT / config[...], ignoring --output-root / --reports-root
    # entirely -- a "harmless in real usage" quirk previously left alone
    # (real runs always use the defaults, which happen to equal these
    # hardcoded paths anyway). It stopped being harmless the moment a real,
    # already-acquired manifest/data-version pair sat at those exact real
    # paths AND the test suite's real (non-dry-run) run() invocations wrote
    # to -- and their cleanup code unlinked -- those same real paths instead
    # of the test's own tmp_path, because this code never actually honoured
    # the CLI overrides those tests passed. That silently deleted a real
    # acquisition's real output. Fixed by deriving both paths from
    # args.reports_root / args.output_root (which already default to the
    # exact same real locations, so this changes nothing for a real run)
    # instead of REPO_ROOT, so a test-provided --output-root/--reports-root
    # is now actually honoured and test runs can never touch real repo state.
    manifest_path = reports_root / Path(config["output_paths"]["manifest_path"]).name
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", newline="") as f:
        if manifest_rows:
            writer = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()))
            writer.writeheader()
            writer.writerows(manifest_rows)

    schema_inventory_path = reports_root / "tennis_data_schema_inventory.json"
    with open(schema_inventory_path, "w") as f:
        json.dump(schema_inventory, f, indent=2, sort_keys=True)

    # config's data_version_path is "data/processed/tennis/..." -- relative
    # to the repo root, i.e. relative to args.output_root's own default
    # (REPO_ROOT / "data"). Strip the leading "data/" so it composes
    # correctly with a non-default --output-root too.
    data_version_relative = Path(*Path(config["output_paths"]["data_version_path"]).parts[1:])
    data_version_path = args.output_root / data_version_relative
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
        "optional_source_families": sorted(optional_source_families),
    }
    with open(data_version_path, "w") as f:
        json.dump(data_version, f, indent=2, sort_keys=True)

    print(f"\nSummary: {summary}")

    if summary.files_failed_optional > 0:
        print(
            f"WARNING: {summary.files_failed_optional} optional-source file(s) failed to "
            f"acquire and are genuinely missing (not fabricated, not silently dropped): "
            f"{', '.join(summary.failed_optional_source_keys)}. See "
            "config/cycle_002_tennis_data.yaml's optional_source_families note -- this does "
            "not block the run, but downstream steps that need this data (the odds/consensus "
            "benchmark) cannot proceed until it's actually acquired, either by this source "
            "recovering or via the manual-download fallback "
            "(scripts/import_manual_tennis_data_co_uk_files.py)."
        )

    if summary.files_failed > 0:
        print(f"CRITICAL: {summary.files_failed} required file(s) failed to acquire.")
        return 1
    return 0


def main() -> int:
    return run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
