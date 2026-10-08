# NFL moneyline — PROVISIONAL_LIVE tier and pre-registered promotion / demotion rule

Registered 2026-10-08, BEFORE any prospective NFL prediction has settled (first prospective prediction:
Buccaneers @ Cowboys, 2026-10-09 00:15Z). Directive: ChatGPT/Fraser consolidated operating directive, 8 Oct 13:02.
Engine: `nfl_moneyline.market@1` (consensus de-vig, holdout 2020–21 gate A, slope 1.02 [0.81, 1.27], n=550).

## Tier (effective now)
Registry: `engine_status` stays `VALIDATED_HISTORICAL` (so bsv2-4 evaluates it unchanged); new field
`live_tier: PROVISIONAL_LIVE`. The Daily Card enforces:
- same bsv2-4 gates as every engine (P ≥ 0.50, net EV ≥ +2%, odds ≥ 1.33, fresh price, spread);
- £1 maximum stake (the live default; no enhanced stake);
- at most **1** NFL live bet per card/day (`config/daily_card_v1.yaml: provisional_live.max_live_bets_per_day_per_engine`);
- **never** a Big Card leg;
- further qualifying NFL bets on the same day show as `SKIP — provisional-live engine limit` (still logged as paper).

## Evaluation population
All settled prospective NFL predictions on `predictions/unified_ledger.csv` (engine `nfl_moneyline.market`, version 1,
prediction_timestamp ≥ 2026-10-08), whether or not they became bets. Ties/void are excluded. Bet P&L is reported but is
NOT a promotion criterion (too few bets to be informative).

## Metrics tracked (weekly report)
Brier score, log loss, calibration-in-the-large (mean P − win rate), logistic calibration slope with 95% CI,
Spiegelhalter z, reliability by 10-pt band; bet-level expected vs realised profit and CLV where available.

## Look schedule (fixed, to limit optional-stopping bias)
Checks only at n = 100, 150, 200 settled predictions and every +50 thereafter.

## PROMOTE to LIVE (remove provisional limits; Big Card allowed) — all must hold, at n ≥ 200
1. calibration slope 95% CI contains 1.0 AND its lower bound ≥ 0.80;
2. Spiegelhalter |z| < 1.96;
3. calibration-in-the-large 95% CI contains 0.
Promotion is proposed in the weekly report and applied only with Fraser's approval as a versioned registry change.

## DEMOTE to paper (money_eligible=false) — any one, at any check with n ≥ 100
1. Spiegelhalter |z| > 2.58; or
2. calibration slope 95% CI upper bound < 0.80 (systematic over-confidence); or
3. a data/price defect affecting NFL rows (immediate, outside the look schedule).

## Otherwise
Remain PROVISIONAL_LIVE until the next look; if n < 200 when the regular season ends, remain PROVISIONAL_LIVE into
next season (no promotion on a partial sample).

## Notes / honesty
- The engine is market consensus, so it can only be as calibrated as the market; its EV vs a single book is the
  dispersion between books, not a proprietary edge.
- Expected volume: favourites at P ≥ 0.5 mostly price below the 1.33 payout floor, so live NFL bets will be rare.
- The automated slope/z computation for this rule is a deferral (first look at n=100 is several weeks away); it will be
  implemented and tested before the first look.
- NHL is NOT covered by this rule. It stays PROVISIONAL_PROSPECTIVE / paper; no retrospective recalibration. Any NHL
  live tier needs a separate pre-registration.
