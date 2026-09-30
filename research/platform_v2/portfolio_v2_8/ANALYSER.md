# V2-8 Offline Portfolio Analyser (v2-8a-1): Architecture (research only)

**Purpose.** Given the frozen V2-7 prospective predictions and prices of one scan, show:
- **(A)** the strongest predictions, ranked by probability;
- **(B)** whether, and how, the available payouts justify staking, comparing every allocation at equal capital, including NO BET.

It follows `research/platform_v2/DECISION_PHILOSOPHY.md`.

**Constraints.**
- Consumes frozen records **read-only**: V2-7 `prospective/<YYYY-MM>/{scan_runs,legs}.csv`, and production `price_snapshots.csv`
  (append-only, with its sha recorded).
- 0 API credits. No network code.
- Writes only to `--out`, which is refused inside V2-7 or production directories.
- Never modifies V2-7, never backfills, never places or creates bets.
- Outcomes are **off** by default. `--with-outcomes` exists for research scoring but needs the same approval as research settlement.

## Pipeline per valid scan (status OK / OK_ZERO_CANDIDATES, mode PROSPECTIVE; DRY_RUN_REPLAY only with `--allow-dry-run`)
**Stage A: Prediction Board** (`prediction_board`). Every frozen HIGH_P prediction (V2-7 event-level legs), **sorted by P, never
by EV**. Each row carries:
- sport, event, market, selection, start;
- P ± σ, where σ = √(band calibration SE² + (exchange width/2)²);
- calibration support (band, holdout n, holdout predicted vs actual);
- model id and scan time;
- the **market benchmark**: the median bookmaker de-vigged P in the same scan, with ΔP and a flag:

| flag | condition |
|---|---|
| `AGREES_WITH_MARKET` | \|ΔP\| ≤ 0.03 |
| `MILD_DISAGREEMENT` | 0.03 < \|ΔP\| ≤ 0.10 |
| `INVESTIGATE_DISAGREEMENT` | \|ΔP\| > 0.10 |
| `NO_BENCHMARK` | no bookmaker quotes |

Disagreement is a reason to investigate. It never raises rank and is never labelled "value".

**Stage B1: single-bet evaluation** (`single_evaluation`). Clean same-scan quotes use the V2-7 quality rules, identical to bsv2-3:
fresh within 240 min, width ≤ 0.03, not started, valid odds, no exchanges. Each row reports fair odds, best offered odds and book,
median book odds, payout, profit if won, downside, EV with its ±1σ range, and quote age. The label is one of:
- `POSITIVE_VALUE_ROBUST_TO_1SIGMA`
- `POSITIVE_CENTRAL_BUT_UNCERTAIN`
- **`STRONG_PREDICTION_POOR_PRICE`**
- `NO_CLEAN_PRICE`

Grade is always `UNGRADED (thresholds not set)`.

**Stage B2: allocation options** (`betting_structures`). Two populations, never merged:
- **HIGH_P**: the N ∈ {3, 5} strongest predictions are fixed **first** (distinct events and participants). Then the one book pricing
  all N in the same scan at the best product is used.
- **POS_EV**: per book, the N ∈ {2, 3} highest-P legs with EV > 0. The book with the highest joint P is used.

For each set, every bounded structure is evaluated at **equal total capital**: SINGLES, ACC_2..N, DBL12+SINGLES, 2DBL+SINGLE,
TBL123+SINGLES, RR_DOUBLES, RR_TREBLES, FULL_COVER, FULL_COVER+SINGLES (≤ 31 lines), and NO_BET. Identical line sets are reported
once. From an exact 2^N enumeration each structure reports:
- P(complete win), fair and indicative odds;
- expected return, and expected return with every leg at P − σ;
- SD, P(any loss), P(total daily loss), P(positive day), maximum loss;
- expected log growth at 1%, 2% and 5%;
- exposure per leg, and an EV sensitivity grid (±0.5…5 pp);
- stake feasibility for £20/30/50/100 × 2%/5% × £0.10/£1 minimum. Lines are rounded down to £0.10 and **never scaled up**.
- Legs-correct distribution: P(0..N correct).

**Qualification views are shown side by side (research only).**
- Leg level: `leg_level_rule_all_legs_ev_gt_0`, the frozen V2-7 rule.
- Structure level: `structure_level_screen_ev_low_gt_0`, meaning the structure's expected return is still > 0 with every leg at
  P − σ.
- If no structure passes, the card defaults to **NO BET**. Neither view creates a bet.

## Outputs
`analysis_<scan>.json` (full), `daily_bet_card_<scan>.md` (a Stage A / Stage B research preview) and `summary.json` (counts of labels,
flags, screen passes and NO BET scans).

## Usage
```
python scripts/run_v2_8_analyser.py --out <scratch dir>                 # all valid PROSPECTIVE V2-7 scans
python scripts/run_v2_8_analyser.py --out <dir> --records research/platform_v2/card_engine_v2_7/dry_run_cer2_scan_2026-09-29T2011 --allow-dry-run
```
Configuration: `config/v2_8_analyser.yaml` (read only by the analyser). Tests: `tests_research/test_v2_8_analyser.py`.
