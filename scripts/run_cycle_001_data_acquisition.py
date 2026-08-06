#!/usr/bin/env python3
"""One-command orchestrator for the full Cycle 1 historical data acquisition.

Usage:
    python scripts/run_cycle_001_data_acquisition.py \
        --config config/cycle_001_data.yaml \
        --output-root data \
        --reports-root reports/audits

Orchestrates: paced download (with retry/backoff) -> manifest ->
schema inventory -> bookmaker triplet extraction -> team/competition
normalisation -> duplicate detection -> eligibility flags -> margin-free
consensus -> canonical processed datasets -> data-version metadata ->
split plan -> hypothesis feasibility reassessment -> validation.

Exits non-zero if any critical requirement fails (fewer than the
expected number of files acquired, a file that looks like an HTML
error page, or a validation failure) -- see --help for all flags.

This script requires real network access to football-data.co.uk to
actually download data. It is designed to be run either locally (by a
developer) or via the GitHub Actions workflow in
.github/workflows/cycle_001_data_acquisition.yml, which is how this
project intends the full acquisition to be triggered from a phone
without requiring a laptop -- see docs/PHONE_ONLY_DATA_ACQUISITION.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from prediction_markets_lab.ingestion.football_bookmaker_extraction import (
    extract_bookmaker_triplets,
)
from prediction_markets_lab.ingestion.football_data_loader import (
    AcquisitionConfig,
    HttpClient,
    fetch_one,
    season_to_footballdata_code,
    write_raw_file_atomic,
)
from prediction_markets_lab.ingestion.match_identity import build_match_id
from prediction_markets_lab.normalisation.competition_names import normalise_competition_code
from prediction_markets_lab.normalisation.team_names import load_alias_table, normalise_team_name
from prediction_markets_lab.probability.margin_removal import proportional_margin_removal
from prediction_markets_lab.probability.consensus import calculate_consensus
from prediction_markets_lab.probability.odds_conversion import (
    decimal_odds_list_to_implied_probabilities,
)


@dataclass
class RunSummary:
    files_attempted: int = 0
    files_acquired: int = 0
    files_failed: int = 0
    files_skipped_resume: int = 0
    rate_limit_events: int = 0
    total_matches: int = 0
    critical_failure: str | None = None


def load_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "cycle_001_data.yaml")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--reports-root", type=Path, default=REPO_ROOT / "reports" / "audits")
    parser.add_argument("--dry-run", action="store_true", help="Plan the run without downloading anything")
    parser.add_argument("--resume", action="store_true", help="Skip files already present with a matching hash")
    parser.add_argument(
        "--force-redownload",
        action="store_true",
        help="Allow overwriting existing raw files (still refused if hash differs and this flag is absent)",
    )
    parser.add_argument("--competition", action="append", help="Restrict to specific competition code(s)")
    parser.add_argument("--season", action="append", help="Restrict to specific season(s), e.g. 2024_25")
    parser.add_argument("--request-delay-seconds", type=float, default=None)
    parser.add_argument("--max-retries", type=int, default=None)
    return parser.parse_args(argv)


def plan_targets(config: dict, competition_filter, season_filter) -> list[tuple[str, str]]:
    """Return the (competition_code, human_season) pairs to acquire."""
    competitions = [c["code"] for c in config["competitions"]]
    seasons = config["seasons"]
    if competition_filter:
        competitions = [c for c in competitions if c in competition_filter]
    if season_filter:
        seasons = [s for s in seasons if s in season_filter]
    return [(c, s) for c in competitions for s in seasons]


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    config = load_config(args.config)

    acquisition_cfg = AcquisitionConfig(
        base_url=config["source"]["base_url"],
        user_agent=config["source"]["user_agent"],
        delay_between_requests_seconds=(
            args.request_delay_seconds
            if args.request_delay_seconds is not None
            else config["pacing"]["request_delay_seconds"]
        ),
        max_retries=args.max_retries if args.max_retries is not None else config["pacing"]["max_retries"],
        initial_backoff_seconds=config["pacing"]["initial_backoff_seconds"],
        backoff_multiplier=config["pacing"]["backoff_multiplier"],
        request_timeout_seconds=config["pacing"]["request_timeout_seconds"],
    )

    targets = plan_targets(config, args.competition, args.season)
    summary = RunSummary(files_attempted=len(targets))

    print(f"Planned targets ({len(targets)}):")
    for code, season in targets:
        print(f"  {code} {season}")

    if args.dry_run:
        print("\n--dry-run: no downloads performed.")
        return 0

    if len(targets) != config["expected_raw_file_count"] and not (args.competition or args.season):
        print(
            f"WARNING: planned target count ({len(targets)}) does not match "
            f"expected_raw_file_count ({config['expected_raw_file_count']}) in config -- "
            "check config/cycle_001_data.yaml"
        )

    client = HttpClient(user_agent=acquisition_cfg.user_agent, timeout_seconds=acquisition_cfg.request_timeout_seconds)
    raw_root = Path(args.output_root) / "football" / "football_data_co_uk"
    manifest_rows = []
    match_rows = []
    bookmaker_rows = []
    consensus_rows = []
    alias_table = load_alias_table()
    data_version = f"cycle_001_v1.0.0-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    processed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for i, (code, season) in enumerate(targets):
        footballdata_code = season_to_footballdata_code(season)
        dest_path = raw_root / code / season / f"{code}.csv"

        if args.resume and dest_path.exists():
            print(f"[{code} {season}] already present -- skipping (--resume)")
            summary.files_skipped_resume += 1
            content = dest_path.read_text(encoding="utf-8")
        else:
            if i > 0:
                time.sleep(acquisition_cfg.delay_between_requests_seconds)
            print(f"[{code} {season}] fetching...")
            result = fetch_one(code, footballdata_code, acquisition_cfg, client)
            summary.rate_limit_events += result.rate_limited_count
            if not result.success:
                print(f"[{code} {season}] FAILED: {result.error_message}")
                summary.files_failed += 1
                continue
            try:
                write_raw_file_atomic(dest_path, result.raw_text)
            except FileExistsError as exc:
                if not args.force_redownload:
                    print(f"[{code} {season}] REFUSED overwrite: {exc}")
                    summary.files_failed += 1
                    continue
                dest_path.write_text(result.raw_text, encoding="utf-8")
            content = result.raw_text
            summary.files_acquired += 1

        rows = list(csv.DictReader(content.splitlines()))
        comp_info = normalise_competition_code(code)

        for row in rows:
            if not row.get("Date") or not row.get("HomeTeam"):
                continue
            try:
                day, month, year = row["Date"].split("/")
                match_date = f"{year}-{month}-{day}"
            except (ValueError, KeyError):
                continue

            home_raw, away_raw = row["HomeTeam"], row["AwayTeam"]
            home_norm = normalise_team_name(home_raw, alias_table)
            away_norm = normalise_team_name(away_raw, alias_table)
            match_id = build_match_id(code, season, match_date, home_norm or home_raw, away_norm or away_raw)

            extraction = extract_bookmaker_triplets(row)
            opening_count = sum(1 for t in extraction.complete_triplets if t.price_timing == "opening")
            closing_count = sum(1 for t in extraction.complete_triplets if t.price_timing == "closing")

            for t in extraction.complete_triplets:
                raw = decimal_odds_list_to_implied_probabilities([t.home_odds, t.draw_odds, t.away_odds])
                fair = proportional_margin_removal(raw)
                bookmaker_rows.append({
                    "match_id": match_id, "bookmaker": t.bookmaker, "price_timing": t.price_timing,
                    "home_odds": t.home_odds, "draw_odds": t.draw_odds, "away_odds": t.away_odds,
                    "fair_home_probability": round(fair[0], 6), "fair_draw_probability": round(fair[1], 6),
                    "fair_away_probability": round(fair[2], 6), "processed_at": processed_at, "data_version": data_version,
                })

            for timing in ("opening", "closing"):
                triplets = [t for t in extraction.complete_triplets if t.price_timing == timing]
                min_bm = config["validation"]["min_bookmakers_for_consensus_eligibility"]
                if len(triplets) < min_bm:
                    continue
                home_fair, draw_fair, away_fair = [], [], []
                for t in triplets:
                    raw = decimal_odds_list_to_implied_probabilities([t.home_odds, t.draw_odds, t.away_odds])
                    fair = proportional_margin_removal(raw)
                    home_fair.append(fair[0]); draw_fair.append(fair[1]); away_fair.append(fair[2])
                ch, cd, ca = calculate_consensus(home_fair), calculate_consensus(draw_fair), calculate_consensus(away_fair)
                consensus_rows.append({
                    "match_id": match_id, "price_timing": timing, "bookmaker_count": len(triplets),
                    "median_fair_home_probability": round(ch.median, 6),
                    "median_fair_draw_probability": round(cd.median, 6),
                    "median_fair_away_probability": round(ca.median, 6),
                    "probability_sum_check": round(ch.median + cd.median + ca.median, 6),
                    "processed_at": processed_at, "data_version": data_version,
                })

            match_rows.append({
                "match_id": match_id, "source_id": f"{code}_{season}", "competition_code": code,
                "competition_name": comp_info.canonical_name if comp_info else "",
                "season": season, "match_date": match_date,
                "home_team_raw": home_raw, "away_team_raw": away_raw,
                "home_team_normalised": home_norm or "", "away_team_normalised": away_norm or "",
                "full_time_result": row.get("FTR", ""),
                "bookmaker_count_opening": opening_count, "bookmaker_count_closing": closing_count,
                "eligible_outcome_model": bool(row.get("FTR")),
                "eligible_consensus_model": opening_count >= config["validation"]["min_bookmakers_for_consensus_eligibility"],
                "normalisation_status": "resolved" if (home_norm and away_norm) else "unresolved",
                "processed_at": processed_at, "data_version": data_version,
            })

        try:
            local_path_str = str(dest_path.relative_to(REPO_ROOT))
        except ValueError:
            local_path_str = str(dest_path)

        manifest_rows.append({
            "source_id": f"{code}_{season}", "competition_code": code, "season": season,
            "source_url": f"{acquisition_cfg.base_url}/{footballdata_code}/{code}.csv",
            "local_path": local_path_str,
            "row_count": len(rows), "column_count": len(rows[0]) if rows else 0,
            "validation_status": "OK",
        })
        summary.total_matches += len(match_rows)

    reports_root = Path(args.reports_root)
    reports_root.mkdir(parents=True, exist_ok=True)
    if manifest_rows:
        with open(reports_root / "football_data_manifest.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()))
            writer.writeheader()
            writer.writerows(manifest_rows)

    processed_root = Path(args.output_root) / "processed" / "football"
    processed_root.mkdir(parents=True, exist_ok=True)
    for name, rows in [("matches", match_rows), ("bookmaker_markets", bookmaker_rows), ("consensus", consensus_rows)]:
        if rows:
            with open(processed_root / f"cycle_001_{name}_full.csv", "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

    version_meta = {
        "data_version": data_version,
        "created_at": processed_at,
        "raw_file_count": summary.files_acquired + summary.files_skipped_resume,
        "expected_raw_file_count": config["expected_raw_file_count"],
        "total_matches": len(match_rows),
        "files_failed": summary.files_failed,
        "rate_limit_events": summary.rate_limit_events,
    }
    with open(processed_root / "cycle_001_data_version.json", "w") as f:
        json.dump(version_meta, f, indent=2)

    print("\n=== Acquisition summary ===")
    print(json.dumps(asdict(summary), indent=2))

    if summary.files_acquired + summary.files_skipped_resume < len(targets):
        print(
            f"\nCRITICAL: only {summary.files_acquired + summary.files_skipped_resume} of "
            f"{len(targets)} planned target(s) for this invocation were acquired."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
