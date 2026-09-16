# Football Cycle 2 -- Behaviour Atlas (Step G)

**Discovery-phase document. No entry below has been formally
pre-registered or validated.** Per the operator's explicit instruction,
only three statuses are used here: **OBSERVED** (a pattern exists in
the data but is weak, inconsistent, or unconfirmed), **CANDIDATE** (a
pattern is directionally consistent, adequately sampled, and worth
formal pre-registration), and **REJECTED** (checked and not supported
-- a clean negative result, kept on record rather than discarded).
**Nothing here is VALIDATED.** That status belongs to the later,
separate formal pre-registration/backtest/OOS pipeline this document
explicitly does not enter.

Source data: `data/processed/football/cycle_002_discovery_features.csv`
(5,800 matches, all pre-match features leakage-safe per step D).
Discovery slice: 2020/21-2022/23 (N=3,480). Stability slice (NOT
out-of-sample -- see
`CYCLE_002_CHRONOLOGICAL_SPLIT_DECISION.md`): 2023/24-2024/25
(N=2,320). Raw results:
`data/processed/football/cycle_002_discovery_scan_results.json` and
`cycle_002_stability_check_results.json`.

---

## BEH-001 -- Favourite-longshot bias, 1X2 (opening prices)

- **Variables:** market 1X2 opening home-win fair probability
  (source: Cycle 1 consensus, unmodified) vs actual full-time result.
- **Population:** discovery slice, N=3,467 (13 matches lacked a
  qualifying consensus).
- **Market:** 1X2.
- **Direction:** at the two extremes, the sign is FLB-consistent
  (lowest-probability bin: observed win rate 0.130 vs predicted
  0.146, signed gap -0.015 -- longshots slightly overpriced; highest
  bin: observed 0.770 vs predicted 0.742, signed gap +0.028 --
  favourites slightly underpriced). The five middle bins do not follow
  a monotonic pattern (one middle bin gap is -0.049, larger than
  either extreme, in the OPPOSITE direction).
- **Sample size:** 3,467 (≈347 per decile bin).
- **Effect:** overall ECE = 0.0255 (2.55 percentage points, sample-
  weighted mean absolute calibration gap across 10 bins). Modest for a
  liquid, well-monitored market.
- **Uncertainty:** no per-bin confidence interval computed (a
  limitation of this pass, noted rather than glossed over); the ECE
  itself has no CI here either.
- **Stability:** not re-checked (this behaviour did not reach
  CANDIDATE; see step F's rule that only CANDIDATE-status findings are
  re-checked on the stability slice).
- **Possible mechanism:** the standard FLB literature mechanism
  (bettor risk-seeking on longshots, skewness preference) would
  predict exactly this two-tail pattern; the non-monotonic middle
  bins argue against it being the dominant effect here.
- **Status: OBSERVED.** Suggestive at the extremes, not a stable or
  monotonic pattern, no CI. Does not meet the bar for CANDIDATE.

## BEH-002 -- Favourite-longshot bias, Over/Under 2.5 (opening prices)

- **Variables:** market Over-2.5 opening fair probability (source: this
  cycle's Football-Data "Avg" summary, margin-removed) vs actual total
  goals > 2.5.
- **Population:** discovery slice, N=3,480 (100% coverage).
- **Market:** Over/Under 2.5.
- **Direction:** no consistent pattern -- bin gaps alternate sign with
  no relationship to bin rank (e.g. bin 2 of 10 has the largest gap,
  -0.081, while bins on either side are much smaller).
- **Sample size:** 3,480.
- **Effect:** overall ECE = 0.0278, similar magnitude to BEH-001 but
  with no discernible directional structure.
- **Uncertainty:** none computed (same limitation as BEH-001).
- **Stability:** not checked (did not reach CANDIDATE).
- **Possible mechanism:** none supported -- the pattern looks like
  sampling noise around a genuinely well-calibrated market rather than
  a systematic bias.
- **Status: REJECTED.** No FLB-consistent (or any other systematic)
  pattern found for this market at this bin resolution.

## BEH-003 -- Market calibration vs Elo-gap magnitude

- **Variables:** |pre-match Elo rating gap (incl. home advantage)| in
  terciles vs market 1X2 home-win calibration (ECE).
- **Population:** discovery slice, three terciles of ~1,155-1,156
  matches each.
- **Market:** 1X2.
- **Direction:** none -- ECE is essentially flat across terciles
  (low-gap 0.0238, mid-gap 0.0303, high-gap 0.0254). The middle
  tercile is marginally the worst-calibrated, not the extremes.
- **Sample size:** ~1,155 per tercile.
- **Effect:** max spread across terciles is 0.0065 (well within what
  ECE point estimates commonly move by from sampling noise alone at
  this N).
- **Uncertainty:** no CI computed.
- **Stability:** not checked (did not reach CANDIDATE).
- **Possible mechanism:** none needed -- this is a clean null. The
  market appears to price large and small pre-match strength gaps with
  similar accuracy (for the WHO-wins question specifically; see
  BEH-009 for the magnitude/handicap question, which tells a different
  story).
- **Status: REJECTED.** No evidence extreme mismatches are priced
  differently from moderate ones, for the 1X2 win-probability question.

## BEH-004 -- Rolling SOT differential vs market opening price

- **Variables:** rolling-last-10 shots-on-target differential (home
  minus away, pre-match) vs actual home win rate, WITHIN five bands of
  market opening home-win probability (a within-price-band comparison,
  not a raw correlation, so any effect found is plausibly incremental
  to the market's own view rather than something the market has
  already priced).
- **Population:** discovery slice, five price quintiles of ~686 each.
- **Market:** 1X2 (conditioning market); SOT is a match-statistics
  feature.
- **Direction:** POSITIVE in all five quintiles in the discovery
  slice (teams with a higher rolling SOT differential than their
  quintile's typical opponent win more often, even holding the
  market's price roughly constant) -- effect size grows toward the
  price extremes (+0.061 in the biggest-underdog quintile, +0.079 in
  the biggest-favourite quintile; the three middle quintiles are
  smaller: +0.015, +0.029, +0.053).
- **Sample size:** 686 per quintile (3,430 total qualifying rows).
- **Effect:** the biggest-favourite quintile's 95% CI [+0.009,
  +0.146] excludes zero; the biggest-underdog quintile's CI [0.000,
  +0.122] touches zero at the boundary; the three middle quintiles'
  CIs all include zero individually.
- **Uncertainty:** percentile bootstrap, 2,000 resamples, seed 42, per
  quintile (not a joint test across quintiles -- that is a limitation:
  "all five point estimates positive" is suggestive on its own terms
  but was not formally tested as a joint hypothesis).
- **Stability check (2023/24-2024/25, N=2,320, NOT out-of-sample):**
  the broad "positive everywhere" pattern does NOT replicate -- two of
  five quintiles flip sign (-0.006, -0.045). The extreme-favourite
  quintile's effect DOES persist and grows: +0.097, CI [+0.010,
  +0.175], excluding zero in both non-overlapping periods.
- **Possible mechanism:** for the most one-sided matches specifically,
  a team materially outshooting its typical level relative to a
  similarly-priced peer may signal short-term over/underperformance
  the market's aggregate price does not fully separate from
  "true" pre-match strength -- but this is speculative; the effect is
  measured, not explained.
- **Status: CANDIDATE**, narrowed. The broad multi-quintile claim is
  downgraded to REJECTED-in-its-general-form; the specific
  "extreme-favourite-quintile SOT effect" is CANDIDATE, having a CI
  excluding zero in two independent, non-overlapping multi-season
  slices with a similar point estimate (+0.079 discovery, +0.097
  stability). Worth formal pre-registration restricted to this
  subgroup, not the whole sample.

## BEH-005 -- Recent-form vs SOT divergence against market movement

- **Variables:** last-5-match points-per-game differential (short-term
  form) and last-10-match SOT differential (longer-window underlying
  quality), each correlated against opening-to-closing 1X2 home-
  probability movement.
- **Population:** discovery slice, N=3,428.
- **Market:** 1X2 movement (opening vs closing).
- **Direction:** OPPOSITE of the hypothesised "overreaction to recent
  results" pattern -- correlation with movement is weaker for recent
  form (r=+0.007, essentially zero) than for the longer SOT window
  (r=+0.058). If anything this points away from a recency-driven
  overreaction story, not toward one.
- **Sample size:** 3,428.
- **Effect:** both correlations are weak in absolute terms; neither
  represents a strong linear relationship.
- **Uncertainty:** no CI computed on the correlations or their
  difference.
- **Stability:** not checked (did not reach CANDIDATE).
- **Possible mechanism:** none supported for the specific
  "recent-goals overreaction" hypothesis as operationalised here.
- **Status: REJECTED**, for this specific operationalisation. This
  does not rule out overreaction in some other form (e.g. a specific
  recent-result type, like a big win/loss) -- only this test of it.

## BEH-006 -- Market movement informativeness beyond closing price

- **Variables:** opening-to-closing 1X2 home-probability movement vs
  actual home win rate, WITHIN five bands of the closing price.
- **Population:** discovery slice, five closing-price quintiles of
  ~693 each.
- **Market:** 1X2.
- **Direction:** inconsistent sign across quintiles (+0.031, +0.028,
  -0.001, -0.039, -0.016) with no relationship to price level.
- **Sample size:** 693 per quintile.
- **Effect:** every quintile's 95% CI includes zero.
- **Uncertainty:** percentile bootstrap, 2,000 resamples, per
  quintile.
- **Stability:** not checked (did not reach CANDIDATE).
- **Possible mechanism:** none -- consistent with the closing price
  already impounding whatever information drove the movement (a
  textbook "prices are close to efficient with respect to their own
  recent history" result).
- **Status: REJECTED.** No evidence that opening-to-closing movement
  adds information beyond the closing snapshot for the outcome
  itself. (This does not preclude movement predicting something
  else, such as further movement -- not tested here.)

## BEH-007 -- Home-favourite vs away-favourite calibration asymmetry

- **Variables:** market calibration (favourite's own win probability
  vs actual) split by whether the home or away side is the market
  favourite.
- **Population:** discovery slice; home-favourite N=2,276, away-
  favourite N=1,191.
- **Market:** 1X2.
- **Direction:** home favourites slightly less well-calibrated (ECE
  0.022) than away favourites (ECE 0.015).
- **Sample size:** 2,276 / 1,191.
- **Effect:** 0.007 ECE gap -- present but modest.
- **Uncertainty:** no CI on the gap.
- **Stability:** not checked (did not reach CANDIDATE).
- **Possible mechanism:** possible mild market bias toward the home
  side generally (a well-documented phenomenon in some historical
  football-betting literature), but the gap is small and unconfirmed
  here.
- **Status: OBSERVED.** Directionally interesting, too small and
  uncertain (no CI, modest absolute gap) to call a CANDIDATE yet.

## BEH-008 -- Competition-specific 1X2 calibration

- **Variables:** market 1X2 home-win calibration (ECE), computed
  separately for E0 (Premier League), E1 (Championship), and SC0
  (Scottish Premiership).
- **Population:** discovery slice; E0 N=1,140, E1 N=1,655, SC0 N=672.
- **Market:** 1X2.
- **Direction:** SC0 (Scottish Premiership) is markedly less well
  calibrated than either English competition in the discovery slice
  (ECE 0.040 vs 0.011 and 0.014).
- **Sample size:** 672 (SC0, smallest of the three but still well
  above the minimum-subgroup gate).
- **Effect:** ~3x the ECE of E0 in the discovery slice.
- **Uncertainty:** no CI computed.
- **Stability check (2023/24-2024/25):** SC0 remains the highest ECE
  and at a similar absolute level (0.041, essentially unchanged from
  discovery's 0.040) -- the SC0-specific level looks stable. However
  E1's ECE more than doubled between slices (0.014 -> 0.031),
  narrowing the SC0-vs-E1 gap substantially and undermining the
  cleaner "English leagues are better calibrated" framing from the
  discovery slice alone.
- **Possible mechanism:** SC0 is plausibly less liquid / less heavily
  monitored by the bookmaker panel than the English competitions
  (fewer bettors, fewer sharp participants), which would predict
  persistently worse calibration -- consistent with SC0's stable
  absolute ECE across both slices. E1's instability suggests either a
  genuinely noisier market there or a real change in coverage/
  liquidity across the two periods that would need further
  investigation.
- **Status: CANDIDATE**, narrowed to the SC0-specific finding only
  ("SC0 1X2 calibration runs a persistent ~0.04 ECE across two
  non-overlapping multi-season periods"), not the broader
  "English-vs-Scottish" framing, which did not hold up.

## BEH-009 -- Dominant-Side Mispricing (LOCKED pre-registered family)

- **Variables:** 1X2 opening favourite probability (pre-match
  dominance measure, defined by the market itself, never by the
  outcome) vs Asian Handicap home-cover calibration (ECE), comparing
  the top quartile of favourite strength ("extreme favourites") to the
  rest of the sample.
- **Population:** discovery slice; extreme-favourite N=676 (mean
  favourite probability 0.678), rest N=2,082 (mean 0.441); 232 pushes
  excluded from the clean cover-rate read (settled separately via a
  from-scratch, quarter-line-aware Asian Handicap settlement
  function).
- **Market:** Asian Handicap (conditioned on 1X2-defined dominance).
- **Direction:** exactly the pre-registered mechanism -- extreme
  favourites show substantially WORSE Asian Handicap cover calibration
  (ECE 0.049) than the rest of the sample (ECE 0.018), consistent with
  "the market prices WHO wins efficiently but the MAGNITUDE of
  dominance (the handicap line) less efficiently" for the most
  one-sided matches.
- **Sample size:** 676 / 2,082 (both well above the minimum-subgroup
  gate even after excluding pushes).
- **Effect:** ~2.7x the ECE for extreme favourites in the discovery
  slice (0.031 absolute gap).
- **Uncertainty:** no CI computed on the ECE gap itself (ECE is not a
  simple mean, so a bootstrap CI on it needs per-bin resampling not
  yet implemented -- an explicit limitation, not an oversight to
  paper over).
- **Stability check (2023/24-2024/25, N=2,309 settled, 149 pushes):**
  the DIRECTION replicates -- extreme favourites again show higher AH
  cover ECE (0.044) than the rest (0.035) -- but the GAP shrinks
  substantially, from 0.031 (discovery) to 0.0095 (stability), roughly
  a third of its original size.
- **Possible mechanism:** as pre-registered -- bookmakers may set the
  1X2 favourite/underdog split efficiently (a coarse, heavily-bet,
  heavily-scrutinised market) while the specific handicap LINE for
  very lopsided fixtures is a finer, lower-liquidity judgement more
  prone to mispricing, particularly at the tails of the dominance
  distribution.
- **Status: CANDIDATE.** This is the strongest and most theoretically
  grounded finding in this scan: a locked, pre-registered mechanism
  that shows a same-signed effect in two independent, non-overlapping
  multi-season periods. The shrinking magnitude across periods is
  reported honestly and is itself informative -- it argues for a real
  but likely smaller effect than the discovery-slice number alone
  would suggest, and any future formal test of this family should
  size its expected effect off the more conservative (stability-slice)
  estimate, not the discovery-slice one.

---

## Summary table

| ID | Behaviour | Market | Status | Discovery effect | Stability effect |
|---|---|---|---|---|---|
| BEH-001 | 1X2 favourite-longshot bias | 1X2 | OBSERVED | ECE 0.026, non-monotonic | not checked |
| BEH-002 | O/U 2.5 favourite-longshot bias | O/U 2.5 | REJECTED | ECE 0.028, no pattern | not checked |
| BEH-003 | Elo-gap magnitude vs calibration | 1X2 | REJECTED | flat ECE across terciles | not checked |
| BEH-004 | SOT differential vs price band | 1X2 | CANDIDATE (narrowed) | +0.079 in top quintile, CI excl. 0 | +0.097 in top quintile, CI excl. 0; broader pattern did not replicate |
| BEH-005 | Recent-form vs SOT divergence | 1X2 movement | REJECTED | opposite of hypothesised direction | not checked |
| BEH-006 | Movement vs closing price | 1X2 | REJECTED | inconsistent sign, all CIs incl. 0 | not checked |
| BEH-007 | Home vs away favourite calibration | 1X2 | OBSERVED | 0.007 ECE gap | not checked |
| BEH-008 | Competition-specific calibration | 1X2 | CANDIDATE (narrowed to SC0) | SC0 ECE 3x E0 | SC0 level stable; E1 unstable |
| BEH-009 | Dominant-Side Mispricing (LOCKED) | Asian Handicap | **CANDIDATE** | ECE gap 0.031 | ECE gap 0.0095 (direction holds, magnitude shrinks) |

**Nine checks run, none discarded. Three CANDIDATEs (BEH-004 narrowed,
BEH-008 narrowed, BEH-009), four REJECTED (clean nulls), two OBSERVED
(suggestive but unconfirmed). Zero VALIDATED, as required at this
stage.**
