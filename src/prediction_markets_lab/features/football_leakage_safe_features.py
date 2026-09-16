"""Leakage-safe pre-match feature engineering for Football Cycle 2
discovery (operator's step D, per the Football Cycle 2 direction-change
execution plan, 2026-09-16).

Hard rule this entire module exists to enforce: a feature attached to
match M may use only information that was knowable strictly BEFORE M
kicked off. Match statistics (shots, SOT, corners, cards -- everything
in `football_richer_extraction.MatchStatistics`) are produced BY a
match, so they may never be used as a same-match feature; they may
only be folded into a team's rolling history and used for that team's
LATER matches. Every rolling computation below follows the same
get-snapshot-before-push discipline already used and tested in
`models/football_elo.py`'s `simulate_pre_match_ratings` (query the
team's current rolling state first, record it as the pre-match
feature, and only afterwards push this match's own stats into that
team's history) -- so a match's own outcome can never contaminate its
own features, and a later match's result can never reach backwards
into an earlier snapshot. `tests/unit/test_football_leakage_safe_features.py`
checks this mechanically (perturbing a match's own/later stats and
asserting earlier snapshots are byte-identical), per the operator's
explicit instruction that leakage safety be checked, not just asserted.

Market-derived fields (pre-match consensus/opening/closing prices) do
NOT need this lag: both the opening and closing snapshots in this data
source are themselves collected before kickoff (see
football_richer_extraction.py's module docstring), so they are already
legitimate pre-match information and are passed through as-is.
"""

from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TeamMatchInput:
    """One team's perspective of one match, chronologically orderable.

    Every *_for/*_against/points field is Optional -- carried straight
    through from a source that may have missing values (see
    football_richer_extraction.MatchStatistics) and never imputed here
    either.
    """

    match_id: str
    match_date: date
    team: str
    is_home: bool
    goals_for: int | None
    goals_against: int | None
    shots_for: int | None
    shots_against: int | None
    shots_on_target_for: int | None
    shots_on_target_against: int | None
    corners_for: int | None
    corners_against: int | None
    cards_for: int | None
    cards_against: int | None
    result_points: int | None  # 3 win / 1 draw / 0 loss, from `team`'s perspective


@dataclass(frozen=True)
class RollingSnapshot:
    """A team's rolling aggregate over its own most recent (<= window)
    matches, STRICTLY BEFORE the match this snapshot is attached to.

    matches_in_window records the actual count used (<= window); every
    average field is None (never 0 or an imputed value) when there is
    no history yet (matches_in_window == 0) or when every value in the
    window for that specific field was itself missing.
    """

    matches_in_window: int
    avg_goals_for: float | None
    avg_goals_against: float | None
    avg_shots_for: float | None
    avg_shots_against: float | None
    avg_shots_on_target_for: float | None
    avg_shots_on_target_against: float | None
    avg_corners_for: float | None
    avg_corners_against: float | None
    avg_cards_for: float | None
    avg_cards_against: float | None
    conversion_rate: float | None  # avg_goals_for / avg_shots_for
    points_per_game: float | None
    goal_difference_volatility: float | None  # population stdev of (goals_for - goals_against); None if < 2 usable matches


_EMPTY_SNAPSHOT = RollingSnapshot(
    matches_in_window=0,
    avg_goals_for=None, avg_goals_against=None,
    avg_shots_for=None, avg_shots_against=None,
    avg_shots_on_target_for=None, avg_shots_on_target_against=None,
    avg_corners_for=None, avg_corners_against=None,
    avg_cards_for=None, avg_cards_against=None,
    conversion_rate=None, points_per_game=None, goal_difference_volatility=None,
)


class _TeamRollingWindow:
    """Mutable, order-dependent rolling state for ONE team, ONE window
    size, ONE split (overall / home-context / away-context).

    Callers MUST call snapshot() to read the pre-match state BEFORE
    calling push() with that same match -- this ordering is what makes
    every feature leakage-safe. This class does not enforce the
    ordering itself (it has no notion of "which match" -- the caller
    drives it); `compute_rolling_features` below is the leakage-safe
    driver and is what tests exercise.
    """

    def __init__(self, window: int):
        if window < 1:
            raise ValueError(f"window must be >= 1, got {window}")
        self.window = window
        self._history: deque[TeamMatchInput] = deque(maxlen=window)

    def snapshot(self) -> RollingSnapshot:
        if not self._history:
            return _EMPTY_SNAPSHOT

        def _avg(attr: str) -> float | None:
            vals = [v for m in self._history if (v := getattr(m, attr)) is not None]
            return sum(vals) / len(vals) if vals else None

        avg_gf = _avg("goals_for")
        avg_ga = _avg("goals_against")
        avg_sf = _avg("shots_for")
        avg_sa = _avg("shots_against")
        avg_sotf = _avg("shots_on_target_for")
        avg_sota = _avg("shots_on_target_against")
        avg_cf = _avg("corners_for")
        avg_ca = _avg("corners_against")
        avg_cdf = _avg("cards_for")
        avg_cda = _avg("cards_against")

        conversion_rate = (avg_gf / avg_sf) if (avg_gf is not None and avg_sf) else None

        pts_vals = [m.result_points for m in self._history if m.result_points is not None]
        points_per_game = sum(pts_vals) / len(pts_vals) if pts_vals else None

        diffs = [
            m.goals_for - m.goals_against
            for m in self._history
            if m.goals_for is not None and m.goals_against is not None
        ]
        volatility = statistics.pstdev(diffs) if len(diffs) >= 2 else None

        return RollingSnapshot(
            matches_in_window=len(self._history),
            avg_goals_for=avg_gf, avg_goals_against=avg_ga,
            avg_shots_for=avg_sf, avg_shots_against=avg_sa,
            avg_shots_on_target_for=avg_sotf, avg_shots_on_target_against=avg_sota,
            avg_corners_for=avg_cf, avg_corners_against=avg_ca,
            avg_cards_for=avg_cdf, avg_cards_against=avg_cda,
            conversion_rate=conversion_rate, points_per_game=points_per_game,
            goal_difference_volatility=volatility,
        )

    def push(self, m: TeamMatchInput) -> None:
        self._history.append(m)


@dataclass(frozen=True)
class TeamMatchFeatures:
    """Everything computed for one (match_id, team) pair -- one team's
    half of one match's pre-match feature row, across every requested
    window and split, plus this team's cumulative appearance count
    (for downstream minimum-sample-size filtering)."""

    match_id: str
    team: str
    is_home: bool
    appearance_number: int  # 1-based count of this team's matches to date, INCLUDING this one
    overall: dict[int, RollingSnapshot]  # window -> snapshot, computed over ALL prior matches
    home_context: dict[int, RollingSnapshot]  # window -> snapshot, computed over prior HOME matches only
    away_context: dict[int, RollingSnapshot]  # window -> snapshot, computed over prior AWAY matches only


def compute_rolling_features(
    team_matches: list[TeamMatchInput], windows: tuple[int, ...] = (5, 10)
) -> list[TeamMatchFeatures]:
    """Compute leakage-safe rolling features for every (match, team) row.

    Args:
        team_matches: ALL team-perspective rows for every match in the
            dataset (two rows per canonical match: one per team). Does
            NOT need to be pre-sorted; this function sorts internally,
            per team, by (match_date, match_id).
        windows: Rolling window sizes to compute (e.g. last 5, last
            10 matches).

    Returns:
        One TeamMatchFeatures per input row (same length), each
        carrying that team's pre-match rolling snapshot as of its
        match_date -- built from strictly earlier matches only.
    """
    by_team: dict[str, list[TeamMatchInput]] = {}
    for tm in team_matches:
        by_team.setdefault(tm.team, []).append(tm)

    results: dict[tuple[str, str], TeamMatchFeatures] = {}

    for team, matches in by_team.items():
        ordered = sorted(matches, key=lambda m: (m.match_date, m.match_id))

        overall_windows = {w: _TeamRollingWindow(w) for w in windows}
        home_windows = {w: _TeamRollingWindow(w) for w in windows}
        away_windows = {w: _TeamRollingWindow(w) for w in windows}

        for i, m in enumerate(ordered, start=1):
            # Snapshot FIRST (pre-match state), push AFTER -- this
            # ordering is the entire leakage-safety guarantee.
            overall_snap = {w: rw.snapshot() for w, rw in overall_windows.items()}
            home_snap = {w: rw.snapshot() for w, rw in home_windows.items()}
            away_snap = {w: rw.snapshot() for w, rw in away_windows.items()}

            results[(m.match_id, team)] = TeamMatchFeatures(
                match_id=m.match_id,
                team=team,
                is_home=m.is_home,
                appearance_number=i,
                overall=overall_snap,
                home_context=home_snap,
                away_context=away_snap,
            )

            for rw in overall_windows.values():
                rw.push(m)
            if m.is_home:
                for rw in home_windows.values():
                    rw.push(m)
            else:
                for rw in away_windows.values():
                    rw.push(m)

    # Return in the same order as the input for predictable output.
    return [results[(tm.match_id, tm.team)] for tm in team_matches]
