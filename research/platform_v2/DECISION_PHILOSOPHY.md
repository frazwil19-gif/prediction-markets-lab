# Decision Philosophy (locked 2026-09-30, per Fraser's directive "PROBABILITY-FIRST DAILY BET ENGINE")

This document governs all future research and engine design. It changes no production behaviour. Anything that would change
production still needs its own approval.

## The objective
**Which available bets have the strongest probability of occurring, given historical data, current information and uncertainty,
and does the available payout adequately compensate us for the risk?**

The project is **not** a bookmaker-beating or value-hunting engine. Market mispricing is useful evidence where it exists, but it is
never a prerequisite for a prediction to count as strong.

## Permanent decision hierarchy
PROBABILITY → CONFIDENCE / STATISTICAL SUPPORT → CURRENT CONTEXT / DATA QUALITY → ODDS / PAYOUT / VALUE → RISK →
BETTING STRUCTURE → STAKE → DECISION

## Two separate qualities
| | Prediction quality | Bet quality |
|---|---|---|
| question | How likely is this outcome, and how sure are we? | Does this price, in this structure, justify risking money? |
| inputs | P, calibration and band support, uncertainty (σ), model/version, context, data quality | the above, plus offered and fair odds, payout, EV and its range, downside, bankroll impact, alternative structures |
| output | the **Prediction Board** (Stage A), ranked by probability and confidence | the **Betting Card** (Stage B): SINGLE / DOUBLE / TREBLE / LARGER MULTI / MIXED / WATCH / NO BET |

"**Strong prediction / poor bet**" is a legitimate, useful output. For example, P = 0.90 at odds 1.02 gives EV −8.2%. Such a prediction
stays visible on the board and is rejected **for staking at that price**. It is never counted as a failed prediction.

## Market consensus: a benchmark, never the target
- It is used as a benchmark, a prior, a sanity check and a disagreement detector. It may be the best available estimator where the
  evidence says so.
- **Agreement** between our P and the market supports confidence.
- **Large disagreement** triggers **investigation, not celebration**. Possible causes: stale information, injury, withdrawal, line-up
  change, context change, data fault, model-domain problem, or information the model lacks. The configured investigation
  threshold is |ΔP| > 0.10, the same size as the V2-6D contamination screen.
- **Disclosure:** the current frozen tennis engine *is* market-derived (the Betfair exchange midpoint). "Model vs market" is therefore
  currently "exchange vs bookmakers". Broader, non-market features belong to future probability research (stream A), not to
  betting rules.

## EV: kept, but downstream
EV = P × decimal odds − 1 is mathematically required before risking money. It is kept together with fair odds, payout, uncertainty,
sensitivity and bankroll risk. It is **never** the filter that decides which predictions exist or are shown. A structure is never
accepted with a negative expected return just because its win probability is high.

## Multis and qualification architecture
- Multis remain part of the engine and are evaluated dynamically alongside singles, mixed portfolios and NO BET.
- Two scoreboards always apply:
  - **predictions** — per leg; a 4/5 card is 4 correct and 1 wrong;
  - **bets** — as settled; the 4/5 accumulator lost.
- The frozen V2-7 experiment keeps its "every leg +EV" rule. Whether the final engine should qualify at **leg level** or at
  **complete-structure level** is an open research question. The V2-8 analyser reports both side by side. **Any alternative stays
  research-only until it is prospectively validated.**

## Grading
The scale is A+ / A / B / C / REJECT, plus NO BET. **No thresholds exist yet.** Thresholds will be configurable, pre-registered and
empirically monitored. There are no forced daily A or A+ picks, and £1–£10 a day is an aspiration, not a quota.

## Research streams (kept distinct)
- **A** — historical probability research
- **B** — prospective probability validation
- **C** — price and payout research
- **D** — card and portfolio research
- **E** — profitability validation of the complete decision process

None of these collapses into a single "market edge" question.

## Anti-overfitting
V2-7H and V2-8 answered the first-order historical card questions. There will be no further mining of the same historical data for
profitable combinations. Value now comes from:
- clean prospective evidence;
- executable-price evidence;
- validated coverage of more sports and markets;
- portfolio analysis of genuinely strong predictions.
