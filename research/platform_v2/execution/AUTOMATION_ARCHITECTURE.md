# Automation: operating mode, execution architecture, API economics and the live gate (2026-10-11)

Directive: Fraser/ChatGPT 2026-10-11. Fraser will not place routine bets manually.

## 1. Operating mode (effective 2026-10-11)
**FULLY AUTOMATED PROSPECTIVE PAPER VALIDATION.**
- Real-money betting is paused; `config/daily_card_v1.yaml` has `real_money_enabled: false`.
- Qualification is unchanged (bsv2-4: P ≥ 0.50, net EV ≥ +2%, odds ≥ 1.33, fresh clean price, eligible engine).
- Engine tiers are kept: LIVE_ELIGIBLE, PROVISIONAL_LIVE (NFL) and PAPER_ONLY (NHL etc.).
- Stakes are SIMULATED at £1 flat. £5 / £10 appear only as labelled hypotheticals.
- Fraser's routine involvement is none. He is contacted only for decisions (paid data or API, bankroll, re-authorising live money) and one-off research inputs.

## 2. Unattended loop and who does what
| Step | How | Automated? |
|---|---|---|
| Market collection | GitHub workflows (daily scan, tennis board, US sports, NBA from 20 Oct); Mac dispatcher at 07:15/16:15 for punctuality | yes |
| Probabilities → bsv2 gate → paper order | `paper_betting_v2/selections.csv` (append-only; decision price and time frozen) | yes |
| Paper-order ledger | `scripts/paper_orders.py` → `paper_betting_v2/paper_orders.csv` (rebuilt daily from append-only sources) | yes |
| Closing price | `clv_capture` workflow (0–25 min before start) | yes; on time only while the Mac LaunchAgent runs (GitHub cron is hours late). Without it, closes are missed and logged, never imputed |
| Settlement | settlement workflow: unified settlement → paper settlement (`run_bet_selection_v2.py settle`) | yes. Football outside EPL/Championship/SPL waits for the 15 Oct alias review |
| CLV / calibration / performance | `reports/paper_performance.{md,json}` (7-day, 30-day, all), `research_shadow/clv/clv_report`, `reports/qualified_capacity`, credit report | yes (daily) |
| Weekly summary to Fraser | scheduled task (Mondays), reading only repo outputs, no Bet Log | yes |

**Remaining Fraser actions (one-off, not routine):**
- run the Mac CLV dispatcher setup once;
- upload the Player SOT holdout data around 13 Oct;
- make decisions when asked.

## 3. Paper-order record
`paper_orders.csv` holds one row per PAPER_BET:
- **Identity:** order_id, prediction_id, event_id, sport, event, start, market, selection, engine, model version, engine status at decision, current tier, rule version.
- **Decision:** P, fair odds, source, execution class (BOOKMAKER_ONLY / EXCHANGE_EXECUTABLE / API_EXECUTABLE), available odds at decision, minimum acceptable odds, commission, estimated EV, EV band, decision time, price age, qualification reasons.
- **Simulated fill:** £1 stake, fill odds = the decision price. A better price is never chosen afterwards.
- **Close:** close time and minutes before start, same-book close, best UK close, closing fair P, price-CLV, fair-CLV.
- **Result:** result, status, paper P/L, settled time.
- **Data-quality flags:** NO_CLOSE_CAPTURED, SETTLEMENT_OVERDUE, OLD_PRICE_AT_DECISION, PRICE_AGE_UNKNOWN.

## 4. Automation feasibility: a core research-priority criterion
Each candidate market is scored on these dimensions. Each is GREEN / AMBER / RED with a reason.

| Dimension | GREEN | RED |
|---|---|---|
| Automatic price collection | API with history or live feed | manual / scraping only |
| Automatic order submission | exchange API (Betfair) | retail bookmaker only (ToS bans bots) |
| Market availability | on ≥ 50% of candidate events | sporadic |
| Liquidity at the decision price | ≥ £2 available on ≥ 50% of markets | thin / one-sided |
| Commission / cost | known; edge survives it | unknown |
| Min / max stake | fits the staking plan | below minimum or capped too low |
| Execution timing | runnable on a reliable trigger | needs a T−60 window we cannot hit |
| Stale-price risk | quotes refresh within a minute | slow / stale |
| API stability | documented, versioned | undocumented |
| Legal / terms | permitted | prohibited |
| Account-limiting risk | exchange (no limits; volume only) | soft bookmaker (limits likely) |
| Dry-run feasibility | paper broker + recorded prices | none |

**Rule:** if two directions have similar model quality and economic potential, prefer the one with more GREEN.

Track opportunities in three classes, kept separate in reports:
- **BOOKMAKER_ONLY**;
- **EXCHANGE_EXECUTABLE**;
- **API_EXECUTABLE**.

Current position:
- All tennis qualifiers so far are bookmaker-outlier prices (8 of 10 were BOOKMAKER_ONLY). Two were at the Betfair price under the old bsv2-1 rule, which bsv2-3/4 now exclude, because the tennis P *is* the Betfair mid.
- The current engines therefore have about **no API-executable edge**.
- Candidates for an exchange edge are proprietary models priced on Betfair: Player SOT and corners.

## 5. Future execution architecture (dry-run implemented; LIVE not implemented)
**Pipeline** (`src/prediction_markets_lab/execution/`):

qualified signal → fresh executable quote → identity check (event/market/selection) → market open → stale-price guard → odds ≥ minimum (slippage limit) → duplicate check → stake limit → daily stake cap → daily loss lock → per-event limit → per-engine limit → drawdown stop → broker submit → acknowledgement / fill / partial / reject → audit log → ledger → later settlement and reconciliation.

**Implemented now:**
- the guards (`guards.py`);
- `PaperBroker`, which simulates a full fill at the quoted price;
- an audit log of every attempt, filled or rejected;
- `config/execution.yaml`: environment PAPER, kill-switch file, all limits.

**Live is refused by design:** `broker_for()` raises `LiveExecutionDisabled` for any environment other than PAPER. There is no live adapter in the codebase.

**Still to build before any live use:**
- a Betfair adapter (placeOrders / listCurrentOrders / cancelOrders);
- partial-fill and unmatched-order handling (cancel or keep rules);
- reconciliation against Betfair account statements;
- API-failure retries with idempotent customer refs;
- separate LIVE credentials stored outside the repo.

## 6. API and access findings (verified 2026-10-11 where marked)
| Item | Finding | Source / status |
|---|---|---|
| Betfair Exchange API | the only mainstream UK venue that officially permits automated bet placement for personal use | Betfair developer docs |
| Delayed app key | free; prices delayed by a variable 1–180 s; **cannot place bets** (`placeOrders` blocked) | botblog.co.uk (2025, updated Aug 2026); consistent with earlier audit |
| Live app key | **£499 one-off activation fee**, debited from your Betfair account; requires a fully KYC-verified account and testing done on the delayed key; read-only use of the live key not permitted | **Betfair developer support, "How do I activate my Live App Key?" (verified)**. One third-party page says £299, so the official £499 is used. A recurring fee is not stated. |
| Commission | Betfair UK market base rate, typically 5% of net winnings per market (discounts possible) | standard terms; **re-verify before purchase** |
| Minimum stake | about £1 for back bets in GBP | **re-verify before purchase** |
| Rate limits / data charges | request-weight limits on market data; transaction charges apply only at very high order counts | **re-verify; irrelevant at our volumes** |
| Smarkets / Matchbook / Betdaq APIs | exist, with lower commission (≈ 1–2%), but access terms and fees are uncertain; earlier desk research found Smarkets £150, Betdaq £250, Matchbook usage-based (unverified) | **unverified**; recheck only if an edge appears there |
| Retail bookmakers (Betway, Paddy Power, LiveScore, …) | no public betting API; terms prohibit bots | not automatable |

**Fraser's "about £500" assumption is right for Betfair:** £499 one-off. Infrastructure is £0 extra (GitHub Actions plus the Mac, or a small VPS at about £5/month if always-on execution is needed). It must be funded inside the Betfair account.

## 7. API-purchase hurdle (conservative)
**API payback months** = £499 ÷ incremental expected monthly profit.

Incremental expected monthly profit =
- API-executable qualified bets/month (prospective, after commission)
- × average accepted stake
- × edge at the **lower** end of the CLV-implied range (not the point estimate).

| Exchange bets/month | Stake | Edge (lower bound) | Monthly profit | Payback |
|---|---|---|---|---|
| 0 (today) | — | — | £0 | never |
| 10 | £5 | 2% | £1.00 | 499 months |
| 30 | £10 | 2% | £6.00 | 83 months |
| 60 | £10 | 3% | £18.00 | 28 months |
| 100 | £20 | 3% | £60.00 | 8 months |

**Purchase is recommended only if:**
- the payback is ≤ 12 months at the lower-bound edge;
- **and** the readiness gate (section 8) passes.

At today's evidence, payback is **never**. The purchase is not justified.

## 8. Automated-live readiness gate (all must hold; the gate is deliberately hard)
**Statistical**
- ≥ 200 settled prospective paper orders in the API_EXECUTABLE class for the engines to be automated, collected after their freeze.
- Calibration slope 95% CI contains 1; |expected − actual wins| z < 2; Brier and log loss no worse than the engine's validation.
- Mean fair-CLV vs Betfair close > 0 with the 95% CI lower bound > 0 (after commission), and close coverage ≥ 70%.
- No drift: rolling 100-order calibration stable, with no sign flip across two consecutive halves.

**Economic**
- API_EXECUTABLE qualified volume ≥ 30 per month for 2 consecutive months.
- Payback ≤ 12 months at the lower-bound edge.
- Liquidity: ≥ £2 available at the decision price on ≥ 80% of paper orders, measured at decision time.
- Edge survives commission plus observed slippage.

**Engineering**
- Betfair adapter tested on the delayed key in dry-run.
- Duplicate protection, stale-price guard, kill switch, partial fills, API-failure handling and reconciliation each covered by tests and a recorded dry-run.
- ≥ 4 weeks of shadow execution: the dry-run broker against live delayed quotes, with complete audit logs and zero unexplained discrepancies.

**Risk**
- Bankroll rule: stake ≤ 2% of bankroll; daily stake cap; daily loss lock; per-event and per-engine caps.
- Maximum drawdown stop at 30% of bankroll.
- No Kelly; flat stakes.
- Fraser's explicit written authorisation, plus a versioned config change (`environment: LIVE`) and the live adapter merged through `safe_merge`.
