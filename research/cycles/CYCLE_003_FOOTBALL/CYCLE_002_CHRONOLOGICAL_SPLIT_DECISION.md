# Football Cycle 2 -- Chronological Split Decision (Step E)

**Status: FROZEN.** This document fixes the chronological design for
Football Cycle 2's discovery work (step F onward) before any outcome
discovery begins, per the operator's explicit instruction ("freeze
chronological periods before outcome discovery begins... explicitly
recommend the cleanest split given what Cycle 1 previously exposed").

## 1. The question this document answers

Football Cycle 1 already ran market-vs-model comparisons over the
2020/21-2024/25 corpus. Football Cycle 2 reuses that same corpus (via
the richer extraction in step C) to search for new behavioural
patterns. Before that search starts, we need an honest answer to one
question: **is there any part of the existing 2020/21-2024/25 corpus
that can still serve as a genuinely blind sealed out-of-sample (OOS)
test for what Cycle 2 will discover?** If not, we must say so plainly
rather than label a compromised period "OOS" later.

## 2. The exposure, verified precisely

Re-reading `research/cycles/CYCLE_001/results/STAGE_3B_FINAL_REPORT.md`
in full (not just its summary) surfaced a fact that earlier framing in
this project understated. That report computed model-vs-market
log-loss, Brier score, and calibration (ECE) comparisons on **both**:

- the walk-forward **development folds**, 2020/21-2023/24, N=3,446
  matches (report section 2, table row `elo_poisson` Δ = **+0.0262**
  vs. market on development), and
- the sealed, one-time **2024/25 holdout**, N=1,160 matches (all three
  competitions: E0 380, E1 552, SC0 228) -- report section 2, table row
  `elo_poisson` Δ = **+0.0169**, 95% CI **[+0.0066, +0.0274]** (both
  figures confirmed verbatim against the source file, lines 29-30 and
  50 respectively).

So the exposure is not "2024/25 only, aggregate-only" as earlier
project framing had it -- it is **the entire five-season corpus**, via
two separate evaluations. It is real, and it is specific enough that
both Fraser and the operator have now seen the exact number
(elo_poisson loses to the market by +0.0169 log-loss on the 2024/25
holdout, with a confidence interval that excludes zero -- i.e. a
statistically clear market win for that one comparison).

## 3. What is and is not exposed -- a granular breakdown

The exposure is real but narrow. It does not touch most of what Cycle
2 investigates:

| Dimension | Exposed? | Detail |
|---|---|---|
| Market: 1X2 | Yes | The only market Stage 3B evaluated. |
| Market: Over/Under 2.5 | No | Never extracted or evaluated in Cycle 1 at all. |
| Market: Asian Handicap | No | Never extracted or evaluated in Cycle 1 at all. |
| Variable: match statistics (shots, SOT, corners, cards, referee) | No | Never extracted by Cycle 1's canonicalisation (this is the entire premise of Cycle 2 -- see the direction-change report). |
| Model family: Elo, Poisson, Elo+Poisson blends | Yes | The only families Stage 3B scored. |
| Model family: anything Cycle 2 might discover (subgroup rules, dominant-side thresholds, price-band effects, etc.) | No | Did not exist at the time; Stage 3B tested three predeclared model families, not behavioural subgroup rules. |
| Aggregation level: pooled/whole-corpus average | Yes | Stage 3B reported pooled log-loss/Brier/ECE only. |
| Aggregation level: any subgroup (by Elo-gap size, by favourite/underdog, by price band, by competition, by season) | No | Stage 3B never sliced by subgroup -- only three seasons' worth of per-checkpoint pooled numbers and one pooled holdout number. |
| Aggregation level: opening-vs-closing price movement | No | Stage 3B used only closing-adjacent consensus prices for its comparisons; opening/closing movement as its own object of study is new to Cycle 2. |

**Conclusion:** the exposure is a single coarse fact (an aggregate,
pooled, 1X2-only, Elo/Poisson-only, whole-season comparison) repeated
across two overlapping windows (development folds + the holdout). It
is not remotely the same thing as having already examined the specific
candidate behaviours Cycle 2 will test. It is, however, real enough
that the corpus cannot honestly be called "untouched."

## 4. Why no genuine sealed OOS survives within 2020/21-2024/25

A sealed OOS period is only as good as the seal. The whole point of
never touching it is that no one -- researcher or decision-maker --
has any prior information from it that could (even subconsciously)
shape which hypotheses get proposed, which subgroups get defined, or
which effect sizes get treated as "expected." Once Stage 3B evaluated
market-vs-model performance across **all five seasons** (not a subset
held in reserve), there is no remaining season inside this corpus that
was never looked at in some capacity. The 2024/25 holdout in
particular already has a specific, memorable, published number
attached to it -- a stronger form of exposure than "some model touched
this data once," because it is a number both principals in this
project can now recall and could, even unintentionally, use as an
anchor ("the market wins by about this much here").

Given that, picking any single season within the existing corpus and
relabelling it "the new sealed OOS" would not fix the problem -- it
would just be applying the OOS label to a period that has already lost
its blindness, which is precisely the outcome the operator's
instruction ("be conservative... do not consume the best untouched
period casually") is asking us to avoid.

## 5. Decision (frozen)

**There is no genuine sealed historical OOS available inside the
2020/21-2024/25 corpus for Football Cycle 2.** The full five-season
corpus is treated as a **discovery + development** corpus only. A true
sealed final historical OOS is deferred until genuinely new data (the
2025/26 season) is acquired -- specifically for that purpose, and kept
completely unexamined until a candidate behaviour is ready for formal
pre-registration and testing against it.

Within the discovery + development corpus, Cycle 2 uses an internal
chronological division for practical purposes -- but this division is
explicitly **not** a blind holdout and must never be reported as
"out-of-sample" or "validation" in the load-bearing sense those words
carry elsewhere in this project:

| Period | Seasons | Date range | N (matches) | Role in Cycle 2 |
|---|---|---|---|---|
| **Discovery slice** | 2020/21 - 2022/23 | 2020-08-01 to 2023-05-28 | 3,480 | Open-ended behavioural exploration (step F). Candidate behaviours are proposed and first measured only here. |
| **Internal stability slice** | 2023/24 - 2024/25 | 2023-08-04 to 2025-05-25 | 2,320 | NOT a blind test. Used only to check whether a candidate's sign and rough magnitude persist out of the discovery slice. A candidate that reverses sign or vanishes here is downgraded (REJECTED or CANDIDATE-with-caveat in the Behaviour Atlas), never promoted past CANDIDATE regardless of how it performs here. |
| **Sealed final historical OOS** | 2025/26 (not yet acquired) | -- | -- | Reserved. Acquisition explicitly HOLD per current instructions; when eventually acquired, must remain untouched until a specific pre-registered hypothesis from this cycle's discovery is ready to test against it. |
| **Prospective validation** | Live/future matches | -- | -- | Paper trading; explicitly HOLD per current instructions. Final gate before any live-money consideration, unchanged from existing project standards. |

Row totals: 3,480 + 2,320 = 5,800, matching the full corpus exactly (no
matches double-counted or dropped by this split).

### Why 2020/21-2022/23 for discovery specifically

This gives the broadest possible discovery base (3 full seasons,
3,480 matches, all three competitions) while reserving a materially
sized, contiguous, chronologically-later block (2 seasons, 2,320
matches) for the stability check. Splitting 3-and-2 rather than
4-and-1 (which would mirror Stage 3B's own development/holdout split)
is a deliberate choice: Stage 3B's 4-and-1 split is exactly the
structure whose holdout number is now known, so mirroring it here
would invite the same false sense of a "fresh" final season. Using a
2-season stability slice also gives the stability check itself a
larger, less noisy sample than a single season would.

## 6. Rules this decision imposes on later steps

1. Any statement in the Behaviour Atlas (step G) or the checkpoint
   report (step H) about a behaviour "holding up" in 2023/24-2024/25
   must use the phrase **"stability check"** or **"persists out of the
   discovery slice"** -- never "out-of-sample," "holdout," "OOS," or
   "validated on unseen data." Those terms are reserved for a genuine
   blind test against 2025/26 data or later.
2. No behaviour discovered in this cycle may be promoted beyond
   CANDIDATE status on the strength of the 2023/24-2024/25 stability
   check alone, regardless of how strong it looks there.
3. Any finding that happens to closely replicate Stage 3B's specific
   published number (elo_poisson losing to the market by roughly
   +0.015-0.020 log-loss, pooled, on 1X2) should be flagged explicitly
   as a replication of a previously known result, not reported as a
   new discovery.
4. This split governs Football Cycle 2 discovery only. It does not
   reopen, alter, or retroactively relabel Football Cycle 1's own
   frozen Stage 3B results, and it has no bearing on the permanently
   closed Tennis Workstream B.
5. If 2025/26 data is acquired in a future cycle, it must be staged
   behind an explicit freeze (mirroring
   `research/cycles/CYCLE_001/DATA_SPLIT_PLAN.md`'s
   `validate_test_period_untouched()` pattern) before any development
   work on it begins.

## 7. What would change this decision

Only the acquisition of genuinely new, previously-unexamined-by-anyone
match data (2025/26 or later) changes the sealed-OOS picture. Nothing
about re-analysing the existing 2020/21-2024/25 corpus more carefully,
with better statistics, or with new variables restores its blindness
for the one narrow comparison Stage 3B already made -- that specific
door is permanently closed, which is exactly why this document treats
the whole existing corpus as discovery+development rather than trying
to carve out a "clean enough" residual holdout from it.
