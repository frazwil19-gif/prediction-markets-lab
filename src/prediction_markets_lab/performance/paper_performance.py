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

2026-09-22 addition (TARGETED PRODUCTION CHANGE -- DAILY MONEY WINDOW +
MONEY/PAPER SEPARATION instruction, Section 12): every top-level key this
module has always returned (overall/by_grade/by_sport/by_competition/
by_market/by_odds_band/pending_bet_count/current_paper_bankroll_gbp)
keeps its EXACT existing meaning, unchanged -- the broad "paper research"
universe: every A+/A/B graded candidate ever recorded to the ledger,
whether or not it later passed real-money qualification. This is
deliberate backward compatibility, not an oversight. A NEW sibling key,
`money_strategy`, mirrors the same overall/by_grade/by_sport/
by_competition/by_market/by_odds_band/pending_bet_count shape but is
computed ONLY over rows where storage.paper_ledger.PaperBet.
money_qualified is true -- the actual, selective real-money strategy's
own forward performance. The two are never combined or averaged
together anywhere in this module: "Need to know 'how would the actual
money strategy have performed?' separately from 'how did the broader
research candidate universe perform?'"
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


def _is_money_qualified(row: dict) -> bool:
    """Truthy-string-tolerant read of the ledger's money_qualified column.

    storage.paper_ledger writes bool fields through csv.DictWriter, which
    stringifies True/False -- and an older row recorded before this
    column existed reads back as "" (see storage/paper_ledger.py's
    money_qualified field comment). Both "" and "False" (any case) are
    treated as not money-qualified; nothing here ever guesses a row INTO
    the money strategy that was not explicitly recorded as such.
    """
    return str(row.get("money_qualified", "")).strip().lower() in {"true", "1", "yes"}


def _breakdown(rows: list[dict]) -> dict:
    """Build the overall/by_grade/.../by_odds_band breakdown shared by
    both the broad paper-research report and the narrower money-strategy
    report -- kept as one function so the two are computed identically
    and never drift apart in method, only in which rows feed them."""
    by_odds_band: dict[str, list[dict]] = {label: [] for label, _, _ in ODDS_BANDS}
    for row in rows:
        by_odds_band[band_for_odds(_to_float(row["quoted_odds"]))].append(row)

    return {
        "overall": _summarise(rows),
        "by_grade": {k: _summarise(v) for k, v in sorted(_group_by(rows, "grade").items())},
        "by_sport": {k: _summarise(v) for k, v in sorted(_group_by(rows, "sport").items())},
        "by_competition": {k: _summarise(v) for k, v in sorted(_group_by(rows, "competition").items())},
        "by_market": {k: _summarise(v) for k, v in sorted(_group_by(rows, "market").items())},
        "by_odds_band": {k: _summarise(v) for k, v in by_odds_band.items() if v},
    }


def build_performance_report(paper_bets: list[dict], starting_bankroll_gbp: float) -> dict:
    """Build the full latest_performance.json contract for the paper ledger.

    Args:
        paper_bets: Every row of paper_ledger/paper_bets.csv (as returned
            by storage.paper_ledger.load_paper_bets) -- all statuses, this
            function does its own settled/pending filtering.
        starting_bankroll_gbp: config/bankroll.yaml's starting_bankroll_gbp.

    Returns:
        A JSON-serialisable dict: the broad paper-research breakdown at
        the top level (unchanged shape/meaning -- see module docstring),
        plus a `money_strategy` key with the identical breakdown shape
        computed only over money-qualified rows.
    """
    settled = [r for r in paper_bets if r.get("status") == "settled"]
    pending_count = sum(1 for r in paper_bets if r.get("status") == "pending")

    money_bets = [r for r in paper_bets if _is_money_qualified(r)]
    money_settled = [r for r in money_bets if r.get("status") == "settled"]
    money_pending_count = sum(1 for r in money_bets if r.get("status") == "pending")

    paper_bankroll_gbp = starting_bankroll_gbp
    if settled:
        with_bankroll = [r for r in settled if r.get("paper_bankroll_after_settlement")]
        if with_bankroll:
            paper_bankroll_gbp = _to_float(
                with_bankroll[-1]["paper_bankroll_after_settlement"], starting_bankroll_gbp
            )

    report = {
        "starting_bankroll_gbp": starting_bankroll_gbp,
        "current_paper_bankroll_gbp": round(paper_bankroll_gbp, 2),
        "pending_bet_count": pending_count,
        "paper_universe_note": (
            "overall/by_grade/by_sport/by_competition/by_market/by_odds_band above cover the "
            "BROAD paper-research candidate universe -- every A+/A/B graded candidate recorded "
            "to the ledger, whether or not it passed real-money qualification. See "
            "money_strategy below for the narrower, selective real-money strategy's own "
            "forward performance; the two are never mixed together in any calculation here."
        ),
    }
    report.update(_breakdown(settled))
    report["money_strategy"] = {
        "pending_bet_count": money_pending_count,
        **_breakdown(money_settled),
    }
    return report
