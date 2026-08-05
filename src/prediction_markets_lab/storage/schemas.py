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


class HistoricalMatchRecord(BaseModel):
    """Canonical processed record: one row per unique historical match
    (Cycle 1 / Stage 3A). See docs/DATA_DICTIONARY.md.

    Bookmaker-specific odds are NOT flattened into this record -- see
    HistoricalBookmakerMarketRecord, which can always be joined back on
    match_id to reconstruct each bookmaker's complete H/D/A market.
    """

    match_id: str
    source_id: str
    source_file: str
    competition_code: str
    competition_name: str
    season: str
    match_date: str
    match_time: str = ""
    home_team_raw: str
    away_team_raw: str
    home_team_normalised: str | None = None
    away_team_normalised: str | None = None
    full_time_home_goals: int | None = None
    full_time_away_goals: int | None = None
    full_time_result: str | None = None
    half_time_home_goals: int | None = None
    half_time_away_goals: int | None = None
    half_time_result: str | None = None
    average_opening_home_odds: float | None = None
    average_opening_draw_odds: float | None = None
    average_opening_away_odds: float | None = None
    average_closing_home_odds: float | None = None
    average_closing_draw_odds: float | None = None
    average_closing_away_odds: float | None = None
    maximum_opening_home_odds: float | None = None
    maximum_opening_draw_odds: float | None = None
    maximum_opening_away_odds: float | None = None
    maximum_closing_home_odds: float | None = None
    maximum_closing_draw_odds: float | None = None
    maximum_closing_away_odds: float | None = None
    bookmaker_count_opening: int = Field(ge=0, default=0)
    bookmaker_count_closing: int = Field(ge=0, default=0)
    complete_market_count: int = Field(ge=0, default=0)
    data_quality_flags: str = ""
    duplicate_status: str = ""
    normalisation_status: str = ""
    eligible_outcome_model: bool = False
    eligible_consensus_model: bool = False
    eligible_opening_analysis: bool = False
    eligible_closing_analysis: bool = False
    eligible_clv_proxy_analysis: bool = False
    exclusion_reasons: str = ""
    processed_at: str
    data_version: str


class HistoricalBookmakerMarketRecord(BaseModel):
    """Canonical processed record: one row per (match, bookmaker, price
    timing) complete H/D/A triplet. See docs/DATA_DICTIONARY.md and
    ingestion.football_bookmaker_extraction."""

    match_id: str
    bookmaker: str
    price_timing: str  # "opening" | "closing"
    home_odds: float = Field(gt=1.0)
    draw_odds: float = Field(gt=1.0)
    away_odds: float = Field(gt=1.0)
    raw_implied_home: float | None = None
    raw_implied_draw: float | None = None
    raw_implied_away: float | None = None
    overround: float | None = None
    fair_home_probability: float | None = None
    fair_draw_probability: float | None = None
    fair_away_probability: float | None = None
    processed_at: str
    data_version: str


class HistoricalConsensusRecord(BaseModel):
    """Canonical processed record: one row per (match, price timing)
    margin-free consensus, built ONLY from complete bookmaker-specific
    triplets -- never from Avg*/Max* aggregate columns (see
    docs/HISTORICAL_PRICE_AND_CLV_LIMITATIONS.md)."""

    match_id: str
    price_timing: str  # "opening" | "closing"
    bookmaker_count: int = Field(ge=0)
    median_fair_home_probability: float | None = None
    median_fair_draw_probability: float | None = None
    median_fair_away_probability: float | None = None
    mean_fair_home_probability: float | None = None
    mean_fair_draw_probability: float | None = None
    mean_fair_away_probability: float | None = None
    std_fair_home_probability: float | None = None
    std_fair_draw_probability: float | None = None
    std_fair_away_probability: float | None = None
    iqr_fair_home_probability: float | None = None
    iqr_fair_draw_probability: float | None = None
    iqr_fair_away_probability: float | None = None
    min_fair_home_probability: float | None = None
    max_fair_home_probability: float | None = None
    probability_sum_check: float | None = None  # should be ~1.0 (medians won't be exact)
    processed_at: str
    data_version: str
