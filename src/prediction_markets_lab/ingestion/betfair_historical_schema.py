"""Parsing for Betfair's historical Match Odds stream files (Workstream B,
per research/cycles/CYCLE_002_TENNIS/WORKSTREAM_B_MARKET_AWARE_RESEARCH_PROTOCOL.md).

**STATUS: VERIFIED AGAINST A REAL DOWNLOADED SAMPLE (2026-09-16).**
Fraser's real Betfair BASIC-tier ATP tennis sample (Jan-Sep 2026,
161,025 files, 402,132,971 bytes -- full audit in
`research/cycles/CYCLE_002_TENNIS/WORKSTREAM_B_SAMPLE_AUDIT_REPORT.md`)
confirmed the documented shape this module was built against: one JSON
object per line, a top-level "op"/"pt", an "mc" array of per-market
updates, a full "marketDefinition" on a market's first message,
"rc" runner-level price changes on subsequent ones. Zero lines failed
to parse across a 3,000-file real sample. Real deviations found and
handled: (1) the download is a plain nested directory tree
(sport/year/month/day/eventId/*.bz2), not a single .tar archive as the
docs implied -- this module doesn't care, since it only ever sees one
already-decompressed line at a time; (2) BASIC-tier "rc" updates carry
only "ltp", never "batb"/"batl" -- already optional here, parses fine;
(3) a market-change file exists in two flavours per event -- one file
per individual marketId (`1.<marketId>.bz2`, what this module expects)
and one combined multi-market capture per event (`<eventId>.bz2`,
containing the same data multiplexed across sibling markets) -- only
the per-marketId files are used; (4) **a real bug**, found and fixed
here: `to_singles_event_candidate` did not filter by market type, and
a real event carries several non-Match-Odds two-runner markets (see
that function's docstring for the fix and why it mattered).

Only the fields needed for Workstream B's linkage and pricing steps are
modelled -- this is deliberately not a complete Betfair stream-API
client. Fields this project doesn't yet use (in-play trading state,
market status transitions beyond OPEN/SUSPENDED/CLOSED, non-Match-Odds
market types, and the runner-level WINNER/LOSER/REMOVED outcome status
confirmed present in real settled markets) are not modelled and are out
of scope until a concrete need for them is pre-registered -- the
WINNER/LOSER status in particular is a real, useful future source of
ground-truth match outcomes directly from Betfair, noted here for when
that need arises.
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


def latest_singles_event_candidates(messages):
    """Reduce a market's full message history down to one
    BetfairEventCandidate per market_id, using the LAST message that
    carries a usable Match Odds definition, not the first.

    **Real-data discovery (2026-09-16, Fraser's first Betfair BASIC
    sample):** a market's scheduled date can be revised within its own
    message history (postponement/rain delay) -- one real Nick
    Kyrgios v Aleksandar Kovacevic market carried three different
    marketDefinition dates (Jan 4, 5, and 6) across its stream before
    settling on the actual played date. Building a candidate from the
    FIRST marketDefinition message risks using a stale, pre-revision
    date and missing the date-tolerance window against TML's played
    date; keeping the LAST one fixed 8 of 9 real date-drift misses in
    a 137-match real-data linkage test (137 -> 136 matched, only the
    "Auger-Aliassime" hyphen case remained -- see
    tennis_betfair_linkage._fold for that fix). Messages must be passed
    in file/chronological order (Betfair's historical files already are).

    Args:
        messages: An iterable of BetfairMarketChangeMessage, in the
            order they appear in the source file(s) -- typically every
            message parsed from one or more of a market's
            `1.<marketId>.bz2` files.

    Returns:
        A dict of market_id -> BetfairEventCandidate, one entry per
        market_id that ever produced a usable singles candidate (see
        to_singles_event_candidate). A market_id with no valid Match
        Odds definition anywhere in its history is simply absent, not
        an error -- callers get a coverage count for free from
        len(result) vs. the number of distinct market files scanned.
    """
    latest: dict[str, object] = {}
    for message in messages:
        candidate = to_singles_event_candidate(message)
        if candidate is not None:
            latest[message.market_id] = candidate
    return latest


def to_singles_event_candidate(message: BetfairMarketChangeMessage):
    """Build a tennis_betfair_linkage.BetfairEventCandidate from a
    market-change message that carries a full MATCH_ODDS market
    definition with exactly two runners (a tennis singles Match Odds
    market).

    **Real-data discovery (2026-09-16, Fraser's first Betfair BASIC
    sample):** a single tennis event on Betfair carries many market
    types beyond Match Odds under the same eventId -- SET_WINNER,
    SET_BETTING, HANDICAP, COMBINED_TOTAL, PLAYER_A/B_WIN_A_SET,
    NUMBER_OF_SETS, SET_CORRECT_SCORE, QUARTER_WINNER, TOURNAMENT_WINNER
    were all observed. Several of these (SET_WINNER in particular) also
    have exactly two runners, with the SAME two player names as the
    real Match Odds market for that event. Without the market_type
    check below, one real match produced 3 separate "singles
    candidates" (1 Match Odds + 2 Set Winner markets, confirmed against
    a real sample), which would make classify_tennis_betfair_match
    report a perfectly matchable real match as AMBIGUOUS purely because
    of this upstream duplication -- not because the match itself was
    ambiguous. Restricting to marketType == "MATCH_ODDS" is the fix.

    Returns:
        A BetfairEventCandidate, or None if this message doesn't carry
        a usable Match Odds market definition (e.g. it's a runner-
        price-only update, a non-Match-Odds market type, or it doesn't
        have exactly two runners -- doubles, walkovers-turned-void-
        markets, or a parsing surprise all fall here and are
        deliberately skipped rather than guessed at).
    """
    from prediction_markets_lab.normalisation.tennis_betfair_linkage import BetfairEventCandidate

    md = message.market_definition
    if md is None or md.market_time is None or md.event_id is None:
        return None
    if md.market_type != "MATCH_ODDS":
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
