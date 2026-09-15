# Cycle 2 Tennis -- Exploratory Analysis (Workstream A3)

**Data-first discovery pass over 14564 canonical TML-Database ATP matches (2021-2025). This is DISCOVERY, not betting-edge validation -- no market price exists yet to compare against (see reports/research/TENNIS_HISTORICAL_ODDS_SOURCE_AUDIT.md), so nothing here is labelled an edge. Every feature is built with a strict no-look-ahead rule: for a given match, every rolling/expanding statistic uses only matches strictly before it for the player(s) involved (see tests/unit/test_cycle_002_tennis_exploratory_analysis.py for the direct check on this).**

## 1. Rank gap and upset frequency

Across 14342 matches with a clear rank favourite (excluding exact rank ties), the favourite (lower ATP rank) wins **64.0%** of the time overall -- this is the baseline every other cut below should be read against.

**Favourite win rate by rank-gap size** (bigger gap = bigger favourite):

| rank_gap_bucket | n | rate |
|---|---|---|
| 1-5 | 1010 | 0.541 |
| 6-10 | 964 | 0.593 |
| 11-25 | 2726 | 0.593 |
| 26-50 | 3429 | 0.626 |
| 51-100 | 3318 | 0.665 |
| 101-250 | 2032 | 0.705 |
| 250+ | 863 | 0.766 |

**By surface:**

| surface | n | rate |
|---|---|---|
| Clay | 4229 | 0.634 |
| Grass | 1551 | 0.642 |
| Hard | 8529 | 0.643 |

**By tournament level:**

| tourney_level | n | rate |
|---|---|---|
| 250 | 5111 | 0.598 |
| 500 | 2119 | 0.652 |
| A | 349 | 0.665 |
| D | 875 | 0.672 |
| F | 75 | 0.640 |
| G | 2518 | 0.701 |
| M | 3171 | 0.636 |
| O | 124 | 0.734 |

**By best-of format:**

| best_of | n | rate |
|---|---|---|
| 3 | 11764 | 0.627 |
| 5 | 2578 | 0.697 |

As expected from tennis's well-documented format effects, this is a real, sanity-checking finding, not a discovery: best-of-5 matches should show a higher favourite win rate than best-of-3 (more sets gives the better player more chances to assert themselves) -- worth confirming the direction matches that prior before trusting anything else in this report.

## 2. Rolling recent-form edge (last 10 matches, no look-ahead)

| form_bucket | n | rate |
|---|---|---|
| b much better | 1479 | 0.298 |
| b better | 2324 | 0.393 |
| similar | 5404 | 0.507 |
| a better | 2609 | 0.612 |
| a much better | 1174 | 0.738 |

`form_bucket` compares player_a's pre-match rolling win rate (last 10 matches, strictly before this one) against player_b's. If recent form carries real information beyond current ranking, the win rate should move monotonically across these buckets.

## 3. Surface-specific rolling form edge

| surface_form_bucket | n | rate |
|---|---|---|
| b much better | 1273 | 0.311 |
| b better | 2146 | 0.402 |
| similar | 4836 | 0.507 |
| a better | 2350 | 0.603 |
| a much better | 1040 | 0.719 |

Same idea as section 2, but restricted to the player's rolling win rate on THIS match's specific surface only -- tests whether surface specialism carries information beyond overall form.

## 4. Rest days and match congestion (fatigue)

| rest_bucket | n | rate |
|---|---|---|
| a much less rested | 2712 | 0.495 |
| a less rested | 138 | 0.449 |
| similar rest | 8208 | 0.513 |
| a more rested | 786 | 0.580 |
| a much more rested | 2028 | 0.475 |

`rest_bucket` compares how many days since each player's last match, taking the difference (player_a's rest minus player_b's).

**Favourite win rate by the favourite's own match congestion (matches played in the prior 14 days):**

| player_a_matches_last_14_days | n | rate |
|---|---|---|
| 0 | 5642 | 0.650 |
| 1 | 2814 | 0.613 |
| 2 | 2347 | 0.624 |
| 3 | 1478 | 0.641 |
| 4 | 931 | 0.654 |
| 5 | 680 | 0.666 |
| 6 | 270 | 0.681 |
| 7 | 112 | 0.705 |
| 8 | 42 | 0.786 |
| 9 | 19 | 0.737 |
| 10 | 5 | 0.400 |
| 11 | 2 | 0.500 |

Note: this cut is keyed on player_a's congestion regardless of whether player_a is the favourite, which is a real simplification of this first pass -- the honest reading is directional only, not a clean fatigue-of-the-favourite result. Flagged here rather than glossed over.

## 5. Head-to-head history

Only 4804 of 14564 matches (33.0%) have ANY prior head-to-head history within this 2021-2025 window (most ATP pairings are first-time meetings in a given 5-year window, or the data simply doesn't go back far enough to capture earlier meetings) -- this cut has real coverage limits, stated plainly rather than implied to be more complete than it is.

| h2h_bucket | n | rate |
|---|---|---|
| a dominated by b | 1852 | 0.398 |
| a slightly behind | 246 | 0.455 |
| even | 551 | 0.525 |
| a slightly ahead | 289 | 0.592 |
| a dominates b | 1866 | 0.613 |

## 6. Handedness

| handedness_matchup | n | rate |
|---|---|---|
| L vs L | 250 | 0.448 |
| L vs R | 1360 | 0.482 |
| R vs L | 1915 | 0.524 |
| R vs R | 10897 | 0.508 |

Restricting to lefty-vs-righty matchups only (3275 matches): left-handed players win **47.9%** of the time -- essentially even, and if anything slightly below 50%, which does NOT confirm the common tennis-folklore claim that left-handers carry a structural edge. Important caveat, stated plainly: this raw figure does not control for rank -- if lefties in this dataset happen to skew slightly lower-ranked than the righties they played (plausible, since left-handers are a minority of the tour), that alone would explain a below-50% raw win rate without saying anything about handedness itself. A fair test would compare this after controlling for the rank gap, which this pass does not do -- flagged as a specific follow-up rather than left as an unqualified finding.

## 7. Age gap

| age_bucket | n | rate |
|---|---|---|
| a much younger | 2719 | 0.554 |
| a younger | 2278 | 0.539 |
| similar age | 3832 | 0.506 |
| a older | 2405 | 0.476 |
| a much older | 3321 | 0.471 |

## 8. What this pass does NOT cover, and why

Stated honestly rather than silently skipped: this pass does not attempt explicit travel/geographic-transition features (defensible geographic distance between consecutive tournaments would need a tournament-location reference table this dataset doesn't include), interaction effects between the features above (e.g. "does the form edge matter more on clay than hard" -- a natural next question, deferred to keep this pass tractable), seasonality/fatigue-across-a-season effects, or any formal statistical significance / multiple-testing correction (every cut above is reported as a raw rate and sample size, not a p-value or confidence interval -- with roughly a dozen cuts examined here, some apparent patterns are expected to arise by chance alone, and none of this should be read as a confirmed effect without that correction applied first).

## 9. Candidate hypotheses for pre-registration (NOT yet validated)

Per the instruction to only form hypotheses after exploration, not before: the patterns above (if they hold up under the multiple-testing caveat) suggest three candidates worth formally pre-registering before any model-building: (1) recent rolling form (last 10 matches) adds information on top of current ATP rank -- testable by comparing a rank-only baseline against a rank-plus-rolling-form model on log loss/Brier score under walk-forward validation; (2) surface-specific rolling form adds information beyond overall rolling form, specifically on clay and grass where the raw skill transfer from hard-court results is weaker; (3) match congestion (matches in the prior 14 days) has a fatigue effect large enough to matter once combined with rank, worth testing as an interaction term rather than a standalone feature given section 4's coverage caveat. None of these are betting edges -- they are candidate PREDICTIVE features for Workstream A4's odds-independent baseline models, to be evaluated on calibration and skill, not assumed to translate into anything tradeable without market prices to compare against.
