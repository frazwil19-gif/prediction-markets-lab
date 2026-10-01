# MONEY_ELIGIBILITY_REVIEW — <engine / market / competition> — <date>

Template (pcard-1). A review is triggered by the Evidence & Promotion Protocol (FULL trigger: h ≤ 2.5pp in the
decision region) — never by elapsed time, by a winning streak or by wanting more bets. Completing this template does
**not** activate money: activation requires Fraser's explicit written approval in chat, recorded in section 9.

## 1. Scope
Engine id + version, market, competitions, bsv2 rule version, pcard rule version, period covered (first/last decision).

## 2. Evidence state history
Dates each protocol state was reached (HISTORICAL_VALIDATED → … → PAPER_FINANCIAL_VALIDATION), with commit hashes.

## 3. Probability quality (prospective, decision region D only)
n, ESS, mean P vs observed rate with Wilson 95% CI, half-width h, calibration slope/intercept with CI, Brier, log loss,
reference benchmark (market consensus) on the same rows. Historical (pre-prospective) numbers listed separately.

## 4. Paper financial evidence
Paper bets, settled, void; expected vs realised P&L (units); ROI with bootstrap CI; max drawdown; longest losing run;
CLV where available; breakdown by grade (A+/A/B), odds band, source type, competition.

## 5. Execution realism
Price availability at the recorded odds (snapshot evidence), price age at decision, exchange commission, practical
minimum stakes, account restrictions risk, settlement source reliability (voids, disputes).

## 6. Risk
Proposed bankroll, policy (from the bsv2 bankroll block only), per-bet and daily caps, loss lock, drawdown stop,
correlation/duplicate exposure checks. No martingale, chasing or recovery staking.

## 7. Negative findings and open issues
Every failed check, unexplained deviation, data gap or rule change during the period (never omitted).

## 8. Recommendation
One of: REMAIN_PAPER / EXTEND_PAPER (with the specific evidence still missing) / MONEY_ELIGIBLE_CANDIDATE (with scope
and limits). The recommendation is advice only.

## 9. Decision (Fraser only)
Approved? yes/no · scope · bankroll · start date · review date · quoted approval text and timestamp.
