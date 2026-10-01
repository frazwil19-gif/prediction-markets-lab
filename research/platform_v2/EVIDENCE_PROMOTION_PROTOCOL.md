# Evidence & Promotion Protocol (per engine) — APPROVED 2026-10-01 (V2-13 revision; replaces superseded A1)

**Status:** **APPROVED 2026-10-01** (your expansion directive §13: "use the approved evidence-promotion framework"). The proposed text is unchanged.
- The pre-registered sample-triggered rules in `unified_board/PROSPECTIVE_PROTOCOL.md` §5–6 remain in force alongside it: maturity (COLLECTING / EARLY / INTERMEDIATE / MATURE, counted in events) and the 10pp alarm;
- this document adds to them and replaces nothing;
- `money_eligible` changes **only** by your explicit approval, never automatically.

**Principles:**
- Elapsed time is reported but is never evidence.
- No trigger is tuned to observed outcomes: every number below is fixed now from pre-registered quantities, before football or NBA prospective outcomes exist.

## 0. Units and effective sample size

| Term | Definition |
|---|---|
| **Unit** | One independent **event** (match or game). 1X2 (3 rows) and DC (3 rows) collapse to the event; tennis and NBA have 1 row per event. |
| **ESS** | For cross-event dependence (same matchday × competition, same tournament day): ESS = n × Var_iid / Var_cluster, where Var_cluster is the cluster-bootstrap variance of the realised rate (1,000 resamples, clusters = date × competition). ESS is reported beside the raw N; triggers use ESS. |
| **Precision target** | For a set with mean *predicted* probability p̄ (from predictions, never outcomes): ESS_req(h) = p̄(1 − p̄)(1.96/h)², the size at which the 95% CI half-width of calibration-in-the-large (realised − predicted) reaches h. |

## 1. Three evidence layers

### A. Probability quality (all valid predictions of the engine)
- Events N and ESS;
- Brier and log loss, compared with the engine's historical reference and a naive benchmark (base rate, or market consensus where the engine is not itself the market);
- calibration intercept and slope, with cluster-bootstrap CI;
- band table with Wilson 99.5% intervals (as the historical gates);
- **temporal stability:** first vs second half of the prospective sample, plus a rolling series;
- **subgroup stability:** league or tournament, home/away, tour, minutes-to-event bucket;
- **data-quality failure rate:**
  - scheduled scans without a valid snapshot;
  - rows lost to staleness or quality gates;
  - settlement UNRESOLVED or AMBIGUOUS;
  - missed pre-match windows;
- **estimator consistency:** live P vs the validated estimator on the same events, where obtainable (e.g. closing odds from football-data.co.uk or a near-close snapshot).

### B. Decision-region quality (defined empirically; **no probability ceiling**)

| Set | Definition |
|---|---|
| **D (assessable region)** | Predictions that, at decision time under the frozen Stage B rules, had a clean executable same-snapshot quote. That means all quality gates passed, offered odds ≥ the payout floor, inside the horizon, and engine status allowed. **D does not condition on EV.** It is fixed by price availability and rules, so calibration measured on D is not biased by the model's own errors. |
| **D⁺** | D ∩ {net EV > 0} |
| **D\*** | D ∩ {passes the paper-bet EV gate}, i.e. the action set |

For D, D⁺ and D\*, report:
- N, ESS;
- the joint distribution of P and offered odds (the empirical shape of the region, e.g. P 0.82 at odds 1.35 sits inside D whenever those rules are met);
- calibration-in-the-large with CI;
- band calibration;
- stability.

**Selection effect.** D⁺ and D\* are selected on model P exceeding the price, which over-represents the model's upward errors. A realised − predicted shortfall that is larger in D⁺/D\* than in D is the key diagnostic of overstated edge, and is reported explicitly.

### C. Financial / paper evidence (when paper bets exist)

By engine, market, sport and grade:
- paper-bet N and ESS;
- **expected vs realised wins:** Σp vs wins, with a Poisson-binomial CI;
- **expected vs realised return:** Σ(p × odds × (1 − c) − 1) vs realised, with a bootstrap CI;
- ROI / yield with CI;
- average odds;
- EV distribution;
- CLV where a legitimate closing price exists;
- maximum drawdown;
- risk concentration (per day, event, sport and correlated group);
- calibration of the probabilities behind the bets.

**Realised profit alone is never a promotion criterion.** A calibrated positive-EV process can lose over finite samples. The test is consistency of realised with expected, together with calibration.

## 2. Evidence states (per engine × market)

```
HISTORICAL_VALIDATED ──► PROSPECTIVE_SHADOW ──► PROSPECTIVE_CALIBRATION_SUPPORTED ──► PAPER_FINANCIAL_VALIDATION
                                                                                         └─► MONEY_ELIGIBLE_CANDIDATE ─(explicit approval only)─► money_eligible
any state ──(pre-registered alarm or review finding)──► REVIEW_REQUIRED (never auto-retuned)
```

| State | Meaning |
|---|---|
| HISTORICAL_VALIDATED | Passed its sealed or exposed historical gate. Current registry `status`. |
| PROSPECTIVE_SHADOW | Collecting Stage A predictions; settlement running. Current `prospective_status: COLLECTING`. |
| PROSPECTIVE_CALIBRATION_SUPPORTED | A formal Layer A + B review found prospective calibration consistent with prediction, with adequate precision and stability and an acceptable data-quality failure rate. |
| PAPER_FINANCIAL_VALIDATION | Stage B paper bets accruing under the current rule version; Layer C monitored. |
| MONEY_ELIGIBLE_CANDIDATE | Layers A, B and C reviewed. The review recommends money eligibility, **but nothing changes until you approve it.** |

Every transition is made only by a recorded review (engine, data snapshot hash, metrics, decision, approver). Results seen between reviews are monitoring only, except the pre-registered alarm.

## 3. Quantitative review triggers (schedule a review; not pass thresholds)

The triggers derive from the already pre-registered **10pp alarm shortfall** (PROSPECTIVE_PROTOCOL §6), not from outcomes:
- **INTERIM review** when the precision half-width h ≤ **5pp** (half the alarm scale).
- **FULL review** when h ≤ **2.5pp** (a quarter of the alarm scale).

| Layer | Fires when |
|---|---|
| A | ESS_all ≥ ESS_req(h) for the engine's overall p̄ |
| B | ESS_D ≥ ESS_req(h) for p̄_D; and D spans ≥ 2 independent halves (stability split possible) |
| C (paper) | Paper-bet ESS ≥ ESS_req(5pp) for the bets' p̄ (interim); ROI CI always reported, never a gate |

Reference sizes (computed from p̄ alone):

| p̄ | ESS_req(5pp) | ESS_req(2.5pp) |
|---|---|---|
| 0.60 | 369 | 1,475 |
| 0.70 | 323 | 1,291 |
| 0.80 | 246 | 983 |
| 0.90 | 138 | 553 |

**Further rules:**
- The existing INTERMEDIATE and MATURE maturity checkpoints (300 / 100 at ≥80%; 1,000 / 300 at ≥80%) remain **checkpoints, not universal pass rules**.
- A review must also report coverage of the engine's own decision region. An engine whose D is tiny cannot be promoted on Layer A alone.
- **Never sufficient on its own:** win rate, elapsed weeks, or realised profit.

## 4. Expected trigger timing (illustrative, from prediction volumes only)

- **NBA:** about 50 games/week, all in D if priced. The Layer A interim review is about 5–7 weeks after 20 Oct.
- **Football 1X2:** about 29 events/week. Layer A interim at about 11–13 weeks. Layer B depends on D size, unknown until Stage B prices accrue.
- **Football DC:** Layer A is **masked** for Aug–Dec 2026 events until the sealed holdout opens (DC_HOLDOUT_NO_PEEK.md). DC Stage B is DATA_BLOCKED, so DC has no D.
- **Tennis:** volume varies (0–60/week). It is computed from the prospective ledger at each report.

These are projections of *when evidence becomes informative*. They do not predict the outcome.

## 5. Implementation (after approval)

A read-only `evidence_report` module, `reports/engine_evidence.{json,md}`, generated in the existing settlement workflow, with 0 credits:
- computes layers A, B and C;
- computes ESS and the triggers;
- lists the current state per engine from a new registry field `evidence_state`.

The review records live in `research/platform_v2/reviews/`.
