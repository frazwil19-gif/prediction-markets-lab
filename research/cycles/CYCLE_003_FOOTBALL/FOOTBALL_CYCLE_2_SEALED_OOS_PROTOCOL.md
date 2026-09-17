# Football Cycle 2 -- Sealed 2025/26 Out-of-Sample Protocol (H-FB2-002 only)

**Status: AUTHORISED FOR EXECUTION (operator GO, 2026-09-17), subject to the Phase 0 sequential gate in section 17 -- 2025/26 data may not be acquired until the sealed-OOS classifier and every other pre-data step below are implemented, tested, and committed.** Per the
operator's explicit instruction ("define the future sealed OOS before
acquisition... do not acquire or inspect 2025/26 yet... if one or more
DEVELOPMENT-PROMOTE: STOP, do not yet inspect 2025/26, return a
decision-grade checkpoint, we will review the frozen specification
before authorising acquisition"), this document fixes the sealed-OOS
test in full BEFORE any 2025/26 data is downloaded, read, or inspected
in any way. Writing this document does not itself authorise acquiring
the data -- that is a separate, later decision, made only after this
protocol has been reviewed.

## 0. Scope

Only **H-FB2-002** (SOT differential x extreme-favourite price band)
reached DEVELOPMENT-PROMOTE (see
`H_FB2_001_H_FB2_002_DEVELOPMENT_CHECKPOINT.md`). **H-FB2-001**
(Dominant-Side Mispricing) was DEVELOPMENT-REJECT and is closed; it has
no sealed-OOS protocol and will not be tested against 2025/26 data
under this hypothesis ID. A genuine future revisit of the Dominant-Side
Mispricing question would require a new hypothesis ID and a fresh
pre-registration, not a re-run of H-FB2-001 against new data.

## 1. Data source

Football-Data.co.uk, the same source used throughout Football Cycle 1
and Cycle 2 (`data/raw/football/football_data_co_uk/{E0,E1,SC0}/2025_26/`),
extracted with the existing, already-tested `football_richer_extraction.py`
and `football_leakage_safe_features.py` modules, unchanged. No new
acquisition pathway, scraper, or vendor is introduced for this test.

## 2. Competitions

E0 (Premier League), E1 (Championship), SC0 (Scottish Premiership) --
identical to the development corpus, no addition or removal of
competitions.

## 3. Season / date range

The complete 2025/26 season, from its first eligible match date through
either (a) the season's final matchday, or (b) the date this protocol
is executed, whichever comes first if the test is run before the
season concludes. If run mid-season, the exact cutoff date used is
recorded in the results, and the season is not "topped up" with more
matches later under the same evaluation -- a genuine sealed test is
run exactly once.

## 4. Eligibility

Identical rule to the development-test script's `build_eligible()`:
non-missing `market_1x2_opening_home_probability` and both
`home_team_overall_last10_avg_sot_for` / `away_team_overall_last10_avg_sot_for`
(leakage-safe, `.shift(1)`-lagged rolling features carried forward from
the end of the 2024/25 season for each team's first 2025/26 matches --
i.e. rolling history is NOT reset to empty at the season boundary,
exactly as the existing rolling-feature module already handles
cross-season continuity for Elo and rolling windows).

## 5. Exclusions

Identical to the development corpus: no walkovers/abandonments-without-
a-result; a match is excluded outright (never imputed) if any required
field is missing.

## 6. Market fields

1X2 opening fair home-win probability (price-band definition) and the
match's actual full-time result (home win vs not). No new markets are
introduced for this test -- H-FB2-002 was never about pricing an SOT
market, it is about incremental predictive information relative to the
1X2 price (see the pre-registration document section 4, item D).

## 7. Bookmaker/source and probability transformation

Identical to development: Football-Data's own "Avg" cross-bookmaker
field, margin-removed via the existing two-way normalisation in
`probability/margin_removal.py`.

## 8. Settlement

Not applicable to H-FB2-002 in the AH sense (no handicap settlement
involved) -- the outcome is simply the actual full-time 1X2 result.

## 9. Primary metric (frozen, identical to the development test)

Sort all eligible 2025/26 matches ascending by
`market_1x2_opening_home_probability`; take the top quintile (index 4,
recomputed on the 2025/26 sample specifically -- the "top 20%" rule is
frozen, not a fixed numeric probability threshold carried over from the
development corpus, exactly as the development test itself recomputed
quintiles on its own combined corpus rather than reusing the original
discovery-slice cut points); within that quintile, median-split by
rolling-last-10 SOT differential (home minus away); compute:

```
diff_high_minus_low = home_win_rate(high SOT diff half)
                     - home_win_rate(low SOT diff half)
```

with a 95% percentile bootstrap CI (seed=42, n=2000), using the exact
same `median_split_diff` logic already implemented and tested in
`scripts/run_h_fb2_002_development_test.py` -- reused unchanged, not
reimplemented.

## 10. Uncertainty method

Percentile bootstrap, seed=42, 2,000 resamples -- identical to every
prior stage of this project.

## 11. PASS / PARTIAL / FAIL logic (frozen, mechanical, mutually exclusive)

A new, dedicated function will be required (mirroring
`holdout_verdict.classify_holdout_result` and
`development_verdict.classify_development_result`, but for a true
sealed-OOS decision, not a development one) -- specified here in full so
it can be implemented and reviewed before 2025/26 is touched:

1. **FAIL** if the primary 95% CI does not lie entirely above zero
   (i.e. the CI includes zero, or is negative) -- there is no
   "inconclusive but promising" category for a one-shot sealed test in
   the FAIL/PASS boundary; a CI that merely touches zero is FAIL, not
   PARTIAL, because this is the ONE evaluation this hypothesis gets
   against genuinely unseen data.
2. Otherwise **PASS** if, in addition to (1)'s CI condition: the
   realised sample size in the top quintile is >= 100 (item J's floor,
   applied to the 2025/26 sample on its own); AND the point estimate's
   sign matches the development-phase point estimate's sign (a genuine
   sign reversal, even with a technically-positive CI due to a small
   sample, is treated with suspicion -- see item 13 below for the
   small-sample fallback).
3. Otherwise **PARTIAL** -- covers a CI that excludes zero and is
   positive, but with the realised 2025/26 sample below the 100-match
   floor (see item 13).

This function must be written, reviewed, and committed BEFORE 2025/26
is acquired -- the same discipline as Tennis Cycle 1's pre-holdout
freeze (`TENNIS_CYCLE_1_PRE_HOLDOUT_FREEZE.md`) and its dedicated
`holdout_verdict.py`.

## 12. Minimum N

100 matches in the top price quintile (item J, unchanged from
development). A full 2025/26 season across E0/E1/SC0 is expected to
contain roughly 1,100-1,200 matches in total (matching the development
corpus's per-season average), of which the top quintile would be
roughly 220-240 -- comfortably above the floor if the full season is
used; a mid-season evaluation (section 3(b)) could fall short.

## 13. Treatment if the realised sample is smaller than expected

If the top-quintile sample at the time of evaluation is below 100
matches (e.g. a mid-season run, or an unexpectedly small 2025/26
corpus), the result is reported as **PARTIAL regardless of the CI**,
and is NOT treated as a PASS even if the point estimate is favourable
and the CI technically excludes zero -- a small sample's CI excluding
zero is a weaker form of evidence than the same CI on the full
season's data, and this rule prevents an early, favourable-looking
partial season from being mistaken for the genuine one-shot test.

## 14. Missing-price rules

A match with any required field missing is excluded outright, never
imputed, exactly as in every prior stage.

## 15. No-retuning rule

The quintile cut (top 20% by 1X2 opening home-win probability), the
SOT rolling window (last-10 matches, overall context), and the median-
split method are frozen exactly as used in the development test.
None of these may be changed after 2025/26 results are visible. If a
genuine methodological defect is found only once 2025/26 data is
examined, the defect and its fix must be documented transparently
(mirroring the two real linkage bugs found and fixed during Tennis
Workstream B Phase 1), and the sealed test is then explicitly marked as
compromised for THIS specific evaluation -- it does not get a second
attempt at looking "fresh" on the same 2025/26 data.

## 16. What this protocol does not authorise

Writing this document does NOT authorise downloading, reading, or
inspecting any 2025/26 data. That remains a separate decision for
Fraser/the operator, to be made only after this protocol itself has
been reviewed and, if necessary, revised (without ever weakening its
PASS/PARTIAL/FAIL logic to make a specific expected result more likely
-- any revision must be justified on methodological grounds alone,
documented as such, and made before, never after, the data is touched).

## 17. Correction (2026-09-17, pre-acquisition) -- refined PASS/PARTIAL/FAIL logic; population-completeness precondition; frozen role of the continuous-correlation diagnostic

The operator's GO authorisation (2026-09-17) explicitly required resolving
any ambiguity in sections 11-13's verdict logic NOW, before 2025/26 is
acquired, and documenting the correction transparently -- mirroring the
same discipline already used once for Tennis Cycle 1's freeze document
(see roadmap update, "Correction to the freeze's PASS/PARTIAL/FAIL logic,
applied before 2025 was opened"). This section supersedes sections 11-13
for implementation purposes; those sections are kept unmodified above as
the historical record of the original design.

### 17.1 Restating Phase 0 -- the absolute rule

No 2025/26 file may be downloaded, opened, inspected, parsed, summarised,
counted, or otherwise accessed until ALL of the following are implemented,
tested, documented, and committed: this section's frozen classifier logic;
its implementation as tested code (`src/prediction_markets_lab/research/
oos_verdict.py`); its boundary tests; and a commit that predates any
2025/26 acquisition, whose hash is recorded in the eventual checkpoint as
proof of precedence. This mirrors, item for item, the discipline already
used for H-FB2-001/H-FB2-002's own pre-registration (commit `4757031`
preceding the development test).

### 17.2 Refined verdict logic (frozen, ordered, mutually exclusive, exhaustive)

Evaluated in this exact order:

1. **PARTIAL ("population deviation")** if any of the three frozen
   competitions (E0, E1, SC0) is entirely absent from the acquired
   2025/26 raw corpus. This check is evaluated FIRST, before the CI or
   sample-size conditions, and its result does not depend on how
   favourable the effect looks -- if the acquired population does not
   match the pre-registered E0+E1+SC0 specification, the evaluation
   cannot count as the genuine one-shot sealed test, regardless of
   outcome. (This did not need a case in sections 11-13 because it was
   implicitly assumed all three competitions' files would always be
   available; made explicit now as its own precondition, per the
   operator's explicit request for a "missing competition" boundary
   case.)
2. Otherwise **FAIL** if the primary 95% CI does not lie entirely above
   zero -- i.e. `ci_lower <= 0.0` (this covers a CI that includes zero,
   a CI that touches zero exactly at its lower bound, and a CI that is
   entirely negative). Unchanged from section 11.1: there is no
   "inconclusive but promising" category for this one-shot test.
3. Otherwise **PASS** if the realised top-price-quintile sample size is
   `>= 100` (the frozen floor, item J / section 12). Unchanged from
   section 11.2, but the redundant "sign matches development" clause in
   the original section 11.2 is dropped: given step 2 already requires
   `ci_lower > 0.0` for a one-sided-positive pre-registered hypothesis,
   the point estimate's sign is already positive by construction, so a
   separate sign-match check adds nothing and is removed to avoid two
   rules silently disagreeing at a boundary. This is a resolution of an
   ambiguity, not a loosening: no result that would have passed under
   the old wording now fails, and no result that would have failed now
   passes.
4. Otherwise **PARTIAL ("sample too small")** -- the CI is favourable
   (step 2 passed) but the realised sample falls short of the floor
   (step 3 failed). Unchanged from section 13.

### 17.3 Competition-level effects and per-competition sample size are diagnostics only, never gating

Per section 9's own instruction ("Do not reject a passing aggregate
hypothesis merely because one small league has a noisy negative estimate
unless the frozen classifier explicitly requires competition-level
stability"): **this frozen classifier does NOT require competition-level
stability of the effect itself as a gating condition.** A competition
contributing very few matches to the top quintile, or showing a locally
noisy or even sign-reversed estimate, does not by itself change a PASS to
anything else, provided step 1's population-completeness precondition is
satisfied (i.e. the competition's raw season data was acquired at all --
it simply may not have produced many top-quintile matches this season).
Competition-by-competition breakdowns are reported in the OOS results as
`DIAGNOSTIC -- NOT PRIMARY EVIDENCE`, exactly as section 9 already
requires, never folded into the mechanical verdict.

### 17.4 Season-level stability does not apply to a one-shot test

The development-phase verdict (`development_verdict.py`) required a
minimum count of individual seasons sharing the pooled sign, because that
test spanned five seasons. The sealed OOS test spans exactly one season
(2025/26) by definition (section 3), so no season-level stability
criterion exists or is applicable here -- this is stated explicitly so
its absence from the classifier's inputs is a documented design decision,
not an oversight.

### 17.5 Frozen role of the continuous SOT-differential correlation diagnostic

Development produced a primary quintile-4 median-split effect of +0.0999
(95% CI [+0.0511, +0.1557]) alongside a near-zero secondary continuous
Pearson correlation (`sot_diff` vs. the market's own pricing residual,
r=0.0212, see item I of the H-FB2-002 pre-registration and the
development checkpoint). This discrepancy is real and is not explained
away. Before 2025/26 is acquired, its role in the sealed OOS report is
frozen as follows:

- The same continuous-correlation diagnostic is computed on the 2025/26
  eligible top-quintile sample, using the identical `pearson_correlation`
  function already implemented and tested
  (`football_cycle2_development.py`), unchanged.
- It is reported alongside the primary result, explicitly labelled
  `DIAGNOSTIC -- NOT PRIMARY EVIDENCE`, exactly like the competition
  breakdown.
- It is discussed in terms of three pre-registered interpretive
  possibilities, decided now rather than invented after seeing the OOS
  number: (A) the true relationship is genuinely nonlinear or
  threshold-like -- concentrated at the median split rather than varying
  smoothly across the whole range of `sot_diff`, which a linear
  correlation coefficient would under-detect even if the subgroup effect
  is real; (B) the true relationship is a broad, roughly monotonic
  effect that the development sample's correlation estimate simply
  under-measured by chance; (C) the development-phase quintile-4 effect
  is itself a sample artefact of that specific corpus, and the near-zero
  correlation is the more representative signal.
- **This diagnostic never overrides, upgrades, or downgrades the
  mechanical PASS/PARTIAL/FAIL verdict from section 17.2.** Its sole
  role is descriptive: whether the 2025/26 pattern (primary effect vs.
  continuous correlation) resembles or diverges from the development
  pattern is reported as commentary, not as a rule input. If the OOS
  correlation also comes back near zero alongside a PASS primary result,
  this is reported honestly as continued unresolved evidence for
  interpretation (A) or (C) above -- it does not retroactively become
  grounds to question a mechanical PASS, and it does not get "explained"
  with a new post-hoc mechanism invented after the number is seen.

### 17.6 What this correction does not authorise

This section resolves ambiguity in the verdict logic and formally
records the operator's GO decision. It does not, by itself, mean
2025/26 may now be acquired -- that remains gated on implementing,
testing, and committing `oos_verdict.py` first (section 17.1 / Phase 0).
