# Probability Engine Review Standard (V2-5; sample-triggered)

**Trigger:** an engine reaches INTERMEDIATE (≥ 300 settled events, including ≥ 100 settled at ≥ 80%). Dates never trigger a review. An
earlier review happens only on the pre-declared alarm (≥ 100 settled ≥80% rows with realised < predicted − 10 pp), which leads to
REVIEW_REQUIRED, never to retuning.

**Evidence assessed:**
1. Historical validation (sealed holdout; for DC, the 2026/27 holdout once opened).
2. Prospective calibration: slope with bootstrap CI including 1; every prospective band with n ≥ 200 inside the realised
   99.5% Wilson interval; ≥80% mean predicted vs realised.
3. Live-source compatibility: were the prospective inputs the same kind of price the engine was validated on?
4. Operational reliability: share of scheduled runs producing valid snapshots, and the missed/late-snapshot rate.
5. High-probability coverage: ≥80% share of events.
6. Timing: calibration by minutes to event (once a bucket has n ≥ 100).
7. Uncertainty and current-context limits (all current engines are market-only, with no injury/lineup context).

**Outcomes:** (a) eligible to enter the Bet-Selection layer (paper first), (b) continue collecting, (c) REVIEW_REQUIRED /
BLOCKED. Profit is not a review criterion. Thresholds are the ones above and are not changed after results are seen.
