# Frozen-V1 Backtest Report — money-strategy-v1-frozen / 2026-09-22-phase1-primary-closing

**Dataset:** Cycle 1 1X2 (E0/E1/SC0, 2020/21-2025/26), closing snapshot -- data/processed/football/cycle_001_{matches,bookmaker_markets}_full.csv
**Config hash:** `fca6f23522c449880791e9195c8e5f4eabe77beb5d12494c24e1c1fb2beb4544`
**Price basis:** closing snapshot (both consensus and best price) — PROXY, not exact replay.

## Proxy disclosure (read this before the numbers below)

- PROXY BACKTEST, not an exact replay of the live 07:00 UTC daily scan
- trivially passes for every candidate with a known kickoff, by construction of this proxy's simulated scan timestamp (kickoff minus a fixed 60-minute offset) -- this run does NOT meaningfully exercise the 24h money-event-horizon gate. See research/backtesting/BACKTEST_DATA_FEASIBILITY_AUDIT.md section 5.
- best (highest) closing decimal odds among bookmakers accepted into that match's consensus -- an optimism risk relative to a real bettor checking a small number of bookmakers, not a leakage risk. See research/backtesting/LEAKAGE_AUDIT.md.
- Risk gates applied: True. risk.decision_gates (exposure caps, daily/weekly loss stops) are tested production modules NOT currently wired into scripts/run_daily_scan.py's automated live path -- applied here regardless, per the master directive's 'no duplicate exposure' requirement.

## Coverage

- Source matches file rows: 5800
- Excluded (ineligible consensus model): 24
- Excluded (missing bookmaker panel): 0
- Excluded (kickoff join failed): 0
- Matches included: 5776
- Candidates generated (matches × 3 outcomes): 17328
- Money-qualified candidates: 0
- Candidates actually staked: 0
- Bankroll exhausted during run: False

## Probability quality — ALL graded candidates (research population)

- n = 17328
- Mean estimated probability: 0.3332651695625765
- Actual outcome rate: 0.3333333333333333
- Brier score: 0.1957773144684839
- Log loss: 0.5759426453996506
- Expected calibration error: 0.009874323999935925
- Calibration intercept/slope: 0.04695479017589767 / 1.0719952974141636
- AUC: 0.6956293033763745

## Probability quality — MONEY-QUALIFIED candidates only

- n = 0
- Mean estimated probability: None
- Actual outcome rate: None
- Brier score: None
- Log loss: None

## Betting performance — money-qualified bets actually staked

**NO MONEY-QUALIFIED BETS WERE PLACED IN THIS BACKTEST RUN.** This is a valid, honestly-reported result, not an error.

## Conservative audit checklist

See research/backtesting/PHASE1_RESULTS_AUDIT.md for the full 30-point return checkpoint. This report does not, on its own, claim the strategy is 'validated' — a positive ROI figure above is not treated as proof of anything without the uncertainty and sample-size context in that document.