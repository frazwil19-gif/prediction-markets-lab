# Football Cycle 2 -- Discovery Checkpoint (Step H)

This checkpoint answers, in order, the operator's 17-point return list
from the "GO on re-extraction/discovery" execution plan (2026-09-16).
It covers steps A-H, run autonomously as instructed, stopping here
(before formal validation of any newly discovered hypothesis and
before any new external data acquisition), exactly as directed.

Everything below is grounded in code that ran against the real
5,800-match dataset and in files committed to
`prediction-markets-lab` at commits `413ebd3` through `8155205`
(listed in full at point 16). No number in this report is invented or
extrapolated from a partial run.

---

## 1. Exact fields discovered

From the raw Football-Data.co.uk files already downloaded for Cycle 1
(never re-fetched), extracted for the first time this cycle:

- **Match statistics** (produced BY the match, never a same-match
  feature): full-time home/away shots, shots on target, corners,
  fouls, yellow cards, red cards, referee identity.
- **Two new markets**, each at opening AND closing prices: **Over/Under
  2.5 goals** and **Asian Handicap** (plus the AH reference line
  itself, opening and closing).
- Individual-bookmaker coverage for the two new markets is narrower
  than 1X2's six-bookmaker panel: only **Bet365 (B365) and Pinnacle
  (P)** cover the full 2020/21-2024/25 corpus; **Betfair Exchange
  (BFE)** appears only from 2024/25. Football-Data's own cross-
  bookmaker summary statistics, **Max** and **Avg**, are also
  extracted and kept explicitly labelled as the source's own
  computation, not something this project built.

## 2. Coverage by league/season

A full competition x season header sweep (not assumed) confirmed:
match statistics, O/U 2.5, and AH (B365, P, Max, Avg) are present at
**100% of files** across all 15 competition x season combinations
(E0/E1/SC0 x 2020/21-2024/25). BFE and a third 1X2 bookmaker (1XB)
appear only in 2024/25, all three competitions. Extracted output:
5,800 match rows, 100% coverage on match statistics and both new
markets' opening/closing snapshots.

## 3. Price fields and verified semantics

Verified against every raw file in the repo plus
`football-data.co.uk/notes.txt` directly (not assumed from memory):
closing columns insert a single "C" immediately after the bookmaker
prefix, uniformly across 1X2/O-U/AH (e.g. `B365>2.5` ->
`B365C>2.5`). "Opening" prices are collected at a fixed pre-match time
(Tue/Fri afternoon), not a true market-open snapshot -- both
timestamps precede kickoff, so both are legitimate pre-match features
requiring no leakage lag. **Max** is a per-side, cross-bookmaker best
price -- NOT a coherent two-sided book (the two sides need not share a
bookmaker) and is never margin-removed or converted to a probability.
**Avg** is a per-side, cross-bookmaker mean -- treated as a
market-consensus proxy after margin removal, but explicitly labelled
as the source's own computation. This correction was made mid-cycle,
after an initial run using the wrong (1X2-style, six-bookmaker)
extraction defaults silently produced zero market-consensus rows for
the new markets -- caught and fixed before proceeding (see
`football_richer_extraction.py`'s module docstring for the full
writeup).

## 4. Canonical dataset size

- `cycle_002_match_statistics.csv`: 5,800 rows (100% of Cycle 1's
  match set).
- `cycle_002_bookmaker_markets_ou25.csv` / `..._ah.csv`: 25,454 /
  25,415 individual-bookmaker price rows.
- `cycle_002_market_context_ou25.csv` / `..._ah.csv`: 11,600 rows each
  (5,800 matches x 2 timings), 100% source-Avg coverage, >99.6%
  individual-bookmaker-median coverage.
- `cycle_002_discovery_features.csv` (step D's output): 5,800 rows,
  157 columns, combining Elo, rolling team-form, and market-derived
  features. 93.2% of rows carry a full 10-match rolling history for
  both teams (the remainder are teams' early-season/early-dataset
  matches, correctly showing fewer prior matches rather than being
  imputed).
- All join 1:1 by `match_id` against Cycle 1's frozen
  `cycle_001_matches_full.csv` (5,800 = 5,800, verified exactly).

## 5. Leakage controls

Rolling match-statistics features (`features/football_leakage_safe_features.py`)
follow a get-snapshot-before-push discipline identical to the existing,
already-tested `football_elo.py` Elo model: a team's pre-match snapshot
is read before that match's own stats are folded into its history.
Verified mechanically, not just asserted: two dedicated tests perturb
(a) a match's own stats and (b) a later match's stats, and assert an
earlier snapshot is byte-identical in both cases. Market
opening/closing fields need no lag (both precede kickoff -- point 3).
Elo ratings are a pure replay of the existing frozen model with no new
fitting. 12/12 new feature tests plus the pre-existing Elo leakage
tests all pass.

## 6. Chronological split used/proposed

**Frozen, documented in full in**
`CYCLE_002_CHRONOLOGICAL_SPLIT_DECISION.md`. Headline finding: Stage
3B's model-vs-market exposure is broader than earlier project framing
had it -- it spans the ENTIRE 2020/21-2024/25 corpus (both the
walk-forward development folds, N=3,446, AND the sealed 2024/25
holdout, N=1,160), not 2024/25 alone. Given that, **no genuine sealed
historical OOS survives inside the existing corpus.** Decision: the
full corpus is discovery+development only; discovery uses 2020/21-
2022/23 (N=3,480), 2023/24-2024/25 (N=2,320) serves only as a
non-blind internal stability check; a true sealed OOS is deferred to
genuinely new (2025/26+) data, not yet acquired.

## 7. Number of behaviours systematically examined

**Nine**, pre-declared before running against real data (D1-D9 in
`run_cycle_002_discovery_scan.py`'s module docstring), spanning 1X2,
Over/Under 2.5, and Asian Handicap, and covering favourite-longshot
bias, Elo-gap-magnitude effects, SOT-differential incremental
information, recent-form-vs-underlying-quality divergence, market-
movement informativeness, home/away asymmetry, competition effects,
and the locked Dominant-Side Mispricing family. No check was added,
removed, or re-binned after seeing results.

## 8. All interesting candidate behaviours

Three, all narrowed from their initial framing after the stability
check (full detail in `FOOTBALL_CYCLE_2_BEHAVIOUR_ATLAS.md`):

- **BEH-009, Dominant-Side Mispricing (the locked family):** extreme
  1X2 favourites (top quartile, mean favourite probability 0.68) show
  Asian Handicap cover calibration error (ECE) of 0.049 in the
  discovery slice vs 0.018 for the rest of the sample -- direction
  replicates in the stability slice (0.044 vs 0.035) though the gap
  shrinks from 0.031 to 0.0095.
- **BEH-004, SOT differential vs price band:** narrowed to the
  extreme-favourite price quintile specifically -- a positive,
  CI-excluding-zero effect (+0.079 discovery, +0.097 stability) that
  persists across both non-overlapping periods; the broader
  "positive in every price quintile" claim did not replicate.
- **BEH-008, competition-specific calibration:** narrowed to "SC0
  (Scottish Premiership) 1X2 calibration runs a persistent ~0.04 ECE"
  -- stable in level across both slices -- rather than the broader
  "English leagues are better calibrated" framing, which did not hold
  up (E1's ECE more than doubled between slices).

## 9. All important null/negative findings

Six of nine checks, reported in full rather than discarded:
BEH-001 (1X2 favourite-longshot bias -- suggestive at the extremes
only, non-monotonic, OBSERVED not CANDIDATE); BEH-002 (no O/U 2.5
favourite-longshot pattern, REJECTED); BEH-003 (no relationship
between Elo-gap magnitude and 1X2 calibration, REJECTED); BEH-005
(recent-form-vs-market-movement correlation was, if anything, the
OPPOSITE sign of the hypothesised "overreaction" story, REJECTED);
BEH-006 (opening-to-closing movement carries no detectable information
beyond the closing price for the outcome itself, REJECTED); BEH-007
(home/away favourite calibration gap is real-signed but small and
uncertain, OBSERVED not CANDIDATE).

## 10. Dominant-Side Mispricing findings specifically

Covered in full at point 8 / BEH-009. This is the strongest and most
theoretically grounded finding of the scan: the mechanism the family
was designed to test (market prices WHO wins efficiently but the
MAGNITUDE of dominance less efficiently) shows up with the correct
sign in two independent multi-season periods. The honest caveat: the
effect size roughly a third of its discovery-slice value in the
stability slice, so any future formal test should size its minimum-
detectable-effect off the smaller, more conservative number.

## 11. Whether any candidate appears incremental to market price

Two different senses, kept separate per the operator's own framing
(section 7 of the execution plan):

- **BEH-004** is explicitly an incremental-information test: it
  measures whether SOT differential predicts outcome BEYOND what the
  market's own opening price already implies (a within-price-band
  design). Yes, in the narrowed extreme-favourite subgroup, with a CI
  excluding zero in both slices.
- **BEH-009** is a different kind of finding: it measures whether the
  Asian Handicap PRICE ITSELF is well-calibrated for extreme
  favourites, not whether some other variable beats that price. A
  calibration gap alone does not yet establish a positive-EV
  opportunity (P_true - P_market) -- that requires a next step this
  checkpoint does not take: converting the calibration gap into an
  actual P_true estimate and comparing it to the AH price, which is
  exactly what formal pre-registration and backtesting would do.
- **BEH-008** (SC0 calibration) is calibration-only, same caveat as
  BEH-009: real, but not yet translated into a P_true-vs-P_market edge
  estimate.

## 12. Opening/closing-price findings

Two checks used opening-vs-closing movement directly, both null:
BEH-005 found the market's own price movement correlates more with a
longer-window underlying-quality proxy than with recent short-term
form (opposite of an "overreaction" story); BEH-006 found no evidence
that movement itself predicts the outcome beyond the closing price.
Per this cycle's price-semantics work (point 3), any use of these
movement fields as "CLV" would require exchange-based, `true_execution_clv`
verification that this data source does not provide -- they are
reported here as `bookmaker_consensus_movement`-style figures per
`docs/HISTORICAL_PRICE_AND_CLV_LIMITATIONS.md`'s existing terminology,
never as CLV.

## 13. Behaviour Atlas status

Nine entries (BEH-001 through BEH-009) in
`FOOTBALL_CYCLE_2_BEHAVIOUR_ATLAS.md`: 3 CANDIDATE (narrowed), 2
OBSERVED, 4 REJECTED, **0 VALIDATED** as required. Kept deliberately
separate from the project's formal, heavier
`research/behaviours/behaviour_atlas.csv` system, which is reserved
for behaviours that have already passed through formal hypothesis
pre-registration and testing -- none of these nine have.

## 14. Which candidates deserve formal pre-registration

Ranked:

1. **BEH-009 (Dominant-Side Mispricing)** -- highest priority. It is
   the operator's locked family, has the clearest a priori mechanism,
   and is the only candidate with a full statistical design already
   matching what formal pre-registration would need (a pre-match-only
   dominance definition, a real settlement function, two independent
   replications). Recommend pre-registering next, sized off the
   stability-slice effect (0.0095 ECE gap), not the discovery-slice one.
2. **BEH-004 (SOT differential, extreme-favourite subgroup)** --
   second priority. A real, twice-replicated, CI-excluding-zero effect,
   but the subgroup is narrower and the mechanism more speculative.
   Worth pre-registering as a subgroup-specific hypothesis, explicitly
   NOT the broader all-quintiles claim.
3. **BEH-008 (SC0 calibration level)** -- third priority. Stable and
   real, but calibration alone, not yet an edge estimate, and tested
   only via 1X2; would benefit from checking whether SC0's O/U and AH
   markets show the same pattern before committing to formal
   pre-registration.

## 15. Whether evidence justifies acquiring xG or another new data family

**No.** Nothing in this scan points to a specific gap that shots/SOT/
corners/cards cannot address, and the strongest candidate (BEH-009)
uses only data already in hand. The GO/HOLD recommendation from the
direction-change report stands: HOLD on xG, weather, Betfair football,
paid vendor data, and additional leagues. The next useful step is
formalising what is already found, not acquiring more.

## 16. Tests/commits/docs created

**Commits** (all in `prediction-markets-lab`, none pushed -- Fraser
pushes from his own Terminal per standing arrangement):

- `c280989` -- richer canonical extraction module + script (match
  stats, O/U 2.5, AH), 17 new tests.
- `a870d1b` -- leakage-safe rolling feature module + tests (12 new) +
  feature-assembly script.
- `8adaab2` -- chronological split decision document.
- `56691e3` -- discovery scan (9 pre-declared checks) + stability
  check scripts.
- `8155205` -- Behaviour Atlas document.

**Tests:** 662/662 passing (650 prior + 12 new this cycle's feature
module; the extraction module's 17 tests are included in the 650
baseline from the prior commit in this same cycle). Full suite run
clean after every code change.

**Docs:** `CYCLE_002_CHRONOLOGICAL_SPLIT_DECISION.md`,
`FOOTBALL_CYCLE_2_BEHAVIOUR_ATLAS.md`, this checkpoint. Cycle 1's raw
and processed files confirmed untouched by mtime after every run.

## 17. Exact next decision gate

**Formal pre-registration of BEH-009 (Dominant-Side Mispricing) as a
genuine falsifiable Hypothesis** in the project's Hypothesis Registry
format (`research/hypotheses/hypothesis_registry.csv` schema): a
stated economic rationale, a predeclared target metric and minimum
sample size, and a predeclared out-of-sample period. Per point 6,
that OOS period cannot come from the existing 2020/21-2024/25 corpus
(no genuine seal remains) -- so formal backtesting of BEH-009 (and, if
pursued, BEH-004) proceeds using the existing corpus for in-sample
development ONLY, with the sealed OOS test explicitly deferred until
2025/26 data is acquired for that specific purpose. This checkpoint
stops here, before that pre-registration step, exactly as instructed
("STOP before formal validation of newly discovered hypotheses").
Awaiting direction on whether to proceed with formal pre-registration
of BEH-009 now (using in-sample development only, OOS deferred) or to
wait for 2025/26 data before any further work on this family.
