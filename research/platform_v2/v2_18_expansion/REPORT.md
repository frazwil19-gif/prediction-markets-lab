# EXISTING-SPORT EXPANSION + PAPER-LAUNCH REPORT (V2-18 / V2-19 / V2-20)

Date: 2026-10-01. Directive: "NEXT PHASE — RAPID MARKET EXPANSION → PAPER BETTING".
Pre-registration: `PREREGISTRATION.md` (commit `8f760da`, before any analysis). Results: `RESULTS.json`,
`LEAGUE_SUMMARY.csv` (script `scripts/v2_18_expansion_study.py`). Paper layer: `research/platform_v2/v2_20_paper/`.

Statuses used: READY_FOR_PAPER · READY_FOR_PROSPECTIVE_SHADOW · NEEDS_SMALL_FIX · NEEDS_MODEL_RESEARCH · DATA_BLOCKED · REJECT.

## 1. Current master state
`03132ee` (Evidence & Promotion Protocol APPROVED). Step 0 work merged: NBA fixes (`aad2aeb`), first-row verifier
(`0a5ed68`), V2-8 analyser on the stage-a-2 input (`0cd6d2e`). Tests on master: 1261 passed / 8 skipped; research 82.
Live layers: Stage A board stage-a-2 (P only, never suppressed by price), bsv2-4 paper decisions, V2-7 card logger,
Credit Plan A (fixtures-first gate). Real money: off. Paper multis: off. NHL: not started. DC holdout: sealed.

## 2. Current active / pending sports and markets
| Sport · market | Engine | State | Paper (bsv2) |
|---|---|---|---|
| Tennis ATP/WTA match winner | betfair_market v1 | PROSPECTIVE_SHADOW (live since Sep) | **live** (10 paper selections, 1 under bsv2-4 rules; none settled yet — results feed lag) |
| Football 1X2 (E0/E1/SC0) | market_consensus@1-live | PROSPECTIVE_SHADOW; first rows ~8 Oct | automatic from first rows |
| Football Double Chance | derived_1x2 | shadow probability only | DATA_BLOCKED (no executable DC prices) |
| NBA moneyline | market v1 / @1-live | HISTORICAL_VALIDATED; activation 20 Oct | automatic from 20 Oct |

## 3. Football league expansion audit
Data: xgabora/Club-Football-Match-Data (MIT, commit `25882a58`, sha256 `ef224cf2…`), Bet365 closing-proxy odds,
dev 2017–21 / validation 2022–24 / confirmation 2025. Estimator = single-book de-vig (no fitting). The proxy reproduces
our prior E0 result (val log loss 0.9485 vs Gate-1 0.955).

| League | 1X2 grade | Val slope / conf slope | Strong (≥0.70 top pick) / season | Credits / in-season month | Outcome |
|---|---|---|---|---|---|
| E0 / E1 / SC0 (ref) | A / A / A | 1.07/0.88 · 1.03/0.93 · 1.17/1.06 | 48.7 / 21.3 / 38.7 | 33.7 / 38.5 / 25.7 | live |
| **N1 Eredivisie** | A | 1.04 / 0.99 | 53.3 | 29.6 | **EXPAND NOW** |
| **D1 Bundesliga** | A | 0.99 / 1.24 | 41.0 | 30.2 | **EXPAND NOW** |
| F1 Ligue 1 | A | 1.07 / 1.08 | 24.0 | 30.1 | SHADOW (budget) |
| B1 Belgium | A | 1.15 / 1.06 | 17.0 | 31.6 | SHADOW (budget) |
| E3, D2, F2 | A | — | 2–4 | 28–31 | SHADOW (few strong) |
| G1 Greece, SC1 Scot. Champ. | A | — | 37 / 5 | 27 / 25 | NEEDS MORE RESEARCH (val+conf 392 / 699 matches < 900) |
| E2, SP1, I1, SP2, I2, P1, T1 | **B** (slope CI above 1 in a period) | e.g. SP1 1.22/1.27, P1 1.28/1.16, T1 1.34/1.14 | 2–65 | 31–42 | SHADOW (grade B) |

Grade B = the de-vigged market is *under-confident* (slope > 1) — favourites win more than implied. That is not a
reason to deploy faster; it means the transfer of our estimator is not established there. Retained as a finding.

## 4. Football market expansion audit
| Market | Definition / settlement | Historical evidence (proxy) | Strong-P frequency | Live executable price | Status |
|---|---|---|---|---|---|
| 1X2 | 90-min result | grade A in refs, N1, D1 | ~20–55 /season/league | featured h2h (in scan) | E0/E1/SC0 live; N1/D1 READY_FOR_PROSPECTIVE_SHADOW → paper on first rows |
| Double Chance | 1X/12/X2, 90 min | grade A in refs | very frequent ≥0.80 (E0 145/season) | per-event only (1 cr/event); fair odds mostly < 1.33 | READY_FOR_PROSPECTIVE_SHADOW (shadow only); Stage B **DATA_BLOCKED** |
| Over/Under 2.5 | total goals vs 2.5 | calibration A (wide CIs, E0 slope 1.13 [0.79, 1.50]) | favoured side ≥0.70 rare, never ≥0.80 | featured totals (already paid in scan) | **REJECT** for strong-prediction use (no high-P region) — negative result retained |
| BTTS | both score | E0 slope 0.72 [0.25, 1.25] | never ≥0.70 | per-event only | **REJECT** (no high-P region; credit-heavy) |
| Draw No Bet | draw = void | E0 val ≥0.80: n 186, pred 0.878 vs actual 0.903 (under-confident at top) | frequent | derived from h2h for P; executable DNB price per-event only; fair odds < 1.33 at P ≥ 0.80 | READY_FOR_PROSPECTIVE_SHADOW (Stage A); Stage B **DATA_BLOCKED** |
| Asian Handicap (half lines) | line-adjusted | lines set ~0.5 by construction | none ≥0.60 | per-event only | **REJECT** |

No market was forced into deployment because code already exists (O/U, BTTS research modules stay research-only).

## 5. Tennis market expansion audit
Match winner remains the core. Set winner / set handicap / total games / correct score: The Odds API exposes these
only via the per-event endpoint (≥1 credit per event per market) and we hold no free historical set-score + set-market
odds dataset in the repo to validate a model (match-winner P cannot be converted without a validated point/set model).
Status: **DATA_BLOCKED** (all tennis secondary markets) this sprint. No in-play.

## 6. NBA market expansion audit
SBR archive (flancast90/sportsbookreview-scraper, MIT, `1a820e50`), 2011–2021, n = 12,967 games with closing spread,
total, scores. Home ATS cover 0.484; spread residual sd 12.61; over rate 0.491; total residual sd 17.93. Lines are
set near 50/50 — there is no high-probability region; a model would need to *beat the line*, which is a different
objective (persistent mispricing) from this project's probability-first core. Data ends 2022 (no recent seasons for a
chronological holdout); +2 credits/day for live spreads+totals. Status: spread **REJECT** (for now), totals **REJECT**
(for now), team totals DATA_BLOCKED. Frozen ML untouched.

## 7. Historical data inventory
Football: xgabora Matches.csv (2000–2026, 1X2 + O/U 2.5 + AH + max odds, 40+ leagues) — not committed (provenance
pinned in RESULTS.json); football-data.co.uk direct is proxy-blocked, GitHub mirror works. Tennis: existing Betfair
match-winner history (ATP/WTA; n ≈ 10k+ per tour). NBA: SBR archive 2011–22 (ML/spread/total); existing NBA ML set.
Tennis set/games odds: none.

## 8. Model / calibration evidence
All 1X2/DC/DNB estimators are market consensus (no fitted parameters), graded by pre-registered C1 (slope CI covers 1
in validation and confirmation) and C2 (bands n ≥ 200 inside 99.5% Wilson). calibration_transfer to the live
median-of-UK-books estimator is NOT_ASSUMED: prospective rows decide (protocol INTERIM h ≤ 5pp, FULL h ≤ 2.5pp).

## 9. Live bookmaker coverage
The Odds API UK region: Eredivisie and Bundesliga h2h available on the featured endpoint with the same UK books as
the EPL (to be confirmed by the first-row verifier — `verify_first_rows.py --sport football`). DC/DNB/BTTS/AH and
tennis set markets: per-event only.

## 10. Incremental API-credit cost
Worst-case month: football 3 leagues 98 + tennis 150 + NBA 60 + settlement 20 + manual 10 = 338. +N1 → 368, +D1 → 398,
+F1 → 428 (> 425 target, so F1 waits). V2-19 caps: football 160, settlement 50, sum 420 ≤ 425. Paper card / dashboard:
0 credits. Per-event markets (DC/DNB/BTTS): ~1 credit × fixtures × markets — not funded.

## 11. Expected prediction volume
Strong 1X2 top picks per season: refs ~109; +N1 53, +D1 41 → ~203/season (≈ 5/week in season). DC/DNB add shadow
probability rows at 0 credits. Tennis: ~10–25 strong/day in tour weeks. NBA from 20 Oct: ~1–4 strong/day.
Financially assessable (price ≥ 1.33, EV ≥ 2%) is a small fraction — most strong favourites are priced < 1.33.

## 12. Recommended expansion universe
Football 1X2: E0, E1, SC0 + **N1, D1** (V2-19). DC + DNB Stage A shadow probabilities. Tennis match winner. NBA ML
(20 Oct). Nothing else this sprint.

## 13. Rejected / deferred markets and why
F1, B1 (budget) · E3/D2/F2 (few strong) · G1/SC1 (sample) · E2/SP1/I1/SP2/I2/P1/T1 (grade B) · O/U 2.5, BTTS, AH
(no high-P region) · DC/DNB executable (per-event credits; fair < 1.33) · tennis secondary (data) · NBA spread/total
(line-balanced; old data) · NHL (directive: not yet).

## 14. Exact implementation work required
* N1/D1: done on `v2-19-football-n1-d1` (sport keys, COMP_TO_FD, competitions, guard scope, caps). After merge: on
  first observation add team aliases for any unmapped spellings (unresolved names are never guessed).
* Paper layer: done on `v2-20-paper-card`. After merge it runs automatically after each bsv2 evaluate/settle.
* Nothing else is required for the recommended universe.

## 15. Paper-betting readiness by market
| Market | Status |
|---|---|
| Tennis ATP/WTA match winner | **READY_FOR_PAPER** (already paper-live) |
| Football 1X2 E0/E1/SC0 | **READY_FOR_PAPER** (automatic from first rows ~8 Oct) |
| Football 1X2 N1/D1 | READY_FOR_PROSPECTIVE_SHADOW → READY_FOR_PAPER on merge of V2-19 + first-row PASS |
| NBA moneyline | **READY_FOR_PAPER** from 20 Oct (activation date) |
| Football DC, DNB | READY_FOR_PROSPECTIVE_SHADOW; paper DATA_BLOCKED |
| F1, B1, E3, D2, F2 1X2 | READY_FOR_PROSPECTIVE_SHADOW (budget-deferred) |
| E2, SP1, I1, SP2, I2, P1, T1 1X2 | NEEDS_MODEL_RESEARCH (grade B transfer) |
| G1, SC1 1X2 | NEEDS_MODEL_RESEARCH (sample) |
| O/U 2.5, BTTS, AH | REJECT |
| Tennis secondary | DATA_BLOCKED |
| NBA spread / total | REJECT (for now) |

## 16. Earliest evidence-safe paper launch path
Paper is already running for tennis. Football 1X2 joins with the first prospective rows (~8 Oct) after the first-row
verifier PASS; N1/D1 the same week if V2-19 is merged now. NBA joins 20 Oct. The Daily Paper Bet Card starts with the
first workflow run after V2-20 is merged. No threshold is lowered; zero-bet days are valid and shown as such.

## 17. Unified paper-bet schema
bsv2 `selections.csv` (immutable) + `settlements.csv` (immutable) + new `card_enrichment.csv` (append-only, first sight,
keyed by selection_id): competition, σ, σ method, calibration status, P first snapshot / current scan, EV at P,
EV at P−1σ / P−1.645σ, evidence state, grade, grade reason, hypothetical stakes per bankroll × policy. Selections decided
before pcard-1 are `UNGRADED_PRE_PCARD` (never back-filled).

## 18. Daily Bet Card design
`reports/daily_paper_card.{json,md}`: A+/A/B paper bets (bsv2 PAPER_BET only, real observed price + source + age),
then grade C (WATCH / multi research, no stake), rejected count. Grades pre-registered: A+ = EV>0 at P−1.645σ and
evidence ≥ PROSPECTIVE_CALIBRATION_SUPPORTED (empty today), A = EV>0 at P−1σ, B = other PAPER_BET, C = WATCH/MULTI,
REJECT otherwise. Stakes £20/30/50/100 × flat 1% / 2% / ⅛ Kelly / min stake from the bsv2 block; 5% per bet, 10% per
day; singles. Every row `money_eligible = False`. Local dry run on today's data: 0 paper bets (A+ 0, A 0, B 0, C 12,
REJECT 33) — every strong tennis favourite was priced below fair or below 1.33.

## 19. Paper-performance dashboard
`reports/paper_dashboard.{json,md}`: expected vs realised P&L, ROI, drawdown, losing run, bankroll replays; prediction
quality separately (mean P vs win rate, expected vs realised wins, Brier, log loss); breakdowns by sport, competition,
market, engine, rule version, grade (plus bsv2 P/odds/source bands).

## 20. Paper → real-money review protocol
Evidence & Promotion Protocol (APPROVED) + `v2_20_paper/MONEY_ELIGIBILITY_REVIEW_TEMPLATE.md`. Review triggered only
by the FULL evidence trigger; output is advice; activation only by Fraser's explicit written approval. Nothing in code
can enable money.

## 21. Branches / commits / tests
| Branch | Commits | Tests | Merge |
|---|---|---|---|
| `v2-18-expansion-sprint` | `8f760da` prereg · `9be316e` study · this report | research only | needs approval (docs) |
| `v2-19-football-n1-d1` | `2f23e2c` | 1262 passed / 8 skipped; research 82 | **needs approval** |
| `v2-20-paper-card` | `8c855e0` | 1269 passed / 8 skipped | **needs approval** |

## 22. Explicit blockers
1. Approval to merge V2-19 (N1/D1 live football; changes budget caps).
2. Approval to merge V2-20 (paper card + dashboard; touches the three workflows, fail-soft).
3. Approval to merge V2-18 docs.
4. Executable DC/DNB prices need per-event credits — not funded (no purchase).
5. Tennis paper selections of 29–30 Sep are unsettled: the TennisCourtLog results feed has not yet published those
   matches; bsv2 settles fail-closed, so they stay PENDING until it does (no manual settlement).

## 23. Exact next actions
1. On approval: merge V2-19 and V2-20 (then V2-18 docs).
2. ~8 Oct: run `verify_first_rows.py --sport football`; add N1/D1 aliases for any unresolved names.
3. 20 Oct: NBA first-row verification.
4. Let the paper card run daily; no new features (directive §14). Review at protocol INTERIM/FULL triggers only.
