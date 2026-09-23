# Next Sport/Market Audit — "where can we produce the strongest validated probabilities?"

Scoring is evidence-based. It is **not** based on historical profit. Live checks used the free `/v4/sports` endpoint
(0 credits) on 2026-09-23 (`ODDS_API_ACTIVE_SPORTS_2026-09-23.json`). Items marked *unverified* were not checked this session.

| candidate | predictability / high-P potential | historical data | sample | live compatibility | frequency | cost | verdict |
|---|---|---|---|---|---|---|---|
| **Margin-removal calibration (all market engines)** | directly fixes the high-P region | in repo (football 6 books × 5 seasons; tennis Betfair) | 17k+ football candidates, 7k+ tennis | same live feeds | all | £0 | **FIRST (cross-cutting)** |
| **Tennis Match Winner (market engine)** | highest measured: 20.7% of matches ≥80%, calibrated | in repo: Betfair-archive linkage 2021–2025 (12,956 of 14,564 TML matches linked); 2026 BASIC files on Fraser's Mac. Workstream B's discovery used 2021–23 and its 2025 OOS was never opened, so 2024–25 is a likely genuine holdout (to confirm in the cycle's own audit) | large | **gap:** Odds API lists tennis per tournament (1 active today). Candidate: Betfair *Delayed* app key (free, read-only; delay acceptable pre-match, *terms to verify*) | daily, year-round | £0 (delayed key) | **NEXT MARKET** |
| Football breadth (more leagues, same engines) | same as current; more favourites per day | football-data.co.uk carries ~20 more leagues in the same format (*to verify per league*) | large | 44 soccer keys active on the Odds API | high | £0 data; +2 credits/league/scan | strong, low-risk **scale step** once de-vig is settled |
| Football Asian Handicap | moderate; lines vary per match | thin (2–3 books) | ~5.8k | spreads available | high | £0 | later |
| Basketball (NBA moneyline) | plausibly high (heavy favourites common); unmeasured | none in repo; free historical odds archives exist (*unverified*) | ~1,230 games/season | `basketball_nba` active | Oct–Jun | £0–low | audit later |
| Baseball (MLB) | low (few games priced ≥75%) | none in repo | 2,430/season | `baseball_mlb` active | Mar–Oct | £0–low | deprioritise for high-P |
| Ice Hockey (NHL) | low-moderate | none in repo | 1,312/season | `icehockey_nhl` active | Oct–Jun | £0–low | deprioritise |
| Cricket | — | — | — | 2 keys | — | — | stays PAUSED (§14) |

## Recommendation
1. **Cycle V2-1: market-probability calibration study (margin-removal method).** Pre-registered comparison of
   proportional vs power vs Shin vs odds-ratio de-vigging. Chronological: football 2020/21–2023/24 development,
   2024/25 holdout; tennis 2021–23 development, 2024–25 holdout. Primary metrics: log loss, calibration slope, and
   high-probability band reliability. No new data and no production change until promoted.
2. **Cycle V2-2: Tennis Match Winner market engine.** Formal validation on the 2024–25 Betfair archive (holdout status to be confirmed first), plus a live-source
   audit (Betfair Delayed key terms and coverage vs Odds API tournament coverage). Tennis is the most promising source
   of strong, calibrated predictions and multi legs, **but it has no dependable live feed today**, and that is the gating item.
3. Then football league breadth, then AH. US sports only after a proper data audit.
**No data purchase is needed for any of these.**
