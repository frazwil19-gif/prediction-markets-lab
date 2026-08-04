"""Shared record schemas for the manual workflow.

These pydantic models are the single source of truth for the columns
used in CSV storage (storage/csv_store.py) and the Google Sheets
workbook (see docs/GOOGLE_SHEETS_DESIGN.md). Every field name here
should match a Sheets tab column exactly, so that CSV <-> Sheets stays
consistent.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Grade = Literal["A+", "A", "B", "C", "Reject"]
Sport = Literal["football", "tennis", "basketball", "cricket", "politics"]
Exchange = Literal["Smarkets", "Betfair"]
BetResult = Literal["win", "loss", "void", "pending"]


class BookmakerOddsRecord(BaseModel):
    """A single bookmaker's price for a single outcome. Mirrors the
    Bookmaker Odds tab."""

    odds_record_id: str
    market_id: str
    timestamp: str
    bookmaker: str
    outcome: str
    decimal_odds: float = Field(gt=1.0)
    implied_probability_raw: float | None = None
    overround: float | None = None
    fair_probability: float | None = None
    source: str = ""
    source_url_or_note: str = ""
    data_quality_flag: str = "ok"


class MarketRecord(BaseModel):
    """A single graded opportunity. Mirrors the Markets tab."""

    market_id: str
    scan_timestamp: str
    event_date: str
    event_time: str = ""
    sport: Sport
    competition: str
    event: str
    market_type: str
    selection: str
    bookmaker_count: int = Field(ge=0)
    consensus_probability: float = Field(gt=0.0, lt=1.0)
    consensus_mean: float | None = None
    consensus_median: float | None = None
    consensus_std: float | None = None
    model_probability: float | None = None
    final_probability: float | None = None
    exchange: Exchange
    exchange_odds: float = Field(gt=1.0)
    exchange_implied_probability: float = Field(gt=0.0, lt=1.0)
    commission: float = Field(ge=0.0, lt=1.0)
    probability_edge: float
    gross_ev: float
    net_ev: float
    confidence_score: str = ""
    data_quality_score: str = ""
    liquidity_score: str = ""
    grade: Grade
    decision: str = ""
    rejection_reason: str = ""
    notes: str = ""


class DailyShortlistRow(BaseModel):
    """A single ranked row on the Daily Shortlist tab."""

    rank: int
    date: str
    event: str
    selection: str
    sport: Sport
    competition: str
    exchange: Exchange
    current_odds: float
    final_probability: float
    net_ev: float
    confidence: str = ""
    grade: Grade
    recommended_stake: float = Field(ge=0.0)
    price_expiry_note: str = ""
    action: str = ""
    status: str = ""


class BetRecord(BaseModel):
    """A live bet record. Mirrors the Bets tab (Paper Trades reuses
    this schema — see storage.csv_store)."""

    bet_id: str
    market_id: str
    bet_timestamp: str
    sport: Sport
    competition: str
    event: str
    market: str
    selection: str
    venue: Exchange
    requested_odds: float = Field(gt=1.0)
    matched_odds: float = Field(gt=1.0)
    stake: float = Field(gt=0.0)
    estimated_probability: float = Field(gt=0.0, lt=1.0)
    implied_probability: float = Field(gt=0.0, lt=1.0)
    net_ev_at_entry: float
    confidence_score: str = ""
    grade: Grade
    bankroll_before: float = Field(ge=0.0)
    liability: float = Field(ge=0.0)
    result: BetResult = "pending"
    gross_profit: float = 0.0
    commission_paid: float = 0.0
    net_profit: float = 0.0
    bankroll_after: float | None = None
    closing_odds: float | None = None
    closing_probability: float | None = None
    clv: float | None = None
    notes: str = ""


class ResultRecord(BaseModel):
    """A settlement record. Mirrors the Results tab."""

    market_id: str
    event: str
    settlement_date: str
    winning_outcome: str
    result_source: str = ""
    settlement_status: str = "settled"
    notes: str = ""


class BankrollTransaction(BaseModel):
    """A single bankroll ledger entry. Mirrors the Bankroll tab."""

    timestamp: str
    transaction_type: str  # e.g. "deposit", "withdrawal", "bet_settlement"
    deposit: float = 0.0
    withdrawal: float = 0.0
    stake: float = 0.0
    return_: float = Field(default=0.0, alias="return")
    commission: float = 0.0
    net_change: float
    balance: float = Field(ge=0.0)
    peak_balance: float = Field(ge=0.0)
    drawdown: float = Field(ge=0.0)
    notes: str = ""

    model_config = ConfigDict(populate_by_name=True)
