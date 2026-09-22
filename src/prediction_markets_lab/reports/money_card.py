"""Daily Money Card -- the concise, actionable subset of the full Daily
Bet Card contract (TARGETED PRODUCTION CHANGE -- DAILY MONEY WINDOW +
MONEY/PAPER SEPARATION instruction, 2026-09-22).

This module does NOT recompute probability, EV, grading, or money
qualification -- it only filters and re-presents candidates that
reports.daily_bet_card.build_daily_bet_card_contract already built and
decisions.money_qualification already evaluated. That full contract
(card.json/card.csv/card.md, unchanged) remains the canonical, complete
research/audit output; this is the new, narrower sibling the operator's
instruction calls for:

    "The concise user-facing card should contain ONLY money_qualified =
    true candidates inside the money horizon -- do NOT show backend B
    longshots as actionable."

Written to daily_cards/<date>/money_card.json and money_card.md,
alongside (never replacing) the existing card.json/card.csv/card.md.
"""

from __future__ import annotations

import json
from pathlib import Path

from prediction_markets_lab.reports.daily_bet_card import _fair_odds, _potential_profit_gbp  # noqa: F401 (re-exported for callers that want the same helpers)


def build_money_card_contract(
    full_contract: dict,
    money_event_horizon_hours: float,
) -> dict:
    """Build the Daily Money Card contract from an already-built full contract.

    Args:
        full_contract: The dict from
            reports.daily_bet_card.build_daily_bet_card_contract -- every
            candidate in it must already carry money_qualified (see
            decisions.recommendation.build_recommendation).
        money_event_horizon_hours: The configured
            decisions.money_qualification.MoneyQualificationThresholds.
            event_horizon_hours, recorded here for transparency (so a
            consumer never has to guess which horizon produced this card).

    Returns:
        A JSON-serialisable dict: header fields, the list of
        money-qualified candidates only (in the same grade/net-EV rank
        order the full contract already uses), and a `best_bet` pointer
        (the top-ranked money-qualified candidate, or None).
    """
    money_candidates = [c for c in full_contract["candidates"] if c.get("money_qualified")]
    total_exposure = sum(c["recommended_stake"] for c in money_candidates)

    return {
        "run_timestamp": full_contract["run_timestamp"],
        "data_timestamp": full_contract["data_timestamp"],
        "engine_version": full_contract["engine_version"],
        "bankroll_gbp": full_contract["bankroll_gbp"],
        "money_event_horizon_hours": money_event_horizon_hours,
        "fixtures_scanned": full_contract["fixtures_scanned"],
        "research_candidates_analysed": full_contract["candidates_analysed"],
        "money_qualified_count": len(money_candidates),
        "recommended_total_exposure_gbp": total_exposure,
        "best_bet": money_candidates[0] if money_candidates else None,
        # Not built in V1 -- see reports.daily_bet_card's module docstring;
        # kept null here rather than fabricated, same convention.
        "optional_multi": None,
        "money_qualified_candidates": money_candidates,
        "system_warnings": list(full_contract.get("system_warnings", [])),
    }


def render_money_card_markdown(contract: dict, date_label: str) -> str:
    """Render the human-readable Daily Money Card, per the operator's
    specified format. Returns the explicit "NO MONEY BETS QUALIFIED
    TODAY" message (never a fabricated bet) when the list is empty --
    "a valid, expected outcome; thresholds are never loosened to
    manufacture a bet," matching this project's existing convention in
    reports.daily_bet_card.render_daily_bet_card.
    """
    lines: list[str] = []
    lines.append(f"DAILY MONEY CARD -- {date_label}")
    lines.append("")
    lines.append(f"Bankroll: £{contract['bankroll_gbp']:.2f}")
    lines.append(f"Money horizon: next {contract['money_event_horizon_hours']:.0f}h")
    lines.append(f"Fixtures scanned: {contract['fixtures_scanned']}")
    lines.append(f"Research candidates: {contract['research_candidates_analysed']}")
    lines.append(f"Money-qualified bets: {contract['money_qualified_count']}")
    lines.append(f"Recommended exposure: £{contract['recommended_total_exposure_gbp']:.2f}")
    lines.append("")

    candidates = contract["money_qualified_candidates"]
    if not candidates:
        lines.append("NO MONEY BETS QUALIFIED TODAY")
        lines.append("")
        lines.append(
            f"{contract['research_candidates_analysed']} candidate(s) analysed; none satisfied the "
            "combined horizon/probability/confidence/payout/value/risk gate. Thresholds are never "
            "loosened to manufacture a bet."
        )
        return "\n".join(lines) + "\n"

    lines.append("Grade | Event | Bet | Odds | Est P | Fair | Confidence | Stake | Potential Profit")
    for c in candidates:
        lines.append(
            f"{c['grade']} | {c['event']} | {c['selection']} ({c['market']}) | "
            f"{c['available_odds']:.2f} | {c['estimated_probability']:.1%} | {c['fair_odds']:.2f} | "
            f"{c['confidence']} | £{c['recommended_stake']:.2f} | £{c['expected_payout']:.2f}"
        )
    lines.append("")

    best = contract["best_bet"]
    lines.append("BEST BET")
    lines.append(
        f"[{best['grade']}] {best['selection']} -- {best['event']} ({best['market']}) @ "
        f"{best['available_odds']:.2f}, stake £{best['recommended_stake']:.2f}, "
        f"potential profit £{best['expected_payout']:.2f}"
    )
    lines.append("")

    lines.append("OPTIONAL MULTI")
    lines.append(
        "Not built -- singles only. See the Daily Bet Card's own note; a multi engine remains "
        "explicitly deprioritised behind a working, selective singles money strategy."
    )

    return "\n".join(lines) + "\n"


def write_money_card_outputs(directory: Path, contract: dict, markdown_text: str) -> dict[str, Path]:
    """Write money_card.json / money_card.md to `directory` (the same
    daily_cards/<date>/ directory reports.daily_bet_card.
    write_daily_bet_card_outputs already writes card.json/card.csv/
    card.md into) -- these are new SIBLING files, never a replacement.

    Returns:
        {"json": <path>, "md": <path>}.
    """
    directory.mkdir(parents=True, exist_ok=True)

    json_path = directory / "money_card.json"
    json_path.write_text(json.dumps(contract, indent=2, sort_keys=False) + "\n")

    md_path = directory / "money_card.md"
    md_path.write_text(markdown_text)

    return {"json": json_path, "md": md_path}
