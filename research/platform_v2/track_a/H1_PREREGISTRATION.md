# H1 — Power de-vig shadow for football 1X2 — PRE-REGISTRATION

Date: 2026-10-02. Approved by Fraser: "I APPROVE the research-only H1 prospective shadow". Origin: Edge Discovery C1
(`research/platform_v2/edge_discovery_c1/HYPOTHESIS_REGISTRY.md` H1). Written before any prospective H1 data exists.

## Hypothesis
For football 1X2, the consensus probability built from **power de-vig** gives better probability quality than the
frozen production consensus (proportional de-vig). Two consequences are expected:

* log loss and Brier are lower;
* the favourite under-confidence at high probability is smaller.

H1 is about probability quality only. It is not a betting rule.

## What is computed (per live football 1X2 market, every daily scan)
The same accepted bookmaker set the production consensus uses (complete H/D/A quotes) feeds both estimates.

* **p_frozen.** The production value. It is the median, across books, of each book's proportional fair probability.
  It is copied, never recomputed differently.
* **p_power.** The median, across books, of each book's power-de-vig fair probability. The power method solves for a
  single exponent k per book such that Σ(1/oᵢ)^k = 1, giving pᵢ = (1/oᵢ)^k.
* **Normalised versions** of both triplets, which are what Stage A displays.
* **Context columns:** n_books, the per-book odds (JSON), scan timestamp, competition, event and kickoff.

Output: `research_shadow/h1_devig/<date>[_label].csv`, append-only. It is never written to the ledger, Stage A, bsv2,
grades, stakes or money logic. A failure only warns; the scan continues.

## Evaluation (confirmatory, at the review trigger)
* **Population:** every shadow row whose match has a verified result (football-data FTR, matched with the existing
  settlement matcher).
* **Snapshot rule:** the first snapshot per match within 48h of kickoff, mirroring the production snapshot rule.
* **Primary metric:** paired difference in 3-way log loss (power − frozen, normalised triplets). A match-cluster
  bootstrap gives the 95% CI. **H1 is supported if the CI upper bound is < 0.**
* **Secondary metrics:** Brier; calibration slope and intercept (favourite side); probability bands; high-P
  (≥ 0.70) calibration bias; per-league and per-month stability; N; ESS (= matches).
* **Review trigger (evidence, not calendar):** whichever comes first:
  * ≥ 300 settled matches. At the ~0.0006 log-loss difference seen historically, a paired-SD power analysis says this
    is roughly the first informative point; that will be reported;
  * the Evidence & Promotion Protocol INTERIM football trigger.
* **Holdout discipline:** none of these rows is seen before the trigger, apart from row-count and coverage
  monitoring.
* **Promotion:** requires separate approval from Fraser. A negative result is retained.
