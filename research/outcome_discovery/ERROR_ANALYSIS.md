# Error Analysis -- Outcome Discovery & Winner/Loser Prediction Cycle

Date: 2026-09-22. Section 21's requirement: analyse the largest prediction errors and check
whether they share pre-match characteristics -- hypothesis generation only, per Section 21's own
explicit instruction not to modify any model based on individual anecdotes.

## The 20 highest-confidence market misses (all 6 seasons pooled)

Defined as: matches where the market's top pick (highest of P(home)/P(draw)/P(away)) did not
occur, ranked by that top pick's probability. Full list: `analysis_summary.json`'s
`top_misses_market` key.

**Predicted probability range**: 80.4% to 85.5% -- these are exactly the kind of high-confidence
picks Section 21's examples describe ("model predicted Home 80%, Home lost").

**Predicted side**: 16 of 20 (80%) were home picks, 4 of 20 were away picks, zero were draw picks
(the market never picks draw as its single most likely outcome across the whole 5,631-match pooled
sample -- see MODEL_COMPARISON.csv / PROBABILITY_BANDS.csv discussion). This mirrors the market's
general home-favouring tendency (3,790 of 5,631 top picks are home, vs 1,841 away) rather than
indicating anything specific to these 20 misses.

**Actual outcome when the favourite lost**: 13 of 20 (65%) were draws, 5 of 20 were the other
side winning outright, 2 of 20 were the market's away-pick failing to a home win. **The dominant
failure mode for a heavy pre-match favourite, when it fails, is a draw rather than an outright
loss** -- an intuitive football pattern (a strong side more often fails to win than is beaten
outright) rather than a surprising discovery.

**Competition**: 14 of 20 (70%) are Scottish Premiership (SC0), 5 are Premier League (E0), 1 is
Championship (E1). SC0 is only one of three competitions in the pooled sample (roughly a third of
matches), so this is a real over-representation among the largest misses. **Hypothesis, not
confirmed**: SC0 has fewer bookmakers quoting per match on average than E0 (consistent with prior
cycles' data-quality findings), which could produce a noisier consensus probability at the high end
-- or Scottish football may simply have genuinely higher variance/draw propensity. This is not
tested further in this cycle; it is named as a candidate direction for a future, properly
pre-registered competition-stratified analysis, not acted on here.

**Season**: no season is meaningfully over-represented (2021/22: 7, 2022/23: 4, 2023/24: 4,
2024/25: 3, 2025/26: 2) -- roughly proportional to each season's share of matches. No evidence the
2025/26 holdout season's own lower top-pick accuracy (see HOLDOUT_REPORT.md) concentrates in these
largest-magnitude misses specifically.

## Interpretation, and what this does NOT justify

None of the above misses fall outside what the market's own stated calibration would predict: the
80%+ probability band's actual win rate was 88.0% against a mean predicted probability of 83.7%
(PROBABILITY_BANDS.csv) -- if anything slightly UNDER-confident at that level, not over-confident.
A ~12-18% failure rate for 80-86%-probability picks is exactly what good calibration predicts, not
evidence of a fixable error pattern. Per Section 21's explicit instruction, no model or threshold
is modified based on this anecdotal review; the SC0 over-representation is flagged as a
hypothesis for a possible future, separately pre-registered investigation, not treated as a
finding here.
