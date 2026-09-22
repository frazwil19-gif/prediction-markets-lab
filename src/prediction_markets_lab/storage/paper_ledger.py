"""Append-only live paper-bet ledger (Track B) -- 2026-09-19 build.

Operator's "MAJOR NEXT PHASE -- LIVE COMMISSIONING + BACKTEST/PAPER-
TRADING VALIDATION" instruction, Phase 3B: "Build an append-only paper-
bet ledger. Every live candidate meeting the paper-bet threshold must be
recorded automatically as a hypothetical bet whether Fraser actually
places it or not... Once written, its core decision fields cannot be
retrospectively changed."

Design:

- Storage lives at `paper_ledger/paper_bets.csv` at the repo root --
  deliberately NOT under `data/` or `reports/daily/`, both gitignored,
  for the exact same reason `daily_cards/` was placed at the repo root
  (see reports/daily_bet_card.py's module docstring): this ledger is the
  unbiased forward evidence record the whole future automation decision
  depends on, so it must be committed, not lost to a gitignored path or
  an ephemeral CI runner.
- "Core decision fields" (everything recorded at bet-creation time --
  the price, probability, grade, reasoning, etc.) are treated as
  immutable once written. `record_qualifying_candidates` only ever
  appends new rows for a (market_id, selection) not already present in
  the ledger -- re-running the same day's scan does not duplicate or
  overwrite an already-recorded candidate, satisfying the "duplicate-bet
  protection" principle this project applies everywhere (see
  decisions/liquidity.py and the risk rules in the master directive).
- The ONLY sanctioned mutation to an existing row is settlement
  (`settle_paper_bet`): it updates status/result/closing_odds_if_available/
  actual_pnl/paper_bankroll_after_settlement and nothing else.
  `settle_paper_bet` asserts every other field is byte-identical to the
  row it read before writing back, so an accidental corruption of a
  decision field raises loudly rather than silently drifting.
- The **paper-bet threshold is Grade B or better** (A+/A/B) -- Grade C
  is "watchlist only" in the existing grading language
  (decisions/grading.py's own reason strings already say so), not a
  qualifying candidate; Reject is obviously excluded. This mirrors the
  Daily Bet Card's own "A+/A/B selections" bucket exactly, so the paper
  ledger's population is never a separate, undocumented rule from what
  the card itself already displays as "qualifying."
- KNOWN LIMITATION, stated rather than hidden: `kickoff` is currently
  only the fixture's date (from MarketRecord.event_date), not a full
  kickoff time-of-day, because the full commence_time from
  ingestion.the_odds_api_loader.ParsedEvent is not currently threaded
  through decisions.recommendation.build_recommendation's MarketRecord.
  This is precise enough for "has this event started yet" checks done a
  reasonable margin before kickoff, but not for a same-day, close-to-
  kickoff settlement trigger. Threading a real kickoff timestamp through
  is a small, well-scoped follow-on, not done in this pass to keep this
  change additive rather than touching the MarketRecord schema.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from prediction_markets_lab.decisions.recommendation import RecommendationResult

PAPER_BET_THRESHOLD_GRADES = frozenset({"A+", "A", "B"})

_FIELDS = [
    "bet_id",
    "scan_id",
    "created_at",
    "event_id",
    "event",
    "kickoff",
    "sport",
    "competition",
    "market",
    "selection",
    "bookmaker",
    "quoted_odds",
    "estimated_probability",
    "fair_odds",
    "break_even_probability",
    "confidence",
    "grade",
    "recommended_stake",
    "model_version",
    "data_version",
    "decision_reason",
    "status",
    "result",
    "closing_odds_if_available",
    "actual_pnl",
    "paper_bankroll_after_settlement",
    # --- Added 2026-09-22 (TARGETED PRODUCTION CHANGE -- DAILY MONEY
    # WINDOW + MONEY/PAPER SEPARATION). A core decision field, set once at
    # bet-creation time from decisions.money_qualification's result and
    # never touched by settle_paper_bet (it is not in _SETTLEMENT_FIELDS
    # below). This is what lets performance.paper_performance separate
    # the narrow, actually-selective "paper_money_strategy" from the
    # broad "paper_research" universe -- see that module's module
    # docstring. Appended at the end so every existing row (written
    # before this field existed) still parses: csv.DictReader leaves a
    # missing trailing column as a KeyError-free absence, and
    # load_paper_bets/_write_all round-trip it as "" for old rows, which
    # performance.paper_performance treats as not money-qualified.
    "money_qualified",
]

# Fields that settle_paper_bet is allowed to change. Everything else in
# _FIELDS is a "core decision field" and is asserted immutable.
_SETTLEMENT_FIELDS = frozenset(
    {"status", "result", "closing_odds_if_available", "actual_pnl", "paper_bankroll_after_settlement"}
)


@dataclass(frozen=True)
class PaperBet:
    """One row of the append-only paper-bet ledger."""

    bet_id: str
    scan_id: str
    created_at: str
    event_id: str
    event: str
    kickoff: str
    sport: str
    competition: str
    market: str
    selection: str
    bookmaker: str
    quoted_odds: float
    estimated_probability: float
    fair_odds: float
    break_even_probability: float
    confidence: str
    grade: str
    recommended_stake: float
    model_version: str
    data_version: str
    decision_reason: str
    status: str = "pending"
    result: str = ""
    closing_odds_if_available: str = ""
    actual_pnl: str = ""
    paper_bankroll_after_settlement: str = ""
    money_qualified: bool = False


def _fair_odds(probability: float) -> float:
    return float("inf") if probability <= 0 else 1.0 / probability


def load_paper_bets(ledger_path: Path) -> list[dict]:
    """Load every row of the ledger as-is (strings, per csv.DictReader)."""
    if not ledger_path.exists():
        return []
    with open(ledger_path, newline="") as f:
        return list(csv.DictReader(f))


def _write_all(ledger_path: Path, rows: list[dict]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in _FIELDS})


def record_qualifying_candidates(
    ledger_path: Path,
    recommendations: list[RecommendationResult],
    scan_id: str,
    created_at: str,
    data_version: str = "",
    min_grade_set: frozenset[str] = PAPER_BET_THRESHOLD_GRADES,
) -> tuple[list[str], list[str]]:
    """Append every qualifying candidate not already in the ledger.

    Args:
        ledger_path: Path to paper_bets.csv (created if missing).
        recommendations: Every graded candidate from one scan (all
            grades -- this function does its own threshold filtering,
            so pass the full list, not a pre-filtered one).
        scan_id: Identifier for this scan run (e.g. the ISO scan
            timestamp), recorded on every new row for provenance.
        created_at: ISO timestamp this ledger write happened.
        data_version: Optional data/engine version tag.
        min_grade_set: The paper-bet qualifying grades. Defaults to
            Grade B or better (A+/A/B) -- see module docstring.

    Returns:
        (newly_recorded_bet_ids, skipped_duplicate_bet_ids). A candidate
        is skipped, not re-recorded, if its (market_id, selection) pair
        already has a row in the ledger -- core decision fields, once
        written, are never overwritten by a later scan of the same
        fixture.
    """
    existing_rows = load_paper_bets(ledger_path)
    existing_ids = {row["bet_id"] for row in existing_rows}

    new_rows: list[dict] = []
    newly_recorded: list[str] = []
    skipped: list[str] = []

    for rec in recommendations:
        m = rec.market_record
        if m.grade not in min_grade_set:
            continue

        bet_id = f"{m.market_id}::{m.selection}"
        if bet_id in existing_ids:
            skipped.append(bet_id)
            continue

        probability = m.final_probability if m.final_probability is not None else m.consensus_probability
        bet = PaperBet(
            bet_id=bet_id,
            scan_id=scan_id,
            created_at=created_at,
            event_id=m.market_id,
            event=m.event,
            # Prefer the real kickoff timestamp when this scan supplied one
            # (live odds-api scans -- see ingestion/the_odds_api_loader.py
            # and decisions/money_qualification.py); fall back to the
            # date-only value for manual-mode scans, which never had one --
            # see this module's KNOWN LIMITATION note above, now resolved
            # for the live path.
            kickoff=m.kickoff_time or m.event_date,
            sport=m.sport,
            competition=m.competition,
            market=m.market_type,
            selection=m.selection,
            bookmaker=m.exchange,
            quoted_odds=m.exchange_odds,
            estimated_probability=probability,
            fair_odds=_fair_odds(probability),
            break_even_probability=m.exchange_implied_probability,
            confidence=m.confidence_score,
            grade=m.grade,
            recommended_stake=rec.stake_gbp,
            model_version=data_version,
            data_version=data_version,
            decision_reason=m.decision,
            status="pending",
            money_qualified=m.money_qualified,
        )
        new_rows.append(asdict(bet))
        newly_recorded.append(bet_id)

    if new_rows:
        _write_all(ledger_path, existing_rows + new_rows)

    return newly_recorded, skipped


def settle_paper_bet(
    ledger_path: Path,
    bet_id: str,
    result: str,
    closing_odds_if_available: str,
    actual_pnl: str,
    paper_bankroll_after_settlement: str,
) -> None:
    """Settle exactly one existing paper bet, mutating only settlement fields.

    Args:
        ledger_path: Path to paper_bets.csv.
        bet_id: The bet to settle (must already exist in the ledger).
        result: e.g. "won", "lost", "void".
        closing_odds_if_available: The closing price for this selection,
            if collected; "" if not available.
        actual_pnl: Realised profit/loss in GBP as a string (e.g.
            "1.20" or "-0.25"), kept as a string here to match the CSV's
            uniform typing -- callers should parse/format consistently.
        paper_bankroll_after_settlement: The running paper bankroll
            after this settlement.

    Raises:
        KeyError: If bet_id is not found in the ledger.
        ValueError: If settling this bet would change any field other
            than the settlement fields listed above -- this should never
            happen through normal use of this function; it exists as a
            guard against accidental corruption of an immutable decision
            field.
    """
    rows = load_paper_bets(ledger_path)
    updated_rows = []
    found = False
    for row in rows:
        if row["bet_id"] != bet_id:
            updated_rows.append(row)
            continue
        found = True
        new_row = dict(row)
        new_row["status"] = "settled"
        new_row["result"] = result
        new_row["closing_odds_if_available"] = closing_odds_if_available
        new_row["actual_pnl"] = actual_pnl
        new_row["paper_bankroll_after_settlement"] = paper_bankroll_after_settlement

        for field_name in _FIELDS:
            if field_name in _SETTLEMENT_FIELDS:
                continue
            if row.get(field_name, "") != new_row.get(field_name, ""):
                raise ValueError(
                    f"settle_paper_bet attempted to change immutable field "
                    f"{field_name!r} for bet {bet_id!r} -- this is not allowed"
                )
        updated_rows.append(new_row)

    if not found:
        raise KeyError(f"bet_id {bet_id!r} not found in ledger at {ledger_path}")

    _write_all(ledger_path, updated_rows)


def record_qualifying_candidates_from_contract(
    ledger_path: Path,
    contract: dict,
    scan_id: str,
    created_at: str,
    min_grade_set: frozenset[str] = PAPER_BET_THRESHOLD_GRADES,
) -> tuple[list[str], list[str]]:
    """Same as record_qualifying_candidates, but from an already-built
    Daily Bet Card contract dict (reports.daily_bet_card.build_daily_bet_card_contract)
    instead of a list of RecommendationResult.

    This exists for the case where a scan already ran and produced
    card.json, but the ledger still needs populating from it -- e.g. a
    one-off backfill for a card generated before this ledger existed, or
    recovering from a failure that happened after the card was written
    but before the ledger write. It never re-runs probability/EV/
    grading; it only reads the numbers the contract already has.

    The bet_id here is keyed on (event, market, selection) rather than
    market_id, since the contract's candidate rows do not carry the
    engine's internal market_id -- event+market+selection is equally
    unique within one day's scan.
    """
    existing_rows = load_paper_bets(ledger_path)
    existing_ids = {row["bet_id"] for row in existing_rows}

    new_rows: list[dict] = []
    newly_recorded: list[str] = []
    skipped: list[str] = []

    for candidate in contract["candidates"]:
        if candidate["grade"] not in min_grade_set:
            continue

        bet_id = f"{candidate['event']}::{candidate['market']}::{candidate['selection']}"
        if bet_id in existing_ids:
            skipped.append(bet_id)
            continue

        bet = PaperBet(
            bet_id=bet_id,
            scan_id=scan_id,
            created_at=created_at,
            event_id=bet_id,
            event=candidate["event"],
            # Prefer the real kickoff timestamp when the contract carries
            # one (see this module's other record_* function) -- older
            # contracts built before 2026-09-22 will not have this key.
            kickoff=candidate.get("kickoff_time") or candidate["date"],
            sport=candidate["sport"],
            competition=candidate["competition"],
            market=candidate["market"],
            selection=candidate["selection"],
            bookmaker=candidate["bookmaker"],
            quoted_odds=candidate["available_odds"],
            estimated_probability=candidate["estimated_probability"],
            fair_odds=candidate["fair_odds"],
            break_even_probability=1.0 / candidate["available_odds"] if candidate["available_odds"] else 0.0,
            confidence=candidate["confidence"],
            grade=candidate["grade"],
            recommended_stake=candidate["recommended_stake"],
            model_version=candidate["model_version"],
            data_version=candidate["model_version"],
            decision_reason=candidate["reason"],
            status="pending",
            money_qualified=bool(candidate.get("money_qualified", False)),
        )
        new_rows.append(asdict(bet))
        newly_recorded.append(bet_id)

    if new_rows:
        _write_all(ledger_path, existing_rows + new_rows)

    return newly_recorded, skipped
