"""Build and write the full frozen-V1 backtest report set for one ReplayRun.

Reuses, rather than duplicates, this project's existing performance
metrics modules: performance.binary_classification (log loss, Brier,
calibration bins + intercept/slope, AUC), performance.drawdown,
performance.roi, performance.odds_bands. New functionality only where
none already existed: probability-band bucketing (this project only had
odds bands before) and single-series bootstrap CIs (backtesting.metrics).

Output layout, per the governing "BACKTEST PHASE 1" instruction, Section
10: backtests/<strategy_name>/<run_id>/{manifest.json, bets.csv,
predictions.csv, performance.json, calibration.csv, bankroll.csv,
report.md}.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from prediction_markets_lab.backtesting.frozen_strategy import frozen_strategy_to_dict
from prediction_markets_lab.backtesting.metrics import bootstrap_mean_ci, bootstrap_ratio_ci
from prediction_markets_lab.backtesting.replay import BacktestCandidate, ReplayRun
from prediction_markets_lab.performance.binary_classification import (
    binary_auc,
    binary_brier_score,
    binary_calibration_bins,
    binary_log_loss,
    expected_calibration_error,
    fit_calibration_intercept_slope,
)
from prediction_markets_lab.performance.drawdown import compute_drawdown, longest_losing_streak
from prediction_markets_lab.performance.odds_bands import band_for_odds
from prediction_markets_lab.performance.roi import roi_fraction

PROBABILITY_BANDS: tuple[tuple[str, float, float], ...] = (
    ("<50%", 0.0, 0.50),
    ("50-54.9%", 0.50, 0.55),
    ("55-59.9%", 0.55, 0.60),
    ("60-64.9%", 0.60, 0.65),
    ("65-69.9%", 0.65, 0.70),
    ("70-79.9%", 0.70, 0.80),
    ("80%+", 0.80, 1.0000001),
)


def probability_band_for(p: float) -> str:
    for label, low, high in PROBABILITY_BANDS:
        if low <= p < high:
            return label
    return PROBABILITY_BANDS[-1][0]


def _probability_quality_block(candidates: list[BacktestCandidate]) -> dict:
    if not candidates:
        return {"n": 0, "note": "no candidates in this population"}
    probs = [c.consensus_probability for c in candidates]
    actuals = [1 if c.actual_won else 0 for c in candidates]
    block: dict = {
        "n": len(candidates),
        "mean_estimated_probability": sum(probs) / len(probs),
        "actual_outcome_rate": sum(actuals) / len(actuals),
        "brier_score": binary_brier_score(probs, actuals),
        "log_loss": binary_log_loss(probs, actuals),
    }
    n_bins = min(10, len(candidates))
    if n_bins >= 2:
        bins = binary_calibration_bins(probs, actuals, n_bins=n_bins)
        block["calibration_bins"] = [{**asdict(b), "gap": b.gap} for b in bins]
        block["expected_calibration_error"] = expected_calibration_error(bins)
        try:
            intercept, slope = fit_calibration_intercept_slope(probs, actuals)
            block["calibration_intercept"] = intercept
            block["calibration_slope"] = slope
        except ValueError as exc:
            block["calibration_intercept_slope_error"] = str(exc)
    if len(set(actuals)) == 2:
        block["auc"] = binary_auc(probs, actuals)
    else:
        block["auc"] = None
        block["auc_note"] = "AUC undefined -- only one outcome class present in this population"
    return block


def _betting_performance_block(staked: list[BacktestCandidate], starting_bankroll_gbp: float) -> dict:
    if not staked:
        return {"n_bets": 0, "note": "no money-qualified bets were placed in this run"}

    stakes = [c.staked_gbp for c in staked]
    net_changes = [c.net_change_gbp for c in staked]
    odds = [c.decimal_odds for c in staked]
    wins = [c for c in staked if c.actual_won]
    losses = [c for c in staked if not c.actual_won]
    results_seq = ["won" if c.actual_won else "lost" for c in staked]

    total_staked = sum(stakes)
    total_profit = sum(net_changes)
    gross_returns = sum(c.staked_gbp * c.decimal_odds for c in wins)

    drawdown = compute_drawdown(starting_bankroll_gbp, net_changes)
    roi_ci = bootstrap_ratio_ci(net_changes, stakes, "roi")
    win_rate_ci = bootstrap_mean_ci([1.0 if c.actual_won else 0.0 for c in staked], "win_rate")

    return {
        "n_bets": len(staked),
        "n_won": len(wins),
        "n_lost": len(losses),
        "win_rate": len(wins) / len(staked),
        "win_rate_bootstrap_ci_95": [win_rate_ci.ci_lower, win_rate_ci.ci_upper],
        "expected_win_rate_mean_estimated_probability": sum(c.consensus_probability for c in staked) / len(staked),
        "avg_odds": sum(odds) / len(odds),
        "median_odds": sorted(odds)[len(odds) // 2],
        "total_staked_gbp": total_staked,
        "gross_returns_gbp": gross_returns,
        "net_profit_gbp": total_profit,
        "roi_fraction": roi_fraction(total_staked, total_profit),
        "roi_bootstrap_ci_95": [roi_ci.ci_lower, roi_ci.ci_upper],
        "avg_net_ev_at_placement": sum(c.net_ev for c in staked) / len(staked),
        "max_drawdown_gbp": drawdown.max_drawdown_gbp,
        "max_drawdown_pct": drawdown.max_drawdown_pct,
        "longest_losing_streak": longest_losing_streak(results_seq, loss_label="lost"),
        "largest_win_gbp": max((c.net_change_gbp for c in wins), default=0.0),
        "largest_loss_gbp": min((c.net_change_gbp for c in losses), default=0.0),
        "starting_bankroll_gbp": starting_bankroll_gbp,
        "ending_bankroll_gbp": staked[-1].bankroll_after_gbp,
        "clv": None,
        "clv_note": (
            "not available -- both the consensus and the best price are drawn from the same "
            "bookmaker closing snapshot; there is no independent exchange execution price to "
            "compare a closing line against (see docs/HISTORICAL_PRICE_AND_CLV_LIMITATIONS.md)."
        ),
    }


def _breakdown(candidates: list[BacktestCandidate], key_fn, staked_only: bool = False) -> dict:
    groups: dict[str, list[BacktestCandidate]] = {}
    for c in candidates:
        if staked_only and c.staked_gbp <= 0:
            continue
        groups.setdefault(key_fn(c), []).append(c)
    out = {}
    for key, group in sorted(groups.items()):
        out[key] = (
            _betting_performance_block(group, group[0].bankroll_after_gbp or 0.0)
            if staked_only
            else _probability_quality_block(group)
        )
    return out


def bankroll_simulation_at_alternate_starting_balances(
    staked: list[BacktestCandidate], balances: list[float]
) -> dict:
    """Analytically re-derive drawdown at alternate starting bankrolls.

    Valid because V1 uses FIXED per-grade stakes (risk/staking.py), not
    proportional/Kelly staking -- the pnl sequence itself does not depend
    on the starting bankroll, only the drawdown-as-percentage and how much
    headroom existed. Re-simulating from scratch at each balance would
    change nothing about which bets were placed or how much they won/lost.
    """
    net_changes = [c.net_change_gbp for c in staked]
    result = {}
    for balance in balances:
        dd = compute_drawdown(balance, net_changes)
        result[f"gbp_{int(balance)}"] = {
            "starting_bankroll_gbp": balance,
            "ending_balance_gbp": dd.ending_balance_gbp,
            "max_drawdown_gbp": dd.max_drawdown_gbp,
            "max_drawdown_pct": dd.max_drawdown_pct,
        }
    return result


def build_performance_report(run: ReplayRun) -> dict:
    all_candidates = run.candidates
    staked = [c for c in all_candidates if c.staked_gbp > 0]
    money_qualified = [c for c in all_candidates if c.money_qualified]

    report = {
        "proxy_disclosure": {
            "price_timing_used_for_both_sides_of_comparison": run.price_timing,
            "classification": "PROXY BACKTEST, not an exact replay of the live 07:00 UTC daily scan",
            "money_event_horizon_gate": (
                "trivially passes for every candidate with a known kickoff, by construction of this "
                "proxy's simulated scan timestamp (kickoff minus a fixed 60-minute offset) -- this run "
                "does NOT meaningfully exercise the 24h money-event-horizon gate. See "
                "research/backtesting/BACKTEST_DATA_FEASIBILITY_AUDIT.md section 5."
            ),
            "best_price_selection": (
                "best (highest) closing decimal odds among bookmakers accepted into that match's "
                "consensus -- an optimism risk relative to a real bettor checking a small number of "
                "bookmakers, not a leakage risk. See research/backtesting/LEAKAGE_AUDIT.md."
            ),
            "risk_gates_applied": run.apply_risk_gates,
            "risk_gates_disclosure": (
                "risk.decision_gates (exposure caps, daily/weekly loss stops) are tested production "
                "modules NOT currently wired into scripts/run_daily_scan.py's automated live path -- "
                "applied here regardless, per the master directive's 'no duplicate exposure' requirement."
            ),
        },
        "coverage": {
            "total_rows_in_source_matches_file": run.load_report.total_rows_in_matches_file,
            "excluded_ineligible_consensus_model": run.load_report.excluded_ineligible_consensus_model,
            "excluded_missing_complete_bookmaker_panel": run.load_report.excluded_missing_complete_bookmaker_panel,
            "excluded_kickoff_join_failed": run.load_report.excluded_kickoff_join_failed,
            "matches_included": run.load_report.included,
            "matches_excluded_during_replay": len(run.excluded_matches),
            "candidates_generated": len(all_candidates),
            "money_qualified_candidates": len(money_qualified),
            "candidates_actually_staked": len(staked),
            "bankroll_exhausted": run.bankroll_exhausted,
            "bankroll_exhausted_at_match_id": run.bankroll_exhausted_at_match_id,
        },
        "probability_quality": {
            "all_candidates": _probability_quality_block(all_candidates),
            "money_qualified_only": _probability_quality_block(money_qualified),
            "by_research_grade": _breakdown(all_candidates, lambda c: c.research_grade),
            "by_confidence": _breakdown(all_candidates, lambda c: c.confidence_label),
            "by_probability_band": _breakdown(all_candidates, lambda c: probability_band_for(c.consensus_probability)),
            "by_odds_band": _breakdown(all_candidates, lambda c: band_for_odds(c.decimal_odds)),
            "by_season": _breakdown(all_candidates, lambda c: c.season),
            "by_competition": _breakdown(all_candidates, lambda c: c.competition_code),
        },
        "betting_performance": {
            "overall": _betting_performance_block(staked, run.starting_bankroll_gbp),
            "by_odds_band": _breakdown(staked, lambda c: band_for_odds(c.decimal_odds), staked_only=True),
            "by_probability_band": _breakdown(
                staked, lambda c: probability_band_for(c.consensus_probability), staked_only=True
            ),
            "by_season": _breakdown(staked, lambda c: c.season, staked_only=True),
            "by_competition": _breakdown(staked, lambda c: c.competition_code, staked_only=True),
            "by_money_decision": _breakdown(all_candidates, lambda c: c.money_decision, staked_only=False),
        },
        "bankroll_simulation_alternate_starting_balances": bankroll_simulation_at_alternate_starting_balances(
            staked, [25.0, 50.0, 100.0, 250.0, 500.0, 1000.0]
        ),
    }
    return report


def build_manifest(run: ReplayRun, run_id: str, dataset_description: str) -> dict:
    return {
        "run_id": run_id,
        "strategy": frozen_strategy_to_dict(run.frozen_strategy),
        "dataset": dataset_description,
        "price_timing": run.price_timing,
        "apply_risk_gates": run.apply_risk_gates,
        "starting_bankroll_gbp": run.starting_bankroll_gbp,
        "ending_bankroll_gbp": run.ending_bankroll_gbp,
        "bankroll_exhausted": run.bankroll_exhausted,
        "excluded_matches": run.excluded_matches,
        "coverage": {
            "total_rows_in_source_matches_file": run.load_report.total_rows_in_matches_file,
            "excluded_ineligible_consensus_model": run.load_report.excluded_ineligible_consensus_model,
            "excluded_missing_complete_bookmaker_panel": run.load_report.excluded_missing_complete_bookmaker_panel,
            "excluded_kickoff_join_failed": run.load_report.excluded_kickoff_join_failed,
            "matches_included": run.load_report.included,
        },
    }


def _candidate_row(c: BacktestCandidate) -> dict:
    return {
        "match_id": c.match_id,
        "selection": c.selection,
        "event_date": c.event_date,
        "competition_code": c.competition_code,
        "season": c.season,
        "home_team": c.home_team,
        "away_team": c.away_team,
        "accepted_bookmaker_count": c.accepted_bookmaker_count,
        "consensus_probability": c.consensus_probability,
        "decimal_odds": c.decimal_odds,
        "venue": c.venue,
        "net_ev": c.net_ev,
        "probability_edge_pp": c.probability_edge_pp,
        "confidence_label": c.confidence_label,
        "data_quality_ok": c.data_quality_ok,
        "research_grade": c.research_grade,
        "money_decision": c.money_decision,
        "money_qualified": c.money_qualified,
        "money_rejection_reason": c.money_rejection_reason,
        "recommended_stake_gbp": c.recommended_stake_gbp,
        "actual_won": c.actual_won,
        "kickoff_iso": c.kickoff_iso,
        "scan_timestamp_iso": c.scan_timestamp_iso,
        "risk_gate_passed": c.risk_gate_passed,
        "risk_gate_reason": c.risk_gate_reason,
        "staked_gbp": c.staked_gbp,
        "net_change_gbp": c.net_change_gbp,
        "bankroll_after_gbp": c.bankroll_after_gbp,
    }



_CANDIDATE_ROW_FIELDS = [
    "match_id", "selection", "event_date", "competition_code", "season", "home_team", "away_team",
    "accepted_bookmaker_count", "consensus_probability", "decimal_odds", "venue", "net_ev",
    "probability_edge_pp", "confidence_label", "data_quality_ok", "research_grade", "money_decision",
    "money_qualified", "money_rejection_reason", "recommended_stake_gbp", "actual_won", "kickoff_iso",
    "scan_timestamp_iso", "risk_gate_passed", "risk_gate_reason", "staked_gbp", "net_change_gbp",
    "bankroll_after_gbp",
]


def write_backtest_outputs(run: ReplayRun, run_id: str, dataset_description: str, out_root: Path) -> dict[str, Path]:
    """Write the full output file set for one run under
    out_root/<strategy_name>/<run_id>/, per the governing instruction's
    Section 10 file layout. Returns a dict of {kind: path} written."""
    run_dir = out_root / run.frozen_strategy.strategy_name / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    written: dict[str, Path] = {}

    manifest = build_manifest(run, run_id, dataset_description)
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    written["manifest"] = manifest_path

    predictions_path = run_dir / "predictions.csv"
    rows = [_candidate_row(c) for c in run.candidates]
    with open(predictions_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CANDIDATE_ROW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    written["predictions"] = predictions_path

    staked = [c for c in run.candidates if c.staked_gbp > 0]
    bets_path = run_dir / "bets.csv"
    with open(bets_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CANDIDATE_ROW_FIELDS)
        writer.writeheader()
        if not staked:
            f.write("# no money-qualified bets were placed in this run -- see performance.json betting_performance.overall.note\n")
        else:
            writer.writerows(_candidate_row(c) for c in staked)
    written["bets"] = bets_path

    bankroll_path = run_dir / "bankroll.csv"
    with open(bankroll_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["match_id", "selection", "event_date", "staked_gbp", "net_change_gbp", "bankroll_after_gbp"])
        for c in staked:
            writer.writerow([c.match_id, c.selection, c.event_date, c.staked_gbp, c.net_change_gbp, c.bankroll_after_gbp])
    written["bankroll"] = bankroll_path

    performance = build_performance_report(run)
    performance_path = run_dir / "performance.json"
    performance_path.write_text(json.dumps(performance, indent=2, sort_keys=True))
    written["performance"] = performance_path

    calibration_path = run_dir / "calibration.csv"
    with open(calibration_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["bin_index", "n", "mean_predicted_probability", "observed_frequency", "gap"])
        all_block = performance["probability_quality"]["all_candidates"]
        for b in all_block.get("calibration_bins", []):
            writer.writerow([b["bin_index"], b["n"], b["mean_predicted_probability"], b["observed_frequency"], b["gap"]])
    written["calibration"] = calibration_path

    report_md = render_report_markdown(run, run_id, dataset_description, performance)
    report_path = run_dir / "report.md"
    report_path.write_text(report_md)
    written["report"] = report_path

    return written


def render_report_markdown(run: ReplayRun, run_id: str, dataset_description: str, performance: dict) -> str:
    cov = performance["coverage"]
    bp = performance["betting_performance"]["overall"]
    pq_all = performance["probability_quality"]["all_candidates"]
    pq_money = performance["probability_quality"]["money_qualified_only"]
    disclosure = performance["proxy_disclosure"]

    lines = [
        f"# Frozen-V1 Backtest Report — {run.frozen_strategy.strategy_name} / {run_id}",
        "",
        f"**Dataset:** {dataset_description}",
        f"**Config hash:** `{run.frozen_strategy.config_hash}`",
        f"**Price basis:** {run.price_timing} snapshot (both consensus and best price) — PROXY, not exact replay.",
        "",
        "## Proxy disclosure (read this before the numbers below)",
        "",
        f"- {disclosure['classification']}",
        f"- {disclosure['money_event_horizon_gate']}",
        f"- {disclosure['best_price_selection']}",
        f"- Risk gates applied: {disclosure['risk_gates_applied']}. {disclosure['risk_gates_disclosure']}",
        "",
        "## Coverage",
        "",
        f"- Source matches file rows: {cov['total_rows_in_source_matches_file']}",
        f"- Excluded (ineligible consensus model): {cov['excluded_ineligible_consensus_model']}",
        f"- Excluded (missing bookmaker panel): {cov['excluded_missing_complete_bookmaker_panel']}",
        f"- Excluded (kickoff join failed): {cov['excluded_kickoff_join_failed']}",
        f"- Matches included: {cov['matches_included']}",
        f"- Candidates generated (matches × 3 outcomes): {cov['candidates_generated']}",
        f"- Money-qualified candidates: {cov['money_qualified_candidates']}",
        f"- Candidates actually staked: {cov['candidates_actually_staked']}",
        f"- Bankroll exhausted during run: {cov['bankroll_exhausted']}",
        "",
        "## Probability quality — ALL graded candidates (research population)",
        "",
        f"- n = {pq_all.get('n')}",
        f"- Mean estimated probability: {pq_all.get('mean_estimated_probability')}",
        f"- Actual outcome rate: {pq_all.get('actual_outcome_rate')}",
        f"- Brier score: {pq_all.get('brier_score')}",
        f"- Log loss: {pq_all.get('log_loss')}",
        f"- Expected calibration error: {pq_all.get('expected_calibration_error')}",
        f"- Calibration intercept/slope: {pq_all.get('calibration_intercept')} / {pq_all.get('calibration_slope')}",
        f"- AUC: {pq_all.get('auc')}",
        "",
        "## Probability quality — MONEY-QUALIFIED candidates only",
        "",
        f"- n = {pq_money.get('n')}",
        f"- Mean estimated probability: {pq_money.get('mean_estimated_probability')}",
        f"- Actual outcome rate: {pq_money.get('actual_outcome_rate')}",
        f"- Brier score: {pq_money.get('brier_score')}",
        f"- Log loss: {pq_money.get('log_loss')}",
        "",
        "## Betting performance — money-qualified bets actually staked",
        "",
    ]
    if bp.get("n_bets", 0) == 0:
        lines.append("**NO MONEY-QUALIFIED BETS WERE PLACED IN THIS BACKTEST RUN.** This is a valid, honestly-reported result, not an error.")
    else:
        lines += [
            f"- Bets: {bp['n_bets']} (won {bp['n_won']}, lost {bp['n_lost']})",
            f"- Win rate: {bp['win_rate']:.1%} (95% bootstrap CI: {bp['win_rate_bootstrap_ci_95'][0]:.1%}–{bp['win_rate_bootstrap_ci_95'][1]:.1%})",
            f"- Expected win rate (mean estimated probability): {bp['expected_win_rate_mean_estimated_probability']:.1%}",
            f"- Total staked: £{bp['total_staked_gbp']:.2f}",
            f"- Net profit: £{bp['net_profit_gbp']:.2f}",
            f"- ROI/yield: {bp['roi_fraction']:.1%} (95% bootstrap CI: {bp['roi_bootstrap_ci_95'][0]:.1%}–{bp['roi_bootstrap_ci_95'][1]:.1%})",
            f"- Max drawdown: £{bp['max_drawdown_gbp']:.2f} ({bp['max_drawdown_pct']:.1%})",
            f"- Longest losing streak: {bp['longest_losing_streak']}",
            f"- Starting bankroll: £{bp['starting_bankroll_gbp']:.2f} -> Ending: £{bp['ending_bankroll_gbp']:.2f}",
            f"- CLV: {bp['clv']} — {bp['clv_note']}",
        ]
    lines += [
        "",
        "## Conservative audit checklist",
        "",
        "See research/backtesting/PHASE1_RESULTS_AUDIT.md for the full 30-point return checkpoint. "
        "This report does not, on its own, claim the strategy is 'validated' — a positive ROI figure "
        "above is not treated as proof of anything without the uncertainty and sample-size context "
        "in that document.",
    ]
    return "\n".join(lines)
