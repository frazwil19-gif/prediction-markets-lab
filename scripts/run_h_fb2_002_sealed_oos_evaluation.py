"""H-FB2-002 sealed 2025/26 out-of-sample evaluation.

Executes, in strict order, the frozen protocol in
research/cycles/CYCLE_003_FOOTBALL/FOOTBALL_CYCLE_2_SEALED_OOS_PROTOCOL.md
(as refined by its section 17 pre-acquisition correction) against the
three manually-downloaded 2025/26 Football-Data.co.uk raw files. This
is a ONE-SHOT test: H-FB2-002 gets exactly one sealed evaluation here.

Order of operations, mirroring the protocol's own Phase 0-13 sequence
(operator instruction, 2026-09-17):
  1. Provenance -- hash/size/row-count/date-range for each raw file.
  2. DATA-ONLY audit -- schema drift vs. the frozen 2024/25 file, row
     counts vs. full-season expectations, duplicates, missing values.
     Computes NO win rate, no SOT effect, no hypothesis-related figure.
  3. Canonicalisation -- exactly Cycle 1's own match/bookmaker/consensus
     logic (see scripts/run_cycle_001_data_acquisition.py), applied to
     the new 2025/26 files only. Writes NEW files under an
     `h_fb2_002_sealed_oos_2025_26_*` prefix; touches no cycle_001_* or
     cycle_002_* frozen file.
  4. Match statistics -- exactly Cycle 2's own extraction
     (football_richer_extraction.extract_match_statistics).
  5. Rolling SOT features WITH cross-season continuity -- the frozen
     2020/21-2024/25 team histories (already-committed cycle_001/
     cycle_002 processed files) are combined with the new 2025/26
     matches into ONE chronological replay of
     compute_rolling_features, so each team's first 2025/26 rolling
     snapshot legitimately inherits its 2024/25 tail history, exactly
     as the frozen feature semantics already handle (see
     features/football_leakage_safe_features.py's own docstring). No
     team's history is reset to empty at the season boundary.
  6. Freeze the eligible 2025/26 OOS sample (exclusions recorded by
     reason) BEFORE the primary test is computed.
  7. Run the frozen primary test EXACTLY ONCE (top price quintile,
     recomputed on the 2025/26 sample itself per protocol section 9;
     median SOT-differential split; bootstrap_ci_mean_diff reused
     unchanged from football_cycle2_development.py).
  8. Only THEN run the pre-registered secondary diagnostics
     (competition breakdown, continuous correlation, favourite-price
     distribution, within-season time-slice stability).
  9. Classify mechanically via oos_verdict.classify_sealed_oos_result.

No threshold, window, price source, or classifier rule is changed
anywhere in this script in response to what the data shows -- every
free parameter here (SOT window=10, quintile count=5, top_index=4,
bootstrap seed=42/n=2000, min_n=100) is copied verbatim from the frozen
development script/protocol, never re-derived.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from prediction_markets_lab.features.football_leakage_safe_features import (
    TeamMatchInput,
    compute_rolling_features,
)
from prediction_markets_lab.ingestion.football_bookmaker_extraction import (
    BOOKMAKER_PREFIXES_2025_26,
    extract_bookmaker_triplets,
)
from prediction_markets_lab.ingestion.football_richer_extraction import extract_match_statistics
from prediction_markets_lab.ingestion.match_identity import build_match_id
from prediction_markets_lab.normalisation.competition_names import normalise_competition_code
from prediction_markets_lab.normalisation.team_names import load_alias_table, normalise_team_name
from prediction_markets_lab.probability.consensus import calculate_consensus
from prediction_markets_lab.probability.margin_removal import proportional_margin_removal
from prediction_markets_lab.probability.odds_conversion import decimal_odds_list_to_implied_probabilities
from prediction_markets_lab.research.football_cycle2_development import (
    bootstrap_ci_mean_diff,
    pearson_correlation,
)
from prediction_markets_lab.research.oos_verdict import (
    SealedOOSVerdictInput,
    classify_sealed_oos_result,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = REPO_ROOT / "data" / "raw" / "football" / "football_data_co_uk"
PROCESSED_ROOT = REPO_ROOT / "data" / "processed" / "football"

OOS_SEASON = "2025_26"
OOS_COMPETITIONS = ["E0", "E1", "SC0"]
REFERENCE_SEASON_FOR_SCHEMA = "2024_25"  # the most recent frozen season, for schema-drift comparison
DEV_SEASONS = ["2020_21", "2021_22", "2022_23", "2023_24", "2024_25"]
MIN_BOOKMAKERS_FOR_CONSENSUS = 4  # identical to config/cycle_001_data.yaml
MIN_SUBGROUP_N = 100  # frozen floor, item J / protocol section 12
FULL_SEASON_EXPECTED_MATCHES = {"E0": 380, "E1": 552, "SC0": 228}  # 20/24/12-team round-robins

RESULT_POINTS = {"H": (3, 0), "D": (1, 1), "A": (0, 3)}


def _f(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _int_or_none(v):
    x = _f(v)
    return int(x) if x is not None else None


def looks_like_html(text: str) -> bool:
    stripped = text.strip().lower()
    return stripped.startswith("<!doctype") or stripped.startswith("<html") or "<body" in stripped[:2000]


def sha256_of_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# =====================================================================
# 1 + 2. PROVENANCE AND DATA-ONLY AUDIT (no hypothesis-related figure
# computed anywhere in this function or the ones it calls)
# =====================================================================

def provenance_and_audit() -> dict:
    audit: dict = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "files": {}}

    reference_header = None
    ref_path = RAW_ROOT / "E0" / REFERENCE_SEASON_FOR_SCHEMA / "E0.csv"
    if ref_path.exists():
        with open(ref_path, encoding="latin1") as f:
            reference_header = next(csv.reader(f))

    for code in OOS_COMPETITIONS:
        path = RAW_ROOT / code / OOS_SEASON / f"{code}.csv"
        entry: dict = {"path": str(path.relative_to(REPO_ROOT)), "exists": path.exists()}
        if not path.exists():
            audit["files"][code] = entry
            continue

        raw_bytes = path.read_bytes()
        text = raw_bytes.decode("latin1")
        entry["byte_size"] = len(raw_bytes)
        entry["sha256"] = hashlib.sha256(raw_bytes).hexdigest()
        entry["acquisition_method"] = (
            "manual (Fraser, via curl -L in Terminal after a temporary football-data.co.uk "
            "server-side redirect bug to 127.0.0.1 was fixed on the site's own end; automated "
            "network access to football-data.co.uk was unavailable from every path this session "
            "could reach -- device shell, cloud container, and the built-in browser)"
        )
        entry["is_html_error_page"] = looks_like_html(text)

        rows = list(csv.DictReader(text.splitlines()))
        entry["row_count"] = len(rows)
        entry["column_count"] = len(rows[0]) if rows else 0
        header = text.splitlines()[0].split(",") if text.splitlines() else []
        entry["header_columns"] = header

        if reference_header is not None:
            missing_vs_reference = sorted(set(reference_header) - set(header))
            extra_vs_reference = sorted(set(header) - set(reference_header))
            entry["schema_drift_vs_2024_25"] = {
                "columns_missing_vs_2024_25": missing_vs_reference,
                "columns_added_vs_2024_25": extra_vs_reference,
                "drift_detected": bool(missing_vs_reference or extra_vs_reference),
            }

        dates = []
        seen_fixture_keys = set()
        duplicate_fixtures = []
        missing_critical = defaultdict(int)
        critical_fields = ["Date", "HomeTeam", "AwayTeam", "FTR", "AvgH", "AvgD", "AvgA", "HST", "AST"]
        for row in rows:
            for field in critical_fields:
                if not row.get(field):
                    missing_critical[field] += 1
            if row.get("Date") and row.get("HomeTeam") and row.get("AwayTeam"):
                try:
                    day, month, year = row["Date"].split("/")
                    dates.append(f"{year}-{month}-{day}")
                except ValueError:
                    pass
                key = (row["Date"], row["HomeTeam"], row["AwayTeam"])
                if key in seen_fixture_keys:
                    duplicate_fixtures.append(key)
                seen_fixture_keys.add(key)

        entry["earliest_match_date"] = min(dates) if dates else None
        entry["latest_match_date"] = max(dates) if dates else None
        entry["duplicate_fixture_count"] = len(duplicate_fixtures)
        entry["duplicate_fixtures"] = duplicate_fixtures[:10]  # sample only
        entry["missing_critical_field_counts"] = dict(missing_critical)
        entry["expected_full_season_matches"] = FULL_SEASON_EXPECTED_MATCHES[code]
        entry["appears_season_complete"] = entry["row_count"] >= FULL_SEASON_EXPECTED_MATCHES[code]
        entry["truncation_evidence"] = (
            None if entry["appears_season_complete"]
            else f"only {entry['row_count']} of {FULL_SEASON_EXPECTED_MATCHES[code]} expected matches present"
        )

        audit["files"][code] = entry

    audit["all_three_frozen_competitions_present"] = all(
        audit["files"].get(c, {}).get("exists") and audit["files"][c]["row_count"] > 0
        for c in OOS_COMPETITIONS
    )
    audit["any_schema_drift_detected"] = any(
        audit["files"][c].get("schema_drift_vs_2024_25", {}).get("drift_detected")
        for c in OOS_COMPETITIONS if c in audit["files"] and "schema_drift_vs_2024_25" in audit["files"][c]
    )
    audit["any_html_error_page_detected"] = any(
        audit["files"][c].get("is_html_error_page") for c in OOS_COMPETITIONS if c in audit["files"]
    )
    audit["all_seasons_appear_complete"] = all(
        audit["files"][c].get("appears_season_complete") for c in OOS_COMPETITIONS if c in audit["files"]
    )
    audit["note"] = (
        "This audit computes schema/quality/coverage facts ONLY. No win rate, SOT effect, "
        "subgroup profitability, or any H-FB2-002-related figure is computed in this function."
    )
    return audit


# =====================================================================
# 3. Canonicalisation -- exactly Cycle 1's own match/bookmaker/consensus
# logic, applied to the new 2025/26 files only.
# =====================================================================

def canonicalise_2025_26(alias_table: dict[str, str]) -> dict:
    processed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data_version = f"h_fb2_002_sealed_oos_2025_26_v1.0.0-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"

    match_rows, bookmaker_rows, consensus_rows, statistics_rows = [], [], [], []

    for code in OOS_COMPETITIONS:
        path = RAW_ROOT / code / OOS_SEASON / f"{code}.csv"
        with open(path, newline="", encoding="latin1") as f:
            rows = list(csv.DictReader(f))
        comp_info = normalise_competition_code(code)

        for row in rows:
            if not row.get("Date") or not row.get("HomeTeam"):
                continue
            try:
                day, month, year = row["Date"].split("/")
                match_date = f"{year}-{month}-{day}"
            except ValueError:
                continue

            home_raw, away_raw = row["HomeTeam"], row["AwayTeam"]
            home_norm = normalise_team_name(home_raw, alias_table)
            away_norm = normalise_team_name(away_raw, alias_table)
            match_id = build_match_id(code, OOS_SEASON, match_date, home_norm or home_raw, away_norm or away_raw)

            extraction = extract_bookmaker_triplets(row, bookmaker_prefixes=BOOKMAKER_PREFIXES_2025_26)
            opening_count = sum(1 for t in extraction.complete_triplets if t.price_timing == "opening")
            closing_count = sum(1 for t in extraction.complete_triplets if t.price_timing == "closing")

            for t in extraction.complete_triplets:
                raw = decimal_odds_list_to_implied_probabilities([t.home_odds, t.draw_odds, t.away_odds])
                fair = proportional_margin_removal(raw)
                bookmaker_rows.append({
                    "match_id": match_id, "bookmaker": t.bookmaker, "price_timing": t.price_timing,
                    "home_odds": t.home_odds, "draw_odds": t.draw_odds, "away_odds": t.away_odds,
                    "fair_home_probability": round(fair[0], 6), "fair_draw_probability": round(fair[1], 6),
                    "fair_away_probability": round(fair[2], 6), "processed_at": processed_at,
                    "data_version": data_version,
                })

            for timing in ("opening", "closing"):
                triplets = [t for t in extraction.complete_triplets if t.price_timing == timing]
                if len(triplets) < MIN_BOOKMAKERS_FOR_CONSENSUS:
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
                    "processed_at": processed_at, "data_version": data_version,
                })

            match_rows.append({
                "match_id": match_id, "competition_code": code,
                "competition_name": comp_info.canonical_name if comp_info else "",
                "season": OOS_SEASON, "match_date": match_date,
                "home_team_normalised": home_norm or home_raw, "away_team_normalised": away_norm or away_raw,
                "full_time_result": row.get("FTR", ""),
                "bookmaker_count_opening": opening_count, "bookmaker_count_closing": closing_count,
                "processed_at": processed_at, "data_version": data_version,
            })

            stats = extract_match_statistics(row)
            statistics_rows.append({
                "match_id": match_id,
                "home_shots": stats.home_shots, "away_shots": stats.away_shots,
                "home_shots_on_target": stats.home_shots_on_target, "away_shots_on_target": stats.away_shots_on_target,
                "home_corners": stats.home_corners, "away_corners": stats.away_corners,
                "home_yellow_cards": stats.home_yellow_cards, "away_yellow_cards": stats.away_yellow_cards,
                "home_red_cards": stats.home_red_cards, "away_red_cards": stats.away_red_cards,
                "full_time_home_goals": row.get("FTHG", ""), "full_time_away_goals": row.get("FTAG", ""),
            })

    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)
    def _write(name, rows):
        p = PROCESSED_ROOT / f"h_fb2_002_sealed_oos_2025_26_{name}.csv"
        if rows:
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
        return p

    _write("matches", match_rows)
    _write("bookmaker_markets", bookmaker_rows)
    _write("consensus", consensus_rows)
    _write("match_statistics", statistics_rows)

    return {
        "match_rows": match_rows,
        "consensus_rows": consensus_rows,
        "statistics_rows": statistics_rows,
        "data_version": data_version,
    }


# =====================================================================
# 4 + 5. Cross-season rolling SOT features -- combine the frozen
# 2020/21-2024/25 team histories with the new 2025/26 matches into ONE
# chronological replay, so 2025/26's first rolling snapshots legitimately
# inherit each team's 2024/25 tail history (no reset at the season
# boundary), exactly as the frozen feature semantics already require.
# =====================================================================

def _team_match_inputs_from_frozen_corpus() -> list[TeamMatchInput]:
    """Rebuild the exact same TeamMatchInput rows the frozen development
    feature build used (scripts/run_cycle_002_leakage_safe_features.py),
    reading only already-committed, untouched frozen files."""
    with open(PROCESSED_ROOT / "cycle_001_matches_full.csv", newline="", encoding="utf-8") as f:
        matches = list(csv.DictReader(f))
    with open(PROCESSED_ROOT / "cycle_002_match_statistics.csv", newline="", encoding="utf-8") as f:
        statistics = list(csv.DictReader(f))
    stats_by_id = {s["match_id"]: s for s in statistics}

    inputs: list[TeamMatchInput] = []
    for m in matches:
        ftr = m["full_time_result"]
        if ftr not in RESULT_POINTS:
            continue
        s = stats_by_id.get(m["match_id"])
        match_date = datetime.strptime(m["match_date"], "%Y-%m-%d").date()
        home_pts, away_pts = RESULT_POINTS[ftr]

        shots_home = _int_or_none(s["home_shots"]) if s else None
        shots_away = _int_or_none(s["away_shots"]) if s else None
        sot_home = _int_or_none(s["home_shots_on_target"]) if s else None
        sot_away = _int_or_none(s["away_shots_on_target"]) if s else None
        corners_home = _int_or_none(s["home_corners"]) if s else None
        corners_away = _int_or_none(s["away_corners"]) if s else None
        cards_home = cards_away = None
        if s:
            hy, hr = _int_or_none(s["home_yellow_cards"]), _int_or_none(s["home_red_cards"])
            ay, ar = _int_or_none(s["away_yellow_cards"]), _int_or_none(s["away_red_cards"])
            cards_home = (hy + hr) if (hy is not None and hr is not None) else None
            cards_away = (ay + ar) if (ay is not None and ar is not None) else None
        goals_home = _int_or_none(m.get("full_time_home_goals") or (s.get("full_time_home_goals") if s else None))
        goals_away = _int_or_none(m.get("full_time_away_goals") or (s.get("full_time_away_goals") if s else None))

        inputs.append(TeamMatchInput(
            match_id=m["match_id"], match_date=match_date, team=m["home_team_normalised"], is_home=True,
            goals_for=goals_home, goals_against=goals_away, shots_for=shots_home, shots_against=shots_away,
            shots_on_target_for=sot_home, shots_on_target_against=sot_away,
            corners_for=corners_home, corners_against=corners_away,
            cards_for=cards_home, cards_against=cards_away, result_points=home_pts,
        ))
        inputs.append(TeamMatchInput(
            match_id=m["match_id"], match_date=match_date, team=m["away_team_normalised"], is_home=False,
            goals_for=goals_away, goals_against=goals_home, shots_for=shots_away, shots_against=shots_home,
            shots_on_target_for=sot_away, shots_on_target_against=sot_home,
            corners_for=corners_away, corners_against=corners_home,
            cards_for=cards_away, cards_against=cards_home, result_points=away_pts,
        ))
    return inputs


def _team_match_inputs_from_2025_26(match_rows: list[dict], statistics_rows: list[dict]) -> list[TeamMatchInput]:
    stats_by_id = {s["match_id"]: s for s in statistics_rows}
    inputs: list[TeamMatchInput] = []
    for m in match_rows:
        ftr = m["full_time_result"]
        if ftr not in RESULT_POINTS:
            continue
        s = stats_by_id.get(m["match_id"])
        match_date = datetime.strptime(m["match_date"], "%Y-%m-%d").date()
        home_pts, away_pts = RESULT_POINTS[ftr]

        shots_home = _int_or_none(s["home_shots"]) if s else None
        shots_away = _int_or_none(s["away_shots"]) if s else None
        sot_home = _int_or_none(s["home_shots_on_target"]) if s else None
        sot_away = _int_or_none(s["away_shots_on_target"]) if s else None
        corners_home = _int_or_none(s["home_corners"]) if s else None
        corners_away = _int_or_none(s["away_corners"]) if s else None
        cards_home = cards_away = None
        if s:
            hy, hr = _int_or_none(s["home_yellow_cards"]), _int_or_none(s["home_red_cards"])
            ay, ar = _int_or_none(s["away_yellow_cards"]), _int_or_none(s["away_red_cards"])
            cards_home = (hy + hr) if (hy is not None and hr is not None) else None
            cards_away = (ay + ar) if (ay is not None and ar is not None) else None
        goals_home = _int_or_none(s["full_time_home_goals"]) if s else None
        goals_away = _int_or_none(s["full_time_away_goals"]) if s else None

        inputs.append(TeamMatchInput(
            match_id=m["match_id"], match_date=match_date, team=m["home_team_normalised"], is_home=True,
            goals_for=goals_home, goals_against=goals_away, shots_for=shots_home, shots_against=shots_away,
            shots_on_target_for=sot_home, shots_on_target_against=sot_away,
            corners_for=corners_home, corners_against=corners_away,
            cards_for=cards_home, cards_against=cards_away, result_points=home_pts,
        ))
        inputs.append(TeamMatchInput(
            match_id=m["match_id"], match_date=match_date, team=m["away_team_normalised"], is_home=False,
            goals_for=goals_away, goals_against=goals_home, shots_for=shots_away, shots_against=shots_home,
            shots_on_target_for=sot_away, shots_on_target_against=sot_home,
            corners_for=corners_away, corners_against=corners_home,
            cards_for=cards_away, cards_against=cards_home, result_points=away_pts,
        ))
    return inputs


def build_cross_season_sot_last10(match_rows_2025_26: list[dict], statistics_rows_2025_26: list[dict]) -> dict:
    """Returns {match_id: {"home_sot_last10": float|None, "away_sot_last10": float|None}}
    for the 2025/26 matches, computed from a SINGLE chronological replay
    spanning 2020/21-2025/26 combined -- team histories are NOT reset at
    the season boundary."""
    frozen_inputs = _team_match_inputs_from_frozen_corpus()
    new_inputs = _team_match_inputs_from_2025_26(match_rows_2025_26, statistics_rows_2025_26)
    combined = frozen_inputs + new_inputs

    features = compute_rolling_features(combined, windows=(10,))
    by_match_team = {(feat.match_id, feat.team): feat for feat in features}

    new_match_ids = {m["match_id"] for m in match_rows_2025_26}
    out: dict = {}
    for m in match_rows_2025_26:
        mid = m["match_id"]
        home_feat = by_match_team.get((mid, m["home_team_normalised"]))
        away_feat = by_match_team.get((mid, m["away_team_normalised"]))
        out[mid] = {
            "home_sot_last10": home_feat.overall[10].avg_shots_on_target_for if home_feat else None,
            "away_sot_last10": away_feat.overall[10].avg_shots_on_target_for if away_feat else None,
            "home_appearance_number": home_feat.appearance_number if home_feat else None,
            "away_appearance_number": away_feat.appearance_number if away_feat else None,
        }
    assert new_match_ids == set(out.keys())
    return out


# =====================================================================
# 6. Freeze the eligible 2025/26 OOS sample.
# =====================================================================

def build_eligible_2025_26(match_rows, consensus_rows, sot_lookup) -> tuple[list[dict], dict]:
    consensus_opening = {c["match_id"]: c for c in consensus_rows if c["price_timing"] == "opening"}
    eligible = []
    exclusions = defaultdict(int)
    for m in match_rows:
        mid = m["match_id"]
        c = consensus_opening.get(mid)
        p = _f(c["median_fair_home_probability"]) if c else None
        sot = sot_lookup.get(mid, {})
        sot_h, sot_a = sot.get("home_sot_last10"), sot.get("away_sot_last10")

        if p is None:
            exclusions["missing_1x2_opening_consensus"] += 1
            continue
        if sot_h is None or sot_a is None:
            exclusions["missing_full_10_match_rolling_sot_history"] += 1
            continue
        if m["full_time_result"] not in RESULT_POINTS:
            exclusions["missing_or_invalid_full_time_result"] += 1
            continue

        eligible.append({
            "match_id": mid, "season": m["season"], "competition_code": m["competition_code"],
            "match_date": m["match_date"], "p": p, "sot_diff": sot_h - sot_a,
            "home_win": m["full_time_result"] == "H",
        })
    exclusion_summary = {
        "total_raw_matches": len(match_rows),
        "eligible_n": len(eligible),
        "excluded_n": len(match_rows) - len(eligible),
        "exclusions_by_reason": dict(exclusions),
    }
    return eligible, exclusion_summary


# =====================================================================
# 7. Primary test -- reused UNCHANGED from
# scripts/run_h_fb2_002_development_test.py (top_price_band,
# median_split_diff), recomputed on the 2025/26 sample per protocol
# section 9.
# =====================================================================

def top_price_band(eligible: list[dict], n_bands: int, top_index: int) -> list[dict]:
    ordered = sorted(eligible, key=lambda r: r["p"])
    n = len(ordered)
    band_size = n // n_bands
    start = top_index * band_size
    end = (top_index + 1) * band_size if top_index < n_bands - 1 else n
    return ordered[start:end]


def median_split_diff(group: list[dict]) -> dict:
    if len(group) < 4:
        return {"n": len(group), "status": "insufficient_n_for_split"}
    ordered = sorted(group, key=lambda r: r["sot_diff"])
    half = len(ordered) // 2
    low, high = ordered[:half], ordered[half:]
    ci = bootstrap_ci_mean_diff(
        [1.0 if r["home_win"] else 0.0 for r in high],
        [1.0 if r["home_win"] else 0.0 for r in low],
    )
    return {
        "n": len(group),
        "high_sot_diff_home_win_rate": sum(1.0 if r["home_win"] else 0.0 for r in high) / len(high),
        "low_sot_diff_home_win_rate": sum(1.0 if r["home_win"] else 0.0 for r in low) / len(low),
        "diff_high_minus_low": ci["point_estimate"],
        "ci_95": [ci["ci_lower"], ci["ci_upper"]],
    }


def main() -> int:
    print("=" * 70)
    print("PHASE A -- PROVENANCE AND DATA-ONLY AUDIT (before any hypothesis analysis)")
    print("=" * 70)
    audit = provenance_and_audit()
    print(json.dumps({k: v for k, v in audit.items() if k != "files"}, indent=2))
    for code, entry in audit["files"].items():
        print(f"-- {code}: n={entry.get('row_count')}, dates={entry.get('earliest_match_date')}..{entry.get('latest_match_date')}, "
              f"complete={entry.get('appears_season_complete')}, duplicates={entry.get('duplicate_fixture_count')}, "
              f"drift={entry.get('schema_drift_vs_2024_25', {}).get('drift_detected')}")

    if audit["any_html_error_page_detected"]:
        print("CRITICAL: an HTML error page was detected instead of CSV content -- ABORTING before any further step.")
        return 1

    audit_path = PROCESSED_ROOT / "h_fb2_002_sealed_oos_2025_26_data_audit.json"
    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Audit written to {audit_path}")

    print("\n" + "=" * 70)
    print("PHASE B -- CANONICALISATION (new 2025/26 files only; no frozen file touched)")
    print("=" * 70)
    alias_table = load_alias_table()
    canon = canonicalise_2025_26(alias_table)
    print(f"canonicalised {len(canon['match_rows'])} matches, {len(canon['consensus_rows'])} consensus rows")

    print("\n" + "=" * 70)
    print("PHASE C -- CROSS-SEASON ROLLING SOT FEATURES (2020/21-2025/26 combined replay)")
    print("=" * 70)
    sot_lookup = build_cross_season_sot_last10(canon["match_rows"], canon["statistics_rows"])
    n_with_full_history = sum(
        1 for v in sot_lookup.values() if v["home_sot_last10"] is not None and v["away_sot_last10"] is not None
    )
    print(f"2025/26 matches with full 10-match SOT rolling history on both sides: {n_with_full_history}/{len(sot_lookup)}")

    print("\n" + "=" * 70)
    print("PHASE D -- FREEZE ELIGIBLE OOS SAMPLE")
    print("=" * 70)
    eligible, exclusion_summary = build_eligible_2025_26(canon["match_rows"], canon["consensus_rows"], sot_lookup)
    eligible_by_comp = defaultdict(int)
    for r in eligible:
        eligible_by_comp[r["competition_code"]] += 1
    exclusion_summary["eligible_n_by_competition"] = dict(eligible_by_comp)
    fingerprint = hashlib.sha256(
        "|".join(sorted(r["match_id"] for r in eligible)).encode("utf-8")
    ).hexdigest()
    exclusion_summary["eligible_dataset_fingerprint_sha256"] = fingerprint
    print(json.dumps(exclusion_summary, indent=2))

    print("\n" + "=" * 70)
    print("PHASE E -- PRIMARY TEST (run exactly once; recorded before any diagnostic)")
    print("=" * 70)
    quintile4 = top_price_band(eligible, n_bands=5, top_index=4)
    primary = median_split_diff(quintile4)
    print(json.dumps({"primary_price_quintile_4": primary, "quintile4_n": len(quintile4)}, indent=2))

    print("\n" + "=" * 70)
    print("PHASE F -- SECONDARY DIAGNOSTICS (recorded only after the primary result above)")
    print("=" * 70)
    results: dict = {
        "audit_summary": {k: v for k, v in audit.items() if k != "files"},
        "provenance": audit["files"],
        "exclusion_summary": exclusion_summary,
        "primary_price_quintile_4": primary,
        "quintile4_n": len(quintile4),
    }

    ps = [r["p"] for r in quintile4]
    results["favourite_price_distribution_quintile_4"] = {
        "min": min(ps) if ps else None, "max": max(ps) if ps else None,
        "mean": (sum(ps) / len(ps)) if ps else None,
    }

    comp_out = {}
    for comp in OOS_COMPETITIONS:
        group = [r for r in quintile4 if r["competition_code"] == comp]
        comp_out[comp] = median_split_diff(group)
    results["competition_breakdown_price_quintile_4_DIAGNOSTIC_NOT_PRIMARY_EVIDENCE"] = comp_out

    residuals = [(1.0 if r["home_win"] else 0.0) - r["p"] for r in quintile4]
    sot_diffs = [r["sot_diff"] for r in quintile4]
    results["continuous_correlation_diagnostic_DIAGNOSTIC_NOT_PRIMARY_EVIDENCE"] = {
        "n": len(quintile4),
        "pearson_r": pearson_correlation(sot_diffs, residuals) if len(quintile4) >= 2 else None,
        "development_reference_pearson_r": 0.02117,
    }

    dated = sorted(quintile4, key=lambda r: r["match_date"])
    half = len(dated) // 2
    results["within_season_time_slice_diagnostic_DIAGNOSTIC_NOT_PRIMARY_EVIDENCE"] = {
        "first_half_of_season": median_split_diff(dated[:half]),
        "second_half_of_season": median_split_diff(dated[half:]),
    }

    print(json.dumps({k: v for k, v in results.items() if k not in ("provenance",)}, indent=2, default=str))

    print("\n" + "=" * 70)
    print("PHASE G -- MECHANICAL VERDICT")
    print("=" * 70)
    competitions_present = frozenset(
        c for c in OOS_COMPETITIONS if audit["files"].get(c, {}).get("row_count", 0) > 0
    )
    ci_lower, ci_upper = primary.get("ci_95", [None, None])
    if ci_lower is None:
        verdict = {"verdict": "FAIL", "reason": "primary test could not be computed (insufficient sample for a split)"}
    else:
        verdict_input = SealedOOSVerdictInput(
            ci_lower=ci_lower, ci_upper=ci_upper, point_estimate=primary["diff_high_minus_low"],
            n_top_quintile=primary["n"], competitions_present=competitions_present, min_n=MIN_SUBGROUP_N,
        )
        verdict_result = classify_sealed_oos_result(verdict_input)
        verdict = {"verdict": verdict_result.verdict, "reason": verdict_result.reason}
    results["verdict"] = verdict
    print(json.dumps(verdict, indent=2))

    out_path = PROCESSED_ROOT / "h_fb2_002_sealed_oos_2025_26_results.json"
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\nFull results written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
