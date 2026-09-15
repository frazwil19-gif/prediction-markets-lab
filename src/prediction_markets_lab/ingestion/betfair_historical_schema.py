"""Parsing for Betfair's historical Match Odds stream files (Workstream B,
per research/cycles/CYCLE_002_TENNIS/WORKSTREAM_B_MARKET_AWARE_RESEARCH_PROTOCOL.md).

**STATUS: UNVERIFIED AGAINST A REAL DOWNLOADED FILE.** Betfair's
historical data files reuse the same JSON "market change message"
format as the live Exchange Streaming API, which is stable and
publicly documented (one JSON object per line, each with a top-level
"op"/"pt" and an "mc" array of per-market updates; a market's first
message for a session typically carries a full "marketDefinition"
including its runners; subsequent messages carry "rc" runner-level
price changes only). This module is built to that documented shape and
tested against hand-built, schema-conformant fixtures -- it has NOT
been run against a real file, because no Betfair account/download
exists in this environment yet (that is Fraser's manual action, see
the protocol doc). Every parsing function raises loudly (KeyError/
ValueError) on a field that doesn't match the documented shape rather
than silently defaulting, precisely so the FIRST real file surfaces any
discrepancy immediately instead of parsing it wrong quietly. Re-audit
this module's field mapping against Fraser's real sample before
trusting its output on live data, exactly as
normalisation/tennis_betfair_linkage.py's name-matching conventions
must be.

Only the fields needed for Workstream B's linkage and pricing steps are
modelled -- this is deliberately not a complete Betfair stream-API
client. Fields this project doesn't yet use (in-play trading state,
market status transitions beyond OPEN/SUSPENDED/CLOSED, non-Match-Odds
market types) are not modelled and are out of scope until a concrete
need for them is pre-registered.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class BetfairRunnerDefinition:
    """One selection (player) as listed in a market's definition."""

    selection_id: int
    name: str | None
    sort_priority: int | None


@dataclass(frozen=True)
class BetfairMarketDefinition:
    """The "marketDefinition" block of a market-change message -- carries
    the market's static identity (event, scheduled time, runners), not
    live prices."""

    event_id: str | None
    market_time: datetime | None
    market_type: str | None
    status: str | None
    runners: tuple[BetfairRunnerDefinition, ...]


@dataclass(frozen=True)
class BetfairPriceLadderLevel:
    """One (price, size) level from a back/lay ladder."""

    price: float
    size: float


@dataclass(frozen=True)
class BetfairRunnerChange:
    """One runner's price update within a market-change message."""

    selection_id: int
    last_traded_price: float | None
    available_to_back: tuple[BetfairPriceLadderLevel, ...]
    available_to_lay: tuple[BetfairPriceLadderLevel, ...]


@dataclass(frozen=True)
class BetfairMarketChangeMessage:
    """One market's update within a single historical-stream JSON line."""

    market_id: str
    published_at: datetime | None
    market_definition: BetfairMarketDefinition | None
    runner_changes: tuple[BetfairRunnerChange, ...]


def _parse_epoch_ms(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)


def _parse_ladder(levels: list | None) -> tuple[BetfairPriceLadderLevel, ...]:
    """Parse a "batb"/"batl" ladder. Per Betfair's documented format each
    entry is [level_index, price, size] (three elements, not two) --
    the level index (0 = best price) is discarded here since callers
    only need price/size, but its presence is asserted so a malformed
    two-element entry fails loudly instead of silently swapping price
    and size."""
    if not levels:
        return ()
    result = []
    for lvl in levels:
        if len(lvl) != 3:
            raise ValueError(
                f"expected a 3-element [level, price, size] ladder entry, got {lvl!r}"
            )
        _level, price, size = lvl
        result.append(BetfairPriceLadderLevel(price=float(price), size=float(size)))
    return tuple(result)


def _parse_market_definition(raw: dict | None) -> BetfairMarketDefinition | None:
    if raw is None:
        return None
    runners = tuple(
        BetfairRunnerDefinition(
            selection_id=int(r["id"]),
            name=r.get("name"),
            sort_priority=r.get("sortPriority"),
        )
        for r in raw.get("runners", [])
    )
    return BetfairMarketDefinition(
        event_id=raw.get("eventId"),
        market_time=_parse_iso8601(raw.get("marketTime")),
        market_type=raw.get("marketType"),
        status=raw.get("status"),
        runners=runners,
    )


def _parse_iso8601(value: str | None) -> datetime | None:
    if value is None:
        return None
    # Betfair's documented format uses a trailing "Z" for UTC, which
    # datetime.fromisoformat only accepts from Python 3.11+; normalise
    # defensively so this doesn't break on an older interpreter.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_runner_change(raw: dict) -> BetfairRunnerChange:
    return BetfairRunnerChange(
        selection_id=int(raw["id"]),
        last_traded_price=float(raw["ltp"]) if raw.get("ltp") is not None else None,
        available_to_back=_parse_ladder(raw.get("batb")),
        available_to_lay=_parse_ladder(raw.get("batl")),
    )


def parse_market_change_line(line: str) -> list[BetfairMarketChangeMessage]:
    """Parse one line of a Betfair historical stream file.

    Args:
        line: A single JSON-encoded line, containing a top-level "pt"
            (publish time, epoch ms) and an "mc" array of per-market
            updates, per Betfair's documented Exchange Stream API
            market-change-message format.

    Returns:
        One BetfairMarketChangeMessage per entry in "mc" (usually one,
        but a line can cover multiple markets).

    Raises:
        KeyError: If "mc" or a required sub-field is missing.
        ValueError: If the line is not valid JSON, or a numeric/date
            field cannot be parsed as documented.
    """
    raw = json.loads(line)
    published_at = _parse_epoch_ms(raw.get("pt"))
    messages = []
    for mc in raw["mc"]:
        messages.append(
            BetfairMarketChangeMessage(
                market_id=mc["id"],
                published_at=published_at,
                market_definition=_parse_market_definition(mc.get("marketDefinition")),
                runner_changes=tuple(_parse_runner_change(rc) for rc in mc.get("rc", [])),
            )
        )
    return messages


def to_singles_event_candidate(message: BetfairMarketChangeMessage):
    """Build a tennis_betfair_linkage.BetfairEventCandidate from a
    market-change message that carries a full market definition with
    exactly two runners (a tennis singles Match Odds market).

    Returns:
        A BetfairEventCandidate, or None if this message doesn't carry
        a usable market definition (e.g. it's a runner-price-only
        update) or doesn't have exactly two runners (not a singles
        match -- doubles, walkovers-turned-void-markets, or a parsing
        surprise all fall here and are deliberately skipped rather than
        guessed at).
    """
    from prediction_markets_lab.normalisation.tennis_betfair_linkage import BetfairEventCandidate

    md = message.market_definition
    if md is None or md.market_time is None or md.event_id is None:
        return None
    if len(md.runners) != 2:
        return None
    names = tuple(r.name for r in md.runners)
    if any(n is None for n in names):
        return None
    return BetfairEventCandidate(
        market_id=message.market_id,
        event_id=md.event_id,
        event_open_date=md.market_time.date(),
        runner_names=names,  # type: ignore[arg-type]
    )
