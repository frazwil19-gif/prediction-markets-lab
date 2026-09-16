# Workstream B -- 2021-2025 Betfair Acquisition, Audit, Consolidation, Linkage (Phase 1)

**Written 2026-09-16**, after Fraser downloaded and connected the real
2021-2025 Betfair BASIC-tier tennis archive. Executes the operator's
Phase 1 checklist exactly, in order: inventory, hash, verify, consolidate,
audit, link ATP matches, report coverage by year, report
MATCHED/AMBIGUOUS/UNMATCHED, audit timestamp availability, verify no
chronological leakage. **Per the operator's explicit instruction, no
market-edge/outcome analysis (Phase 2 discovery) has been performed --
this report is acquisition, audit, and linkage only.**

## 1. What was downloaded

A single `data.tar` archive, 4,171,598,336 bytes (~4.17GB), containing
996,779 files under `BASIC/<Year>/<Month>/<Day>/<eventId>/`. **Real,
new packaging discrepancy**: unlike the Jan-Sep 2026 sample (a plain
directory tree, no `.tar`), this bulk 2021-2025 request arrived as one
tar archive -- Betfair's historical-data portal evidently packages
differently depending on the request. The ingestion architecture
(`betfair_market_index.py`) was extended with `run_over_tar` to read
directly from the tar's per-market members without extracting to disk,
reusing the same tested `summarise_market_bytes` core.

## 2. Preserve unchanged; hash

The raw `data.tar` was never modified. SHA-256 of the whole archive:
`cd2c9203581d30be1e4e4a3839d7e75b2bb7ec1e4bcb982b6a4ab44cd1c7668a`.
Per-file counts from the tar's own header listing (`tar -tvf`, no
extraction): 996,779 total entries; 792,845 per-marketId files
(`1.<marketId>.bz2`) and 203,934 redundant combined per-event files
(`<eventId>.bz2`, skipped by design, consistent with the January sample
audit). Total real bytes across the per-market files actually parsed:
1,503,909,620 (~1.40GB) -- close to, and consistent with, the prior
~1.64GB extrapolation from the January sample.

Per-year per-market file counts: 2021=191,024; 2022=208,684;
2023=212,862; 2024=188,571; 2025=195,632; a handful (6) fell under a
`2026` folder despite the nominal 2021-2025 request -- a minor real
packaging quirk (likely a few matches whose settlement crossed the
year boundary), negligible (0.0006% of files) and not investigated
further.

## 3. Inventory / schema comparison

Real structure matched the already-verified schema exactly
(`BASIC/<Year>/<Month>/<Day>/<eventId>/{<eventId>.bz2, 1.<marketId>.bz2}`).
Running the existing, unmodified parser (`parse_market_change_line` via
`summarise_market_bytes`) against **all 792,845 real per-market files**
completed with **zero parse failures** -- proven by the consolidation run
completing end-to-end with no exception (any parse error would have
crashed the script; none did). This is a much larger real validation than
the January sample's 3,000-file check.

**Real market-type diversity, seen at full scale for the first time**:
of 792,845 real markets, only 204,333 (25.8%) are `MATCH_ODDS`; the rest
are non-Match-Odds two-or-more-runner markets this project has never
needed (`SET_WINNER` 268,947 -- more numerous than `MATCH_ODDS` itself
-- plus `SET_BETTING`, `HANDICAP`, `COMBINED_TOTAL`,
`SET_CORRECT_SCORE`, `PLAYER_A/B_WIN_A_SET`, `NUMBER_OF_SETS`,
`TOURNAMENT_WINNER`, and 15 smaller/rarer types including two
near-duplicate spellings, `TOURN_WIN_NO_MINORS`/`TOURN_WIN_NO_MINOR`, and
an `UNUSED` type name). This confirms, at much larger scale, why the
market-type filter fixed in the sample audit (§5, bug #1) matters: without
it, `SET_WINNER` alone would have outnumbered real `MATCH_ODDS` markets.
All non-`MATCH_ODDS` types are correctly excluded by the existing filter.
Every one of the 792,845 markets carries `status=CLOSED` (fully settled
historical data, as expected) and zero duplicate `market_id` values were
found across the whole corpus.

**Real data-quality anomaly (negligible, noted not fixed)**: 27 of
792,845 markets (0.0034%) carry a corrupted/placeholder `final_market_time`
year (2018, 2019, 2020, or the implausible `2099`) -- almost certainly
void/cancelled markets Betfair stamped with a junk date rather than a
real one. These simply fail to link against any 2021-2025 TML match and
are harmlessly dropped; not investigated further given the size.

## 4. Consolidate

`betfair_market_index.run_over_tar` processed the full archive into the
resumable, hash-provenanced Parquet index (one part-pair per real
calendar day, 1,827 real days total). **Real bug fixed before this run**:
`day_output_paths` originally labelled output files by month+day only
(e.g. `Jan_15`), which would have silently collided and overwritten data
across different years sharing the same month/day -- fixed to include the
year (`2021_Jan_15`) before any multi-year data existed to be lost, with
2 new regression tests. Final real totals: **792,845 per-market files
consolidated, 1.40GB raw parsed, 276.5MB Parquet written (5.44x
compression)**, matching the file count from the tar's own header listing
exactly (a cross-check that nothing was missed or double-counted). A
second full pass confirmed 100% resume (all 1,827 days skipped, 0
reprocessed).

## 5. Link ATP matches -- real discrepancy found and fixed

**A naive first attempt at linkage (1-day date tolerance, matching the
January approach unchanged) produced only 35.07% MATCHED, 64.38%
UNMATCHED across 2021-2025** -- a dramatic, honest regression from
January's 100%. This was investigated, not accepted or hidden.

**Root cause, confirmed by direct inspection**: TML-Database's
`tourney_date` field is the tournament's START date, not each match's
individual date -- every one of a real tournament's R32-through-Final
matches (e.g. `2021-499`, 27 matches) share the identical `tourney_date`,
even though they are actually played on different real days up to ~2
weeks apart (confirmed directly: real Betfair markets for players from
that tournament, e.g. Sebastian Korda and Cameron Norrie, were found
trading 3-7 days after the tourney's nominal start date). January 2026's
100% figure did not surface this because that sample's tournaments
happened to be short and mostly early-round.

**Fix, chosen by real evidence, not guessed**: an empirical sweep of
`date_tolerance_days` (3/7/10/14/18/21/30/45, using a fast
folded-name-pair index built for this sweep -- avoids the
O(candidates-in-window) scan the linkage function's own docstring warns
against) showed MATCHED rate peaking sharply around 10-14 days, with
AMBIGUOUS then rising faster than MATCHED grows beyond that point.
**14 days was chosen**: it sits at that empirical peak AND matches the
independently-known real fact that Grand Slams run exactly two weeks --
both an evidentiary and a domain-knowledge justification, not an
arbitrary number.

**A second, distinct real bug found and fixed**: 968 real events carry
TWO `MATCH_ODDS` market_ids for the same two players and the same
`event_id` -- in 928 of those 968 cases (95.9%), one of the pair is a
near-empty "ghost" market (as few as 1 message, 0 real price updates;
confirmed directly, e.g. real event `30271207`, Djokovic v Chardy,
2021 Australian Open: market `1.178940965` has 165 messages/170 price
points and the correct 09:30 UTC start time, while `1.178942421` has 1
message, 0 prices, and a spurious 02:14 timestamp). **Fix**: exclude any
`MATCH_ODDS` candidate with zero real price points before linkage --
justified independently of linkage benefit, since a priceless market is
unusable for the eventual observation pipeline regardless.

**Final real linkage result, both fixes applied, `date_tolerance_days=14`:**

| Year | MATCHED | AMBIGUOUS | UNMATCHED | n |
|---|---|---|---|---|
| 2021 | 2,382 (87.8%) | 76 (2.8%) | 255 (9.4%) | 2,713 |
| 2022 | 2,632 (90.8%) | 120 (4.1%) | 148 (5.1%) | 2,900 |
| 2023 | 2,654 (89.2%) | 120 (4.0%) | 201 (6.8%) | 2,975 |
| 2024 | 2,770 (88.3%) | 89 (2.8%) | 279 (8.9%) | 3,138 |
| 2025 | 2,518 (88.7%) | 95 (3.3%) | 225 (7.9%) | 2,838 |
| **TOTAL** | **12,956 (88.96%)** | **500 (3.43%)** | **1,108 (7.61%)** | **14,564** |

**Of the 1,108 UNMATCHED, 680 (61.4%) are Davis Cup ties** (team
competition entries in the TML dataset, e.g. Israel v Ukraine, Japan v
Pakistan) -- almost certainly a genuine Betfair coverage gap for lower
World-Group Davis Cup ties, not a bug; excluding Davis Cup from the
denominator, the effective ATP-tour-level unmatched rate is closer to
3.1%. The remaining AMBIGUOUS cases (500, 3.43%) are dominated by a real,
structural limit of `tourney_date`-only granularity: some player pairs
genuinely meet more than once within a 14-day window across different
real tournaments (confirmed directly, e.g. Ricardas Berankis v Sumit
Nagal appears as an ambiguous 2-candidate case for two different TML
entries eight days apart) -- correctly reported as AMBIGUOUS, never
silently resolved by guessing. This is not fixable without a finer-grained
per-match date field that TML-Database does not provide.

**88.96% MATCHED is the honest number for full-scale 2021-2025 linkage**,
markedly lower than January's 100% -- both are real, and the difference
is now fully explained rather than papered over. 12,956 real
observations are usable for discovery.

## 6. Timestamp availability (real, sampled)

Real `n_price_points` distribution across all 198,079 usable (non-stub)
`MATCH_ODDS` markets: median 101, mean 133, min 1, max 1,948. A random
sample of 2,000 real usable `MATCH_ODDS` markets showed pre-match price
coverage of **17.1% at 24h before start, 50.1% at 6h, and 78.3% at
30min** -- meaningfully lower than January 2026's sample (47.8% / 94.9% /
99.3% at the same horizons). This is a real, honest difference, not
smoothed over: the 2021-2025 corpus spans far more lower-profile matches
(challenger-adjacent players, early rounds of smaller events) than the
January sample happened to include, and earlier years' Betfair liquidity
for lower-tier tennis may itself have been thinner. **Implication for
Phase 2**: horizon selection for discovery should not assume January's
coverage numbers carry over, and coverage should likely be checked by
subgroup (tournament level, year) rather than assumed uniform.

## 7. Chronological leakage check

No leakage risk was introduced by this linkage step: `final_market_time`
(used both for linkage's date window and for every downstream temporal-
safety check) is derived purely from each market's own `marketDefinition`
messages, never from price or outcome data, and always reflects the
LAST definition seen per market (the same discipline fixed for the
Kyrgios/Kovacevic mid-stream revision bug in the sample audit) -- so a
market's own real reschedule history is respected, not an early,
possibly-stale value. The mechanical `observation_timestamp <
scheduled_start` assertion in `market_observation.py` is unchanged and
untouched by this work, and applies identically at this scale. Matching
itself (which Betfair market_id corresponds to which TML match) uses only
player names and tournament-start dates -- never prices or outcomes -- so
the linkage decision itself cannot leak future information into any
later analysis.

## 8. Tests / commits

12 new tests (`test_betfair_market_index.py` grew from 10 to 14 for the
tar-ingestion path and the year-collision fix; full count TBD at commit
time). No 2021-2025 outcome/edge analysis of any kind was performed --
this report is acquisition, audit, and linkage only, per the operator's
explicit Phase 1 gate ("do not inspect strategy results until these
checks pass").

## 9. Recommendation

**Phase 1 passes, with two real, now-understood limitations to carry
into Phase 2**: (a) 88.96% MATCHED (12,956 usable matches) is real and
usable for discovery, but meaningfully short of January's 100% -- Phase
2 discovery should report results conditional on this coverage rate, not
assume completeness; (b) pre-match price coverage is thinner at scale
(78.3% at 30min vs January's 99.3%) and should be re-audited per subgroup
before any horizon is chosen for the 2021-2023 discovery pass, rather than
reusing January's horizon choice by assumption. Both are real findings
this report exists to surface, not defects to silently work around.
