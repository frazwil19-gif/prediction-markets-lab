# Model Promotion & Prospective-Validation Standard

## Research → PAPER (engine may feed the Prediction Board and paper ledger)
All required, each with a committed artefact:
1. Data audit (coverage, provenance, hashes).
2. Leakage audit plus tests, with a declared prediction time.
3. Pre-registration (models, selection rule, metrics) committed **before** results.
4. Chronological development with validation.
5. Frozen spec (hash-committed) and a sealed holdout opened once.
6. Calibration: slope CI includes 1 or |slope − 1| ≤ 0.15; ECE and band table reported with CIs.
7. Uncertainty method defined (`PROBABILITY_ENGINE_SPEC.md`).
8. Stability across seasons/leagues (no sign-flipping core inputs).
9. Live implementation feasible (source, cost, latency) and an adapter tested with recorded fixtures.
10. Engine evidence record added to the registry and the Atlas.

## PAPER → MONEY-ELIGIBLE (engine's candidates may appear on the Daily Money Card)
Pre-registered prospective criteria, evaluated only after the sample is reached (no peeking-and-stopping):
- ≥ 300 settled paper predictions **in the probability bands it would bet** (or 8 weeks, whichever is later).
- Prospective band calibration within the historical band CI; interval coverage near nominal.
- Paper bets: CLV ≥ 0 on average against the closing reference (primary); ROI reported with CI (secondary, never sufficient alone).
- No unresolved data/settlement defects.
- Fraser's explicit approval, recorded in the master directive.

## Multis
The same two steps, applied to the **joint** probability: historical joint-calibration replay, then ≥ 100 settled paper
multis generated mechanically, then approval. Same-game multis also need the joint scoreline model validated.

## Demotion (monitoring)
An engine is demoted to PAPER if a rolling prospective window (config) shows calibration outside its historical CI
or CLV persistently negative. Demotion is automatic and logged; re-promotion follows the full PAPER → MONEY rule.
Never retune after individual results.
