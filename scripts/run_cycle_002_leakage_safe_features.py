"""Football Cycle 2 -- leakage-safe pre-match discovery feature build
(operator's step D, Football Cycle 2 direction-change execution plan,
2026-09-16).

Reads ONLY already-built Cycle 1 (frozen, untouched) and Cycle 2
(this cycle's own richer extraction, step C) processed files. Fetches
nothing, modifies nothing upstream. Writes exactly one new file:
cycle_002_discovery_features.csv -- one row per match, every column
either (a) a strictly-pre-match feature, safe by construction, or (b)
explicitly prefixed `outcome_` and never to be used as a model input,
kept only so the later discovery step (F) can join predictions against
what actually happened.

Three feature families, combined here:
  1. Elo ratings -- reuses `models/football_elo.py`'s
     `simulate_pre_match_ratings` UNCHANGED. Pre-match ratings do not
     depend on draw_margin (see that module's docstring), so no
     calibration/fitting happens here at all -- this is a pure,
     deterministic replay of already-tested, already-frozen logic.
  2. Rolling team-form features -- `features/football_leakage_safe_features.py`
     (built and leakage-tested in this same step), windows of 5 and 10
     matches, in three splits (overall / home-context / away-context).
  3. Market-derived fields -- Cycle 1's own 1X2 consensus
     (cycle_001_consensus_full.csv, unmodified) plus this cycle's new
     Over/Under 2.5 and Asian Handicap market-context files (step C).
     Both opening and closing snapshots are pre-kickoff information in
     this data source (see football_richer_extraction.py's module
     docstring) so neither needs lagging -- only match STATISTICS
     (goals/shots/etc, family 2 above) do.

Global Elo state is shared across all three competitions (matches
promotion/relegation between E0 and E1 competitions in reality; SC0
teams never meet E0/E1 teams so simply never interact in the shared
rating dict -- no special-casing needed, exactly as football_elo.py's
own docstring anticipates).
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from prediction_markets_lab.features.football_leakage_safe_features import (
    TeamMatchInput,
    compute_rolling_features,
)
from prediction_markets_lab.models.football_elo import (
    EloConfig,
    EloMatchInput,
    simulate_pre_match_ratings,
    three_way_probabilities,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_ROOT = REPO_ROOT / "data" / "processed" / "football"

ROLLING_WINDOWS = (5, 10)
RESULT_POINTS = {"H": (3, 0), "D": (1, 1), "A": (0, 3)}  # (home_points, away_points)


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _float_or_none(v: object) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _int_or_none(v: object) -> int | None:
    f = _float_or_none(v)
    return int(f) if f is not None else None


def run() -> int:
    matches = _read_csv(PROCESSED_ROOT / "cycle_001_matches_full.csv")
    statistics = _read_csv(PROCESSED_ROOT / "cycle_002_match_statistics.csv")
    consensus_1x2 = _read_csv(PROCESSED_ROOT / "cycle_001_consensus_full.csv")
    context_ou25 = _read_csv(PROCESSED_ROOT / "cycle_002_market_context_ou25.csv")
    context_ah = _read_csv(PROCESSED_ROOT / "cycle_002_market_context_ah.csv")

    processed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data_version = f"cycle_002_features_v1.0.0-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"

    match_by_id = {m["match_id"]: m for m in matches}
    stats_by_id = {s["match_id"]: s for s in statistics}

    # ---------- 1. Elo: pre-match ratings for every match, one global replay ----------
    elo_inputs = [
        EloMatchInput(
            match_id=m["match_id"],
            season=m["season"],
            match_date=_parse_date(m["match_date"]),
            home_team=m["home_team_normalised"],
            away_team=m["away_team_normalised"],
            full_time_result=m["full_time_result"],
        )
        for m in matches
        if m["full_time_result"] in ("H", "D", "A")
    ]
    elo_inputs_sorted = sorted(elo_inputs, key=lambda e: (e.match_date, e.match_id))
    elo_simulated = simulate_pre_match_ratings(elo_inputs_sorted, EloConfig())
    elo_by_match_id: dict[str, tuple[float, float]] = {
        m.match_id: (pre_home, pre_away) for m, pre_home, pre_away in elo_simulated
    }

    # ---------- 2. Rolling team-form features ----------
    team_match_inputs: list[TeamMatchInput] = []
    for m in matches:
        mid = m["match_id"]
        s = stats_by_id.get(mid)
        ftr = m["full_time_result"]
        if ftr not in RESULT_POINTS:
            continue
        home_pts, away_pts = RESULT_POINTS[ftr]
        match_date = _parse_date(m["match_date"])
        goals_home = _int_or_none(m.get("full_time_home_goals") or (s or {}).get("full_time_home_goals"))
        goals_away = _int_or_none(m.get("full_time_away_goals") or (s or {}).get("full_time_away_goals"))

        shots_home = _int_or_none(s["home_shots"]) if s else None
        shots_away = _int_or_none(s["away_shots"]) if s else None
        sot_home = _int_or_none(s["home_shots_on_target"]) if s else None
        sot_away = _int_or_none(s["away_shots_on_target"]) if s else None
        corners_home = _int_or_none(s["home_corners"]) if s else None
        corners_away = _int_or_none(s["away_corners"]) if s else None
        cards_home = None
        cards_away = None
        if s:
            hy, hr = _int_or_none(s["home_yellow_cards"]), _int_or_none(s["home_red_cards"])
            ay, ar = _int_or_none(s["away_yellow_cards"]), _int_or_none(s["away_red_cards"])
            cards_home = (hy + hr) if (hy is not None and hr is not None) else None
            cards_away = (ay + ar) if (ay is not None and ar is not None) else None

        team_match_inputs.append(TeamMatchInput(
            match_id=mid, match_date=match_date, team=m["home_team_normalised"], is_home=True,
            goals_for=goals_home, goals_against=goals_away,
            shots_for=shots_home, shots_against=shots_away,
            shots_on_target_for=sot_home, shots_on_target_against=sot_away,
            corners_for=corners_home, corners_against=corners_away,
            cards_for=cards_home, cards_against=cards_away,
            result_points=home_pts,
        ))
        team_match_inputs.append(TeamMatchInput(
            match_id=mid, match_date=match_date, team=m["away_team_normalised"], is_home=False,
            goals_for=goals_away, goals_against=goals_home,
            shots_for=shots_away, shots_against=shots_home,
            shots_on_target_for=sot_away, shots_on_target_against=sot_home,
            corners_for=corners_away, corners_against=corners_home,
            cards_for=cards_away, cards_against=cards_home,
            result_points=away_pts,
        ))

    rolling = compute_rolling_features(team_match_inputs, windows=ROLLING_WINDOWS)
    rolling_by_match_team: dict[tuple[str, str], object] = {(r.match_id, r.team): r for r in rolling}

    # ---------- 3. Market-derived fields ----------
    # 1X2: pivot cycle_001's own consensus (unmodified) into opening/closing fair probs.
    consensus_1x2_by_match: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in consensus_1x2:
        consensus_1x2_by_match[row["match_id"]][row["price_timing"]] = row

    ou25_by_match: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in context_ou25:
        ou25_by_match[row["match_id"]][row["price_timing"]] = row

    ah_by_match: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in context_ah:
        ah_by_match[row["match_id"]][row["price_timing"]] = row

    # ---------- Assemble one wide row per match ----------
    output_rows: list[dict] = []
    default_config = EloConfig()

    def _snap_fields(prefix: str, snap) -> dict:
        return {
            f"{prefix}_matches_in_window": snap.matches_in_window,
            f"{prefix}_avg_goals_for": snap.avg_goals_for,
            f"{prefix}_avg_goals_against": snap.avg_goals_against,
            f"{prefix}_avg_shots_for": snap.avg_shots_for,
            f"{prefix}_avg_shots_against": snap.avg_shots_against,
            f"{prefix}_avg_sot_for": snap.avg_shots_on_target_for,
            f"{prefix}_avg_sot_against": snap.avg_shots_on_target_against,
            f"{prefix}_avg_corners_for": snap.avg_corners_for,
            f"{prefix}_avg_corners_against": snap.avg_corners_against,
            f"{prefix}_avg_cards_for": snap.avg_cards_for,
            f"{prefix}_avg_cards_against": snap.avg_cards_against,
            f"{prefix}_conversion_rate": snap.conversion_rate,
            f"{prefix}_points_per_game": snap.points_per_game,
            f"{prefix}_goal_diff_volatility": snap.goal_difference_volatility,
        }

    for m in matches:
        mid = m["match_id"]
        ftr = m["full_time_result"]
        home_team = m["home_team_normalised"]
        away_team = m["away_team_normalised"]
        s = stats_by_id.get(mid)  # cycle_002_match_statistics.csv row (has goals; cycle_001 does not)

        row: dict = {
            "match_id": mid,
            "competition_code": m["competition_code"],
            "season": m["season"],
            "match_date": m["match_date"],
            "home_team": home_team,
            "away_team": away_team,
        }

        # --- Elo (pre-match ratings; three-way prob is a descriptive baseline, not a fitted prediction) ---
        if mid in elo_by_match_id:
            pre_home, pre_away = elo_by_match_id[mid]
            probs = three_way_probabilities(pre_home, pre_away, default_config.home_advantage, default_config.draw_margin)
            row.update({
                "elo_pre_match_home_rating": round(pre_home, 4),
                "elo_pre_match_away_rating": round(pre_away, 4),
                "elo_rating_gap_incl_home_advantage": round((pre_home + default_config.home_advantage) - pre_away, 4),
                "elo_baseline_home_win_probability": round(probs["home"], 6),
                "elo_baseline_draw_probability": round(probs["draw"], 6),
                "elo_baseline_away_win_probability": round(probs["away"], 6),
            })
        else:
            row.update({k: None for k in (
                "elo_pre_match_home_rating", "elo_pre_match_away_rating", "elo_rating_gap_incl_home_advantage",
                "elo_baseline_home_win_probability", "elo_baseline_draw_probability", "elo_baseline_away_win_probability",
            )})

        # --- Rolling team-form (home team + away team, each window, each split) ---
        home_feat = rolling_by_match_team.get((mid, home_team))
        away_feat = rolling_by_match_team.get((mid, away_team))
        for w in ROLLING_WINDOWS:
            if home_feat:
                row.update(_snap_fields(f"home_team_overall_last{w}", home_feat.overall[w]))
                row.update(_snap_fields(f"home_team_homecontext_last{w}", home_feat.home_context[w]))
                row["home_team_appearance_number"] = home_feat.appearance_number
            if away_feat:
                row.update(_snap_fields(f"away_team_overall_last{w}", away_feat.overall[w]))
                row.update(_snap_fields(f"away_team_awaycontext_last{w}", away_feat.away_context[w]))
                row["away_team_appearance_number"] = away_feat.appearance_number

        # Relative-strength differentials (overall split only, to keep column count sane).
        for w in ROLLING_WINDOWS:
            if home_feat and away_feat:
                h, a = home_feat.overall[w], away_feat.overall[w]
                if h.avg_goals_for is not None and a.avg_goals_for is not None:
                    row[f"diff_avg_goals_for_last{w}"] = round(h.avg_goals_for - a.avg_goals_for, 4)
                if h.avg_shots_for is not None and a.avg_shots_for is not None:
                    row[f"diff_avg_shots_for_last{w}"] = round(h.avg_shots_for - a.avg_shots_for, 4)
                if h.points_per_game is not None and a.points_per_game is not None:
                    row[f"diff_points_per_game_last{w}"] = round(h.points_per_game - a.points_per_game, 4)

        # --- Market-derived: 1X2 (Cycle 1's own consensus, unmodified) ---
        for timing in ("opening", "closing"):
            c = consensus_1x2_by_match.get(mid, {}).get(timing)
            prefix = f"market_1x2_{timing}"
            if c:
                row[f"{prefix}_home_probability"] = _float_or_none(c["median_fair_home_probability"])
                row[f"{prefix}_draw_probability"] = _float_or_none(c["median_fair_draw_probability"])
                row[f"{prefix}_away_probability"] = _float_or_none(c["median_fair_away_probability"])
                row[f"{prefix}_bookmaker_count"] = _int_or_none(c["bookmaker_count"])
            else:
                row[f"{prefix}_home_probability"] = None
                row[f"{prefix}_draw_probability"] = None
                row[f"{prefix}_away_probability"] = None
                row[f"{prefix}_bookmaker_count"] = None

        # --- Market-derived: Over/Under 2.5 (this cycle's source-avg fair probabilities) ---
        for timing in ("opening", "closing"):
            c = ou25_by_match.get(mid, {}).get(timing)
            prefix = f"market_ou25_{timing}"
            row[f"{prefix}_source_avg_over_probability"] = _float_or_none(c["source_avg_fair_over_2_5_probability"]) if c else None
            row[f"{prefix}_source_avg_under_probability"] = _float_or_none(c["source_avg_fair_under_2_5_probability"]) if c else None
            row[f"{prefix}_individual_bookmaker_count"] = _int_or_none(c["individual_bookmaker_count"]) if c else None

        # --- Market-derived: Asian Handicap (this cycle's source-avg fair probabilities + line) ---
        for timing in ("opening", "closing"):
            c = ah_by_match.get(mid, {}).get(timing)
            prefix = f"market_ah_{timing}"
            row[f"{prefix}_line"] = _float_or_none(c["line"]) if c else None
            row[f"{prefix}_source_avg_home_probability"] = _float_or_none(c["source_avg_fair_home_ah_probability"]) if c else None
            row[f"{prefix}_source_avg_away_probability"] = _float_or_none(c["source_avg_fair_away_ah_probability"]) if c else None
            row[f"{prefix}_individual_bookmaker_count"] = _int_or_none(c["individual_bookmaker_count"]) if c else None

        # --- Convenience dominance/movement fields (all inputs already pre-match) ---
        open_home_p = row.get("market_1x2_opening_home_probability")
        open_away_p = row.get("market_1x2_opening_away_probability")
        close_home_p = row.get("market_1x2_closing_home_probability")
        if open_home_p is not None and open_away_p is not None:
            row["market_favourite_side_opening"] = "home" if open_home_p > open_away_p else "away"
            row["market_favourite_probability_opening"] = max(open_home_p, open_away_p)
        else:
            row["market_favourite_side_opening"] = None
            row["market_favourite_probability_opening"] = None
        if open_home_p is not None and close_home_p is not None:
            row["market_1x2_home_movement_close_minus_open"] = round(close_home_p - open_home_p, 6)
        else:
            row["market_1x2_home_movement_close_minus_open"] = None
        if row.get("elo_baseline_home_win_probability") is not None and open_home_p is not None:
            row["elo_vs_market_1x2_home_gap_opening"] = round(row["elo_baseline_home_win_probability"] - open_home_p, 6)
        else:
            row["elo_vs_market_1x2_home_gap_opening"] = None

        # --- Outcome fields (NEVER a feature -- kept only for later scoring) ---
        # cycle_001_matches_full.csv does not carry goal counts (FTR only);
        # cycle_002_match_statistics.csv does -- fall back to it.
        row["outcome_full_time_result"] = ftr
        row["outcome_full_time_home_goals"] = m.get("full_time_home_goals") or (s.get("full_time_home_goals") if s else None)
        row["outcome_full_time_away_goals"] = m.get("full_time_away_goals") or (s.get("full_time_away_goals") if s else None)

        row["processed_at"] = processed_at
        row["data_version"] = data_version

        output_rows.append(row)

    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_ROOT / "cycle_002_discovery_features.csv"
    if output_rows:
        # Not every row necessarily populates every conditional column
        # (e.g. relative-strength diffs, or a team's very first-ever
        # appearance lacking rolling context) -- take the union of keys
        # across ALL rows, in first-seen order, so every column exists
        # uniformly and a genuinely absent value is written as blank
        # (None), never silently dropped as a missing CSV column.
        fieldnames: list[str] = []
        seen = set()
        for r in output_rows:
            for k in r:
                if k not in seen:
                    seen.add(k)
                    fieldnames.append(k)
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, restval=None)
            writer.writeheader()
            writer.writerows(output_rows)

    n_full_rolling_10 = sum(
        1 for r in output_rows
        if (r.get("home_team_overall_last10_matches_in_window") == 10
            and r.get("away_team_overall_last10_matches_in_window") == 10)
    )
    n_with_ou25_opening = sum(1 for r in output_rows if r.get("market_ou25_opening_source_avg_over_probability") is not None)
    n_with_ah_opening = sum(1 for r in output_rows if r.get("market_ah_opening_source_avg_home_probability") is not None)

    summary = {
        "data_version": data_version,
        "created_at": processed_at,
        "total_match_rows": len(output_rows),
        "columns": len(output_rows[0]) if output_rows else 0,
        "rows_with_full_10_match_rolling_history_both_teams": n_full_rolling_10,
        "rows_with_ou25_opening_market_data": n_with_ou25_opening,
        "rows_with_ah_opening_market_data": n_with_ah_opening,
        "note": (
            "Every column is either a strictly pre-match feature or is "
            "prefixed outcome_ (never to be used as a model input). "
            "Match-statistics-derived rolling features are lagged by "
            "construction (see features/football_leakage_safe_features.py); "
            "market opening/closing fields are not lagged because both "
            "snapshots already precede kickoff in this data source."
        ),
    }
    (PROCESSED_ROOT / "cycle_002_discovery_features_version.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
