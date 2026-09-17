# Football Cycle 2 -- Sealed 2025/26 Out-of-Sample Protocol (H-FB2-002 only)

**Status: FROZEN, NOT YET AUTHORISED FOR EXECUTION.** Per the
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
