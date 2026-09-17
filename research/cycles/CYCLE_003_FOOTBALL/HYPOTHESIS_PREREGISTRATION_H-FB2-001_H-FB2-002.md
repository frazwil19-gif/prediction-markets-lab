# Football Cycle 2 -- Formal Hypothesis Pre-Registration: H-FB2-001, H-FB2-002

**Status at commit time: DEFINED (pre-registered, not yet tested).**
This document is committed BEFORE either hypothesis is tested against
development data. Per the operator's explicit instruction ("pre-
registration must be complete before testing... commit the
pre-registration BEFORE running development tests"), the commit hash
that introduces this file is the fixed reference point: any
development-test result reported after it was, by construction,
computed after the specification below was frozen, never before.

This document answers the operator's 2026-09-17 instruction in full.
It supersedes nothing already committed: the discovery record
(`CYCLE_002_CHRONOLOGICAL_SPLIT_DECISION.md`,
`FOOTBALL_CYCLE_2_BEHAVIOUR_ATLAS.md`,
`FOOTBALL_CYCLE_2_DISCOVERY_CHECKPOINT.md`, and the six commits from
`c280989` through `1e257ce`) is frozen and immutable -- nothing in it
is rewritten in light of anything that happens in this phase.

**Naming note.** `research/hypotheses/hypothesis_registry.csv` already
contains six placeholder ideas, `H-FB-001` through `H-FB-006`, written
2026-08-03 (before Football Cycle 2's discovery process existed) and
never tested or revisited. Those are untouched by this document. The
two hypotheses below use the operator's own `H-FB2-` prefix
specifically to avoid any collision or confusion with that earlier,
unrelated placeholder list.

## 0. Discovery record freeze -- confirmed, not re-opened

- The discovery outputs, Behaviour Atlas, chronological split decision,
  checkpoint report, discovery scripts (`run_cycle_002_discovery_scan.py`,
  `run_cycle_002_stability_check.py`), and candidate definitions are all
  committed as of `1e257ce` (2026-09-16) and are not modified by this
  phase.
- The existing 2020/21-2024/25 corpus (5,800 matches, E0/E1/SC0) remains
  permanently classified **DISCOVERY + DEVELOPMENT ONLY** per
  `CYCLE_002_CHRONOLOGICAL_SPLIT_DECISION.md` section 5. It is never
  subsequently described as sealed out-of-sample (OOS).
- **2025/26 data has not been downloaded, read, or inspected in any way
  as of this document's commit**, and will not be until a separate,
  later, explicitly authorised step (see the companion
  `FOOTBALL_CYCLE_2_SEALED_OOS_PROTOCOL.md`, itself written and frozen
  BEFORE that data is touched).

## 1. Two hypotheses pre-registered, kept entirely separate

Per the operator's explicit instruction, **both** surviving CANDIDATEs
from the discovery checkpoint that showed a same-signed, stability-
persistent effect are pre-registered now, not just the originally
locked family:

- **H-FB2-001**, derived from **BEH-009** (Dominant-Side Mispricing,
  the locked family) -- strongest mechanism, replicated direction.
- **H-FB2-002**, derived from **BEH-004** (SOT differential x extreme-
  favourite price band) -- narrower than H-FB2-001's original framing,
  but arguably more directly informative because it is explicitly
  framed as information *incremental to* the market price, not a
  calibration anomaly.

**BEH-008** (Scottish Premiership calibration) is explicitly **not**
promoted to a hypothesis in this round, per the operator's instruction.
It remains recorded as CANDIDATE in the Behaviour Atlas, unchanged,
available for a future round.

No combined model, interaction term, or joint test between H-FB2-001
and H-FB2-002 is specified or run in this phase. They are developed,
tested, and classified completely independently.

## 2. Shared conventions (apply to both hypotheses)

- **Corpus**: the existing frozen 2020/21-2024/25 canonical/discovery
  dataset (`data/processed/football/cycle_002_discovery_features.csv`,
  5,800 rows, E0/E1/SC0), used here in full as the DEVELOPMENT sample
  (per section 0, no OOS survives inside it, so discovery-slice and
  stability-slice rows are combined for this phase -- this is a
  deliberate, documented change from the discovery scan's own slice-
  restricted scripts, not an accidental scope change).
- **Bookmaker/consensus price source (item R)**: Football-Data.co.uk's
  own cross-bookmaker "Avg" summary field, run through this project's
  existing two-way margin-removal procedure
  (`probability/margin_removal.py`) to produce a fair probability --
  labelled throughout as `source_avg_fair_*` in the underlying
  extraction and as `market_..._source_avg_*_probability` in the
  discovery-features dataset. This is the source's own cross-bookmaker
  computation (see `FOOTBALL_CYCLE_2_DISCOVERY_CHECKPOINT.md` and
  `football_richer_extraction.py`'s module docstring for the Max/Avg
  semantics finding) -- never presented as a single bookmaker's quote.
- **Margin-removal procedure (item S)**: standard two-way normalisation
  -- fair_probability_side = (1/odds_side) / sum_of_(1/odds) across both
  sides of the market, applied identically to every match.
- **Uncertainty method**: percentile bootstrap, seed=42, 2,000
  resamples, i.i.d. resampling within each group -- identical
  convention to every prior stage of this project (discovery scan,
  stability check, Tennis Cycle 1/Workstream B).
- **Multiple-testing family**: `football_cycle2_development_2026_09`
  -- both hypotheses share this family label in the registry so any
  future addition to this specific development round is visibly
  grouped; this round tests exactly 2 pre-registered estimands (the
  two hypotheses' primary metrics), no correction beyond that is
  applied since no additional comparisons are made within this family
  (no threshold scanning, no additional subgroup promoted to a formal
  test).
- **Commission/execution caveat (item T)**: none of the metrics in this
  phase are net-of-cost, net-of-commission, or execution-aware. No
  Betfair/exchange football price data exists in this project (see
  `FOOTBALL_CYCLE_2_INITIATION_REPORT.md`); only static bookmaker
  closing/opening snapshots are available. Every number in this
  document and its development-test results is a **theoretical, gross,
  pre-execution pricing-error estimate only** -- explicitly not a net
  expected value, not adjusted for spread/slippage/liquidity, and not a
  trading signal.
- **Missing-data handling (item Q)**: a match is excluded from a given
  hypothesis's test if any field that hypothesis's estimand needs is
  missing (never imputed). Exact exclusion counts are reported in the
  development-test results, not assumed here.
- **No-retuning rule (applies throughout)**: neither hypothesis's
  population-defining rule (a price quintile/quartile cut, a rolling
  window length, a favourite-side definition) is changed after seeing
  development results. A change is permitted only to correct a
  documented methodological defect (mirroring the correction already
  made once in Phase 2 of Tennis Workstream B), never to improve a
  result.
- **Prohibition on post-result threshold modification (item W)**: no
  scanning of favourite cut-offs, AH lines, SOT windows, Elo
  thresholds, leagues, seasons, odds bands, bookmakers, or metrics is
  performed after development results are visible. Any such
  exploration is confined to a clearly labelled "exploratory, not
  confirmatory" appendix and can generate at most a future hypothesis,
  never rescue either H-FB2-001 or H-FB2-002.

---

## 3. H-FB2-001 -- Dominant-Side Mispricing (Asian Handicap), derived from BEH-009

### A. Economic/mechanistic rationale
Bookmakers set the coarse, heavily-bet, heavily-scrutinised 1X2
favourite/underdog split efficiently, but the specific Asian Handicap
LINE for very lopsided fixtures is a finer, lower-liquidity judgement
more prone to a systematic (not just noisy) pricing error, particularly
at the tails of the pre-match dominance distribution.

### B. Exact eligible population
Every E0/E1/SC0 match in the 2020/21-2024/25 development corpus with:
non-missing 1X2 opening home and away fair probabilities; a non-missing
Asian Handicap opening line and both AH fair probabilities (home and
away, from source Avg); and non-missing full-time goals for both teams
(needed for settlement). Pre-match favourite side and favourite
strength are determined ONLY from the 1X2 opening fair probabilities,
never from the outcome.

### C. Exact pre-match variables
`market_1x2_opening_home_probability`, `market_1x2_opening_away_probability`
(together define `favourite_side` and `favourite_p = max(home, away)`);
`market_ah_opening_line`, `market_ah_opening_source_avg_home_probability`,
`market_ah_opening_source_avg_away_probability`.

### D. Exact market
Asian Handicap, opening price (the same timing used throughout the
discovery phase for this family).

### E. Exact outcome/settlement definition
Full-time goal margin (home goals minus away goals) settled against the
AH opening line via `settle_asian_handicap_home` (whole/half/quarter-
line aware; quarter lines split 50/50 between neighbouring half-lines),
then re-expressed from the pre-match FAVOURITE's own side via
`favourite_perspective` (both in
`src/prediction_markets_lab/research/football_cycle2_development.py`,
15 unit tests, hand-verified cases including the quarter-line
half-result case already validated in the discovery checkpoint).
Pushes (0.5) and quarter-line half-results (0.25/0.75) are excluded
from the clean cover-rate read, exactly as the discovery-phase scan did.

### F. Exact direction of hypothesis
Two-sided going in (per the operator's explicit instruction not to
assume a direction): extreme favourites' actual AH-cover rate differs
systematically from the market's own fair AH-cover probability, in
EITHER direction. The discovery-phase ECE finding (extreme favourites
show worse calibration) is consistent with either a positive or a
negative signed residual -- this development test is what determines
which.

### G. Exact statistical estimand
**Primary**: the mean SIGNED pricing residual for the pre-match
favourite's side of the AH line, restricted to the extreme-favourite
group (defined in population terms below):

```
residual_i = 1{favourite_i covers} - favourite_cover_probability_i
mean_residual = mean(residual_i) over the extreme-favourite group
```

computed by `signed_ah_pricing_residual()`. Positive => the market
UNDERPRICES the favourite covering (favourites cover more than implied
-- backing the favourite on the handicap would show positive
theoretical edge before costs on this evidence). Negative => the market
OVERPRICES the favourite covering.

**Extreme-favourite group definition (frozen, recomputed on the full
development corpus)**: the top quartile of `favourite_p` across all
eligible matches in the development corpus (same operational rule as
the discovery scan's `extreme_favourite_top_quartile` -- top 25% by
favourite strength -- now computed over the combined discovery+
stability corpus rather than the discovery slice alone, since no part
of the corpus is held back as OOS in this phase). The comparator group
("non-extreme rest") is the remaining 75%, computed and reported for
context but is not this hypothesis's primary estimand target (H-FB2-001
is specifically about the extreme-favourite subgroup, per BEH-009's own
framing).

### H. Primary metric
Mean signed AH pricing residual for the extreme-favourite group (item G),
with its 95% percentile bootstrap CI.

### I. Secondary diagnostics
- The unsigned ECE comparison already established in the discovery
  checkpoint (extreme vs rest), reported again on the full development
  corpus for continuity, not as a second primary metric.
- The same signed residual computed for the non-extreme comparator
  group, to check whether any mispricing is specific to the extreme
  tail or present more broadly (a broader effect would be a genuine,
  useful finding, but would also mean BEH-009's "dominant-side-
  specific" framing needs qualifying -- reported honestly either way).
- Season-by-season and competition-by-competition (E0/E1/SC0) breakdown
  of the primary signed residual.
- A robustness check using the top QUINTILE (20%) instead of the top
  QUARTILE (25%) as the "extreme" cut, to gauge fragility to the exact
  cut point (does NOT replace or compete with the frozen quartile
  definition as the primary result).

### J. Minimum sample size
100 clean (non-push, non-quarter-result) matches in the extreme-
favourite group, matching `MIN_SUBGROUP_N` used throughout this cycle.
Expected order of magnitude, extrapolating from the discovery-slice
(676) and stability-slice (roughly 580, back-calculated from its
reported n=477 clean settled) counts, is comfortably above this floor
for the combined corpus.

### K. Multiple-testing treatment
See section 2 (shared): `football_cycle2_development_2026_09` family,
2 pre-registered primary estimands total across both hypotheses, no
threshold scanning within this family.

### L. Confidence interval method
Percentile bootstrap, seed=42, 2,000 resamples (section 2).

### M. Development-period evaluation procedure
Run once, mechanically, via `scripts/run_h_fb2_001_development_test.py`,
reading the frozen `cycle_002_discovery_features.csv` and reporting
every item in this section without post hoc modification.

### N. Stability requirements
The primary result must have the SAME SIGN in at least 3 of the 5
individual seasons (2020/21 through 2024/25) considered separately (an
additional, more granular replication check than the discovery
checkpoint's original 2-period, discovery-vs-stability comparison), and
must not depend on a single competition alone (i.e. must not flip sign
if any single one of E0/E1/SC0 is excluded).

### O. Failure criteria (DEVELOPMENT-REJECT)
- The primary 95% CI on the extreme-favourite signed residual includes
  zero, OR
- the sign is unstable across seasons/competitions per item N, OR
- a genuine methodological defect is found in the settlement or
  favourite-perspective logic that cannot be fixed without materially
  changing the population or estimand (in which case the hypothesis is
  re-specified as a new ID, never silently patched and re-scored).

### P. Promotion criteria (DEVELOPMENT-PROMOTE)
All of: primary CI excludes zero; sign stable per item N; N clears item
J's floor in every reported season with a usable sample; no single
competition drives the entire effect; the effect's economic direction
is coherent (i.e. it says something specific and actionable about which
side of the handicap is mispriced, not just "some calibration gap
exists"). Anything meeting the CI/sign/N bar but failing the
single-competition-independence or stability-breadth checks is
DEVELOPMENT-PARTIAL, not DEVELOPMENT-REJECT outright and not
DEVELOPMENT-PROMOTE either.

### Q. Missing-data handling
See section 2 (shared).

### R. Bookmaker/consensus price source
See section 2 (shared).

### S. Margin-removal procedure
See section 2 (shared).

### T. Commission/execution caveat
See section 2 (shared).

### U. Exact definition of what would falsify the hypothesis
The hypothesis (as operationalised here) is falsified if the primary
CI includes zero, or if the sign of the point estimate reverses when
measured on a materially different but reasonable extreme-favourite
cut (e.g. quintile vs quartile) in a way that suggests the discovery-
phase finding was an artefact of the specific 25% cut rather than a
real, broad tail effect. A shrinking-but-same-signed effect (as already
seen between the discovery and stability slices) does NOT by itself
falsify the hypothesis.

### V. Future sealed-OOS protocol
Deferred entirely to `FOOTBALL_CYCLE_2_SEALED_OOS_PROTOCOL.md`,
written and frozen before any 2025/26 data is acquired.

### W. Prohibition on post-result threshold modification
See section 2 (shared).

---

## 4. H-FB2-002 -- SOT Differential x Extreme-Favourite Price Band, derived from BEH-004

### A. Economic/mechanistic rationale
For the most one-sided matches specifically, a team materially
outshooting its typical level (rolling shots-on-target differential)
relative to a similarly-priced peer may signal short-term
over/underperformance that the market's aggregate 1X2 price does not
fully separate from "true" pre-match strength. This is explicitly
framed as information INCREMENTAL to the market's own price (the
discovery test controls for price band before looking at SOT), not a
standalone predictor.

### B. Exact eligible population
Every E0/E1/SC0 match in the 2020/21-2024/25 development corpus with
non-missing `market_1x2_opening_home_probability` and non-missing
rolling last-10-match overall SOT-for figures for both the home and
away team (`home_team_overall_last10_avg_sot_for`,
`away_team_overall_last10_avg_sot_for` -- both leakage-safe, `.shift(1)`
lagged, per `features/football_leakage_safe_features.py`, mechanically
tested against look-ahead leakage in step D).

### C. Exact pre-match variables
`market_1x2_opening_home_probability` (defines the price quintile);
`home_team_overall_last10_avg_sot_for`,
`away_team_overall_last10_avg_sot_for` (their difference is
`sot_diff = home - away`).

### D. Exact market
1X2 (the conditioning/price-band market); the underlying outcome tested
is the actual 1X2 result (home win vs not), exactly as in the
discovery-phase D4 check -- this hypothesis is NOT about pricing an SOT
market (none exists), it is about whether SOT differential predicts the
1X2 outcome beyond what the opening price already implies.

### E. Exact outcome/settlement definition
Actual full-time result: home win (`outcome_full_time_result == "H"`)
vs not.

### F. Exact direction of hypothesis
One-sided, per the discovery-phase finding's own direction, extended
(not re-derived) into this test: within the extreme-favourite price
quintile specifically, a HIGHER rolling SOT differential (home minus
away) is associated with a HIGHER home-win rate than the price alone
would imply, i.e. the effect is expected to be POSITIVE.

### G. Exact statistical estimand
**Primary (frozen, identical to the discovery-phase D4 check's method,
applied unchanged to the larger development corpus)**: within the
extreme-favourite price quintile, split the group at its own median
`sot_diff` into "low SOT diff" and "high SOT diff" halves, and compute:

```
diff_high_minus_low = home_win_rate(high SOT diff half)
                     - home_win_rate(low SOT diff half)
```

with a 95% bootstrap CI (two-sample, `bootstrap_ci_mean_diff`, same
convention as the discovery scan).

**Extreme-favourite price quintile definition (frozen, recomputed on
the full development corpus)**: sort all eligible matches ascending by
`market_1x2_opening_home_probability`, split into 5 equal-count
quintiles, take quintile index 4 (the top 20% -- the strongest home
favourites specifically, matching the discovery-phase D4 check's own
convention exactly, including that it is defined from the HOME team's
perspective, not a generic "favourite of either side" framing). This
mirrors BEH-004's own narrowed finding precisely: the broader
"positive in every quintile" claim did not replicate and is NOT
retested here; only the specific quintile-4 effect that did replicate
is carried forward as a formal hypothesis.

### H. Primary metric
`diff_high_minus_low` for price quintile 4 (item G), with its 95% CI.

### I. Secondary diagnostics
- Season-by-season and competition-by-competition (E0/E1/SC0)
  breakdown of the primary metric.
- A robustness check using QUARTILES (4-way split) instead of
  QUINTILES (5-way split) for the price-band cut, to gauge fragility
  to the exact number of bands (does not replace the frozen
  quintile-based primary result).
- A robustness check using the last-5-match SOT differential instead of
  last-10, to gauge fragility to the rolling-window length (does not
  replace the frozen last-10 primary result).
- A supplementary correlation diagnostic: within the same quintile-4
  group, the Pearson correlation between `sot_diff` and the market's
  own pricing residual (`1{home win} - market_1x2_opening_home_probability`),
  reported as a secondary, more continuous view of "does SOT diff track
  the market's own error," not as a replacement primary metric.

### J. Minimum sample size
100 matches in the top price quintile, matching `MIN_SUBGROUP_N`.
Expected order of magnitude, extrapolating from the discovery slice's
686-per-quintile count, is roughly 1,150 for the combined development
corpus (comfortably above the floor).

### K. Multiple-testing treatment
See section 2 (shared).

### L. Confidence interval method
Percentile bootstrap, seed=42, 2,000 resamples (section 2).

### M. Development-period evaluation procedure
Run once, mechanically, via `scripts/run_h_fb2_002_development_test.py`,
reading the frozen `cycle_002_discovery_features.csv`.

### N. Stability requirements
Same-signed (positive) point estimate in at least 3 of the 5 individual
seasons considered separately, and not dependent on a single
competition alone.

### O. Failure criteria (DEVELOPMENT-REJECT)
- The primary 95% CI includes zero, OR
- the point estimate is negative (wrong direction per the pre-
  registered one-sided hypothesis), OR
- the sign is unstable across seasons/competitions per item N.

### P. Promotion criteria (DEVELOPMENT-PROMOTE)
All of: primary CI excludes zero AND is positive; sign stable per item
N; N clears item J's floor; no single competition drives the entire
effect. Meeting the CI/sign bar but failing the stability-breadth or
single-competition-independence checks is DEVELOPMENT-PARTIAL.

### Q. Missing-data handling
See section 2 (shared).

### R. Bookmaker/consensus price source
See section 2 (shared) -- 1X2 opening fair probability specifically for
this hypothesis's price-band definition.

### S. Margin-removal procedure
See section 2 (shared).

### T. Commission/execution caveat
See section 2 (shared). This hypothesis in particular has no direct
route to a trade at all yet -- it is about incremental predictive
information relative to the 1X2 price, not about a mispriced SOT
market (none exists); any future trading application would need this
information to be tested against an executable price, which is a
separate, later step.

### U. Exact definition of what would falsify the hypothesis
A primary CI that includes zero, or a negative point estimate, or a
sign that reverses in a majority of individual seasons.

### V. Future sealed-OOS protocol
Deferred entirely to `FOOTBALL_CYCLE_2_SEALED_OOS_PROTOCOL.md`.

### W. Prohibition on post-result threshold modification
See section 2 (shared).

---

## 5. What this document does NOT authorise

Per the operator's explicit instructions: no acquisition or inspection
of 2025/26 data; no combined/interaction model between H-FB2-001 and
H-FB2-002; no formal promotion of BEH-008; no broadening into xG,
weather, injuries, new leagues, Betfair football, or paid data; no
paper trading; no live trading; no new football behaviour discovery
beyond what is already in the frozen Behaviour Atlas. This document
only fixes the two hypotheses' specifications before the development
test in the immediately following commit.
