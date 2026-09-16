# Workstream B -- Historical Scale-Up + Market-Edge Discovery Protocol

**Written 2026-09-16, in direct response to the operator's "WORKSTREAM B --
HISTORICAL SCALE-UP + MARKET-EDGE DISCOVERY" prompt**, which accepted the
January 2026 pipeline-validation checkpoint but corrected one thing: the
proposal in `WORKSTREAM_B_JANUARY_2026_OBSERVATION_REPORT.md` section 9 to
reserve "2026 onward" as an untouched market-edge holdout. That report's
own section 6 already linked outcomes, computed disagreement bins, and
looked at them -- January 2026 is therefore **market-edge EXPOSED**, not
untouched, and can never be used as a holdout. Section 9 of that report
now carries a correction note pointing here.

This document freezes the corrected chronological research design, the
2021-2025 acquisition/processing architecture (built and benchmarked
against real data below), and the discovery-phase rules -- all BEFORE any
2021-2025 market-edge outcome has been examined, per the operator's
explicit instruction: "DO NOT inspect 2021-2025 market-edge outcomes
until this research protocol is written and frozen." **No 2021-2025
Betfair data has been acquired yet.** Nothing below analyses outcomes;
everything below is architecture, design, and pre-registration.

---

## 1. Corrected holdout classification

| Period | Role |
|---|---|
| 2021-2023 | Market-edge **DISCOVERY / hypothesis generation** |
| 2024 | Market-edge **DEVELOPMENT VALIDATION** |
| 2025 | Market-edge **FINAL HISTORICAL OOS CONFIRMATION** |
| January 2026 | **ALREADY EXPOSED** -- pipeline-validation/exploratory only, permanently ineligible as a holdout |
| Future data acquired after this protocol is frozen | **TRUE PROSPECTIVE VALIDATION / paper-trading phase** |

2021-2025 remains legitimate for market-edge discovery/validation despite
already being used for Global Elo's own *predictive* validation/holdout
(Tennis Cycle 1): Elo is frozen and unmodified, and market-edge research
asks a different question (pricing error, not predictive accuracy) of
different target data (market prices, never touched by Cycle 1). Only
January 2026 is disqualified, because it specifically has already been
market-edge examined (`WORKSTREAM_B_JANUARY_2026_OBSERVATION_REPORT.md`
section 6). Global Elo remains permanently frozen from Tennis Cycle 1 --
nothing here retunes it using market results.

## 2. 2021-2025 acquisition/processing architecture -- built and benchmarked, not just designed

Per the operator's explicit instruction to verify the ingestion
architecture BEFORE asking Fraser for the larger download, a real,
runnable prototype was built and benchmarked against the existing real
Jan-Sep 2026 sample (as a stand-in for the not-yet-acquired 2021-2025
corpus): `src/prediction_markets_lab/ingestion/betfair_market_index.py`
(10 new unit tests, `tests/unit/test_betfair_market_index.py`).

**Design:**
- Raw downloaded files are never modified, moved, or deleted -- this
  script only reads them.
- Only the per-marketId `1.<marketId>.bz2` files are parsed; the
  redundant combined `<eventId>.bz2` capture (confirmed in the sample
  audit) is skipped by construction.
- Each per-market file's raw (still-compressed) bytes are SHA-256 hashed
  BEFORE decompression -- the provenance hash is over exactly what
  Fraser downloaded, never over anything derived.
- Each market's full message history reduces to one summary row (final
  marketDefinition fields, a compact per-runner price series) plus one
  manifest row (raw relative path, byte size, SHA-256) -- every
  consolidated row is traceable back to its untouched raw source file.
- Output is Parquet, written **one part-pair per calendar day** (the raw
  data's own natural chunk boundary) -- never one in-memory table
  spanning the whole multi-year corpus, so peak memory is bounded by the
  single busiest real day, not by how many years are being indexed.
- **Resumable by construction**: a day is skipped entirely (two
  `Path.exists()` checks, no I/O) if both its Parquet parts already
  exist. An interrupted run picks back up at the next unfinished day.

**Real benchmark (against the full real January 2026 month -- all 31
real days, run via `device_bash` on Fraser's machine):**

| Metric | Real value |
|---|---|
| Per-market files processed | 14,218 (of January's 17,502 real files; the other ~3,284 are the redundant combined per-event files, correctly skipped) |
| Raw bytes read | 26,809,663 (~25.6 MiB) |
| Parquet bytes written | 5,105,841 (~4.87 MiB) -- **5.25x smaller** than the already-compressed raw input |
| Total processing wall-clock (all days) | ~35.9 seconds |
| Average throughput | ~396 files/second |
| Peak resident memory | ~150-153 MB (bounded by the single busiest day, 830 files) |
| Resume on a fully-processed month | 0.0 seconds (all 31 days skipped) |
| Interrupted-run recovery | verified directly: one day's output file was deleted mid-experiment; re-running reprocessed only that one day (~1.35s) while the other 30 were skipped instantly |

**Extrapolation to the full 2021-2025 acquisition** (~1.07M total files
per the prior sizing estimate; per-market files are ~81.2% of that mix on
the real January sample, so ~869,000 files will actually be parsed):

- **Estimated processing time: ~37 minutes** (869,000 / 396 files/sec),
  on this same machine.
- **Estimated raw bytes actually parsed: ~1.64 GB** (of the ~2.7 GB total
  download, which also includes the skipped combined-event files).
- **Estimated consolidated Parquet index size: ~312 MB** -- trivial to
  store alongside the untouched ~2.7 GB raw archive.
- **Peak memory does not grow with corpus size** -- five years of daily
  chunks hit the same per-day ceiling as one month did (~150 MB), because
  the architecture never loads more than one day into memory.
- **Whole-corpus provenance fingerprint**: once acquired, the same
  manifest-fingerprinting method already used in
  `WORKSTREAM_B_SAMPLE_AUDIT_REPORT.md` section 1 (a single SHA-256 over
  the sorted `path:size:sha256` lines) will be computed over the full
  2021-2025 manifest, so the exact ingested corpus can always be proven
  to match a specific untouched raw download later.

This is a real, measured result, not a straight-line assumption -- the
only extrapolated numbers are the file-count scale-up itself (2026's
real market volume may not match 2021-2025's, exactly as already flagged
in the original size estimate).

## 3. Discovery families (2021-2023 only, once acquired -- not yet run)

Per the operator's list, refined to what real BASIC-tier data can
actually support (no back/lay ladder or volume, confirmed twice now):

1. Model-market probability disagreement (signed and absolute) --
   `model_market_probability_delta`, already computed by
   `market_observation.py`.
2. Favourite vs. underdog (by model probability, and separately by
   market-reference probability -- these can disagree on which side is
   "the favourite").
3. Market-reference probability band (e.g. deciles).
4. Rank gap (already a first-class feature from A3/A4).
5. Elo gap (the same underlying number as #4's model side).
6. Elo-vs-ranking disagreement (both already computed in A3/A4; new here
   is comparing that disagreement against the market rather than outcome
   alone).
7. Surface.
8. Tournament level / best-of format.
9. Recent form / surface form (A4 step D features, reused unmodified).
10. Congestion/rest (A4 step D feature, reused unmodified).
11. Time-to-start of the observation (the horizon dimension itself --
    does disagreement/accuracy change closer to start?).
12. Price movement between two horizons for the same match (e.g. 3h vs.
    30min reference probability delta) -- a CLV-style feature, still
    labelled non-executable per BASIC's limitations.
13. Favourite-longshot bias proxy (market-reference probability vs.
    realised outcome rate, binned -- distinct from #2/#3 in that it's a
    market-calibration check, not a model-comparison one).

**Explicitly not attempted on BASIC data**: any liquidity or execution-cost
proxy (no volume/back-lay data exists at this tier), and anything
requiring in-play ticks beyond what's already captured.

## 4. Multiple-testing / data-mining controls (frozen before discovery starts)

- Every family in section 3 is tested via **one pre-declared metric per
  family** (outcome-rate-by-bin delta from the naive baseline, exactly
  section 6's style in the January report) plus a bootstrap CI -- not a
  grid of arbitrary thresholds per family.
- **13 families = 13 primary comparisons.** A Bonferroni-style corrected
  significance level is used for promotion decisions (mirroring the
  precedent already set in A4 step D's 3-family Bonferroni correction at
  98.33% per-comparison level) -- for 13 families the per-comparison
  level is adjusted accordingly (95% family-wise -> ~99.6% per-comparison
  under a strict Bonferroni bound) and stated explicitly in the discovery
  report before any 2024 test is run.
- A family that would require scanning many bin-edge choices to find a
  "best" split (e.g. rank-gap threshold) is evaluated on **pre-declared,
  round-number bins** (deciles, or natural categories like surface/format)
  -- never on a threshold chosen after seeing which one looks best.
- The exact number of families explored (13), the number of comparisons
  actually run per family, and which ones were dropped for
  BASIC-tier-support reasons are recorded in the eventual discovery
  report, win or lose -- a family that produces nothing is reported as a
  null, not omitted.

## 5. Hypothesis-promotion gate (2021-2023 discovery -> candidate)

A discovery-phase finding may be pre-registered as a candidate hypothesis
for 2024 testing only if it has, simultaneously:

- a plausible, statable mechanism (not just "the number came out
  significant");
- adequate sample size for its subgroup (a rule of thumb consistent with
  this project's existing small-N caution: no subgroup below roughly 150
  observations is promoted, given the January pass's N=39 extreme bins
  were explicitly judged too small to trust);
- an effect size and bootstrap CI that clears the corrected significance
  level from section 4;
- stability across at least two disjoint sub-periods within 2021-2023
  (e.g. 2021-2022 vs. 2023) -- a pattern present in only one sub-period is
  not promoted;
- stability across at least the surface and tournament-level subgroups
  checked in A3 (not necessarily significant in each, but not reversing
  sign);
- no identifiable leakage path (the same standard already applied to
  every A3/A4 feature);
- robustness to a reasonable alternate binning of the same family (e.g.
  quintiles vs. deciles don't flip the conclusion);
- some stated economic plausibility (even though BASIC can't compute
  realised EV, the direction/magnitude should be large enough that it
  plausibly survives commission and realistic slippage once paid-tier
  data is eventually available -- a token check, not a real EV
  calculation).

Every discovery-phase result -- promoted or not -- is recorded, including
explicit nulls, exactly as A4 step D recorded its clean null result.

## 6. 2024 development validation (only pre-registered candidates tested)

- Test only hypotheses promoted under section 5, using the exact metric,
  bins, and direction pre-registered at promotion time.
- No threshold changes after seeing 2024.
- Each candidate classified **PROMOTE / PARTIAL / REJECT** using the same
  kind of mutually-exclusive, pre-declared decision function already
  built for the Tennis Cycle 1 holdout
  (`src/prediction_markets_lab/research/holdout_verdict.py`) --
  reused/extended for market-edge criteria rather than rebuilt from
  scratch, since that module's ordered, boundary-tested classification
  logic is exactly the discipline this needs.
- Only PROMOTE-classified candidates proceed to 2025.

## 7. 2025 historical OOS confirmation (evaluated once)

- Surviving 2024 candidates are evaluated exactly once on 2025.
- No rescue tuning, no threshold changes, no post-hoc filters.
- A failed 2025 result is a failed hypothesis, reported as such -- exactly
  the discipline already applied to Tennis Cycle 1's own PARTIAL holdout
  verdict, which was not "rescued" after the fact.

## 8. Market-quality metrics reported per surviving candidate

N; model probability; market-reference probability; probability delta;
outcome frequency; log-loss/Brier comparison where applicable;
calibration slope/intercept; effect size; bootstrap CI; stability across
the sub-periods and subgroups checked in section 5; and, where available,
reference-price movement (the CLV-style feature from family #12). Any
return-style number computed from BASIC last-traded prices is always
labelled **NON-EXECUTABLE RESEARCH PROXY**, per the January report's
existing discipline -- never "realised EV" or "executable ROI."

## 9. Eventual profitability gate (unchanged from the existing protocol)

A candidate must still survive, in order: pricing-error discovery ->
chronological validation (sections 5-7) -> historical OOS -> executable
back/lay data (a paid tier decision, not made now) -> commission-aware
net EV -> realistic slippage/liquidity -> bankroll/risk modelling ->
prospective paper trading -> small live validation. Only after all of
that can anything become BET / WATCH / REJECT. This restates
`WORKSTREAM_B_MARKET_AWARE_RESEARCH_PROTOCOL.md` sections 9-10 and is not
re-specified further here.

## 10. Not authorised by this document

The 2021-2025 Betfair download itself (Fraser's manual action, not yet
taken); any 2021-2025 outcome analysis of any kind (blocked until this
document is confirmed frozen); any paid Betfair tier; any betting
threshold or EV/edge computation; Football Cycle 2; any new tennis
predictive-modelling cycle; paper trading; live betting.

## 11. Tests / commits

10 new tests (`test_betfair_market_index.py`), all passing; 629/629 tests
passing project-wide (619 before this update). New dependency: `pyarrow`
(added to `requirements.txt` and `pyproject.toml`) -- free, open-source,
consistent with the project's zero-cost tooling constraint. No 2021-2025
outcome code has been written -- only ingestion architecture and this
design document.

## 12. Fraser's exact next manual action

Unchanged in kind from the January download: sign in at
historicdata.betfair.com with the existing account, select **Tennis +
BASIC (free) tier + 2021-2025** (as one combined range or five yearly
downloads, whichever the portal offers more easily), and hand the folder
over the same way the January sample was connected. No payment, no new
account step, no jurisdiction re-check needed (already confirmed). Once
the folder is available, `betfair_market_index.py` builds the
consolidated index from it directly -- no other manual step is required
before discovery (section 3) can begin, and discovery will not begin
until this protocol is confirmed by the operator/Fraser per the "DO NOT
inspect 2021-2025 market-edge outcomes until this research protocol is
written and frozen" instruction.


## 13. Update 2026-09-16 (same day) -- Phase 1 (ACQUIRE/AUDIT/CONSOLIDATE/LINK) complete on real 2021-2025 data

Full detail: `WORKSTREAM_B_2021_2025_PHASE1_AUDIT_REPORT.md`.

Fraser downloaded and connected the real 2021-2025 Betfair BASIC archive
(996,779 files, one `data.tar`, SHA-256
`cd2c9203581d30be1e4e4a3839d7e75b2bb7ec1e4bcb982b6a4ab44cd1c7668a`). The
ingestion architecture from section 2 was extended (not redesigned) to
read directly from a tar archive (`run_over_tar`), since this bulk
request arrived packaged differently than the Jan-Sep 2026 sample. Full
consolidation completed: 792,845 real per-market files, 276.5MB Parquet
index, 5.44x compression, fully resumable (verified).

**Real linkage result: 88.96% MATCHED (12,956 usable matches), 3.43%
AMBIGUOUS, 7.61% UNMATCHED** -- a genuine, investigated, now-explained
regression from January's 100% (TML-Database's `tourney_date` is a
tournament START date, not a per-match date; fixed via an empirically
chosen 14-day linkage window plus exclusion of zero-price "ghost" duplicate
markets). 61.4% of UNMATCHED are Davis Cup ties (a likely genuine Betfair
coverage gap, not a bug). Pre-match price coverage at scale is thinner
than January's sample (78.3% vs 99.3% at 30min) -- Phase 2 discovery
should re-check coverage by subgroup rather than assume January's numbers
carry over.

**No 2021-2025 market-edge/outcome analysis has been performed.** This
satisfies Phase 1 of the operator's directive ("do not inspect strategy
results until these checks pass"); Phase 2 (2021-2023 discovery) awaits
confirmation.
