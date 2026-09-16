"""Football Cycle 2 -- richer canonical extraction from already-downloaded
Cycle 1 raw files.

This script does NOT fetch anything from the network and does NOT modify
any Cycle 1 raw or processed file. It re-reads the raw Football-Data.co.uk
CSVs already on disk under data/raw/football/football_data_co_uk/ (the
exact same files, byte-for-byte, that Cycle 1 downloaded and hashed) and
extracts fields Cycle 1's canonicalisation never touched: match
statistics (shots, shots-on-target, corners, fouls, cards, referee) and
two new markets (Over/Under 2.5 goals, Asian Handicap), at both opening
and closing prices.

Per the operator's explicit instruction (Football Cycle 2 direction
change, 2026-09-16): "Do not modify the frozen Football Cycle 1 raw
dataset. Build a new Cycle 2 canonical/exploratory dataset from it."
Every output file below is a NEW cycle_002_* file; nothing under
cycle_001_* is read for writing, only for confirming row-count parity.

match_id is rebuilt using the exact same normalisation/build_match_id
logic Cycle 1 used, so cycle_002_* rows join cleanly onto
cycle_001_matches_full.csv by match_id.

PRICE SEMANTICS (verified against a full competition x season header
sweep of every raw file in this repo, plus
https://www.football-data.co.uk/notes.txt -- see
football_richer_extraction.py's module docstring for the full writeup):

  * Over/Under 2.5 and Asian Handicap are NOT quoted by the same
    six-bookmaker panel used for 1X2. Only two individual bookmakers,
    Bet365 (B365) and Pinnacle (P), publish both opening and closing
    odds for these markets across the FULL 2020/21-2024/25 corpus.
    Betfair Exchange (BFE) appears only from the 2024/25 season
    onward -- extracted separately below and never pooled with the
    full-corpus figures.
  * Because there are at most two full-corpus individual bookmakers,
    this script does NOT attempt a >=4-bookmaker median "consensus"
    for these two markets (the >=4 threshold, correct for 1X2, cannot
    be met and would silently produce zero rows -- confirmed by a
    first run of this script that did exactly that). Instead it
    reports, per match per price timing: (a) the individual bookmaker
    quotes themselves (bookmaker column identifies B365/P/BFE); (b) an
    "individual_median" figure computed only when >=2 individual
    quotes are present, reported alongside the exact count used; and
    (c) Football-Data's OWN "Avg" and "Max" cross-bookmaker summary
    statistics, kept clearly labelled as the SOURCE's computation
    (across a wider, unstated bookmaker panel) rather than presented
    as if this script built them. "Max" is never margin-removed or
    turned into a probability (the two sides need not share a
    bookmaker, so it is not a coherent book) -- only its raw odds are
    kept, as a diagnostic upper bound.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from prediction_markets_lab.ingestion.football_richer_extraction import (
    BFE_ONLY_PREFIX,
    extract_asian_handicap_line,
    extract_market_summary_two_way,
    extract_match_statistics,
    extract_two_way_market,
)
from prediction_markets_lab.ingestion.match_identity import build_match_id
from prediction_markets_lab.normalisation.competition_names import COMPETITION_REGISTRY
from prediction_markets_lab.normalisation.team_names import load_alias_table, normalise_team_name
from prediction_markets_lab.probability.consensus import calculate_consensus
from prediction_markets_lab.probability.margin_removal import proportional_margin_removal
from prediction_markets_lab.probability.odds_conversion import (
    decimal_odds_list_to_implied_probabilities,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config" / "cycle_001_data.yaml"
RAW_ROOT = REPO_ROOT / "data" / "raw" / "football" / "football_data_co_uk"
OUTPUT_ROOT = REPO_ROOT / "data" / "processed" / "football"

# Individual bookmakers extracted for Over/Under and Asian Handicap:
# B365 and P cover the full corpus; BFE is 2024/25-only. All three are
# extracted into the same "bookmaker" column (provenance is per-row,
# explicit) rather than silently pooled into one undated figure.
TWO_WAY_PREFIXES_TO_EXTRACT = ("B365", "P") + BFE_ONLY_PREFIX

# Minimum individual bookmakers (of the above) required, at a given
# price timing, before this script reports its own median. Two, not
# four: four cannot be met for these markets in this data source (see
# module docstring). This is a materially different, weaker figure
# than the 1X2 consensus and must never be conflated with it.
MIN_BOOKMAKERS_FOR_INDIVIDUAL_MEDIAN = 2


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _fair_probabilities(odds_a: float, odds_b: float) -> tuple[float, float]:
    raw = decimal_odds_list_to_implied_probabilities([odds_a, odds_b])
    fair = proportional_margin_removal(raw)
    return fair[0], fair[1]


def run() -> int:
    config = load_config()
    competitions = [c["code"] for c in config["competitions"]]
    seasons = config["seasons"]

    alias_table = load_alias_table()
    data_version = f"cycle_002_richer_v1.1.0-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    processed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    statistics_rows: list[dict] = []
    ou25_bookmaker_rows: list[dict] = []
    ou25_context_rows: list[dict] = []
    ah_bookmaker_rows: list[dict] = []
    ah_context_rows: list[dict] = []

    total_rows_read = 0
    files_missing = 0

    def _build_context_rows(
        match_id: str,
        complete_prices,
        summary_prices,
        line_lookup: dict[str, float | None] | None,
    ) -> list[dict]:
        """Shared logic for the OU25/AH 'market context' rows: individual
        median (>=2 bookmakers only) + source Avg (fair) + source Max (raw).
        """
        rows: list[dict] = []
        for timing in ("opening", "closing"):
            individual = [p for p in complete_prices if p.price_timing == timing]
            row_out: dict = {
                "match_id": match_id,
                "price_timing": timing,
                "individual_bookmaker_count": len(individual),
                "individual_bookmakers": "|".join(sorted(p.bookmaker for p in individual)),
                "individual_median_fair_side_a_probability": None,
                "individual_median_fair_side_b_probability": None,
                "source_avg_side_a_odds": None,
                "source_avg_side_b_odds": None,
                "source_avg_fair_side_a_probability": None,
                "source_avg_fair_side_b_probability": None,
                "source_avg_probability_sum_check": None,
                "source_max_side_a_odds": None,
                "source_max_side_b_odds": None,
            }
            if line_lookup is not None:
                row_out["line"] = line_lookup["opening_line"] if timing == "opening" else line_lookup["closing_line"]

            if len(individual) >= MIN_BOOKMAKERS_FOR_INDIVIDUAL_MEDIAN:
                fair_a, fair_b = [], []
                for p in individual:
                    a, b = _fair_probabilities(p.side_a_odds, p.side_b_odds)
                    fair_a.append(a)
                    fair_b.append(b)
                ca, cb = calculate_consensus(fair_a), calculate_consensus(fair_b)
                row_out["individual_median_fair_side_a_probability"] = round(ca.median, 6)
                row_out["individual_median_fair_side_b_probability"] = round(cb.median, 6)

            for s in summary_prices:
                if s.price_timing != timing:
                    continue
                if s.summary_type == "avg":
                    row_out["source_avg_side_a_odds"] = s.side_a_odds
                    row_out["source_avg_side_b_odds"] = s.side_b_odds
                    if s.side_a_odds is not None and s.side_b_odds is not None:
                        raw_sum = (1.0 / s.side_a_odds) + (1.0 / s.side_b_odds)
                        fair_a, fair_b = _fair_probabilities(s.side_a_odds, s.side_b_odds)
                        row_out["source_avg_fair_side_a_probability"] = round(fair_a, 6)
                        row_out["source_avg_fair_side_b_probability"] = round(fair_b, 6)
                        row_out["source_avg_probability_sum_check"] = round(raw_sum, 6)
                elif s.summary_type == "max":
                    row_out["source_max_side_a_odds"] = s.side_a_odds
                    row_out["source_max_side_b_odds"] = s.side_b_odds

            rows.append(row_out)
        return rows

    for code in competitions:
        for season in seasons:
            raw_path = RAW_ROOT / code / season / f"{code}.csv"
            if not raw_path.exists():
                print(f"[{code} {season}] MISSING raw file -- skipping (not re-fetched, per instruction)")
                files_missing += 1
                continue

            with open(raw_path, newline="", encoding="latin1") as f:
                rows = list(csv.DictReader(f))

            comp_info = COMPETITION_REGISTRY.get(code)

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
                total_rows_read += 1

                # --- Match statistics (never a pre-match feature on their own match) ---
                stats = extract_match_statistics(row)
                ah_line = extract_asian_handicap_line(row)
                statistics_rows.append({
                    "match_id": match_id,
                    "competition_code": code,
                    "competition_name": comp_info.canonical_name if comp_info else "",
                    "season": season,
                    "match_date": match_date,
                    "full_time_result": row.get("FTR", ""),
                    "full_time_home_goals": row.get("FTHG", ""),
                    "full_time_away_goals": row.get("FTAG", ""),
                    "home_shots": stats.home_shots,
                    "away_shots": stats.away_shots,
                    "home_shots_on_target": stats.home_shots_on_target,
                    "away_shots_on_target": stats.away_shots_on_target,
                    "home_corners": stats.home_corners,
                    "away_corners": stats.away_corners,
                    "home_fouls": stats.home_fouls,
                    "away_fouls": stats.away_fouls,
                    "home_yellow_cards": stats.home_yellow_cards,
                    "away_yellow_cards": stats.away_yellow_cards,
                    "home_red_cards": stats.home_red_cards,
                    "away_red_cards": stats.away_red_cards,
                    "referee": stats.referee,
                    "asian_handicap_line_opening": ah_line["opening_line"],
                    "asian_handicap_line_closing": ah_line["closing_line"],
                    "processed_at": processed_at,
                    "data_version": data_version,
                })

                # --- Over/Under 2.5 goals ---
                ou25 = extract_two_way_market(row, ">2.5", "<2.5", bookmaker_prefixes=TWO_WAY_PREFIXES_TO_EXTRACT)
                ou25_summary = extract_market_summary_two_way(row, ">2.5", "<2.5")
                for p in ou25.complete_prices:
                    fair_a, fair_b = _fair_probabilities(p.side_a_odds, p.side_b_odds)
                    ou25_bookmaker_rows.append({
                        "match_id": match_id, "bookmaker": p.bookmaker, "price_timing": p.price_timing,
                        "over_2_5_odds": p.side_a_odds, "under_2_5_odds": p.side_b_odds,
                        "fair_over_2_5_probability": round(fair_a, 6),
                        "fair_under_2_5_probability": round(fair_b, 6),
                        "processed_at": processed_at, "data_version": data_version,
                    })
                for r in _build_context_rows(match_id, ou25.complete_prices, ou25_summary, None):
                    r["processed_at"] = processed_at
                    r["data_version"] = data_version
                    ou25_context_rows.append({
                        "match_id": r["match_id"], "price_timing": r["price_timing"],
                        "individual_bookmaker_count": r["individual_bookmaker_count"],
                        "individual_bookmakers": r["individual_bookmakers"],
                        "individual_median_fair_over_2_5_probability": r["individual_median_fair_side_a_probability"],
                        "individual_median_fair_under_2_5_probability": r["individual_median_fair_side_b_probability"],
                        "source_avg_over_2_5_odds": r["source_avg_side_a_odds"],
                        "source_avg_under_2_5_odds": r["source_avg_side_b_odds"],
                        "source_avg_fair_over_2_5_probability": r["source_avg_fair_side_a_probability"],
                        "source_avg_fair_under_2_5_probability": r["source_avg_fair_side_b_probability"],
                        "source_avg_probability_sum_check": r["source_avg_probability_sum_check"],
                        "source_max_over_2_5_odds": r["source_max_side_a_odds"],
                        "source_max_under_2_5_odds": r["source_max_side_b_odds"],
                        "processed_at": processed_at, "data_version": data_version,
                    })

                # --- Asian Handicap (single reference line) ---
                ah = extract_two_way_market(row, "AHH", "AHA", bookmaker_prefixes=TWO_WAY_PREFIXES_TO_EXTRACT)
                ah_summary = extract_market_summary_two_way(row, "AHH", "AHA")
                for p in ah.complete_prices:
                    fair_a, fair_b = _fair_probabilities(p.side_a_odds, p.side_b_odds)
                    ah_bookmaker_rows.append({
                        "match_id": match_id, "bookmaker": p.bookmaker, "price_timing": p.price_timing,
                        "home_ah_odds": p.side_a_odds, "away_ah_odds": p.side_b_odds,
                        "fair_home_ah_probability": round(fair_a, 6),
                        "fair_away_ah_probability": round(fair_b, 6),
                        "processed_at": processed_at, "data_version": data_version,
                    })
                for r in _build_context_rows(match_id, ah.complete_prices, ah_summary, ah_line):
                    ah_context_rows.append({
                        "match_id": r["match_id"], "price_timing": r["price_timing"], "line": r["line"],
                        "individual_bookmaker_count": r["individual_bookmaker_count"],
                        "individual_bookmakers": r["individual_bookmakers"],
                        "individual_median_fair_home_ah_probability": r["individual_median_fair_side_a_probability"],
                        "individual_median_fair_away_ah_probability": r["individual_median_fair_side_b_probability"],
                        "source_avg_home_ah_odds": r["source_avg_side_a_odds"],
                        "source_avg_away_ah_odds": r["source_avg_side_b_odds"],
                        "source_avg_fair_home_ah_probability": r["source_avg_fair_side_a_probability"],
                        "source_avg_fair_away_ah_probability": r["source_avg_fair_side_b_probability"],
                        "source_avg_probability_sum_check": r["source_avg_probability_sum_check"],
                        "source_max_home_ah_odds": r["source_max_side_a_odds"],
                        "source_max_away_ah_odds": r["source_max_side_b_odds"],
                        "processed_at": processed_at, "data_version": data_version,
                    })

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    def _write_csv(path: Path, rows: list[dict]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    _write_csv(OUTPUT_ROOT / "cycle_002_match_statistics.csv", statistics_rows)
    _write_csv(OUTPUT_ROOT / "cycle_002_bookmaker_markets_ou25.csv", ou25_bookmaker_rows)
    _write_csv(OUTPUT_ROOT / "cycle_002_market_context_ou25.csv", ou25_context_rows)
    _write_csv(OUTPUT_ROOT / "cycle_002_bookmaker_markets_ah.csv", ah_bookmaker_rows)
    _write_csv(OUTPUT_ROOT / "cycle_002_market_context_ah.csv", ah_context_rows)

    individual_median_ou25 = sum(
        1 for r in ou25_context_rows if r["individual_median_fair_over_2_5_probability"] is not None
    )
    source_avg_ou25 = sum(1 for r in ou25_context_rows if r["source_avg_fair_over_2_5_probability"] is not None)
    individual_median_ah = sum(
        1 for r in ah_context_rows if r["individual_median_fair_home_ah_probability"] is not None
    )
    source_avg_ah = sum(1 for r in ah_context_rows if r["source_avg_fair_home_ah_probability"] is not None)

    version_info = {
        "data_version": data_version,
        "created_at": processed_at,
        "source_raw_files": "unchanged Cycle 1 raw files (data/raw/football/football_data_co_uk/) -- no new acquisition",
        "total_match_rows": len(statistics_rows),
        "total_rows_read": total_rows_read,
        "files_missing": files_missing,
        "ou25_bookmaker_rows": len(ou25_bookmaker_rows),
        "ou25_context_rows": len(ou25_context_rows),
        "ou25_context_rows_with_individual_median (>=2 of B365/P/BFE)": individual_median_ou25,
        "ou25_context_rows_with_source_avg": source_avg_ou25,
        "ah_bookmaker_rows": len(ah_bookmaker_rows),
        "ah_context_rows": len(ah_context_rows),
        "ah_context_rows_with_individual_median (>=2 of B365/P/BFE)": individual_median_ah,
        "ah_context_rows_with_source_avg": source_avg_ah,
        "note": (
            "OU25/AH have no >=4-bookmaker individual consensus in this "
            "source (only B365+P full-corpus, BFE 2024/25-only) -- see "
            "football_richer_extraction.py module docstring. "
            "'individual_median' fields require >=2 individual bookmakers; "
            "'source_avg' fields are Football-Data's own cross-bookmaker "
            "average, not built by this script."
        ),
    }
    (OUTPUT_ROOT / "cycle_002_richer_extraction_version.json").write_text(
        json.dumps(version_info, indent=2), encoding="utf-8"
    )

    print(json.dumps(version_info, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
