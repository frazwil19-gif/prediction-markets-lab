# Workstream B — Price-Coverage / Selection-Bias Audit (2021-2025)

**Date:** 2026-09-16
**Status:** Complete. Resolves an apparent contradiction with the Phase 1
report's coverage numbers (see section 3) and recommends a working
discovery horizon for Task #21.
**Script:** `scripts/audit_price_coverage_2021_2025.py`. Detail rows (one
per MATCHED match x horizon, 90,692 rows):
`data/interim/workstream_b_price_coverage_audit_rows.csv` (gitignored).

This is a coverage/missingness audit only. It reads no outcome
(`outcome_a_won` is never touched) and computes no model-vs-market
disagreement. `favourite_by_rank` uses pre-match ATP ranking only (never
price or outcome); `price_band_close` uses each market's own closing
(final) price, a structural fact about how lopsided the match ended up
being priced, kept separate from the pre-match coverage question itself.

## 1. Funnel

| Stage | N | % of N_total |
|---|---|---|
| N_total (all 2021-2025 TML canonical matches) | 14,564 | 100% |
| N_linked (MATCHED, frozen linkage spec) | 12,956 | 88.96% |
| N_final_analysis (at the recommended 30min horizon, "fresh" definition) | 12,202 | 83.78% |

(AMBIGUOUS 500 / 3.43% and UNMATCHED 1,108 / 7.61% remain excluded per
the frozen linkage spec, never resolved with outcome knowledge.)

## 2. Two coverage definitions, and why both are reported

`build_pre_match_observation` (unchanged, reused from the January
pipeline) marks a horizon "covered" if *any* price update exists at or
before the cutoff — this can be satisfied by a stale ante-post price set
days or weeks before the match, which is not a meaningful "market's view
30 minutes before the match". This audit therefore also computes a
**"fresh"** coverage flag: both sides priced *and* neither snapshot is
older than `max(2x the horizon, 1 hour)` — a decision-relevant bar for
whether the snapshot genuinely reflects trading near that horizon, not
just any historical price predating the cutoff.

| Horizon | Raw coverage | Fresh coverage | Median snapshot age when priced |
|---|---|---|---|
| 24h | 55.0% | 54.9% | 2.76h |
| 12h | 90.4% | 90.0% | 1.11h |
| 6h | 95.4% | 95.1% | 0.59h |
| 3h | 96.3% | 95.7% | 0.35h |
| 1h | 97.7% | 95.8% | 0.18h |
| 30min | 98.1% | 94.2% | 0.13h |
| 10min | 98.6% | 96.4% | 0.09h |

Raw and fresh are close at every horizon (the gap is largest at 30min-1h,
where a handful of snapshots are meaningfully stale relative to the
horizon) — real Betfair tennis markets trade close enough to match start
that "any price before cutoff" and "a genuinely recent price" mostly
agree. All figures below use the **fresh** definition.

## 3. Reconciling with the Phase 1 report's much lower numbers

The Phase 1 audit reported 17.1% / 50.1% / 78.3% coverage at 24h / 6h /
30min — dramatically lower than the numbers above. Both are real and
correct; **they measure different populations.** Phase 1's number came
from a random sample of the full 198,079 usable MATCH_ODDS markets in the
whole 2021-2025 Betfair tennis corpus — which includes every tennis match
Betfair covers (WTA, Challenger, ITF, and other tours/levels far removed
from the ATP tour, many with very thin liquidity), not only the 12,956
markets that link to an ATP tour canonical match. This audit's numbers are
scoped to exactly the population Phase 2 discovery will actually use: ATP
tour matches that successfully linked to a real TML canonical match. The
corpus-wide number remains a useful, honest fact about Betfair's overall
tennis coverage (worth keeping on record), but it is not the number that
should drive Phase 2's horizon choice — **coverage conditional on
successful ATP linkage is high (>94% at every horizon from 6h to 10min)
and is not, in fact, a binding constraint on discovery.** This correction
is recorded here transparently, the same way the January holdout
misclassification and the two Phase 1 linkage bugs were — a revision, not
a silent edit.

## 4. Coverage by year (fresh, all horizons)

| Year | 24h | 12h | 6h | 3h | 1h | 30min | 10min |
|---|---|---|---|---|---|---|---|
| 2021 | 51.6% | 91.4% | 95.7% | 96.2% | 95.6% | 94.0% | 96.6% |
| 2022 | 51.7% | 89.6% | 94.4% | 95.3% | 95.2% | 91.8% | 95.1% |
| 2023 | 58.0% | 90.4% | 95.2% | 95.3% | 95.5% | 93.5% | 95.9% |
| 2024 | 51.7% | 85.6% | 93.8% | 94.5% | 95.1% | 94.6% | 96.5% |
| 2025 | 61.6% | 93.5% | 96.6% | 97.5% | 97.9% | 97.1% | 97.9% |

Stable across years, with a mild upward trend into 2025 (more recent
liquidity) and a mild dip in 2024 at the 12h/30min marks — none of these
differences look large enough to change discovery conclusions, but Task
#22's analysis should still report year-by-year stability rather than
assume it.

## 5. Coverage by subgroup at the recommended 30min horizon (fresh)

| Surface | Coverage | N |
|---|---|---|
| Grass | 98.4%* | 1,476 |
| Clay | 97.9%* | 3,796 |
| Hard | 95.3%* | 7,684 |

(*figures shown are at 10min for surface/level/favourite/price-band
breakdowns, computed in the same run; 30min breakdowns are in the raw CSV
and are within 1-3pp of these at every level — no subgroup reordering.)

| Tournament level | Coverage (10min) | N |
|---|---|---|
| F (Team-final-type events) | 100.0% | 62 |
| G (Grand Slam) | 98.6% | 2,443 |
| 500 | 98.4% | 1,967 |
| M (Masters 1000) | 97.9% | 2,966 |
| O (Olympics/other) | 96.7% | 61 |
| 250 | 96.1% | 4,761 |
| A (ATP Cup/team) | 93.4% | 317 |
| D (Davis Cup) | 65.2% | 379 |

Davis Cup is the one real outlier — consistent with the linkage report's
finding that Davis Cup ties are also disproportionately UNMATCHED (680 of
1,108 UNMATCHED rows), pointing to a genuine, coherent Betfair Davis Cup
coverage gap (both in getting a market at all, and in how densely a
matched Davis Cup market trades) rather than two unrelated issues.

| Favourite by rank | Coverage (10min) | N |
|---|---|---|
| player_a | 96.4% | 6,550 |
| player_b | 96.5% | 6,378 |
| unknown (rank missing) | 78.6% | 28 |

No meaningful asymmetry between the two players' rank-based favourite
status — coverage is not biased toward "the favourite" or "the underdog"
in a way that would skew discovery families comparing the two.

| Closing price band (favourite's implied prob.) | Coverage (10min) | N |
|---|---|---|
| [0.95, 1.01) | 96.5% | 10,912 |
| [0.85, 0.95) | 96.7% | 1,465 |
| [0.75, 0.85) | 96.4% | 415 |
| [0.65, 0.75) | 91.3% | 126 |
| [0.55, 0.65) | 83.3% | 30 |

The overwhelming majority of matches (89%) close in the [0.95, 1.01) band
— i.e. most closing markets are lopsided by the time they close, which is
itself an artefact of using the CLOSING price only (prices converge toward
the eventual winner as the match is played out and in-play trading
resumes after the pre-match snapshot, this being the CLOSE not a pre-match
read). Coverage is slightly lower in the closest, most competitive bands
(83-91% for near-even closes, n=30-126, small samples) — worth re-checking
with a genuinely pre-match price band once the discovery dataset (Task
#21) is built with the model/market probabilities actually needed for
that, rather than over-reading a small-N pattern here.

## 6. Recommended discovery horizon

The empirically best-covered horizon by the "fresh" definition is 10min
(96.4%), narrowly ahead of 6h (95.1%) and 3h (95.7%), with 30min close
behind (94.2%). Given the small differences among 6h/3h/1h/30min/10min,
and the practical risk that observations very close to the scheduled
start can bleed into suspension/in-play, **30 minutes before the
(post-revision) scheduled start is recommended as the working discovery
horizon**, matching the horizon already used for reporting in this
project's earlier work (the January pipeline and the Phase 1 report both
already speak in terms of a "30min" coverage figure) — a deliberate
consistency choice, not a re-run of the empirical procedure to find a
different answer. Task #21 should build the 2021-2023 discovery dataset
at 30min and carry the exclusion into every downstream N, exactly as this
audit reports it (12,202 / 14,564 = 83.78% of the full universe, 94.2% of
successfully-linked matches).

## 7. Verdict

No dimension checked here (year, surface, tournament level, favourite
side, closing price band) shows coverage concentrated in a way that would
obviously bias a discovery family's estimate — Davis Cup is the one clear,
already-understood exception and is excluded from being a discovery
family target as a result (it was never one of the 13 pre-registered
families). Phase 2 (Task #21: build the 2021-2023 discovery dataset) may
proceed.
