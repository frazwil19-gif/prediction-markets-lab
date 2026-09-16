# Workstream B — Phase 2 Decision-Grade Checkpoint (2021-2023 Discovery)

**Date:** 2026-09-16
**Status:** Phase 2 discovery complete. Clean null across all 13 pre-registered
families. This is the decision-grade checkpoint the operator requested before
any 2024 development validation may begin.

This document answers, in order, the 12 items the operator's Phase 2 directive
asked to have returned once the linkage-integrity gate and 13-family discovery
pass were both complete. Every number below is drawn from the three committed
audit/analysis documents in `research/cycles/CYCLE_002_TENNIS/`:
`WORKSTREAM_B_LINKAGE_INTEGRITY_AUDIT.md`, `WORKSTREAM_B_PRICE_COVERAGE_AUDIT.md`,
and `WORKSTREAM_B_DISCOVERY_2021_2023_RESULTS.md` — nothing here is new
computation, only synthesis for a single decision-grade read.

---

## 1. Linkage-integrity audit and frozen linkage spec

Outcome-blind audit of all 12,956 MATCHED 2021-2025 rows by date-distance band
(0-2 / 3-7 / 8-10 / 11-14 days), using only round labels, tourney start dates,
and Betfair market dates — no outcome was read. Round-chronology violation
rates: 0.07% (0-2d), 0.06% (3-7d), 0.00% (8-10d), 0.00% (11-14d) — the two
bands the operator asked to scrutinize most closely came back clean. The
11-14 day tail (141 rows, 1.1% of MATCHED) is disproportionately Grand Slam
(39.0%) and Masters (59.6%) semi-finals/finals, correctly placed at exactly
the calendar distance those events' real durations predict (e.g. every 2021
Slam final present and correctly dated). A sign-sanity check found 2.48% of
rows with a nominally negative date distance; 84.7% of those are exactly
-1 day (a timezone-boundary artifact) and the remaining 49 rows are
round-robin/Davis-Cup date-field conventions, all manually verified as
plausible real pairings. **Verdict: PASS.**

**Frozen linkage specification** (no further changes authorised except a
transparently-documented defect fix): script `scripts/link_betfair_2021_2025.py`;
matching logic `tennis_betfair_linkage.classify_tennis_betfair_match` /
`names_are_equivalent` (unmodified since Tennis Cycle 1); `date_tolerance_days
= 14`; candidate filter `market_type == "MATCH_ODDS" and n_price_points > 0`;
output 12,956 MATCHED / 500 AMBIGUOUS / 1,108 UNMATCHED (88.96% / 3.43% /
7.61%). AMBIGUOUS/UNMATCHED remain permanently excluded, never resolved by
outcome knowledge.

## 2. Price-coverage / selection-bias audit

Correctly re-scoped to the 12,956 ATP-linked MATCHED markets (Phase 1's
17.1%/50.1%/78.3% numbers were sampled from the full 198,079-market multi-tour
corpus, including WTA/Challenger/ITF — a scoping difference, not a
contradiction, documented in full in the audit doc). On the correct ATP-only
scope, coverage is high at every practical horizon:

| Horizon | Fresh coverage |
|---|---|
| 24h | 54.9% |
| 12h | 90.0% |
| 6h | 95.1% |
| 3h | 95.7% |
| 1h | 95.8% |
| 30min | 94.2% |
| 10min | 96.4% |

"Fresh" requires both sides priced and neither snapshot older than
max(2×horizon, 1 hour) — a stricter, more decision-relevant bar than raw
"any price at or before cutoff." Coverage is high (85-98%) in every year,
surface, tournament level, favourite/underdog side, and price band checked,
with one exception: Davis Cup at 65.2% (N=379), consistent with its
already-known high UNMATCHED rate — a real, explained gap, not random
missingness. 30-minute was retained as the working discovery horizon for
consistency with prior project reporting.

## 3. Exact discovery sample sizes

2021-2023 discovery dataset: 7,668 rows × 37 columns
(`data/interim/workstream_b_2021_2023_discovery_dataset.csv`, gitignored,
build documented in `WORKSTREAM_B_2021_2023_DISCOVERY_DATASET_BUILD.md`).
Per-family analysis N ranges from 4,129 (family 11's thinnest horizon) to
7,668, with most families landing at 6,398-7,136 once each family's specific
required fields (elo, market price at 30min-fresh, form/rest covariates) are
available. Exact N is reported per family and per bucket in
`WORKSTREAM_B_DISCOVERY_2021_2023_RESULTS.md`'s summary table and
family-by-family sections — nothing here is rounded or approximated beyond
what that document already states.

## 4. Results for all 13 families

All 13 pre-registered families REJECT. Full detail (mechanism, numbers,
year-by-year stability, bin-sensitivity) is in
`WORKSTREAM_B_DISCOVERY_2021_2023_RESULTS.md`. Summary:

| # | Family | N | Most extreme deviation | 99.62% CI | Verdict |
|---|---|---|---|---|---|
| 1 | Model-market disagreement | 7,136 | +0.023 | [-0.008, 0.053] | REJECT |
| 2 | Favourite/underdog | 7,136 | -0.009 | [-0.023, 0.006] | REJECT |
| 3 | Price bands | 7,136 | +0.023 | [-0.009, 0.057] | REJECT |
| 4 | Rank gap | 7,120 | +0.030 | [-0.003, 0.066] | REJECT |
| 5 | Elo gap | 7,136 | +0.022 | [-0.002, 0.045] | REJECT |
| 6 | Elo-vs-ranking disagreement | 7,120 | +0.022 | [-0.012, 0.057] | REJECT |
| 7 | Surface (corrected) | 7,136 | -0.014 | [-0.033, 0.006] | REJECT |
| 8 | Tournament level/format (corrected) | 7,136 | -0.029 (N=160) | [-0.123, 0.069] | REJECT |
| 9 | Recent/surface form | 6,398 | +0.010 | [-0.024, 0.046] | REJECT |
| 10 | Congestion/rest | 6,858 | -0.032 (N=434) | [-0.092, 0.025] | REJECT |
| 11 | Time-to-start | 4,129-7,317 | none significant at any horizon | — | REJECT |
| 12 | Cross-horizon price movement | 6,927 | +0.107 (N=66) | [-0.065, 0.275] | REJECT |
| 13 | Favourite-longshot bias | 7,136 | +0.025 | [-0.003, 0.045] | REJECT |

## 5. Every candidate hypothesis (none survived)

Every one of the 13 pre-registered families was tested exactly as
pre-registered — no family was skipped, no bucket was dropped, and no
post-hoc family was added. One nominally significant result appeared during
analysis (family 7, Grass, N=844, deviation +0.047, CI [0.002, 0.092]) and
did not survive scrutiny — see item 6. Zero candidates are being carried
forward under any name.

## 6. Corrected uncertainty/significance results

Every family's CI is built directly at (1 − 0.05/13) ≈ 99.62% coverage via a
2,000-resample paired bootstrap (Bonferroni correction baked into the
interval width, not applied post-hoc to a p-value) — so "CI excludes zero"
already means Bonferroni-significant across the full 13-family family-wise
error rate. Across all ~65 buckets tested, exactly one nominally cleared this
bar before correction of a methodology flaw (see next item); zero clear it
after the flaw was fixed.

**The one real methodological catch of this phase**: families 7 (surface)
and 8 (tournament level) were initially tested from the raw player-A
perspective, like every other family. Because `player_a`/`player_b` are
assigned by an arbitrary lexicographic ID sort that carries no
favourite/underdog information (documented in the canonicalisation script),
bucketing by a variable uncorrelated with that label and testing the raw
A-perspective deviation is a **null test by construction** for any true
symmetric favourite-longshot bias — such a subgroup contains a roughly
50/50 mix of "A is favourite" and "A is underdog" matches, so a real effect
cancels to ~zero, and the only way to get a persistently nonzero result from
this framing is noise. This was caught before acceptance: the Grass result
(N=844, +0.047, CI [0.002, 0.092], consistent sign across all 3 years) was
investigated, the mechanism identified, and both families re-run from the
market-favourite's perspective (the same framing already used, correctly,
in families 2 and 13). The Grass result vanished (-0.008, CI
[-0.056, 0.034]). Recorded in full as a transparent correction, not
discarded quietly — this is the same standard applied to the two real Phase
1 linkage bugs.

## 7. Stability results

Year-by-year point estimates were checked for every family with a nominally
interesting bucket. None showed a stable, same-sign effect across all three
years at a magnitude that would matter: family 1's top bucket crosses sign
(2021 +0.037, 2022 +0.007, 2023 -0.011); family 4's top bucket also crosses
sign (2021 +0.011, 2022 -0.024, 2023 -0.020); family 6's top bucket is the
one pattern with consistent sign across years (+0.025, +0.023, +0.019) despite
never being individually significant — flagged as the single
"worth-revisiting-with-more-data" pattern in the whole study, explicitly not
promotable on current evidence. Bin-sensitivity (alternate cutoffs) was
checked where computed and did not change any REJECT verdict.

## 8. PROMOTE/PARTIAL/REJECT table

All 13 families: **REJECT**. Zero PROMOTE, zero PARTIAL. See the table in
item 4 (full detail, including mechanism plausibility and N≥150 checks, in
`WORKSTREAM_B_DISCOVERY_2021_2023_RESULTS.md`).

## 9. Null/adverse findings

Reported in full, not filtered: family 1's most extreme bucket (Elo far less
bullish on A than the market) shows the market's own confidence was, if
anything, understated relative to the eventual outcome — the opposite of
what a "trust Elo over the market" hypothesis would want. Family 13's
favourite-longshot bands do not show the classic monotonic bookmaker-market
pattern at all (0.5-0.6: -1.9pp, 0.6-0.7: -1.9pp, 0.7-0.8: +0.7pp, 0.8-0.9:
-0.3pp, 0.9-1.0: +2.5pp) — no monotonicity, no CI excluding zero. Family 10's
largest point deviation runs in the direction opposite the hypothesised
mechanism (the more-rested player under-, not over-, performing the market's
implied probability). None of these change any REJECT verdict; they are
recorded because the operator's standard is to report every result honestly,
including the ones that contradict the hypotheses being tested.

## 10. Number of hypotheses eligible for 2024 development validation

**Zero.** Per the operator's own explicit ordering (2024/2025 evaluation only
follows candidates that survive 2021-2023 discovery), no family is opened
against 2024 data. 2024 and 2025 remain completely untouched for any
market-edge purpose.

## 11. What a candidate would have looked like as a bet, if one had validated

None did, so this is illustrative only, to make explicit what "PROMOTE" was
always going to require even in the counterfactual case: a bucket with N≥150,
a Bonferroni-significant deviation between realised outcome rate and the
market's own implied probability, a plausible causal mechanism, same-sign
year stability, and robustness to alternate binning — clearing 2024
development validation and 2025 final historical OOS confirmation — and
even then, `market_reference_probability` here is a non-executable BASIC-tier
last-traded-price proxy: no back/lay ladder, no commission, no liquidity or
staleness model exists. A real bet would additionally require positive net
EV after realistic execution costs (commission, spread, slippage), a
liquidity check at the size intended, and the full paper-trading gate before
any live stake — none of which has been built, because there is currently
nothing to build it for.

## 12. Exact next gate

This is the natural checkpoint. Per the operator's own standing instruction,
Football Cycle 2 was queued to start "unless Tennis Phase 2 returns a clean
null or reaches a natural checkpoint" — this clean 13-for-13 null is exactly
that checkpoint. Three options are on file, decision deliberately left to
Fraser/the operator rather than made unilaterally here:

(a) **Close Workstream B's discovery phase here** and treat Betfair-tennis
    BASIC-tier last-traded pricing as well-calibrated against everything
    tested — no further tennis-market-edge work under this design unless a
    genuinely new information source or covariate is proposed.

(b) **Extend discovery** with a small number of additional, freshly
    pre-registered covariates (e.g. head-to-head history, tournament-specific
    seeding, weather/altitude for outdoor events) before declaring the
    discovery phase closed — this would be a new, separately pre-registered
    family set, not a re-test of the 13 already REJECTed.

(c) **Start Football Cycle 2** (xG + weather + fixture-congestion, queued
    and scoped in the roadmap §3) as the next parallel research stream, per
    the project's stated goal of multiple independent validated strategies
    rather than iterating further on a single clean null.

No live betting, paper trading, 2024/2025 evaluation, or new tennis
predictive-modelling cycle is authorised by this checkpoint. Zero validated
edges exist. "No bet is preferable to a negative-EV bet" remains the
standing rule.
