> **2026-09-30 note (cer-2 prep):** §4's integration proposal is superseded by `SHADOW_INTEGRATION_AUDIT.md` (bounded cer-2 design, measured ~76 KB/scan). The cer-1 settlement name-matching defect found in that audit is fixed in `io.py`. Text below unchanged for provenance.

# V2-7 — Audit of Phase 1, Offline Shadow Card Logger (cer-1), and Integration Proposal (2026-09-30)

## 1. Audit of Phase 1 calculations (done before building)
**No core probability or price assumption failed. Four corrections are on record:**

1. **Singles vs multis — Phase 1 claim WITHDRAWN.** "Singles on the same legs dominate" compared each structure at its *own* Kelly
   stake. At **equal total capital** (the fair test), for legs with P = 0.60 at O = 1.73:

   | total stake (% of bankroll) | 1% | 2% | 5% | 10% |
   |---|---|---|---|---|
   | EV, two singles vs double | 0.038% vs 0.077% | 0.076% vs 0.155% | 0.19% vs 0.39% | 0.38% vs 0.77% |
   | log-growth, two singles vs double | 0.00036 vs **0.00067** | 0.00069 vs **0.00114** | **0.00145** vs 0.00137 | **0.00198** vs −0.00201 |

   The crossover is at a **4.8% total stake**: below it the double grows faster, above it the singles do. A treble beats three singles
   at 1–3% and loses at 6%. What the double always costs: P(lose the entire stake) is 64% vs 16%, and its edge exists only if **every**
   leg is truly +EV. Which structure is better is therefore an **empirical, stake-dependent question**, which the logger now measures per card.

2. **Losing streaks — the assumptions are now exposed.** Exact P(≥ 8 consecutive losses in 50 independent bets) by win probability:
   0.80: 0.000 · 0.70: 0.002 · 0.60: 0.017 · 0.50: 0.084 · 0.40: 0.271 · 0.36: 0.390 · 0.30: 0.601 · 0.25: 0.773 · 0.216: 0.869 · 0.20: 0.905.
   The Phase 1 figures (1% / 40% / 87%) are the rows for p = 0.60, 0.36 and 0.216, the products for the example legs. They are not
   universal constants.

3. **Joint calibration — precision, not just coverage.** Calibration-in-the-large, actual − predicted (day-cluster bootstrap 95% CI),
   pooled over 4 sports and 2 periods:
   - singles: −0.23 pp [−0.68, +0.25] (n = 36,073)
   - doubles: +0.34 pp [−0.93, +1.53] (n = 5,251)
   - trebles: −1.77 pp [−5.94, +2.30] (n = 565)

   Minimum detectable deviation (2 SE) by band: doubles 1.6 / 2.8 / 5.9 pp (50–65 / 65–80 / 80+); trebles 4.5 / 10.1 / 44 pp.
   Brier vs climatology: doubles 0.231 vs 0.240; trebles 0.243 vs 0.247.
   → **Doubles are verified to about ±1.5 pp. Trebles only to about ±4 pp. Trebles above 65% are effectively untested.**

4. **Overlapping cards in the indicative study (B).** Legs were reused across cards, so the observations were dependent.
   | | cards | unique legs | effective n | ROI | day-cluster 95% |
   |---|---|---|---|---|---|
   | ATP doubles | 101 | 151 | ≈ 67 | +0.3% | ±31% |
   | WTA doubles | 85 | 139 | ≈ 75 | +1.2% | ±29% |
   | ATP trebles | 21 | 39 | ≈ 19 | −25.9% | ±70% |
   | WTA trebles | 13 | 23 | ≈ 14 | −19.2% | ±101% |
   → **The indicative study is uninformative.** (The card counts differ by about 2% from Phase 1 because of EV = 0 floating-point ties; the
   logger uses strict EV > 0.) Class A (disjoint cards) was already overlap-free.

## 2. Offline shadow logger `cer-1` (built, tested, not wired)
- **Code:** `src/prediction_markets_lab/card_engine/{__init__,cards,io}.py`, `scripts/run_card_research.py` (`log` / `settle` / `summary`),
  `tests/unit/test_card_engine.py` (13 tests).
- **Inputs (read-only):** `tennis_predictions/exchange_probability_snapshots.csv` (same-scan validated P plus Betfair width) and
  `tennis_predictions/price_snapshots.csv` (same-scan per-book prices).
- **Outputs, only under `research/platform_v2/card_engine_v2_7/shadow_cards/`:** `cards.csv` (append-only, idempotent,
  `card_id = sha256(rule|scan|book|group|sorted legs)`), `card_settlements.csv`, `search_space.json`, `summary.json`.
- **Legs:** the favourite side of every validated same-scan prediction × every named non-exchange book in that scan. Quality checks are
  the bsv2-3 rules: width ≤ 0.03, quote ≤ 240 min, event not started, valid odds. **Quality-failed legs are counted and never combined.**
- **Groups (labelled separately):**
  - `HIGH_P`: clean legs with P ≥ 0.70, any EV. Research only.
  - `POS_EV`: clean legs with EV > 0.
  - Pools are capped at 12 legs per book and group, in a pre-declared order; truncation is recorded.
- **Joint P:** multiplication only for distinct events (A1/A2). Same event or same participant → `UNVERIFIED`, no joint P.
  Same tournament is flagged.
- **σ_joint:** delta method. Per-leg σ = √(band calibration SE² + (width/2)²).
- **Every card records:** P_joint, σ, indicative same-book odds (`ODDS_INDICATIVE_NOT_EXECUTION_VERIFIED`), fair odds, break-even,
  EV with a ±1σ range, and the equal-capital comparison against the same legs as singles at 1%, 2% and 5% stakes (EV, log-growth,
  P(lose all)).
- **Status vocabulary:** `SHADOW_CANDIDATE` (POS_EV, every leg +EV, EV low bound > 0), `SHADOW_WATCH`, `RESEARCH_HIGH_P`,
  `RESEARCH_ONLY_UNVERIFIED`, `REJECT_LEG_QUALITY`. Nothing is a paper bet.
- **Settlement:** from the verified tennis settlement ledger. Every leg must be settled (fail closed); a void leg makes the card VOID;
  the first settlement wins.

### Offline demonstration (real 29 Sep 20:11 UTC scan)
- **Legs:** 995 leg-book pairs (53 tight-book favourites × up to 19 books); 134 legs rejected for quality; 30 truncated.
- **Cards:** 4,857 in total, which is **19 / 88 / 301 unique leg sets** for k = 1 / 2 / 3 (repeated across bookmakers).
  - `HIGH_P`: 199 singles, 1,077 doubles, 3,555 trebles.
  - `POS_EV`: **1 `SHADOW_CANDIDATE` single** (Bai @ Betway 1.73, P 0.599 ± 0.012, EV +3.6% [+1.5, +5.6]); this is the same selection
    as the production paper bet, which is a consistency check. **16 singles, 8 doubles and 1 treble are `SHADOW_WATCH`**: every leg is +EV,
    but the card's EV low bound is ≤ 0.
- **Best double:** BoyleSports, Kudermetova + Djokovic: P 0.450 ± 0.011 at 2.26, EV +1.6% [−0.9, +4.2]. At equal capital it grows
  faster than the singles at a 1% stake, slower at 2% and 5%.
- **Best treble:** P 0.236 at 4.32, EV +2.0% [−1.3, +5.4]. Singles grow faster at every stake tested.
- **Re-run:** adds 0 cards (idempotent). Settled: 0 (these matches were not yet settled when the demo ran).

## 3. Unresolved assumptions and data gaps
- **Execution:** that a book's multiple = the product of its leg prices, and that no acca restrictions or limits apply. **Unverified; Fraser
  needs to check a book.**
- **Trebles above 65%:** joint calibration is untested historically.
- **Legs:** only tennis match-winner. Football and NBA legs are not yet same-scan (the football card is a daily consensus; NBA starts 20 Oct).
- **Timing:** each leg has one snapshot per scan. Cards assume every leg is placed at the same time.
- **Correlation:** the dispersion index for NBA is 1.05 [0.98, 1.12], so its upper bound is monitored.
- **Multiple testing:** thousands of overlapping cards per scan. Judge only **pre-declared** aggregates (by group, k and status), never the
  best-looking card. The "best" cards above are illustrations, not evidence.

## 4. Proposal: prospective shadow integration (NOT approved; needs Fraser)
1. One extra `continue-on-error` step in `tennis_prediction_board`, after bet selection, runs `run_card_research.py log` and `settle`.
   0 credits. It writes only `research/.../shadow_cards/`, with a per-path `git add`.
2. **Growth control (measured):** the demo scan produced 4,857 cards = **9.0 MB**, so about 18 MB/day at 2 scans/day, which is too
   much for git. Log all POS_EV cards plus HIGH_P singles and doubles, and a deterministic 10% hash-sample of HIGH_P trebles, with the
   sample rule pre-declared and the sampled fraction recorded. That gives roughly 1–1.5 MB per scan.
3. **Review, pre-registered, with no automatic "100 cards = validated":** after ≥ 30 settled scans, report per group and k:
   - calibration-in-the-large with a day-cluster CI and effective n;
   - EV-low > 0 hit rate;
   - equal-capital growth, card vs singles, at 1% and 2% stakes.
   The question it can answer: is card-minus-singles growth distinguishable from 0 with its CI? It cannot answer profitability.
4. Paper-multi status stays **HOLD**. It requires the execution check (§3), treble calibration evidence, and singles meeting their own gate.
