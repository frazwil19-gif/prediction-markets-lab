# The Odds API Credit Budget (free tier: 500 credits/month) — 2026-09-24

**Observed:** `x-requests-used` = 42, `remaining` = 458 (24 Sep, read from the free `/sports` endpoint). About 40
credits covered 19–21 Sep of football operation plus smoke tests (22–24 Sep spent almost nothing because the
workflows were failing). Implied steady football cost is **about 12 credits/day**.

## Cost model (documented formula: markets × regions per call; `/sports` and `/events` are free)
| consumer | calls | credits/day | credits/month (30 d) |
|---|---|---|---|
| Football daily scan | 3 leagues × (h2h + totals) × 1 region | 6 | **180** |
| Football settlement | scores `daysFrom=3` (2 credits) × leagues with pending bets (≤3) | ≤6 | **≤180** |
| Tennis board | 2 scans/day × active covered ATP/WTA keys (0–4, typical 1–2) × 1 | 0–8 (typ. 2–4) | **60–240** |
| NBA board (proposed, in season) | 1 key × h2h × 1 region, 1–2 scans/day | 1–2 | **30–60** |
| Manual / research | ad hoc | — | ~10 |
| **Total without changes** | | | **≈ 460–670, over the limit in busy months** |

The earlier estimate of "≈480" undercounted football settlement. **Without changes, the plan exceeds the free tier.**

## Recommended monthly budget (with a 15% reserve)
| consumer | budget | how |
|---|---|---|
| Football scan | 180 | unchanged |
| Football settlement | **≈0–30** | **switch settlement to free results** (football-data.co.uk current-season CSVs, which GitHub runners can reach; the acquisition workflows already use that source), keeping the Odds API scores call only as a fallback for bets still unsettled after 4 days. *Production change → needs Fraser's approval.* |
| Tennis | **≤ 120** | cap at 4 paid calls/day (the script's `--max-keys` plus a daily cap); prefer 1 scan/day when ≤ 1 key is active |
| NBA (from late Oct) | ≤ 60 | 1 key; 1 scan/day near evening UK; shares the guard |
| Manual / research | 30 | |
| **Reserve** | **≥ 75 (15%)** | never planned for |
| **Planned total** | **≤ 425** | |

## Guards (existing and proposed)
- Existing: tennis stops below 150 remaining.
- Proposed: a shared ledger (`status/credit_ledger.csv`), with every consumer logging `x-requests-*`. Research/paper
  consumers (tennis, NBA) stop at **remaining < 150**, and football is protected until remaining < 25.
- Nothing is changed in schedules or production this phase. The settlement switch is the single decision that makes
  NBA activation affordable.
