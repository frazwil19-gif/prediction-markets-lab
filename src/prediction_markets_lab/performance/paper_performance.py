"""Automated paper-bet (Track B) performance reporting (Section 8,
Production Infrastructure Build, 2026-09-20).

Builds the single machine-readable "reports/latest_performance.json"
output the operator's instruction calls for: "Create machine-readable
outputs that ChatGPT can consume without recalculating the underlying
statistics." Reuses existing, already-tested modules rather than
reimplementing them: performance.calibration.compute_calibration_bins
(KEEP -- generic binary calibration, not outcome-specific despite living
alongside the 3-way research modules), performance.roi.roi_fraction and
performance.drawdown (both filled in this same build, Section 3/8),
performance.paper_bet_metrics (binary Brier/log loss, ADDED this build
because the existing performance.brier/log_loss modules score a full
3-outcome vector for research model validation, not a single graded
selection -- see that module's docstring), and performance.odds_bands.

Only SETTLED bets contribute to win-rate/Brier/log-loss/calibration
(there is no "outcome" yet for a pending bet); void bets are excluded
from those same metrics (neither a win nor a loss) but their stake and
zero pnl are still included in exposure/P&L/ROI totals, matching
standard betting-performance convention.
"""

from __future__ import annotations

from prediction_markets_lab.performance.calibration import compute_calibration_bins
from prediction_markets_lab.performance.drawdown import compute_drawdown, longest_losing_streak
from prediction_markets_lab.performance.odds_bands import ODDS_BANDS, band_for_odds
from prediction_markets_lab.performance.paper_bet_metrics import (
    mean_binary_brier_score,
    mean_binary_log_loss,
)
from prediction_markets_lab.performance.roi import roi_fraction

_DECIDED_RESULTS = {"won", "lost"}


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _summarise(rows: list[dict]) -> dict:
    """Compute every required metric (Section 8) for one bucket of settled bets."""
    settled = [r for r in rows if r.get("status") == "settled"]
    decided = [r for r in settled if r.get("result") in _DECIDED_RESULTS]

    n_bets = len(settled)
    n_decided = len(decided)
    wins = sum(1 for r in decided if r["result"] == "won")
    win_rate = (wins / n_decided) if n_decided else None
    expected_win_rate = (
        sum(_to_float(r["estimated_probability"]) for r in decided) / n_decided if n_decided else None
    )
    average_odds = sum(_to_float(r["quoted_odds"]) for r in settled) / n_bets if n_bets else None
    total_staked = sum(_to_float(r["recommended_stake"]) for r in settled)
    total_pnl = sum(_to_float(r["actual_pnl"]) for r in settled)
    roi = roi_fraction(total_staked, total_pnl)

    predicted = [_to_float(r["estimated_probability"]) for r in decided]
    outcomes = [r["result"] == "won" for r in decided]
    brier = mean_binary_brier_score(predicted, outcomes)
    log_loss = mean_binary_log_loss(predicted, outcomes)

    calibration = None
    if n_decided >= 10:
        n_bins = min(5, n_decided // 5) or 1
        bins = compute_calibration_bins(predicted, outcomes, n_bins=n_bins)
        calibration = [
            {
                "n": b.n,
                "mean_predicted_probability": b.mean_predicted_probability,
                "observed_frequency": b.observed_frequency,
            }
            for b in bins
        ]

    pnl_sequence = [_to_float(r["actual_pnl"]) for r in settled]
    drawdown_report = compute_drawdown(0.0, pnl_sequence) if pnl_sequence else None
    streak = longest_losing_streak([r["result"] for r in settled])

    return {
        "bet_count": n_bets,
        "decided_count": n_decided,
        "win_rate": win_rate,
        "expected_win_rate": expected_win_rate,
        "average_odds": average_odds,
        "total_staked_gbp": round(total_staked, 2),
        "total_pnl_gbp": round(total_pnl, 2),
        "roi_yield": roi,
        "brier_score": brier,
        "log_loss": log_loss,
        "calibration_bins": calibration,
        "max_drawdown_gbp": drawdown_report.max_drawdown_gbp if drawdown_report else 0.0,
        "longest_losing_streak": streak,
        "clv_note": (
            "not yet populated -- closing_odds_if_available is currently blank on live rows; "
            "see docs/HISTORICAL_PRICE_AND_CLV_LIMITATIONS.md"
        ),
    }


def _group_by(rows: list[dict], key: str) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row.get(key, ""), []).append(row)
    return groups


def build_performance_report(paper_bets: list[dict], starting_bankroll_gbp: float) -> dict:
    """Build the full latest_performance.json contract for the paper ledger.

    Args:
        paper_bets: Every row of paper_ledger/paper_bets.csv (as returned
            by storage.paper_ledger.load_paper_bets) -- all statuses, this
            function does its own settled/pending filtering.
        starting_bankroll_gbp: config/bankroll.yaml's starting_bankroll_gbp.

    Returns:
        A JSON-serialisable dict: overall summary plus breakdowns by
        grade/sport/competition/market/odds-band (Section 8's required
        breakdowns; probability-band is covered by the calibration bins
        already, so is not separately re-bucketed here to avoid a
        redundant, harder-to-reconcile second slicing of the same data).
    """
    settled = [r for r in paper_bets if r.get("status") == "settled"]
    pending_count = sum(1 for r in paper_bets if r.get("status") == "pending")

    by_odds_band: dict[str, list[dict]] = {label: [] for label, _, _ in ODDS_BANDS}
    for row in settled:
        by_odds_band[band_for_odds(_to_float(row["quoted_odds"]))].append(row)

    paper_bankroll_gbp = starting_bankroll_gbp
    if settled:
        with_bankroll = [r for r in settled if r.get("paper_bankroll_after_settlement")]
        if with_bankroll:
            paper_bankroll_gbp = _to_float(
                with_bankroll[-1]["paper_bankroll_after_settlement"], starting_bankroll_gbp
            )

    return {
        "starting_bankroll_gbp": starting_bankroll_gbp,
        "current_paper_bankroll_gbp": round(paper_bankroll_gbp, 2),
        "pending_bet_count": pending_count,
        "overall": _summarise(settled),
        "by_grade": {k: _summarise(v) for k, v in sorted(_group_by(settled, "grade").items())},
        "by_sport": {k: _summarise(v) for k, v in sorted(_group_by(settled, "sport").items())},
        "by_competition": {k: _summarise(v) for k, v in sorted(_group_by(settled, "competition").items())},
        "by_market": {k: _summarise(v) for k, v in sorted(_group_by(settled, "market").items())},
        "by_odds_band": {k: _summarise(v) for k, v in by_odds_band.items() if v},
    }
