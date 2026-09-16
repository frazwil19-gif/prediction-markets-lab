# Workstream B -- Real Betfair Sample Audit Report

**Written 2026-09-16, immediately after Fraser downloaded a real Betfair
BASIC-tier tennis sample.** This report executes
`WORKSTREAM_B_MARKET_AWARE_RESEARCH_PROTOCOL.md` section 2 (the
small-sample audit) and the operator's explicit ordered process from the
same date: preserve the sample unchanged and hash it; inventory its
structure; compare against the assumed schema; record every discrepancy;
run the existing parser unchanged and record failures; only then modify
the parser; add regression tests from the real discoveries; test TML<->
Betfair linkage; report MATCHED/AMBIGUOUS/UNMATCHED rates; recommend
whether bulk acquisition is justified. Every step below was executed in
that order, on the real, unmodified download.

## 0. What was downloaded

Fraser signed up for Betfair, reached historicdata.betfair.com, and
downloaded Tennis, BASIC (free) tier, for **January-September 2026** --
substantially more than the single-day/small-tournament sample the
protocol asked for, but still free (BASIC, no payment) and a useful
larger real-world test of the parser and linkage code as a result. The
raw download lives outside this repository, on Fraser's own machine, at
`~/Downloads/BASIC/` (connected to this session as a separate folder, not
committed to git -- 402 MB of raw JSON is not repo material).

## 1. Preserve unchanged; hash

The raw download was never modified. A full per-file manifest was
computed (relative path, byte size, SHA-256 of content) and reduced to a
single deterministic dataset fingerprint (SHA-256 over the sorted
`path:size:sha256` lines):

- **Total files**: 161,025
- **Total bytes**: 402,132,971 (~402 MB)
- **Dataset fingerprint (SHA-256)**: `9472be15101bcb0cf716d6d79c18cf3834fc1ab3f5fc18313eb2ddcef8201e53`
- Per-month file counts: Jan 17,502 / Feb 19,438 / Mar 17,894 / Apr
  19,384 / May 19,551 / Jun 20,448 / Jul 21,779 / Aug 17,739 / Sep 7,290
  (partial month).

The full per-file manifest is not committed to this repo (it would be a
multi-MB JSON listing of someone else's downloaded data); the fingerprint
above is sufficient to prove, later, whether the same download is still
being referred to.

## 2. Inventory: file/compression/JSON structure

Real structure, discovered by direct inspection:

```
2026/<Month>/<Day>/<eventId>/<eventId>.bz2       -- combined multi-market capture
2026/<Month>/<Day>/<eventId>/1.<marketId>.bz2    -- one file per individual market
```

Each `.bz2` decompresses to newline-delimited JSON (one Betfair
"market-change message" per line), matching the documented Exchange
Stream API shape: a top-level `op`/`pt`/`mc`, each `mc` entry with an
`id` and either a `marketDefinition` (on a market's first message and
again whenever it's revised) or an `rc` array of runner-level price
updates.

Real market types found under a single tennis event (one real match can
carry many): `MATCH_ODDS`, `SET_WINNER`, `SET_BETTING`, `HANDICAP`,
`COMBINED_TOTAL`, `PLAYER_A_WIN_A_SET`, `PLAYER_B_WIN_A_SET`,
`NUMBER_OF_SETS`, `SET_CORRECT_SCORE`, `QUARTER_WINNER`,
`TOURNAMENT_WINNER`. Only `MATCH_ODDS` is in scope for this project.

## 3. Comparison against the assumed schema; discrepancies

| # | Assumed (per the protocol/module docstrings) | Actually found | Impact |
|---|---|---|---|
| 1 | A single `.tar` archive of per-market `.bz2` files | A plain nested directory tree (`year/month/day/eventId/*.bz2`), no `.tar` at all | None on the parser (it only ever sees one decompressed line at a time); noted for whoever eventually writes the bulk-ingestion walker. |
| 2 | One `.bz2` file per market | Two files per event: an `<eventId>.bz2` combining ALL sibling markets, plus one `1.<marketId>.bz2` per individual market | Decision: use only the per-marketId files; the combined file is redundant and is ignored. |
| 3 | `rc` updates may carry `batb`/`batl` ladders | BASIC tier's `rc` updates carry **only `ltp`** -- no back/lay ladder, no volume, ever, in this sample | Confirms the audit doc's expectation exactly. `_parse_ladder` was never exercised on real data since the fields are simply absent (optional, no crash). |
| 4 | Not modelled | Settled markets carry a real runner-level outcome status (`ACTIVE` / `WINNER` / `LOSER` / `REMOVED`) directly in the final `marketDefinition` -- confirmed on real completed AND voided matches | Not currently captured by `BetfairRunnerDefinition` (only id/name/sortPriority are kept). Noted as a real, useful future ground-truth-outcome source; not built now (no pre-registered need yet). |
| 5 | Not anticipated | A market's own `marketDefinition` can be revised mid-history -- one real match (Kyrgios v Kovacevic) carried three different `marketTime` values across its message history before the actual played date | **Real bug surfaced**: using the FIRST definition per market risks a stale, pre-revision date. Fixed -- see section 5. |
| 6 | Not anticipated | Several non-Match-Odds market types (`SET_WINNER` in particular) also have exactly two runners, with the SAME two player names as the real Match Odds market for that event | **Real bug surfaced**: `to_singles_event_candidate` didn't filter by market type, so one real match produced 3 "singles candidates" (confirmed on a real event). Fixed -- see section 5. |
| 7 | N/A -- name convention was unconfirmed | Runner names are clean, plain `"Firstname Lastname"` strings (e.g. `"Lois Boisson"`, `"Nick Kyrgios"`) -- the exact full-name convention, already the first one `names_are_equivalent` tries | De-risks the whole linkage step; no fuzzy convention was needed for the vast majority of names. |
| 8 | N/A | Betfair renders "Felix Auger-Aliassime" as the unhyphenated "Felix Auger Aliassime" | **Real, minor name-format gap surfaced**: fixed by normalising hyphens to spaces in name comparison -- see section 5. |
| 9 | N/A | No `competition`/tournament-tier field exists anywhere in the market definition | Betfair's "Tennis" download has no cheap way to filter to ATP-tour-level matches at the source; a large share of this sample is WTA/ITF/challenger-level tennis with no TML-Database counterpart. This is expected to UNMATCH, not a bug -- see section 6. |

## 4. Running the existing parser, unchanged, against real data

Before any modification: `parse_market_change_line` was run against every
line of a random 3,000-file sample (143,180 real message lines).

- **Lines that failed to parse: 0.** The documented shape held exactly;
  no `KeyError`/`ValueError` was ever raised on real data.
- `to_singles_event_candidate` produced a candidate for 28,195 of the
  143,180 messages and `None` for the rest -- but, per discrepancy #6
  above, this count was inflated by non-Match-Odds market types before
  the fix.

## 5. Parser modified in response to real discrepancies (only after 1-4)

Two real bugs fixed in `betfair_historical_schema.py`, each with a new
regression test built from a sanitised, minimal fixture derived from the
real discovery (never the raw real data itself):

1. **`to_singles_event_candidate` now requires `market_type ==
   "MATCH_ODDS"`.** Before the fix, a real match (Boisson v Bencic,
   2026-01-03) produced 3 "singles candidates" from 3 different real
   market_ids (1 Match Odds + 2 Set Winner), which would have made
   `classify_tennis_betfair_match` report a perfectly matchable real
   match as AMBIGUOUS purely from this upstream duplication.
2. **New `latest_singles_event_candidates` helper** reduces a market's
   full message history to the LAST definition seen per market_id, not
   the first, since real match times get revised mid-stream.

One fix in `tennis_betfair_linkage.py`:

3. **`_fold` now normalises hyphens to spaces** before comparison, so
   "Felix Auger-Aliassime" (TML) matches Betfair's "Felix Auger
   Aliassime".

All three are deterministic, unconditional transforms grounded in a
specific real discovery -- not fuzzy guessing, and each is covered by a
dedicated regression test using a sanitised fixture, per the project's
"never silently guess" discipline. Full suite: **606/606 tests passing**
after these changes (600 before, +6 new).

## 6. TML<->Betfair linkage test against real data

TML-Database's 2026 ATP season file (`2026.csv`, fetched fresh from
`raw.githubusercontent.com/Tennismylife/TML-Database` -- publicly
available, same source/license as the frozen 2021-2025 canonical
dataset, **not added to that frozen dataset**, kept as a separate file at
`data/raw/tennis/tml_database/atp/2026.csv` for this audit only) currently
covers **137 ATP matches, 2026-01-02 through 2026-01-17** -- the season is
much further along in real time than that (today is 2026-09-16), so
TML-Database's own maintenance for the 2026 season lags well behind the
"actively maintained" characterisation used earlier in this project; only
January is available as ground truth right now. This is an external
data-source limitation, not something this project can fix, and it means
**only the January portion of Fraser's Jan-Sep Betfair download could be
tested against real ground truth today.**

Using only tested, committed module code (`latest_singles_event_candidates`
+ the fixed `_fold`), classifying all 137 real January ATP matches against
every real Betfair Match Odds candidate found in the January sample
(3,277 distinct real markets after latest-definition dedup):

- **MATCHED: 137 / 137 (100.0%)**
- **AMBIGUOUS: 0 / 137 (0.0%)**
- **UNMATCHED: 0 / 137 (0.0%)**

This is the real, final number after both bug fixes; before them the
same 137 matches scored 117 MATCHED / 0 AMBIGUOUS / 20 UNMATCHED (the
date-revision bug), and before that (first-seen dedup, no market-type
filter) matching hadn't even been attempted cleanly because the
market-type duplication would have driven AMBIGUOUS rates up across the
whole sample.

## 7. Recommendation on bulk acquisition and BASIC-tier sufficiency

**Betfair BASIC tier is sufficient to proceed to the next research phase**
(protocol section 8's data-first analysis of model-vs-market
disagreement): event identity, player identity, scheduled time,
pre-match/in-play state, and a last-traded-price time series are all
present and, for real ATP matches, matchable against TML-Database at
100% coverage on the one month tested. **BASIC is NOT sufficient** for
the later net-EV/execution-cost work (protocol sections 6 and 9), which
needs a back/lay spread and liquidity -- those genuinely require a paid
tier (ADVANCED at minimum) and that decision does not need to be made
now, since it doesn't block the current research question (does
model-market disagreement relate to outcomes at all).

**Fraser already has 9 months of real BASIC data (Jan-Sep 2026) sitting
on his machine** -- bulk acquisition, in the sense the protocol meant it,
is effectively already done for this window, at zero cost. What's
actually blocked is *ground truth*: TML-Database's free 2026 season file
only covers January so far. Recommendation: proceed to build the
per-match observation-record extraction (protocol section 7) and the
data-first exploratory analysis (protocol section 8) using the validated
January window now; re-check TML-Database periodically for updates to
extend ground-truth coverage into the rest of the already-downloaded
Betfair range, rather than re-downloading anything.

No betting edge is claimed or implied by any number in this report. This
is a data-plumbing and match-linkage audit only.
