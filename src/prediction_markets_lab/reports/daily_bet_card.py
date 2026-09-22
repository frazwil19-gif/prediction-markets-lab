"""Daily Bet Card renderer -- V1 (2026-09-18) + JSON contract (2026-09-19).

Renders the phone-readable Daily Bet Card format specified by the
operator's "GO -- begin implementation of the Daily Probability Engine
V1" instruction: a header block (timestamp, bankroll, scan counts,
grade counts, total exposure), ranked selections with the requested
per-selection fields, an OPTIONAL MULTI section (V1 always reports "not
built" here -- see decisions.recommendation's module docstring; singles
are the default and multis are explicitly deprioritised), and a
REJECT/WATCH summary with system warnings.

2026-09-19 addition (the operator's "MAJOR NEXT PHASE" instruction,
Phase 5 -- "Standard Daily Bet Card contract"): build_daily_bet_card_contract
and write_daily_bet_card_outputs freeze a stable, machine-readable JSON
shape (plus CSV/Markdown siblings) that any interface -- ChatGPT included
-- can consume without reimplementing any of this project's probability/
EV/grading calculations. This is the CONTRACT the operator's design
calls for between the engine and any downstream consumer.

One field is deliberately left empty for now, not fabricated:
"current_context" (team news, injuries, and similar situational factors)
has no automated source in this project yet -- decisions.grading's
no_material_info_risk stays a human-owned gate, not an automated signal.
Populating current_context with anything else would misrepresent what
the engine actually knows.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from prediction_markets_lab.decisions.recommendation import RecommendationResult

_GRADE_ORDER = {"A+": 0, "A": 1, "B": 2, "C": 3, "Reject": 4}

# Bumped whenever the probability/grading/staking methodology changes in a
# way that would make an old Daily Card's numbers non-comparable to a new
# one. NOT a code/package version -- see model_version on each candidate.
ENGINE_VERSION = "daily-engine-v1.1.0-odds-api"


@dataclass(frozen=True)
class DailyBetCardContext:
    """Header-level context for a Daily Bet Card."""

    generated_at: datetime
    bankroll_gbp: float
    fixtures_scanned: int
    markets_scanned: int


def _rank_key(rec: RecommendationResult) -> tuple[int, float]:
    grade = rec.market_record.grade
    return (_GRADE_ORDER.get(grade, 99), -rec.market_record.net_ev)


def _fair_odds(probability: float) -> float:
    return float("inf") if probability <= 0 else 1.0 / probability


def _potential_profit_gbp(stake_gbp: float, decimal_odds: float) -> float:
    return stake_gbp * (decimal_odds - 1.0)


def render_daily_bet_card(
    context: DailyBetCardContext,
    recommendations: list[RecommendationResult],
    system_warnings: list[str] | None = None,
) -> str:
    """Render the full Daily Bet Card as plain text/Markdown.

    Args:
        context: Header-level scan/bankroll context.
        recommendations: Every graded candidate from today's scan (all
            grades, not just A+/A/B) -- the reject/watch summary is
            derived from this same list, so nothing is silently dropped.
        system_warnings: Any operational warnings to surface (e.g.
            "N bookmakers rejected for an incomplete outcome set",
            "using illustrative/synthetic odds -- see run notes").

    Returns:
        The complete Daily Bet Card as a string.
    """
    ranked = sorted(recommendations, key=_rank_key)
    actionable = [r for r in ranked if r.market_record.grade in ("A+", "A", "B")]
    rejected_or_watch = [r for r in ranked if r.market_record.grade in ("C", "Reject")]
    total_exposure = sum(r.stake_gbp for r in ranked)
    grade_counts = {g: 0 for g in ("A+", "A", "B", "C", "Reject")}
    for r in ranked:
        grade_counts[r.market_record.grade] = grade_counts.get(r.market_record.grade, 0) + 1

    lines: list[str] = []
    lines.append("DAILY BET CARD")
    lines.append(f"Timestamp: {context.generated_at.isoformat(timespec='minutes')}")
    lines.append(f"Bankroll: £{context.bankroll_gbp:.2f}")
    lines.append(f"Fixtures scanned: {context.fixtures_scanned}")
    lines.append(f"Markets scanned: {context.markets_scanned}")
    lines.append(f"Candidates analysed: {len(ranked)}")
    lines.append(
        f"A+/A/B selections: {grade_counts['A+'] + grade_counts['A'] + grade_counts['B']}"
    )
    lines.append(f"Total recommended exposure: £{total_exposure:.2f}")
    lines.append("")

    lines.append("RANKED SELECTIONS")
    if not actionable:
        lines.append("(none -- no candidate cleared Grade B or better today. This is a valid,")
        lines.append(" expected outcome; thresholds are never loosened to manufacture a bet.)")
    for i, rec in enumerate(actionable, start=1):
        m = rec.market_record
        fair_odds = _fair_odds(m.final_probability if m.final_probability is not None else m.consensus_probability)
        potential_profit = _potential_profit_gbp(rec.stake_gbp, m.exchange_odds)
        lines.append(f"{i}. [{m.grade}] {m.selection} -- {m.event} ({m.market_type})")
        lines.append(f"   Odds: {m.exchange_odds:.2f} ({m.exchange})")
        lines.append(
            f"   Estimated P: {m.consensus_probability:.1%}   Fair odds: {fair_odds:.2f}"
        )
        lines.append(f"   Confidence: {m.confidence_score}   Net EV: {m.net_ev:+.1%}")
        lines.append(f"   Stake: £{rec.stake_gbp:.2f}   Potential profit: £{potential_profit:.2f}")
        lines.append(f"   Rationale: {m.decision}")
    lines.append("")

    lines.append("OPTIONAL MULTI")
    lines.append(
        "Not built in V1 -- singles only. A multi engine (independent-leg qualification, "
        "correlation/dependency check, joint-probability estimation) is explicitly "
        "deprioritised behind a working singles pipeline; see "
        "docs/DAILY_ENGINE_V1_LOCK_AND_IMPLEMENTATION_ROADMAP.md."
    )
    lines.append("")

    lines.append("REJECT / WATCH SUMMARY")
    lines.append(
        f"Watch (Grade C): {grade_counts['C']}   Reject: {grade_counts['Reject']}"
    )
    for rec in rejected_or_watch:
        m = rec.market_record
        lines.append(f"- [{m.grade}] {m.selection} ({m.event}, {m.market_type}): {m.decision}")
    if system_warnings:
        lines.append("")
        lines.append("System warnings:")
        for warning in system_warnings:
            lines.append(f"- {warning}")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# JSON contract (2026-09-19) -- the frozen schema shared with any consumer
# ---------------------------------------------------------------------------

# Column order for card.csv -- kept explicit (not dict-key order) so the
# contract does not silently reorder if a candidate dict is built
# differently in a future change.
_CSV_FIELDS = [
    "date",
    "sport",
    "competition",
    "event",
    "market",
    "selection",
    "bookmaker",
    "available_odds",
    "estimated_probability",
    "fair_odds",
    "confidence",
    "uncertainty",
    "historical_statistical_support",
    "current_context",
    "expected_payout",
    "ev_value_indicator",
    "risk",
    "recommended_stake",
    "grade",
    "reason",
    "model_version",
    "price_timestamp",
    # --- Added 2026-09-22 (TARGETED PRODUCTION CHANGE -- DAILY MONEY
    # WINDOW + MONEY/PAPER SEPARATION). Appended at the end so column
    # POSITION for every existing field above is unchanged for any
    # consumer reading card.csv positionally; every consumer should read
    # by header name regardless. `grade` above is unchanged and remains
    # the research classification -- `research_grade` is that same value
    # named explicitly, per the instruction. See
    # decisions/money_qualification.py.
    "research_grade",
    "money_decision",
    "money_qualified",
    "money_rejection_reason",
    "kickoff_time",
]


def _candidate_contract_row(rec: RecommendationResult, engine_version: str) -> dict:
    m = rec.market_record
    probability = m.final_probability if m.final_probability is not None else m.consensus_probability
    return {
        "date": m.event_date,
        "sport": m.sport,
        "competition": m.competition,
        "event": m.event,
        "market": m.market_type,
        "selection": m.selection,
        "bookmaker": m.exchange,
        "available_odds": m.exchange_odds,
        "estimated_probability": probability,
        "fair_odds": _fair_odds(probability),
        "confidence": m.confidence_score,
        "uncertainty": m.consensus_std,
        # Crude, honest proxy: how many independent bookmakers backed this
        # consensus. Not a model sample size (there is no fitted model for
        # V1's consensus-based markets) -- see the module docstring.
        "historical_statistical_support": m.bookmaker_count,
        # Deliberately empty -- see module docstring. No automated context
        # source exists yet; this is a schema placeholder, not a guess.
        "current_context": "",
        "expected_payout": _potential_profit_gbp(rec.stake_gbp, m.exchange_odds),
        "ev_value_indicator": m.net_ev,
        "risk": m.liquidity_score,
        "recommended_stake": rec.stake_gbp,
        "grade": m.grade,
        "reason": m.decision,
        "model_version": engine_version,
        "price_timestamp": m.scan_timestamp,
        # --- Added 2026-09-22 -- see _CSV_FIELDS comment above.
        "research_grade": m.research_grade or m.grade,
        "money_decision": m.money_decision,
        "money_qualified": m.money_qualified,
        "money_rejection_reason": m.money_rejection_reason,
        "kickoff_time": m.kickoff_time,
    }


def build_daily_bet_card_contract(
    context: DailyBetCardContext,
    recommendations: list[RecommendationResult],
    system_warnings: list[str] | None = None,
    engine_version: str = ENGINE_VERSION,
    data_timestamp: str | None = None,
) -> dict:
    """Build the frozen, machine-readable Daily Bet Card contract.

    This is the CONTRACT between the engine and any downstream consumer
    (ChatGPT, a future dashboard, a phone notification) -- see the
    module docstring. Consumers should read this structure rather than
    recomputing probability/EV/grading themselves.

    Args:
        context: Header-level scan/bankroll context.
        recommendations: Every graded candidate from today's scan.
        system_warnings: Any operational warnings to surface.
        engine_version: Tag identifying the probability/grading/staking
            methodology version that produced this card.
        data_timestamp: When the underlying odds data was fetched/entered
            (may differ from context.generated_at, the scan run time).
            Defaults to context.generated_at if not given.

    Returns:
        A JSON-serialisable dict with every field listed in the
        operator's Phase 5 schema: card-level fields (bankroll, scan
        counts, grade counts, total exposure, optional_multi, engine
        version, timestamps) plus a `candidates` list with every
        per-candidate field the instruction specified.
    """
    ranked = sorted(recommendations, key=_rank_key)
    grade_counts = {g: 0 for g in ("A+", "A", "B", "C", "Reject")}
    for r in ranked:
        grade_counts[r.market_record.grade] = grade_counts.get(r.market_record.grade, 0) + 1
    total_exposure = sum(r.stake_gbp for r in ranked)

    return {
        "run_timestamp": context.generated_at.isoformat(),
        "data_timestamp": data_timestamp or context.generated_at.isoformat(),
        "engine_version": engine_version,
        "bankroll_gbp": context.bankroll_gbp,
        "fixtures_scanned": context.fixtures_scanned,
        "markets_scanned": context.markets_scanned,
        "candidates_analysed": len(ranked),
        "grade_counts": grade_counts,
        "recommended_total_exposure_gbp": total_exposure,
        # Not built in V1 -- see decisions.recommendation's module
        # docstring. Always null until a multi engine exists; never a
        # fabricated/empty-but-present multi.
        "optional_multi": None,
        "candidates": [_candidate_contract_row(r, engine_version) for r in ranked],
        "system_warnings": list(system_warnings or []),
    }


def write_daily_bet_card_outputs(
    directory: Path,
    contract: dict,
    markdown_text: str,
) -> dict[str, Path]:
    """Write the frozen card.json / card.csv / card.md trio to `directory`.

    Args:
        directory: Output directory (created if missing) -- the operator's
            suggested layout is daily_cards/YYYY-MM-DD/ at the repo root,
            deliberately NOT under data/ or reports/daily/, both of which
            are gitignored, so a scheduled GitHub Actions run can commit
            these outputs.
        contract: The dict from build_daily_bet_card_contract.
        markdown_text: The human-readable card, from render_daily_bet_card.

    Returns:
        {"json": <path>, "csv": <path>, "md": <path>}.
    """
    directory.mkdir(parents=True, exist_ok=True)

    json_path = directory / "card.json"
    json_path.write_text(json.dumps(contract, indent=2, sort_keys=False) + "\n")

    csv_path = directory / "card.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for candidate in contract["candidates"]:
            writer.writerow({field: candidate.get(field, "") for field in _CSV_FIELDS})

    md_path = directory / "card.md"
    md_path.write_text(markdown_text)

    return {"json": json_path, "csv": csv_path, "md": md_path}
