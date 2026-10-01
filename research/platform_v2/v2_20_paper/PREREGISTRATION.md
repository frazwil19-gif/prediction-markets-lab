# V2-20 — Daily Paper Bet Card, grades, hypothetical stakes, paper dashboard (PRE-REGISTRATION)

Status: PRE-REGISTERED (committed before the module produced any card). Rule version: `pcard-1`.
Directive: "NEXT PHASE — RAPID MARKET EXPANSION → PAPER BETTING", sections 9–14.

## 0. What this layer is and is not

* It is a **presentation + accounting layer on top of bsv2-4**. It does not decide what is a paper bet. bsv2-4
  (`bet_selection_v2/evaluate.py`) remains the only decision rule: PAPER_BET / WATCH / MULTI_RESEARCH_ELIGIBLE / REJECT.
  No gate, threshold or price rule of bsv2-4 is changed or duplicated.
* Every price shown is the **real observed executable price** bsv2 used (source, odds, observed_at). No synthetic or
  derived price is ever shown as executable (DC / DNB stay DATA_BLOCKED for Stage B).
* `paper_betting_v2/selections.csv` and `settlements.csv` are **not modified**. The grade/stake enrichment is written to
  a separate append-only ledger `paper_betting_v2/card_enrichment.csv`, keyed by `selection_id`, written once
  (first sight) and never rewritten.
* No real money. Every card row carries `money_eligible = False`. Money needs a MONEY_ELIGIBILITY_REVIEW
  (`MONEY_ELIGIBILITY_REVIEW_TEMPLATE.md`) and Fraser's explicit approval; nothing in code can flip it.

## 1. Grade definitions (derived, not tuned)

Inputs per candidate: bsv2 decision; P = the probability bsv2 decided on; σ = Stage A sigma for that prediction
(sport-specific, already pre-registered in stage-a-2: tennis exchange-width + calibration SE, football band SE,
NBA Wilson band SE); odds o; commission c; engine evidence state (EVIDENCE_PROMOTION_PROTOCOL.md).

EV at a probability q: `EV(q) = q·(o−1)·(1−c) − (1−q)`.

| Grade | Rule |
|---|---|
| **A+** | bsv2 PAPER_BET **and** EV(P − z₉₅·σ) > 0 **and** engine evidence state ≥ PROSPECTIVE_CALIBRATION_SUPPORTED |
| **A** | bsv2 PAPER_BET **and** EV(P − z₈₄·σ) > 0 (value survives a one-standard-error probability error) |
| **B** | bsv2 PAPER_BET otherwise (value does not survive one σ, or σ unknown) |
| **C** | bsv2 WATCH or MULTI_RESEARCH_ELIGIBLE (information only; no paper stake) |
| **REJECT** | everything else |

z₈₄ = 1.0 (one standard error, one-sided 84%) and z₉₅ = 1.645 (one-sided 95%) are conventional interval multipliers,
fixed here before any card exists; they are not fitted to outcomes and will not be tuned on paper results.
No engine is currently ≥ PROSPECTIVE_CALIBRATION_SUPPORTED, so **A+ is structurally empty today** — this is intended.
Engine evidence states live in `config/paper_card.yaml` and change only through a protocol review commit.

Grades never alter the bsv2 decision, and the Stage A probability board is unaffected (STRONG PREDICTION ≠ VALID BET).

## 2. Ranking on the card

Grade (A+ > A > B > C > REJECT), then P descending, then EV(P) descending, then event start, then prediction_id.
(Project hierarchy: probability → confidence → context → value → risk.)

## 3. Hypothetical stakes (paper only)

Bankrolls £20 / £30 / £50 / £100 and policies flat_1pct, flat_2pct, kelly_1_8, min_stake — **exactly** the bsv2
`bankroll_simulation` block (no new numbers). Per bankroll and policy, for grades A+/A/B in ranked order:

1. stake = policy stake at the nominal bankroll (1/8 Kelly uses P, odds, commission);
2. capped at `max_stake_fraction` (5%);
3. below the practical minimum (exchange £1 / bookmaker £0.10): raised to the minimum only if it fits the cap,
   otherwise `SKIP_BELOW_MIN`;
4. cumulative day exposure capped at `max_daily_exposure_fraction` (10%); excess → `SKIP_DAILY_CAP`.

Singles only. No martingale, chasing or recovery staking (the policy loader refuses unknown kinds).
Realised paper bankroll paths remain the bsv2 `simulate_all` replay (event-start order, loss lock, drawdown stop).

## 4. Unified paper-bet record (directive §9)

bsv2 selection fields (selection_id, prediction_id, sport, engine/model version, event, market, selection, P, fair odds,
odds, source, commission, price time, decision time, net EV, decision, reasons) + settlement fields (status, result,
P&L) + enrichment fields (`card_rule_version, graded_at, competition, sigma, sigma_method, calibration_status,
p_first_snapshot, p_current_scan, ev_at_p, ev_minus_1sigma, ev_minus_1645sigma, evidence_state, grade, grade_reason,
stake_<bankroll>_<policy>`). Selections recorded before pcard-1 are graded `UNGRADED_PRE_PCARD` (σ at their decision
time was not recorded; never back-filled).

## 5. Dashboard (directive §12)

`reports/paper_dashboard.{json,md}`: financial (bets, settled, won, expected vs realised wins, expected vs realised P&L
in units, ROI, max drawdown, longest losing streak, bankroll simulations) **and, separately**, prediction quality on
settled paper bets (mean P vs win rate, Brier, log loss). Breakdowns: sport, competition, market, engine (model),
rule version, P band, odds band, grade, source type. Small samples are labelled with n; no projections.

## 6. Out of scope / unchanged

Paper multis (disabled), NHL, DC holdout, real money, Stage B thresholds, frozen engines, sealed holdouts.

## 7. Amendment A1 (2026-10-01, before merge / before any production card) — approval directive s.6, s.7, s.11, s.12

* **Frozen ≠ optimal.** bsv2-4 gates (odds ≥ 1.33, net EV ≥ 2%, price/spread/age rules) and the pcard-1 grade
  multipliers (1σ, 1.645σ) are frozen prospective policy parameters for this cohort. Nothing here claims they are
  empirically optimal; they will not be changed after a small number of results.
* **Decision shadow (analytical only).** `paper_betting_v2/decision_shadow.csv`, append-only: every decided candidate
  (PAPER_BET, WATCH, MULTI_RESEARCH_ELIGIBLE, REJECT) with P, σ, fair odds, actual price + source + time, Stage A price
  status, central EV, EV at P−1σ / P−1.645σ, bsv2 decision + reasons, grade, `analytical_only = True`. A new row only
  when price or decision changes. It is never a paper bet and never staked; outcomes are joined at analysis time from
  `predictions/unified_settlements.csv` (nothing written back). Purpose: later evaluation of the frozen gates
  (odds < / ≥ 1.33, EV bands, P bands, σ bands, sports/leagues). No threshold optimisation now.
* **Card fields.** Paper-bet rows also show competition, market, price time, engine id + version; the card header shows
  when the candidates were evaluated; zero-bet days print "NO PAPER BETS TODAY".
* **Dashboard.** Adds probability-band and odds-band breakdowns and mean decision-time EV per group. CLV is reported
  as NOT_AVAILABLE (no closing executable price is recorded for paper selections; it is not estimated).
