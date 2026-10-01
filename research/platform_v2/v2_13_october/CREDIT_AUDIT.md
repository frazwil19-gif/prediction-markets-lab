# V2-13 Track B — Odds API credit audit and October plans (no purchase; nothing changed in schedules)

**Plan:** free Starter, 500 credits per month.

**Cost rule** (The Odds API v4 docs, as recorded in `research/platform_v2/API_CREDIT_BUDGET.md`):
- `/odds` costs **markets × regions** per call.
- `/scores` costs 2 credits (with `daysFrom`).
- `/sports` and `/events` are free.
- Paid tiers (the-odds-api.com, checked 2026-10-01): 20K credits $30/month · 100K $59 · 5M $119 · 15M $249.

## 1. Complete call inventory

| # | Sport | Workflow / step (UTC cron; observed start) | Call | Market × region | Credits/call | Frequency | Est. credits/month | Output that uses it | Duplicated? | Timing useful? | Consolidation | Consequence of removing/reducing |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Football | `daily_scan.yml` 07:00 (runs ~13:26) → `run_daily_scan.py` | `/odds` for soccer_epl, soccer_efl_champ, soccer_spl | h2h + totals × uk | 2 | 3 calls daily, **unconditional** | **186** (observed 6/day) | Daily Card, Money Card, unified ledger (1X2/DC/O-U), bsv2 football prices, Stage A | No | Partly. It **pays on days with no fixture inside 48h**: 22–30 Sep cost 54 credits for 0 ledger rows (international break) | **Gate on free `/events`**: pay for a league only if ≥1 fixture kicks off within 48h | Gating loses nothing (a card without in-window fixtures is unused). Dropping `totals` (−3/day) stops the O/U engine and Money Card O/U → approval needed |
| 2 | Football | `settlement_and_performance.yml` 21:00 → `run_settlement.py` (paper ledger) | `/scores` per league, daysFrom=3 | — | 2 | Only for leagues with a pending paper bet kicked off in the last 3 days | 30–90 from 9 Oct (0 since 24 Sep; 6 on 24 Sep) | Paper-ledger settlement (Money Card track) | **Yes:** the unified settle already settles from football-data.co.uk at 0 credits; the migration shadow compares both | Yes | **Migrate to football-data (free)** once the migration gate passes (≥100 matched comparisons); keep scores only as fallback for bets unsettled after 4 days | Small risk if football-data is late; the fallback covers it |
| 3 | Tennis | `tennis_prediction_board.yml` 06:30 (runs ~12:54) and 15:30 (runs ~20:16) → `run_tennis_prediction_board.py` | `/odds` per active covered key (max 6) | h2h × uk | 1 per key | 2 scans/day × active keys (Sept: 1; from 29 Sep: 3) | 60–180 (**cap 120**; floor `min_remaining` 150) | Tennis ledger, bsv2, V2-7, Stage A | The two scans overlap heavily in the Asian swing (the late "morning" run sees mostly the same matches as the previous evening) | The evening run is the decision-relevant one for Asian sessions. The morning run (delayed to ~13:00) arrives after most Asian matches started | Event-gate per key: pay only if ≥1 event starts within the next 30h and has not started | Gating loses nothing. Cutting a scan loses fresher prices for European-session matches |
| 4 | Tennis | 22:30 settlement run | none (`/sports` free; settlement from TennisCourtLog) | — | 0 | daily | 0 | — | — | — | — | — |
| 5 | NBA (from 20 Oct) | `tennis_prediction_board.yml` collect-nba (06:30 and 15:30 runs; ≤1 paid call per UTC day) | `/odds` basketball_nba | h2h × uk | 1 | ≤1/day, only if a game is within 36h (free `/events` check) | 12 in Oct, ~30/month in season | Unified ledger NBA, Stage A | No | The only paid call is at the delayed 06:30 run, ~17–21h before tip. The validated estimator is the close (NBA plan §5) | — | — |
| 6 | NBA | 22:30 settle → `/scores` basketball_nba, daysFrom=3 | — | — | 2 | Every 3rd day, only if an unsettled NBA game started | 8 in Oct, ~20/month | NBA settlement | — | — | A free NBA results source would remove this (NBA plan §7) | — |
| 7 | All | `/sports` lists | — | — | 0 | Every run | 0 | — | — | — | — | — |
| 8 | — | V2-7 shadow, bsv2, unified board build, Stage A, V2-8 analyser | none (read files written by 1/3/5) | — | 0 | — | 0 | — | — | — | — | — |
| 9 | — | Manual / research | ad hoc | — | — | — | ~10 | — | — | — | — | — |

**Reconciliation with the recorded counter.** The counter is the global `x-requests-used` in `tennis_predictions/credit_log.csv`. Football calls are not logged separately; they appear as the gaps between tennis calls.

| Period | Total | Tennis (logged) | Other consumers |
|---|---|---|---|
| 23–30 Sep (41 → 115) | **74 credits** | 25 | 49 |

- The "other consumers" figure matches the football scan (6/day) plus one settlement burst (6, on 24 Sep) and 1 manual credit.
- At the September end-state rate (tennis 3 keys × 2 scans), usage is **~12 credits/day ≈ 370/month** before football settlement resumes and before NBA.

## 2. October projection, current configuration

| Consumer | Credits |
|---|---|
| Football scan | 186 (unguarded) |
| Football settlement | 30–90 |
| Tennis | 120 (cap) |
| NBA | ~20 |
| Manual | ~10 |
| **Total** | **≈ 366–426** |

**The binding constraint is the floor, not the 500 total.** Tennis and NBA stop when *global remaining* < 150 (`min_remaining`), i.e. once about 350 credits have been used. At this rate that is **around 25–28 October**, the week NBA starts.

On the tennis cap alone, at 6/day, tennis exhausts 120 around 20 October.

## 3. Plans

Priority order (from the directive): decision-time probability → executable prices → football launch → NBA launch → tennis continuity.

**PLAN A — stay within 500, maximum useful coverage (recommended).**

1. Football scan **event-gated** with the free `/events` call (pay per league only when a fixture is within 48h). October fixture days 9–12, 17–19, 21–22, 24–26, 28–29 and 31 give about 15–18 paying days × 2–3 leagues × 2 ≈ **70–100**. `totals` kept.
2. Football paper settlement **migrated to football-data.co.uk** after the shadow gate passes; scores only as a ≥4-day fallback: **≈ 0–20**.
3. Tennis **event-gated per key** (≥1 event in the next 30h, not started), both scans kept; cap 120 → **150**: **≈ 100–150**.
4. NBA as configured: **≈ 20** (Oct), ~50 (Nov).
5. Floors: tennis and NBA `min_remaining` 150 → **100**. Football is core and unguarded; add a hard guard at remaining < 25.

**October ≈ 200–300 planned, ≥ 200 headroom.** Items 1 and 3 are code changes (small, testable). Items 2 and 5 are production/config decisions. **All four need your approval.**

**PLAN B — conservative, reduced cost.**
- Plan A's gating;
- plus football **h2h only** (drop totals; the O/U engine and Money Card O/U stop) → 35–50;
- tennis **one scan/day** (the 15:30 run; Asian swing) → 50–90;
- NBA 1/day → 20–50.

About **120–200 per month**. Cost: O/U coverage lost; fresher European tennis prices lost.

**PLAN C — what a paid tier would genuinely buy** (no purchase). The 20K plan ($30/month) is ~40× the credits. It would fund:
- (a) **a near-close second snapshot** for football (e.g. kickoff −2h) and NBA (tip −1h). This is the only way to test live vs validated *closing* estimators and to measure CLV;
- (b) real **Double Chance quotes** (per-event, 1 credit/event): DC Stage B research;
- (c) more leagues (each +2/day);
- (d) **historical snapshots** (10× cost) for NHL odds benchmarks and back-tests;
- (e) hourly tennis scans closer to start (fewer missed pre-match windows, given GitHub delays).

**Recommendation.** Adopt **Plan A** now. Revisit Plan C only when a pre-registered study needs a near-close snapshot. The first candidate is the estimator-consistency check in the football and NBA pre-registrations.

## 4. Redundancy, timing and reuse findings

- **Redundant (biggest):** unconditional daily football odds during fixture-free stretches (54 credits for nothing, 22–30 Sep).
- **Duplicate:** paper settlement via Odds API `/scores` while the unified settle already settles from free football-data.
- **Timing:** the 06:30 tennis run actually executes around 12:54 UTC, after the Asian session. Its NBA call is the day's only one, ~17–21h before tip, far from the validated close. GitHub delay (4–6h observed) is the root cause (scheduling study, V2-9).
- **Reuse:** V2-7, bsv2, Stage A and V2-8 already reuse the same snapshot (0 credits). The Money Card and the unified football rows reuse the same card (0 extra).
- **Unnecessary markets/regions:** none beyond `totals` (Plan B). The single `uk` region is required for executable UK prices.
