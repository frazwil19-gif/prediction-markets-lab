"""Automated settlement runner for the Track B paper-bet ledger (Section 7,
Production Infrastructure Build, 2026-09-20).

Reuses storage.paper_ledger.settle_paper_bet (KEEP -- already tested,
already enforces immutability of every non-settlement field) for the
actual write; this module's own job is purely to work out, for every
still-pending bet, WHAT to settle it as: fetch each sport_key's results
once from The Odds API's /v4/sports/{sport}/scores (ingestion.the_odds_
api_scores), match by the provider's own event id, and compute the
result/pnl with settlement.market_settlement's pure functions.

Idempotency: only rows with status == "pending" are considered. Once
settle_paper_bet marks a row "settled", a second run of this function
will not see it again -- running settlement twice cannot pay a bet
twice.

KNOWN LIMITATION, stated rather than hidden: only bets recorded from a
LIVE odds-api scan carry a parseable provider event id (their
`event_id` field is exactly the market_id ingestion.the_odds_api_loader
constructs, "{sport_key}-{event_id}-{market_suffix}"). Bets recorded via
storage.paper_ledger.record_qualifying_candidates_from_contract (a
one-off card.json backfill, used once so far, for 2026-09-19's first
live card) do not carry a real provider event id and cannot be
auto-settled by this module -- they are reported in
`unresolvable_no_provider_id` and must be settled manually via
storage.paper_ledger.settle_paper_bet directly, once, with the real
result looked up by hand. This is a one-time, bounded gap (9 rows), not
an ongoing one: every bet recorded by a live scan going forward carries
a real provider event id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from prediction_markets_lab.ingestion.the_odds_api_loader import TheOddsApiConfig
from prediction_markets_lab.ingestion.the_odds_api_scores import (
    ParsedScore,
    fetch_scores_raw,
    parse_scores_response,
)
from prediction_markets_lab.settlement.market_settlement import compute_pnl_gbp, determine_result
from prediction_markets_lab.storage.paper_ledger import load_paper_bets, settle_paper_bet


@dataclass(frozen=True)
class SettlementRunSummary:
    settled_bet_ids: list[str] = field(default_factory=list)
    not_yet_completed_bet_ids: list[str] = field(default_factory=list)
    unresolvable_no_provider_id: list[str] = field(default_factory=list)
    event_not_found_bet_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _parse_provider_event_id(event_id_field: str) -> tuple[str, str] | None:
    """Split a live-scan event_id ("{sport_key}-{provider_event_id}-{market}")
    into (sport_key, provider_event_id), or None if it does not match that
    exact 3-part shape (e.g. a contract-backfilled bet -- see module
    docstring's KNOWN LIMITATION).
    """
    parts = event_id_field.split("-")
    if len(parts) != 3:
        return None
    sport_key, provider_event_id, _market_suffix = parts
    if not sport_key or not provider_event_id:
        return None
    return sport_key, provider_event_id


def _running_paper_bankroll(ledger_path: Path, starting_bankroll_gbp: float) -> float:
    """Recompute the current paper bankroll from every already-settled row.

    Deterministic and stateless by design (no separate bankroll-state
    file to keep in sync) -- see the module docstring on idempotency.
    """
    running = starting_bankroll_gbp
    for row in load_paper_bets(ledger_path):
        if row.get("status") == "settled" and row.get("actual_pnl", "") != "":
            try:
                running += float(row["actual_pnl"])
            except ValueError:
                pass
    return running


def settle_pending_paper_bets(
    ledger_path: Path,
    config: TheOddsApiConfig,
    starting_bankroll_gbp: float,
    days_from: int = 3,
    archive_dir: Path | None = None,
) -> SettlementRunSummary:
    """Settle every pending paper bet whose event has a completed score.

    Args:
        ledger_path: Path to paper_bets.csv.
        config: The active TheOddsApiConfig (for scores fetches).
        starting_bankroll_gbp: The Track B paper bankroll's starting
            value (config/bankroll.yaml's starting_bankroll_gbp), used to
            recompute the running paper bankroll after each settlement.
        days_from: Passed through to fetch_scores_raw.
        archive_dir: Optional (added 2026-09-24, V2-4 settlement migration). When given, every raw
            scores payload is also written to archive_dir as JSON so a free-results settlement source
            can be shadow-compared against it. It does not change settlement behaviour.

    Returns:
        A SettlementRunSummary describing what happened to every pending
        bet this run considered.
    """
    summary = SettlementRunSummary()
    rows = load_paper_bets(ledger_path)
    pending = [row for row in rows if row.get("status") == "pending"]

    pending_by_sport_key: dict[str, list[dict]] = {}
    for row in pending:
        parsed = _parse_provider_event_id(row.get("event_id", ""))
        if parsed is None:
            summary.unresolvable_no_provider_id.append(row["bet_id"])
            continue
        sport_key, _provider_event_id = parsed
        pending_by_sport_key.setdefault(sport_key, []).append(row)

    scores_by_sport_key: dict[str, dict[str, ParsedScore]] = {}
    for sport_key in pending_by_sport_key:
        try:
            raw = fetch_scores_raw(sport_key, config, days_from=days_from)
            if archive_dir is not None:
                import json as _json
                from datetime import datetime as _dt, timezone as _tz
                archive_dir.mkdir(parents=True, exist_ok=True)
                stamp = _dt.now(_tz.utc).strftime("%Y%m%dT%H%M%SZ")
                (archive_dir / f"odds_api_scores_{sport_key}_{stamp}.json").write_text(_json.dumps(raw))
            parsed_scores = parse_scores_response(raw, sport_key)
            scores_by_sport_key[sport_key] = {s.event_id: s for s in parsed_scores}
        except Exception as exc:  # noqa: BLE001 -- one sport_key's failure must not block the others
            summary.errors.append(f"{sport_key}: failed to fetch/parse scores -- {exc}")

    for sport_key, bets in pending_by_sport_key.items():
        score_lookup = scores_by_sport_key.get(sport_key, {})
        for row in bets:
            _sport_key, provider_event_id = _parse_provider_event_id(row["event_id"])
            score = score_lookup.get(provider_event_id)
            if score is None:
                summary.event_not_found_bet_ids.append(row["bet_id"])
                continue
            if not score.completed:
                summary.not_yet_completed_bet_ids.append(row["bet_id"])
                continue

            try:
                winning_selection = determine_result(row["market"], score.home_score, score.away_score)
            except ValueError as exc:
                summary.errors.append(f"{row['bet_id']}: {exc}")
                continue

            pnl = compute_pnl_gbp(
                stake_gbp=float(row["recommended_stake"]),
                quoted_odds=float(row["quoted_odds"]),
                selection=row["selection"],
                winning_selection=winning_selection,
            )
            result_label = (
                "void"
                if winning_selection == "void"
                else ("won" if row["selection"] == winning_selection else "lost")
            )
            new_bankroll = _running_paper_bankroll(ledger_path, starting_bankroll_gbp) + pnl

            settle_paper_bet(
                ledger_path,
                bet_id=row["bet_id"],
                result=result_label,
                closing_odds_if_available="",
                actual_pnl=f"{pnl:.2f}",
                paper_bankroll_after_settlement=f"{new_bankroll:.2f}",
            )
            summary.settled_bet_ids.append(row["bet_id"])

    return summary
