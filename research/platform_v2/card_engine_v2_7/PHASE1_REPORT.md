# V2-7 Dynamic Betting-Card Engine (singles / doubles / trebles) — Phase 1 Research Report (2026-09-30)

**Status: research only.** No production, workflow, gate or engine change; no purchase; no merge. Pre-registration: `PREREGISTRATION.md`
(commit `f4ded15`, before any joint result). Code: `scripts/v2_7_card_engine_research.py`. Numbers: `RESULTS.json`.
Evidence classes: **A** probability-only · **B** indicative historical odds · **C** executable multi backtest (**not possible**) · **D** prospective.

## 1. Executive audit
| capability | status |
|---|---|
| Frozen engines | ATP/WTA (Betfair midpoint, live; LTP historical), NBA (average odds), football 1X2/O-U (multi-book consensus), DC (provisional). Unchanged. |
| Historical P + outcomes | ATP 12,202 · WTA 10,352 (2021–25) · NBA 10,527 on disk · football 6,960 (2020/21–2025/26). Holdouts already opened once. |
| Ledgers | First-snapshot prediction ledger (calibration); same-scan `probability_snapshots.csv` + `exchange_probability_snapshots.csv` (bsv2-2/3); per-book `price_snapshots.csv`; immutable paper singles; annotations; settlements. |
| Price controls | Same-snapshot P↔price, latest-snapshot quotes only, 240-min freshness, Betfair width ≤ 0.03, commission by source, fail-closed. |
| Singles | `bsv2-3` live, verified (run 36624496060: 1 genuine paper bet). |
| **Multis** | **Absent.** `MULTI_RESEARCH_ELIGIBLE` is a *single-leg* label (P ≥ 0.80 strong prediction), not a combination. `bet_selection_v2/multi.py` has a dependency-flag schema (same event/participant blocked, same tournament/round flagged) but no card builder, no ledger, no pricing. |
| Accumulator prices | **None anywhere.** The Odds API returns per-selection prices only. A same-book *indicative* combined price (the product of that book's leg prices in one snapshot) is computable from the live `price_snapshots.csv`, but actual acca availability, related-contingency rules, payout caps and whether each book's multiple equals the product are **unverified**. |
| Cannot test now | Executable multi ROI (class C). Joint calibration for *same-event* or *cross-market* legs (no data). Live multi frequency beyond one scan. |

## 2. Mathematical specification
Leg i (one selection, distinct event): P_i (same-snapshot engine P), source, calibration band, uncertainty σ_i, book b, odds O_i,b,
timestamp, EV_i = P_i·O_i·(1−c_b) − 1 (commission only for exchanges), gate reasons.

Card of k ∈ {1, 2, 3} legs at **one** book b, independent events:
- P_joint = ∏P_i; O_joint = ∏O_i,b (indicative until verified per book); EV = P_joint·O_joint − 1 = ∏(1+EV_i) − 1; break-even P = 1/O_joint.
- Each added leg multiplies the gross return multiplier by (P_i·O_i). That is > 1 only if the leg has positive EV, and it cuts the win
  probability by a factor of P_i. **Negative-EV legs make the card worse multiplicatively.** The typical live favourite has P·O ≈ 0.95–0.97,
  so a treble of typical favourites is ≈ −10%.
- **Uncertainty (analytic, not a haircut):** Var(log P_joint) ≈ Σσ_i²/P_i², where σ_i combines (a) the band-level calibration CI (holdout
  Wilson half-width, e.g. ±1.4–2.3 pp at n ≈ 1,000–2,400) and (b) half the Betfair book width (≤ 0.015 under bsv2-3). Sensitivity:
  ∂EV/∂P_i = O_joint·∏_{j≠i}P_j.
- Dependence: multiplication only for **distinct events** that A1/A2 support (below). Same event, same participant or cross-market on one
  match → `RESEARCH_ONLY` with no joint P (no data to estimate it). Same tournament or round → allowed but flagged (A1 found no deviation).
- Execution: all legs at the **same** bookmaker in the **same** snapshot. Mixing best prices from different books is never allowed.

## 3. Historical validation results
**A1 — joint calibration (class A, deterministic disjoint cards within sport-day).** Across **4 sports × 2 periods × 3 sizes × 3 bands**,
every predicted P_joint lies inside the Wilson 95% CI of the actual hit rate. Examples (holdout years, predicted → actual):
| | singles 65–80% | doubles 50–65% | doubles 65–80% | trebles 50–65% |
|---|---|---|---|---|
| ATP | 0.718 → 0.725 (n=1,666) | 0.563 → 0.552 (n=587) | 0.708 → 0.681 (n=185) | 0.553 → 0.489 (n=88) |
| WTA | 0.719 → 0.724 (n=1,495) | 0.565 → 0.519 (n=493) | 0.704 → 0.739 (n=142) | 0.554 → 0.561 (n=57) |
| NBA | 0.720 → 0.714 (n=993) | 0.564 → 0.567 (n=328) | 0.711 → 0.774 (n=102) | 0.556 → 0.561 (n=41) |
| Football | 0.715 → 0.728 (n=250) | 0.550 → 0.480 (n=25) | 0.709 → 1.000 (n=5) | — (n=0) |
- Tennis doubles from the same tournament vs different tournaments: both calibrated.
- **Limits:** doubles at 80%+ and all trebles above 65% have small n (1–61), so their CIs are wide. Football multis are thin.

**A2 — correlated failure.** Dispersion index of daily favourite losses: ATP 0.97 [0.91, 1.04] · WTA 0.94 [0.87, 1.02] ·
NBA 1.05 [0.98, 1.12] · football 0.96 [0.86, 1.06]. All intervals include 1, so there is **no evidence of clustered upset days**
(NBA is borderline at the upper end).
→ **The independence assumption for distinct events is supported at the precision the data allow.**

**B — indicative odds (tennis, Bet365 closing, Pinnacle-closing P; not the frozen engine, not executable):**
| | positive-EV legs | doubles (all legs +EV, same day) | trebles |
|---|---|---|---|
| ATP | 397 / 10,326 favourites (3.8%); ROI +3.7% | 103 cards on 70 of 312 days; est. EV +3.2%; hit 38.8% vs 40.1% predicted; ROI −0.3% | 21 cards; est. EV +5.8%; hit 19.0% vs 25.9%; ROI −25.9% |
| WTA | 401 / 8,823 (4.5%); ROI +0.8% | 87 cards; est. EV +2.8%; hit 40.2% vs 40.1%; ROI +1.1% | 14 cards; hit 14.3% vs 26.1%; ROI −25.0% |
Multis did not improve on singles in this diagnostic, and trebles are too few to judge.

**D — live (one scan, 29 Sep 20:11 UTC, tight books only, 53 favourites):** the median P·O per book is 0.945–0.966. Books with every leg
positive: BoyleSports 3 legs → 3 doubles and 1 treble; Casumo, Grosvenor, LiveScore Bet, 888sport, Virgin Bet → 1 double each; 10 books → none.
Indicative and descriptive only.

## 4. Singles vs doubles vs trebles
- **Maths (same legs, e.g. the live leg class P = 0.60, O = 1.73, EV +3.8%):**
  | | EV | Kelly stake | log-growth |
  |---|---|---|---|
  | single | +3.8% | 5.2% | 0.00099 |
  | double | +7.7% | 3.9% | 0.00149 |
  | treble | +11.8% | 2.8% | 0.00163 |
  | **two singles staked together** | | | **0.00199** (> double) |
  | **three singles together** | | | ≈ 0.0030 (> treble) |

  Higher card EV does not mean better bankroll growth. **Singles on the same positive-EV legs dominate the multi**, unless the multi gets
  better terms (acca bonus or boost), which is not modelled and not verified.
- **Probability error:** ±1.5 pp per leg moves a single's EV from +1.2% to +6.4%, a double's from +2.4% to +13.2%, and a treble's from
  +3.7% to +20.4%. The absolute error band widens with every leg.
- **Streaks (50 bets):** the median longest losing streak is 4 for singles, 7 for doubles and 11 for trebles. P(streak ≥ 8) = 1.3%, 40% and
  87%. With a £20–£30 bankroll, that drawdown profile is severe.
- **Verdict: doubles and trebles are not yet justified.** Joint probabilities look sound for distinct events (A1, A2), but there is no
  executable price evidence (C impossible), the indicative ROI shows no advantage (B), and the maths favours singles.

## 5. Proposed qualification and risk framework (provisional; nothing activated)
1. The prediction board keeps all valid predictions, independent of price (unchanged).
2. Leg eligibility = the current bsv2-3 single gates **plus** EV_i > 0 (every leg positive, as specified by Fraser).
3. Enumerate k ≤ 3 **distinct-event** cards per book per snapshot, deterministically (sorted by event id). Same event, same participant or
   cross-market → `RESEARCH_ONLY`.
4. Card classes:
   - `RESEARCH_ONLY`: odds indicative or dependency unassessable.
   - `WATCH`: all legs positive, but the card's EV lower 1-σ bound ≤ 0.
   - `PAPER_CANDIDATE`: **reserved**, not enabled until the evidence in §7 exists.
   - `REJECT`.
   There is no minimum combined odds by leg count and no forced daily card.
5. Report each multi next to its **singles-equivalent** (the same legs staked as singles, with Kelly growth), so a multi is shown only if
   it beats that alternative.
6. Exposure: one event appears in at most one card per book per day (shared-leg exposure counted). Singles remain the default. No real-money
   staking for multis. Paper stakes are 1 unit, as for singles.

## 6. Daily Bet Card design
Two sections that are never merged: **(A) High-probability predictions** (board: P, band, calibration, source, freshness) and
**(B) Financial cards**. Each card row shows:
- card id, snapshot time, book, legs (sport, event, start, selection, P_i, σ_i, O_i, EV_i, gate codes), k;
- P_joint ± σ, O_joint (INDICATIVE flag), fair odds, break-even P, EV and EV range under ±σ;
- singles-equivalent growth, dependency flags, event exposure;
- an illustrative £1 return and loss;
- class and reason codes;
- after settlement: result and realised P&L.

## 7. Bounded implementation plan (research-only; requires separate approval)
- **New:** `src/prediction_markets_lab/card_engine/{legs.py, enumerate.py, joint.py, compare.py, ledger.py}`,
  `scripts/run_card_research.py`, `research_cards/cards.csv` (append-only; `card_id = sha256(rule|book|sorted leg prediction_ids|snapshot)`).
- **Interfaces (read-only):** the live `exchange_probability_snapshots.csv` and `price_snapshots.csv`, and bsv2-3 `evaluate` for leg
  gating. It never writes `paper_betting_v2/`.
- **Tests:** unit (EV algebra, same-book rule, dependency blocks, idempotent ids, fail-closed on a missing leg price) and integration
  (replay of the 29 Sep scans); the chronological A1 harness is kept as a regression.
- **Wiring:** one extra `continue-on-error` step after bet selection, or offline only at first (preferred). 0 API credits.
- **Evidence before `PAPER_CANDIDATE` can be enabled:**
  1. Fraser verifies, on one or two books, that the multiple price equals the product of leg prices and that no restriction applies.
  2. At least 100 settled research multis with joint calibration inside its CI.
  3. Research multis beat their singles-equivalent on realised growth over the same period.
  4. Singles have met their own live gate first.

## 8. Status
**GO (research-only) for the shadow card logger.** It is non-invasive, uses 0 credits and exists to measure frequency and joint
calibration prospectively. **RESEARCH_MORE** for paper multis. **BLOCKED** for any executable multi backtest (no time-aligned accumulator odds).

## 9. Next approval requested
Approve building the **research-only card logger** (§7), offline-first on a branch with tests, not wired into production workflows. The
separate question of wiring it into the scheduled run comes after a review of the first week of its logs.
