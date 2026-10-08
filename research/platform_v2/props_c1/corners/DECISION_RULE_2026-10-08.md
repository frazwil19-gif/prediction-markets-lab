# Corners: go / no-go decision rule (written 2026-10-08, BEFORE the 10 Oct probe 2 and Betfair windows)

Inputs:
- Gate 0 outcome from `price_probe_2/GATE0_PREREGISTRATION.md` (A robust / A thin / B / C; one EPL event,
  ≤ 24 h);
- the 10 Oct Betfair windows A/B/C, if they include corners markets.

Model status (measured):
- Model A beats league-NB by Δlogloss −0.0038 [−0.0056, −0.0020] on the sealed holdout. This is small.
- Calibration slope 0.89–0.90.

| Probe outcome | Decision |
|---|---|
| **C** (no UK book) | **STOP** corners market work. Model A stays recorded; its free prospective check continues. No third probe. |
| **B** (one-sided / unknown commission only) | **STOP** market work (PRICE_DATA_REQUIRED). Same as C. |
| **A thin** (1–2 complete two-sided books) | **PROBE MORE, no build:** propose one bounded availability sample (≤ 10 EPL/E1 events over 2 weekends, ≈ 20 credits, surplus-only) for Fraser's approval. |
| **A robust** (≥ 3 complete two-sided books at a common line) | **Availability sample** as for A thin. GO to the Model B/C pre-registration only if ≥ 3 two-sided UK books on ≥ 50% of sampled events. |

**Betfair corners:**
- If any window shows corners markets, record the median spread and matched volume.
- If the median spread is above the bsv2 3% gate, Betfair is not an execution venue for corners.
- Earlier evidence put Betfair corners spreads at 15–23%.

**Economic ceiling** (PROJECTED; written before the evidence):
- C ≈ 280 tier-1 matches/month × q (unknown; plausibly 0.5–3% given the small model gain) × u ≈ 0.9 × e (unknown);
- that gives LOW 0 / BASE 2 / HIGH 8 qualified a month.
- Kill also applies if the availability sample implies HIGH < 3 a month.

**Player SOT:** the same windows' player-SOT evidence (spread, volume, listed players) is saved unchanged for the
post-holdout VALIDATED step 5 (liquidity). It is not used before the holdout verdict.
