# V2-15 — NBA prospective pre-registration (fixed 2026-10-01, before the 20 Oct 2026 activation)

**Engine:** `nba_moneyline.market` v1, **frozen**. The method is unchanged: mean decimal odds per side over ≥3 paired non-exchange UK books, then 2-way proportional de-vig. Ledger_version 1, activation 2026-10-20, `money_eligible: false`.

**Live estimator:** **`nba_moneyline.market@1-live`**.
- **Snapshot:** the first scan within 36h of tip. The only paid call is at the 06:30 UTC run, so in practice the snapshot is ~17–21h before tip.
- **Books:** only books quoted within the last 6h (`STALE_AFTER`, the same constant football uses).
- **Teams:** the 30 franchises only.
- **Calibration:** the validated estimator is the closing average. The registry records `calibration_transfer: NOT_ASSUMED`. The prospective ledger is the test of the early-snapshot estimator.

## Data-quality / provenance rules

| Rule | Detail |
|---|---|
| Recorded price | `odds_api:<book key>` of the best book on the predicted side, from the same response (same snapshot). Stage B can price it. |
| One row per game | The first snapshot is canonical. A later scan with a flipped favourite is skipped as `ALREADY_PREDICTED_FIRST_SNAPSHOT_CANONICAL`. |
| Exhibitions | Exhibition / non-franchise events are skipped as `NOT_REGULAR_COMPETITION`. Playoffs and play-in are kept, as in the holdout. |
| Settlement | Odds API `/scores` every 2nd day (`daysFrom=3`, one overlap day). Completed games only; the final score includes OT. Unsettled more than 3 days after tip → REVIEW_REQUIRED, never guessed. |

## Stage A uncertainty

**Method:** pooled Wilson 95% half-width / 1.96, computed from the sealed-holdout market bands (`NBA_SIGMA_EVIDENCE.json`; one row per game, so effective N = games).

| Band | N | Mean predicted → actual | σ |
|---|---|---|---|
| 50–65% | 1,086 | 57.8 → 57.0 | 1.50pp |
| 65–80% | 993 | 72.0 → 71.4 | 1.43pp |
| ≥80% | 550 | 85.5 → 87.5 | 1.41pp |

The σ is band-specific, not event-specific. It **excludes** early-snapshot bias, and is labelled accordingly.

## Promotion

Promotion follows `research/platform_v2/EVIDENCE_PROMOTION_PROTOCOL.md` (pending approval), never elapsed time.

## Provenance erratum

`research/platform_v2/nba/NBA_RETURN_CHECKPOINT.md` cites commits `12561fc` and `abc2b87`. Neither exists in this repository. The actual history is `a047ab1` (study) → `8083a43` (holdout spec, 2026-09-24 15:25:07Z) → `1cd2259` (holdout results; `opened_at` 15:25:09.9Z). The order of events is intact.
