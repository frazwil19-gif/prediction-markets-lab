# FINAL FOOTBALL COVERAGE — design, credit model, state of every target league (2026-10-01)

Directive: "FINAL FOOTBALL COVERAGE TASK — DO NOT REVERT CURRENT MERGES". Master `5652dbe` kept as is.
Uses the V2-18 evidence; no model was re-estimated. Credit model: `scripts/football_coverage_credit_model.py` →
`CREDIT_MODEL.json`, `paying_days_by_month.csv` (data pin as V2-18: xgabora@25882a58, sha256 ef224cf2…).

## 0. Principle

Observation ≠ paper eligibility ≠ real money.

| Layer | Controlled by | What it allows |
|---|---|---|
| Observation | `config/football_coverage.yaml` `observe` + `tier` | Stage A / unified ledger / decision shadow |
| Paper eligibility | `config/football_coverage.yaml` `paper_eligible` | bsv2-4 may record a PAPER_BET (rules frozen) |
| Real money | `config/competitions.yaml` `money_card_competitions` | **Unchanged** (E0/E1/SC0 legacy card only) |

A league that is observed but not paper-eligible gets engine_status `PROSPECTIVE_SHADOW_LEAGUE`. That status is
outside every bsv2 engine-status list, so bsv2 REJECTs it with ENGINE_STATUS_INELIGIBLE. These leagues get no single
or money eligibility. Stage A shows them with `LEAGUE_SHADOW_NOT_TRANSFERRED` calibration status, and the decision
shadow keeps their full P, σ, price and EV record. The probability itself is the same frozen market-consensus estimator.

## 1. Correction to V2-18 (negative finding, recorded)

V2-18 counted a paying day for a league only when it had a fixture on day t+1 or t+2. The 07:00 UTC scan's 48h gate
also pays for that same day's fixtures. The paying days were therefore **under-counted by about 25%**: in-season
paying days are 16–24 per month, not about 15. V2-18 put the merged 5-league configuration at about 398/month in the
worst case. Corrected, it is **343 expected and 462 in the high month**: the reserve shrinks to 38 in a high month.
V2-18's EXPAND NOW choice (N1/D1) is unaffected; its credit margin was smaller than reported.

## 2. Credit architecture

* **HARD LIMIT:** 500 credits per month (free plan; no purchase).
* **SAFETY RESERVE:** 75, unchanged (`global_reserve_remaining`).
* **OPERATING BUDGET:** 425 = 500 − 75. This is now an operating budget managed against *measured* usage, not a
  pass/fail test on planned worst cases.
* **Planned allocations (core):**
  * football Tier 1: expected about 162/month, high about 215;
  * tennis: observed 3.1/day, so about 95 expected, cap 150;
  * NBA: 60;
  * legacy settlement: 10–20.
* **Shadow tiers:** no planned allocation. They run only on measured surplus. A Tier 2 or 3 league pays only while
  remaining ≥ base + days_left × (protected daily need of every higher-priority consumer).
  * base = max(reserve 75, optional-consumer floor 100) = 100.
  * Tier 2 protects football Tier 1, tennis, NBA and settlement.
  * Tier 3 also protects Tier 2.
  * Tier 1 is stopped only by the existing hard floor (25).
  * Needs and their provenance are in `config/api_budget.json` `football_shadow_tiers`.
* **Paid markets:** h2h only outside E0/E1/SC0. O/U 2.5 stays rejected; totals are kept only where the legacy V1 card
  uses them. This also halves N1/D1 cost (no N1/D1 rows existed yet).
* **Legacy V1 paper ledger** (settled through paid /scores calls) keeps its E0/E1/SC0 scope. New leagues settle free
  via football-data, so they add no /scores credits.
* **Monitoring:** `scripts/credit_report.py` now prints a naive month-end run-rate projection. Shadow calls are logged
  as consumer `football_shadow_scan`.

### Scenarios
In-season months, 2023/24–2025/26. "High" is the busiest simultaneous calendar month. Non-football costs are added
as tennis 95/150, NBA 60/60 and settlement 10/20.

| Scenario | Leagues | Football exp / high | Total exp / high | Reserve exp / high | Strong 1X2 (≥0.70) / season |
|---|---|---|---|---|---|
| A as merged (N1/D1 with totals) | E0 E1 SC0 N1 D1 | 178 / 232 | 343 / 462 | 157 / 38 | 203 |
| A core (h2h only for N1/D1) | same | 144 / 197 | 309 / 427 | 191 / 73 | 203 |
| **A + F1 (recommended Tier 1)** | + F1 | 162 / 215 | 327 / 445 | 173 / 55 | 227 |
| B top five + core | + SP1 I1 F1 | 204 / 261 | 369 / 491 | 131 / 9 | 300 |
| C major Europe | + P1 B1 | 242 / 308 | 407 / 538 | 93 / −38 | 382 |
| D full target | + E2 E3 SP2 D2 I2 F2 | 356 / 447 | 521 / 677 | −21 / −177 | 404 |

C and D cannot be funded unconditionally. With the tier throttle, a simulation at average daily rates gives:

| Month type | Credits used | Remaining at month end | Tier 2 coverage | Tier 3 coverage |
|---|---|---|---|---|
| Expected | ≈ 390 | ≈ 110 | 24/31 days | 0 days |
| High | ≈ 469 | ≈ 31 | 8/31 days | 0 days |

Tier 3 will therefore only run when measured usage falls below plan, for example in international-break weeks or
quiet tennis weeks. That is its intended role.

Strong picks per incremental credit, per season:

| League | Strong / credit |
|---|---|
| P1 | 0.33 |
| N1 | 0.31 |
| D1 | 0.25 |
| SP1 | 0.19 |
| I1 | 0.16 |
| F1 | 0.14 |
| E0 | 0.13 |
| SC0 | 0.12 |
| B1 | 0.09 |
| E1 | 0.05 |
| E2/E3/SP2/D2/I2/F2 | ≤ 0.03 |

## 3. Every target league

Credits are expected / high per month at the configured markets. Live coverage means an Odds API UK sport key
exists; book depth is confirmed at the first row. Settlement means a football-data code exists; team aliases are
added from the first observed spellings (no guessing; until then rows stay UNRESOLVED_NAME, i.e. pending, never
settled wrongly).

| League | Hist. grade (1X2) | Strong / season | Credits / month | Live coverage | Settlement | Stage A status | Paper status | Tier | Reason |
|---|---|---|---|---|---|---|---|---|---|
| Premier League (E0) | A (ref) | 48.7 | 37.5 / 56 | ✓ soccer_epl | ✓ E0, aliases in place | ACTIVE | READY_FOR_PAPER (first-row PASS ~7–8 Oct) | 1 | validated core |
| Championship (E1) | A (ref) | 21.3 | 40.8 / 58 | ✓ | ✓ E1 | ACTIVE | READY_FOR_PAPER (first-row PASS) | 1 | validated core |
| Scottish Premiership (SC0) | A (ref) | 38.7 | 32.2 / 54 | ✓ | ✓ SC0 | ACTIVE | READY_FOR_PAPER (first-row PASS) | 1 | validated core |
| Eredivisie (N1) | A | 53.3 | 17.2 / 24 | ✓ | ✓ N1, aliases at first row | ACTIVE | READY_FOR_PAPER after its own first-row PASS | 1 | V2-19 approved |
| Bundesliga (D1) | A | 41.0 | 16.6 / 23 | ✓ | ✓ D1, aliases at first row | ACTIVE | READY_FOR_PAPER after its own first-row PASS | 1 | V2-19 approved |
| **Ligue 1 (F1)** | **A** | 24.0 | 17.2 / 23 | ✓ soccer_france_ligue_one | ✓ F1, aliases at first row | ACTIVE (shadow label) | **RECOMMENDED → needs approval** + first-row PASS | 1 | grade A; previously dropped only by 428 > 425 planning arithmetic; affordable with a 55 high-month reserve |
| La Liga (SP1) | B | 40.0 | 21.2 / 26 | ✓ | ✓ SP1 | ACTIVE (shadow) | SHADOW (NEEDS_MODEL_RESEARCH / prospective evidence) | 2 | slope CI above 1 in both periods (1.22 / 1.27): transfer not established |
| Serie A (I1) | B | 33.3 | 20.8 / 29 | ✓ | ✓ I1 | ACTIVE (shadow) | SHADOW | 2 | grade B |
| Primeira Liga (P1) | B | 65.0 | 19.9 / 28 | ✓ | ✓ P1 | ACTIVE (shadow) | SHADOW | 2 | grade B (1.28 / 1.16); best strong-per-credit, so worth live evidence |
| Belgian Pro League (B1) | A | 17.0 | 18.9 / 24 | ✓ | ✓ B1 | ACTIVE (shadow) | eligible on evidence; HELD for budget (Tier 1 would cut high-month reserve to ≈ 31) | 2 | grade A, low volume |
| League One (E2) | B | 6.0 | 20.2 / 28 | ✓ | ✓ E2 | CONDITIONAL (shadow) | SHADOW | 3 | grade B, low volume |
| League Two (E3) | A | 4.0 | 19.1 / 28 | ✓ | ✓ E3 | CONDITIONAL (shadow) | SHADOW (low volume) | 3 | grade A but ≤ 4 strong / season |
| Segunda (SP2) | B | 5.0 | 23.7 / 28 | ✓ | ✓ SP2 | CONDITIONAL (shadow) | SHADOW | 3 | grade B, low volume |
| 2. Bundesliga (D2) | A | 3.0 | 16.5 / 21 | ✓ | ✓ D2 | CONDITIONAL (shadow) | SHADOW (low volume) | 3 | grade A, low volume |
| Serie B (I2) | B | 2.0 | 17.3 / 23 | ✓ | ✓ I2 | CONDITIONAL (shadow) | SHADOW | 3 | grade B, low volume |
| Ligue 2 (F2) | A | 2.0 | 17.2 / 25 | ✓ | ✓ F2 | CONDITIONAL (shadow) | SHADOW (low volume) | 3 | grade A, low volume |
| Scottish Championship (SC1) | A* | 5.0 | — | ✗ no Odds API key | ✓ SC1 | NOT OBSERVED | DATA_BLOCKED | — | no live odds source (* val + conf 699 matches < 900: needs more research anyway) |

## 4. Top five

| League | Hist. grade | Calibration status | Stage A | Live | Settlement | Credits | Paper | Why not paper |
|---|---|---|---|---|---|---|---|---|
| Premier League | A | reference (Gate 1 + V2-18) | ✓ | ✓ | ✓ | 37.5 / 56 | READY | — |
| Bundesliga | A | V2-18 grade A; live transfer NOT_ASSUMED | ✓ | ✓ | ✓ (aliases at first row) | 16.6 / 23 | READY after first-row PASS | — |
| Ligue 1 | A | as Bundesliga | ✓ | ✓ | ✓ (aliases at first row) | 17.2 / 23 | RECOMMENDED | awaits Fraser's approval (state transition) |
| La Liga | B | slope CI above 1 | ✓ shadow | ✓ | ✓ | 21.2 / 26 | SHADOW | transfer evidence insufficient |
| Serie A | B | slope CI above 1 in one period | ✓ shadow | ✓ | ✓ | 20.8 / 29 | SHADOW | transfer evidence insufficient |

## 5. Throttling order when usage rises

1. Tier 3 (E2, E3, SP2, D2, I2, F2) stops first (highest floor).
2. Tier 2 (SP1, I1, P1, B1) stops next.
3. Tennis and NBA stop at 100 remaining (existing optional floor).
4. Tier 1 football (E0, E1, SC0, N1, D1, F1) stops only at the hard floor of 25.

Every skip is logged with its reason ("tier throttle" / "credit floor").

## 6. Paper → state transitions recorded here (none applied)

* **F1:** recommended paper-eligible (grade A; Tier 1 already). The change is `paper_eligible: true`, with the
  evidence reference already in the config, applied after Fraser approves **and** its own first-row PASS
  (`verify_first_rows.py --sport football --competition "Ligue 1"`).
* **B1:** eligible on evidence, held for budget (would need Tier 1).
* **Grade B leagues** stay shadow until prospective evidence supports transfer under the approved
  Evidence & Promotion Protocol.

## 7. Unchanged

bsv2-4 rules, pcard-1 grades, frozen engines, DC holdout (scoped to E0/E1/SC0), real-money allow-list, the
O/U / BTTS / AH / tennis-secondary / NBA spread-total / NHL conclusions.

## 8. Approval record (2026-10-01, before merge)

Fraser approved the merge and Ligue 1 paper ("APPROVED — FINAL FOOTBALL COVERAGE + LIGUE 1 PAPER"). The directive
requires every Tier-1 league to pass its own first-row verification before paper operation, so `paper_eligible`
became `paper_state`:

* `PENDING_FIRST_ROW_PASS`: E0, E1, SC0, N1, D1, F1. Rows are observed with the shadow status, so they produce no
  PAPER_BET.
* `ACTIVE`: requires `first_row_pass` to be recorded, and the loader enforces this.
* `SHADOW`: all other observed leagues.

The transition to ACTIVE is a single commit after
`verify_first_rows.py --sport football --competition "<name>"` returns PASS. Rows recorded while a league was pending
stay shadow (append-only). Real-money allow-list unchanged; football expansion frozen after this merge.
