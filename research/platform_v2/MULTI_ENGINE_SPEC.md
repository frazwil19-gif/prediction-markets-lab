# Layer C — Portfolio / Multi Engine Specification (DESIGN ONLY — multis stay disabled)

Rule, permanent: **a multi packages independently valid predictions. It never rescues weak ones.** Singles are the default.

## 1. The economics (why the gates below exist)
Multi expected return = Π(pᵢ × oᵢ) − 1. A multi **multiplies whatever edge or margin the legs carry**; it adds none.
- Legs priced at consensus (pᵢoᵢ ≈ 0.97): 2 legs give −5.9%, 3 legs give −8.7%.
- The directive's example (85%@1.18, 82%@1.22, 80%@1.25): leg ratios 1.003 / 1.000 / 1.000, so a 1.80 multi at
  ≈55.8% has EV ≈ +0.3%. A bigger payout with the same ~zero edge and much more variance.
- Practical constraint: a multi is placed at **one** bookmaker, so combined odds are the product of that book's prices,
  not the best price per leg across books. Exchanges don't offer cross-event multis. Evaluation must be per bookmaker.

## 2. MULTI_ELIGIBLE (leg-level)
A selection is MULTI_ELIGIBLE only if it passes **every** single-bet check except the payout floor/preferred range:
validated engine; support ≥ ADEQUATE (initially STRONG only); p_interval within max width; data quality OK; context
checked (V1: explicitly NONE, so eligibility is PAPER_ONLY until context exists or is waived by Fraser); fresh
quote; inside the money window; **and value ≥ 0 against an independent reference** (no negative-value leg, ever).
A leg that fails on probability, support, uncertainty or value is never eligible, whatever the combined odds.

## 3. Dependency screen (before any joint probability)
| relation | policy |
|---|---|
| same event (same-game multi) | **DISABLED.** Needs a validated joint model (§5) |
| same team / same player across events | block |
| same competition, same day | allowed with a dependency flag and an empirical adjustment (below) |
| shared weather / venue / lineup news | flag; block when context indicates a common shock |
| different sport / competition / day | independence assumed, **checked empirically** (§6) |

## 4. Joint probability — cross-event
Default P(joint) = Πpᵢ only after the screen passes. Joint uncertainty: Monte Carlo over each leg's band-reliability
Beta distribution (from the engine's unseen-data hit rate in that band), giving a joint interval. Decisions use its lower
bound. Where same-competition dependence is flagged, apply the empirically measured joint/product ratio for that
relation, with its CI, instead of 1.0.

**Evidence (`CROSS_MARKET_AND_DEPENDENCY_EVIDENCE.json`, football 1X2 closing consensus ≥70% favourites, 293
same-day cross-match pairs):** realised joint 63.1% vs Π p 60.2%. That is explained by the favourites'
own under-prediction (singles won 79.9% vs 77.5% priced, and 0.799² ≈ 0.638), so there is **no sign of cross-event
dependence beyond marginal calibration**. Same-competition pairs: 68.4% vs 60.1% (n = 114; the CI is optimistic
because pairs share dates). It is suggestive, not established. Conclusion: cross-event multis are tractable, and
**leg calibration dominates joint accuracy**, which is another reason to fix margin removal first.

## 5. Same-game multis
Measured on 5,763 matches (realised joint ÷ independence product):
**Over 2.5 & BTTS = 1.54 · Home win & Over 2.5 = 1.18 · Home win & BTTS = 0.85.** Among strong home favourites (≥60%),
home win & Over 2.5 happened 50.5% vs 43.6% from multiplying market probabilities. Multiplying is badly wrong in both
directions. Future method: derive every same-game market from **one** scoreline distribution (market-implied Poisson
from Phase 5, extended with a dependence/low-score correction such as Dixon–Coles), validated on joint-outcome
calibration. Bookmakers price same-game multis with their own correlation margin, so these need their own value test.
Stays disabled until then.

## 6. Multi grading (all values are config and initial; none tuned for profit)
Legs ≤ 3 (2 first) · joint P lower bound ≥ configured floor · combined odds judged by the **existing** payout policy
(1.33 floor, 1.40–2.50 preferred) · multi EV (per-bookmaker product) ≥ the existing EV floor, computed against
independent-reference probabilities · a multi is never shown ahead of a better-supported single.

## 7. Exposure controls
Multi stake ≤ the smallest single stake its legs would get · daily multi exposure cap (config, as a fraction of the
daily cap) · a leg may appear in at most one multi · a leg's single and multi exposure are counted together · a
multi counts as correlated exposure on every leg's event/team · max multis per day (config, initially 1) · loss locks
apply to singles and multis combined.

## 8. Evidence required before any real-money multi
1. **Historical replay** (feasible now for cross-event 1X2, same closing snapshot): leg calibration, joint
   calibration (predicted vs realised joint rate by band), per-book combined odds, EV, drawdown and variance vs the
   same legs as singles.
2. **Prospective paper multis**, generated mechanically from the daily pool, never hand-picked: expected vs realised
   joint win rate, bankroll impact, CLV of legs.
3. Explicit promotion decision (`MODEL_PROMOTION_STANDARD.md`).

---
## Clarification after V2-1 (operator §31, 2026-09-23)
The arithmetic in §1 stands: combining legs does not change their underlying expected value. **That is not a reason
to drop multis.** Their purpose is *payout construction*: several individually strong predictions that are each too
short to bet as singles can be combined into one position with a meaningful payout. The multi question is therefore:
(1) is every leg a trustworthy prediction, (2) is the joint probability defensible, and (3) do the offered combined
payout and risk suit the bankroll? Value against an independent reference is **not** a primary eligibility criterion
for a leg. It is reported, and the combined position still passes the Bet-Selection layer's payout, value and risk
checks as a whole.

## Three-tier status (design)
| status | requires |
|---|---|
| PREDICTION_VALID | validated engine, band support (n ≥ 200 unseen), complete data, no material warning |
| SINGLE_ELIGIBLE | PREDICTION_VALID plus the existing single-bet gates (money window, probability floors, payout policy, value floor, risk) |
| MULTI_ELIGIBLE | PREDICTION_VALID plus P ≥ a configured leg floor, band CI width within max, quote fresh, independent of the other legs under the dependency screen. **Standalone odds may be below the single-bet payout floor.** |

## Evidence from V2-1 relevant to multi legs
Tennis supplies the leg pool. On the sealed holdout, 590 ATP matches (11.6%) were ≥85% (91.2% predicted, 91.0% won)
and 333 (6.6%) were ≥90% (94.0% predicted, 93.4% won). Cross-event tennis legs from different matches are
plausibly independent, but that is *untested*. The next multi-research step would be a historical joint-calibration
replay on tennis pairs from the same day, using exactly this holdout data (design only).
