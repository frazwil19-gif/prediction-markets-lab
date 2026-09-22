# Probability Engine vs Betting Decision Engine — Architecture & Design Note (Phase 5, 2026-09-22)

Design only. **No production file was changed.** For later review by Fraser.

## 1. The separation (now a permanent project principle)

| | PROBABILITY ENGINE | BETTING DECISION ENGINE |
|---|---|---|
| Question | What is the probability this outcome occurs? | Is this specific, currently obtainable price worth taking, given the risk? |
| Inputs | the strongest *validated* estimator for that market (market consensus is a legitimate estimator) | probability, uncertainty, current quotes per bookmaker, payout, bankroll, exposure |
| Output | calibrated P + uncertainty + provenance (estimator id, version, snapshot time) | BET / WATCH / PAPER_ONLY / REJECT + stake |
| Judged by | log loss, Brier, calibration, AUC, band reliability on unseen data | realised ROI, CLV, drawdown, prospective calibration of the bets taken |
| Needs historical profitability? | **No** | yes, prospectively (paper first) |

Market consensus is **not** a null model. It is a probability estimator, and where it validates best it powers that
market's engine.

## 2. Best available probability estimator by market
| market | best estimator | evidence |
|---|---|---|
| Football 1X2 | de-vigged multi-book consensus | Gate 1, Stage 3B, Phases 1–3 |
| Football O/U 2.5 | de-vigged consensus | Phase 4 Gate 1b (dev + holdout) |
| **Football BTTS** | **market-implied Poisson (λ from 1X2 + O/U 2.5 prices)**, until live BTTS quotes allow a direct BTTS consensus | Phase 5 (dev + sealed holdout). A direct BTTS consensus should be benchmarked against it prospectively |
| Football AH | not researched | — |
| Tennis Match Winner | Betfair-archive consensus (edge-hunting exhausted) | Tennis Cycle 1 / Workstream B |

## 3. The dependence problem, when consensus is both probability and price reference

**Concept.** In V1, P = mean de-vigged probability across the panel, and EV = P × best_odds − 1. The best-priced
bookmaker sits inside P. Two worries follow: (a) circularity, and (b) EV then measures *dispersion between
bookmakers*, not a forecast edge.

**Quantified** (`CONSENSUS_PRICE_INDEPENDENCE.json`, football 1X2 closing, 5,800 matches, 17,400 outcome candidates,
same snapshot, no thresholds searched, EV>0 as the only split):

| reference probability for the best price | EV>0 share | mean claimed EV | realised ROI [95% CI] | mean odds |
|---|---|---|---|---|
| inclusive consensus (current V1) | 17.5% | +2.8% | −1.2% [−9.2, +6.9] | 6.97 |
| leave-one-bookmaker-out (exclude the priced book) | 26.7% | +3.4% | −1.9% [−8.2, +4.0] | 6.02 |
| sharp reference (Pinnacle alone; price from the other books) | 10.2% | +2.6% | +1.4% [−7.8, +10.8] | 5.23 |
| *back every best price, no filter* | 100% | — | **−2.9% [−5.2, −0.5]** | — |

Findings:
1. **Including the priced book makes V1's EV *more conservative*, not inflated.** The best-priced book has the lowest
   implied probability for that outcome, so including it pulls the consensus down. Inclusive EV is on average 0.66 pp
   *below* LOO, and no candidate was EV-positive inclusive but not LOO. Circularity is therefore not an inflation bug.
2. **But the claimed EV does not show up as realised return.** Claimed +2.6% to +3.4% against realised −1.9% to +1.4%,
   with no CI excluding zero. Cross-bookmaker dispersion at the closing snapshot with 4–6 books is mostly noise, and
   it concentrates in longshots (mean odds 5–7). This matches Backtest Phase 1's zero-qualified result and why the
   money gate exists.
3. **The sharp reference is the only one pointing positive.** A price from one book compared against a *different*,
   efficient book's probability is the logically clean construction. The CI is still wide, so this is a direction to
   test prospectively, not evidence.
4. Backing the best available price blindly loses about 2.9%. The market is close to efficient even after line shopping.

**Design recommendations (not implemented; each needs explicit approval):**
- R1. For every candidate, compute and log EV against three references: inclusive, LOO, and an independent reference
  (Betfair Exchange where liquid, which is confirmed in the UK Odds API panel; whether Pinnacle is in this account's `uk` panel is unverified, and an extra region costs extra credits). Keep V1's
  decision logic unchanged until prospective data shows which reference predicts realised return and CLV.
- R2. Longer-term candidate rule: *probability from the engine, value only against a reference that excludes the
  priced book*. The priced book never helps set the probability it is judged against.
- R3. Treat CLV (price taken vs closing consensus or exchange) as the primary evidence that a price edge is real. ROI
  on small samples is noise.
- R4. For BTTS specifically, keep P from market-implied Poisson (1X2 + O/U), which excludes the BTTS books entirely.
  EV against a BTTS bookmaker's quote is then independent by construction, which makes this the cleanest EV
  construction in the project.

## 4. Live prospective validation design (design only)
Persist, per scan and per candidate (append-only, e.g. `research_archive/live_quotes/<date>/<scan_ts>.jsonl`, committed
like `paper_ledger/`):
scan_timestamp · provider event_id · kickoff (ISO) · sport/competition · market · exact line/point · selection ·
**every bookmaker's raw quote** (key, price, point, last_update) · quote staleness · inclusive / LOO / exchange
reference probabilities · best odds + bookmaker · probability-engine estimator id + version + P + uncertainty ·
money_decision + rejection reasons · stake (if any) · later: closing snapshot (a separate pre-kickoff fetch) · result ·
settlement · CLV.

BTTS specifics: the `btts` market only comes from the per-event endpoint at 1 credit per event. Fetch it only for fixtures
inside the 24h money window, and add a credit-budget guard (for example, stop BTTS fetches when remaining credits fall
below a configured floor). Estimated +120–170 credits/month on top of ~180. That fits the 500 free tier only with the
money-window restriction. It needs Fraser's approval because it changes live API usage.

Prospective success criteria for BTTS (to be pre-registered before collection starts): calibration of the ≥55% and
≥60% bands against realised outcomes; direct BTTS-consensus vs market-implied-Poisson log loss on the same fixtures;
CLV of any paper BTTS selection.
