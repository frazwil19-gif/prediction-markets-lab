# Workstream B — 2021-2023 Discovery Results (Task #22)

**Date:** 2026-09-16
**Status:** Complete. All 13 pre-registered families REJECT. A clean,
honest null across the full pre-registered set — reported in full, not
searched past, per the operator's explicit instruction to report an
honest null rather than search endlessly if zero hypotheses survive.
**Script:** `scripts/run_discovery_analysis_2021_2023.py`. Outputs:
`data/interim/workstream_b_discovery_2021_2023_results.json` (full detail
per family) and `...bucket_results.csv` (every bucket, flat) — both
gitignored per `data/interim/*`; this document is the durable, committed
record of the results.

**What this tests, and what it does not.** Every family asks the same
underlying question: within a pre-declared bucket of some pre-match
covariate, is the market's own BASIC last-traded price *miscalibrated*
against the realised outcome? `deviation = mean(outcome) −
mean(market_reference_probability)`, paired per match, with a 2000-
resample bootstrap CI built at (1 − 0.05/13) ≈ 99.62% coverage — i.e. the
Bonferroni correction across the 13 families is baked directly into the
CI width, so "the CI excludes 0" already means Bonferroni-significant. A
family is **PROMOTE** only if it has a significant bucket with N≥150, a
plausible mechanism, same-sign year stability, and (where computed)
robustness to an alternate binning; **PARTIAL** if it clears some but not
all of those bars; **REJECT** otherwise. This finds pricing errors in a
non-executable reference price only — no back/lay ladder, commission, or
liquidity model exists yet, so nothing here is an executable edge even
where a real pattern were found.

## Summary table

| # | Family | N | Most extreme deviation | 99.62% CI | Verdict |
|---|---|---|---|---|---|
| 1 | Model-market disagreement | 7,136 | +0.023 (Elo≤-0.10 vs market) | [-0.008, 0.053] | REJECT |
| 2 | Favourite/underdog | 7,136 | -0.009 (favourite vs implied) | [-0.023, 0.006] | REJECT |
| 3 | Price bands | 7,136 | +0.023 ([0.4,0.6) band) | [-0.009, 0.057] | REJECT |
| 4 | Rank gap | 7,120 | +0.030 ((-50,-10] band) | [-0.003, 0.066] | REJECT |
| 5 | Elo gap | 7,136 | +0.022 ([0.4,0.6) band) | [-0.002, 0.045] | REJECT |
| 6 | Elo-vs-ranking disagreement | 7,120 | +0.022 (>0.10 band) | [-0.012, 0.057] | REJECT |
| 7 | Surface (favourite-perspective) | 7,136 | -0.014 (Hard) | [-0.033, 0.006] | REJECT |
| 8 | Tournament level/format | 7,136 | -0.029 (A, N=160) | [-0.123, 0.069] | REJECT |
| 9 | Recent/surface form | 6,398 | +0.010 ((0.1,0.3] band) | [-0.024, 0.046] | REJECT |
| 10 | Congestion/rest | 6,858 | -0.032 ((2,7] band, N=434) | [-0.092, 0.025] | REJECT |
| 11 | Time-to-start | 4,129-7,317 (by horizon) | none significant at any horizon | — | REJECT |
| 12 | Cross-horizon price movement | 6,927 | +0.107 (≤-0.05 band, N=66) | [-0.065, 0.275] | REJECT |
| 13 | Favourite-longshot bias | 7,136 | +0.025 ([0.9,1.0) band) | [-0.003, 0.045] | REJECT |

Every single bucket across all 13 families and ~65 total buckets tested
had a Bonferroni-corrected CI that included zero, with the sole exception
of tournament-level bucket "O" in family 8 (N=1 — a single Olympics-
coded match, correctly excluded from promotion by the pre-declared N≥150
rule, not a real finding).

## A real methodological catch worth recording in full

Families 7 (surface) and 8 (tournament level) were originally tested
using the raw player-A perspective (`outcome_a_won − market_prob_a`),
exactly like every other family. That first pass found a nominally
Bonferroni-significant result: Grass, N=844, deviation=+0.047, CI
[0.002, 0.092] — narrowly clearing the bar, with consistent positive
sign across all three years (2021: +0.062, 2022: +0.044, 2023: +0.035).

Before accepting it, the mechanism was interrogated rather than taken at
face value (the canonical dataset's own documented rule:
`player_a = whichever of winner_id/loser_id sorts first lexicographically
-- carries no information about who won`). Because `player_a` carries no
skill or favourite information, and surface has no reason to correlate
with lexicographic ID ordering, roughly half of Grass matches have A as
the favourite and half as the underdog. A *real* favourite-longshot-type
bias (favourites underpriced, underdogs overpriced, or vice versa) would
be expected to **cancel to approximately zero** under this framing,
because it averages positive and negative deviations from opposite sides
of the same true effect. The only way to get a persistently non-zero
result from this framing is sampling noise or an implausible ID-sorting
artifact — not a genuine market-calibration finding. Re-running both
families from the market-favourite's perspective (the same, symmetric-
bias-robust framing already used for families 2 and 13) made the Grass
result disappear entirely (deviation -0.008, CI [-0.056, 0.034]).

This is recorded in full rather than quietly fixed and forgotten, for
two reasons: it is a genuine, transparent methodology correction (the
same standard applied to the two real Phase 1 linkage bugs), and it is a
concrete illustration of exactly the "no cherry-picking, mechanism must
be plausible, don't stop at the first statistically-clearing number"
discipline the operator asked for. Had this correction not been made,
Task #22 would have wrongly reported one PROMOTE instead of an honest
13-for-13 null.

## Family-by-family detail

### 1. Model-market disagreement
Bucketed by `elo_prob_a − market_prob_a_30min` (bins reused unchanged
from the January 2026 pipeline). The largest-magnitude bucket is the
opposite of what a "trust Elo's disagreement" hypothesis would want:
`<=-0.10` (Elo notably LESS bullish on A than the market — market says
68.8%, Elo says only 50.4%) shows actual outcome rate 71.1%, i.e. even
higher than the market's own already-confident price, and well above
Elo's. If anything this bucket says the market's confidence was
under-, not over-, stated, and that Elo was the less accurate of the two
in exactly the cases where they disagreed most — not a signal that
following Elo over the market would have helped. The CI comfortably
includes zero either way ([-0.008, 0.053]), and the year-by-year point
estimates for the (differently-defined) `>0.10` extreme bucket used for
the supplementary stability check are not stable (2021: +0.037, 2022:
+0.007, 2023: **-0.011**, crossing sign). Bin-sensitivity check (8pp
alternate cutoff) gave the same-sign result for that bucket, but that
alone isn't enough given the CI and year instability. **REJECT.**

### 2. Favourite/underdog
Every match from the market favourite's perspective: 7,136 favourites
had mean implied probability 68.8%, actual win rate 68.0% — deviation
-0.9pp, CI [-0.023, 0.006], consistent (small, negative) across all three
years. No evidence favourites are mispriced either direction. **REJECT.**

### 3. Price bands
A full five-band calibration curve from player A's own price (valid here
since the bucketing variable IS the probability being tested, not an
unrelated covariate). Every band's CI includes zero; the largest nominal
gap is the middle [0.4,0.6) band at +2.3pp, itself the band where
calibration should be easiest to satisfy by chance. **REJECT.**

### 4. Rank gap
Signed rank_gap_b_minus_a in five bands. Largest point deviation +3.0pp
in the (-50,-10] band (B moderately better ranked than A), CI
[-0.003, 0.066] — closest to significant of any bucket in the whole
study, but does not clear the Bonferroni bar, and year stability is
weak (2021 +0.011, 2022 -0.024, 2023 -0.020 — sign flips). **REJECT.**

### 5. Elo gap
Elo_prob_a in five bands, same style as price bands. All CIs include
zero; extreme-Elo buckets (large favourites/underdogs by the frozen
model) show no larger deviation than the middle band. **REJECT.**

### 6. Elo-vs-ranking disagreement
Elo_prob_a − ranking_prob_a in five bands. All CIs include zero, though
year stability in the top bucket is notably consistent in sign
(+0.025, +0.023, +0.019 across 2021-2023) despite not being individually
significant — flagged as the one pattern in the whole study worth
revisiting if a future, larger sample (e.g. adding 2024 data under the
frozen spec) narrows the CI, but not promotable on this evidence.
**REJECT.**

### 7. Surface (favourite-perspective, corrected — see above)
Hard/Clay/Grass favourite-calibration: all three surfaces show small,
CI-including-zero deviations (Hard -1.4pp, Clay +0.2pp, Grass -0.8pp).
No surface-specific mispricing. **REJECT.**

### 8. Tournament level/format (favourite-perspective, corrected)
Eight tourney_level categories; all CIs include zero except the N=1 "O"
(Olympics) bucket, excluded by the pre-declared N≥150 rule. Smaller
events (250s, A, D) show no worse calibration than majors — if anything
250s trend slightly negative (-1.3pp) and majors trend flat (-0.3pp),
opposite the "less-watched events are worse-priced" mechanism
hypothesised. **REJECT.**

### 9. Recent/surface form
Trailing-10-match form difference (A minus B), leakage-safe (shift(1)
before the rolling window). All five bands' CIs include zero; the
largest gap is a modest +1.0pp in the (0.1,0.3] band. No evidence the
market underweights recent form. **REJECT.**

### 10. Congestion/rest
Rest-day difference (A minus B), tourney_date granularity. All bands
include zero; the (2,7] band (A rested noticeably MORE) shows the
largest point deviation but in the unexpected direction (-3.2pp, i.e.
the more-rested player underperforming the market's implied
probability) and with a wide CI [-0.092, 0.025] on N=434. Not
promotable, and the direction itself argues against a real "more rest
helps" pricing gap. **REJECT.**

### 11. Time-to-start
Repeats family 1's bucketing at 24h/6h/1h/30min. No horizon shows a
significant top-bucket deviation; the point estimates in the extreme
disagreement bucket are small and inconsistent in sign across horizons
(24h: -0.011, 6h: +0.006, 1h: +0.010, 30min: +0.015) — no evidence that
disagreement is more informative far from the match or close to it.
**REJECT.**

### 12. Cross-horizon price movement
Price movement from 6h to 30min in five bands. The two most extreme
bands (large moves either direction) show the largest point deviations
in the whole study (+0.107 and +0.044) but on tiny samples (N=66 and
N=68) with very wide CIs comfortably including zero — exactly the kind
of large-looking-but-meaningless estimate a small N produces, not a real
finding. **REJECT.**

### 13. Favourite-longshot bias
Fine favourite-perspective bands from 50% to 100%. The classic pattern
(monotonically increasing deviation toward the extreme-favourite end)
was explicitly checked and **did not hold monotonically** across bands
(0.5-0.6: -1.9pp, 0.6-0.7: -1.9pp, 0.7-0.8: +0.7pp, 0.8-0.9: -0.3pp,
0.9-1.0: +2.5pp) — no CI excludes zero, and the pattern most people would
call "favourite-longshot bias" from bookmaker odds does not show up in
Betfair's own two-sided last-traded price. **REJECT.**

## What this means for the project

Twelve of thirteen families showed no evidence of any kind at any stage
of the correction process; the one family that briefly showed a
significant result (surface) did so only under a framing later shown to
be a null test by construction for the very effect it claimed to detect,
and the effect vanished under the corrected framing. This is a genuinely
clean, honest null across the full 2021-2023 discovery pass — exactly
the outcome the operator explicitly said was an acceptable and expected
result, not a failure of the research process. Betfair's tennis market,
even at the BASIC-tier last-traded-price level with no bookmaker margin,
appears well-calibrated against the frozen Global Elo model and every
other pre-registered covariate tested here, across three full years and
7,136-7,668 matches depending on the family.

**Zero hypotheses are eligible to carry forward to 2024 development
validation.** Per the operator's own explicit ordering, 2024/2025
evaluation only follows candidates that survive 2021-2023 discovery —
there are none. Task #23 will report this decision-grade checkpoint in
full and recommend next steps (a natural stopping point for this
Betfair-tennis-BASIC-LTP discovery pass, per the operator's own
instruction not to start Football Cycle 2 except on "a clean null or a
natural checkpoint" — this is that checkpoint).
