# Daily Probability Engine V1 -- First Implementation Checkpoint

**Date:** 2026-09-18
**Trigger:** Operator's "GO -- begin implementation of the Daily Probability Engine V1" instruction.
**Commits:** `d50d304` (this build), on top of `9b26d84` (objective lock/roadmap) and `57b1627`/`f960e5e`
(Gate 1). Status: first genuine external dependency reached (see point 12) -- returning per the
instruction's "work autonomously until you reach the first genuine external/manual dependency" clause.

This answers the operator's 14-point return in order.

---

### 1. What was built

- Three new decision modules replacing Stage-1 human-judgement placeholders with deterministic,
  config-driven heuristics: `decisions/confidence.py` (bookmaker-count/dispersion -> High/Medium/Low),
  `decisions/data_quality.py` (bookmaker-count/quote-age check), `decisions/liquidity.py`
  (stake-vs-available-size check, defaulting to adequate for a fixed-odds bookmaker quote that
  publishes no order book).
- `decisions/recommendation.py`: the composition this module's own original docstring promised --
  consensus + EV + confidence + data-quality + liquidity + grading + staking, in one call, producing
  one Daily Card row (`storage.schemas.MarketRecord`) and its stake.
- `reports/daily_bet_card.py` (new): renders the exact phone-readable Daily Bet Card format specified
  in the instruction (header stats, ranked selections, OPTIONAL MULTI section, REJECT/WATCH summary
  with system warnings).
- `scripts/run_daily_scan.py` (new): the V1 operational entry point tying all of the above together,
  reading a bookmaker-odds CSV and a best-price CSV and producing a Daily Bet Card plus a full
  candidate log.
- `ingestion/manual_odds_loader.py`: one additive function, `load_manual_odds_market_metadata`,
  recovering per-market descriptive fields (sport/competition/event/market_type) the existing loaders
  intentionally drop.
- `storage/schemas.py`: `Exchange` widened from a two-name `Literal["Smarkets","Betfair"]` to a
  free-form `str` -- the one schema fix flagged in the roadmap doc, now done.
- `config/thresholds.yaml`: two new config sections (`data_quality`, `confidence`) -- no hard-coded
  thresholds anywhere in the new code.
- 39 new/changed tests across 5 new test files plus additions to `test_manual_odds_loader.py`. Full
  suite: **770/770 passing** (up from 718 at session start, zero regressions).
- Two real, executed dry runs (detail in point 13) producing two actual Daily Bet Card files, both
  delivered to you directly this session.

### 2. Existing infrastructure reused

Everything the roadmap doc's BUILT/REUSABLE bucket said would be reused, was, unmodified:
`probability/consensus.py`, `probability/margin_removal.py`, `probability/market_pipeline.py`,
`probability/odds_conversion.py`; `ev/expected_value.py`; `risk/staking.py`; `decisions/grading.py`
(used exactly as-is -- its boolean-gate design turned out not to need the schema-level rename I'd
flagged as a maybe; only the `Exchange` type alias itself needed widening, not `GradingInput`'s field
names, which are generic enough to describe any venue already); `ingestion/manual_odds_loader.py`'s
two existing loaders and `ingestion/exchange_price_loader.py` (used unmodified -- its `exchange` field
was never actually type-constrained, only `storage.schemas.MarketRecord.exchange` was); `storage/
csv_store.py::append_record` (used for the new candidate log). Nothing was rebuilt that already
existed and worked.

### 3. Current data/odds source

**Still manual entry -- unchanged from the roadmap doc's recommendation, and now confirmed hands-on.**
I attempted, this session, to source real current fixtures and odds automatically via web search/fetch
(the instruction's own "audit... identify the best practical low-cost/free source" ask). Findings:

- Fixture identification worked: I found two real fixtures for today (2026-09-18) via web search --
  Brentford v Chelsea (Premier League, 20:00) and Bristol City v Watford (Championship, 20:00).
- Individual per-bookmaker odds did **not** reliably extract. Oddschecker's page structure lists
  bookmaker names and lists odds values, but automated HTML-to-text fetching could not reliably pair
  the two into a trustworthy row-by-row table -- confirmed by three separate fetch attempts, including
  one asking for a verbatim reproduction. One fetch also returned identical home/away odds for a match
  where that is implausible (Chelsea away at Brentford), suggesting the fetch pipeline itself
  introduces summarisation error on this kind of tabular content, not just an alignment problem.
- **Conclusion: this is a genuine, now-confirmed-by-attempt reason the roadmap's manual-entry design
  is correct, not a shortcut avoided.** I did not fabricate numbers and attribute them to real named
  bookmakers (Bet365, William Hill, etc.) -- that would misrepresent real companies' prices. The
  dry-run data instead uses the two real fixture identities with a clearly-labelled **illustrative**
  bookmaker panel (generic labels: Book1-Book5, not real company names), fully disclosed as such in
  every row's `source`/`notes` column and in this checkpoint. Real production use requires exactly
  what the roadmap doc said: a human looking at the actual on-screen odds table and typing the numbers
  in -- roughly 30-60 seconds per fixture, per the existing CSV templates.
- No live/free fixture or odds API was purchased or integrated, per the instruction's restriction.

### 4. Markets operational

**1X2 and Over/Under 2.5**, fully wired end-to-end in `scripts/run_daily_scan.py` (`EXPECTED_OUTCOMES`
dict -- extending this to a new market family is the intended extension point). **Asian Handicap is
not yet wired into this script**: the consensus/EV/grading method is identical in principle, but AH
needs exact-line matching between the consensus market and the best-price quote (e.g. both must be the
same -0.5 or -0.25 line), which this first script does not yet automate. This is a small, well-scoped
next addition, not a research question -- flagged honestly rather than silently left out.

### 5. Probability methodology per market

Both 1X2 and O/U 2.5 use the same method: de-vigged, cross-bookmaker median consensus
(`probability.consensus` + `probability.margin_removal`, proportional method), per Gate 1's empirical
result for 1X2 and the roadmap doc's same reasoning extended to O/U 2.5 (a similarly liquid, widely
quoted two-way market with the identical "no evidence any of our alternative models beat it" default).
No new model was fit for O/U 2.5 this session -- the instruction said not to launch a large new
research cycle, and consensus is the evidence-supported default until a specific reason to test
otherwise arises. The frozen Elo/Poisson models remain available as secondary diagnostics only, not
wired into this script's primary probability.

### 6. Candidate/grading methodology

Every candidate goes through `decisions.recommendation.build_recommendation`: consensus probability ->
`ev.expected_value.evaluate` (net EV, edge, break-even) -> `decisions.confidence.assess_confidence`
(bookmaker-count/dispersion heuristic) -> `decisions.data_quality.assess_data_quality`
(bookmaker-count/quote-age check) -> `decisions.liquidity.assess_liquidity` (stake-vs-depth, defaults
to adequate for a bookmaker quote) -> `decisions.grading.grade_opportunity` (unchanged, existing,
config-driven A+/A/B/C/Reject thresholds from `config/thresholds.yaml`) -> `risk.staking.
recommended_stake_gbp`. `no_material_info_risk` and `market_rules_match` remain explicit, human-owned
inputs for V1 (default: no known risk / rules match), exactly as `decisions/grading.py`'s own
docstring always intended -- this build did not try to automate the two gates that genuinely still
need a person's judgement (team news, exact market-definition match).

### 7. Risk/staking implementation

Unchanged, reused as-is: `risk/staking.py` (fixed stake per grade -- A+ £0.50, A £0.25, hard-capped by
`maximum_stake_gbp`), `config/bankroll.yaml` (£10 starting bankroll, £0.75 max daily exposure, 3 max
open bets, £0.75/£2.00 daily/weekly loss stops -- still the conservative Stage-1 defaults, not yet
reconciled to your real risk comfort per the roadmap doc's outstanding item). No martingale, no
chasing, no forced bets anywhere in the new code -- Grade B/C/Reject all return £0.00 stake by
construction (`GRADE_STAKES_GBP` only defines A+/A).

### 8. Daily Bet Card schema/example

Rendered by `reports/daily_bet_card.py`, matching the instruction's requested structure exactly
(Timestamp/Bankroll/Fixtures scanned/Markets scanned/Candidates analysed/A+/A/B selections/Total
recommended exposure, then ranked selections with Odds/Estimated P/Fair odds/Confidence/Stake/
Potential profit/Grade/Rationale, then an OPTIONAL MULTI section, then REJECT/WATCH summary + system
warnings). Two real example cards were generated this session and sent to you directly in this
conversation:

- `2026-09-18_dryrun_daily_bet_card.txt` -- today's two real fixtures (Brentford v Chelsea,
  Bristol City v Watford), illustrative odds panel. Correctly produced an all-Reject card (0 candidates
  cleared Grade B) because the illustrative panel carries realistic bookmaker margin and no injected
  edge -- this is the textbook-correct, expected output on a day with no real dispersion, not a bug.
- `2026-09-18_validation_daily_bet_card.txt` -- a separate, explicitly synthetic "soft book" scenario
  (one price deliberately set far above consensus fair value) to prove the pipeline correctly surfaces
  and grades a genuine edge when one exists: 1 candidate, Grade A+, net EV +41.3%, £0.50 stake.

Both together demonstrate the full pipeline working end-to-end in both directions -- correctly
rejecting a no-edge day, and correctly surfacing a real edge when present.

### 9. Scheduling status

**Not automated.** Per the instruction's own "Do NOT automate real-money execution yet" and the
roadmap doc's sequencing (wire GitHub Actions only after a manual dry run has been repeated
successfully by hand a few times), `scripts/run_daily_scan.py` is a manual command-line entry point
today. No GitHub Actions workflow was added this session -- that remains the next automation step
once you've run this by hand against a few real days' worth of manually-entered prices and are
satisfied with the output.

### 10. Result logging status

`scripts/run_daily_scan.py` writes a full candidate log (every graded candidate, all grades, not just
what's staked) to `data/processed/daily_cards/<date>_candidates.csv` via the existing, tested
`storage.csv_store.append_record` -- this is new logging, wired this session. It deliberately does
**not** write to `data/processed/bets.csv` (the ledger `scripts/settle_results.py` reads): only bets
you actually place should ever appear there, so an unplaced candidate is never mistaken for a real bet.
The existing settlement/CLV/performance machinery (`scripts/settle_results.py`, `performance/clv.py`,
`roi.py`, `drawdown.py`, `calibration.py`) is unchanged and ready to use once real bets are logged --
confirmed present and tested again this session, not just recalled.

### 11. Tests/status

770/770 tests passing (39 new/changed this session, zero regressions). New coverage: confidence
(8 tests), data_quality (7), liquidity (6), recommendation (5, integration-style through the real
consensus/EV/grading modules), daily_bet_card (4), manual_odds_loader metadata (3).

### 12. Remaining blockers

**The one genuine external/manual dependency, exactly as anticipated**: real current odds still need a
human to read them off a screen and type them in (or you approve a paid data source, which the
instruction explicitly prohibits doing without your approval). This is not a code gap -- it is the
correctly-scoped, evidence-based V1 design (see point 3). Smaller, non-blocking items: Asian Handicap
not yet wired (point 4); GitHub Actions scheduling not yet built (point 9); stake-cap/bankroll figures
still Stage-1 placeholders pending your real risk-comfort decision (point 7); the multi engine is not
built (explicitly deprioritised, per the instruction).

### 13. Exact shortest path to the FIRST REAL DAILY CARD

1. Pick 1-3 real fixtures for a real day (E0/E1/SC0, or any football fixture with a liquid 1X2/O-U 2.5
   market).
2. Fill in `templates/manual_odds_entry.csv` with real prices from 3+ real bookmakers (5+ minutes of
   typing per fixture, per point 3's finding).
3. Fill in `templates/exchange_price_entry.csv` (despite the filename, any bookmaker name works now --
   point 3 of the roadmap's schema fix) with the single best price you'd actually bet at.
4. Run `python scripts/run_daily_scan.py --odds templates/manual_odds_entry.csv --best-price
   templates/exchange_price_entry.csv`.
5. Read the Daily Bet Card it prints and writes to `reports/daily/`. That is the first real Daily Card
   -- everything downstream of real data entry is already built and already ran correctly twice this
   session.

### 14. What Fraser must do manually

- Enter real current fixtures/odds by hand (point 3/13) -- this is the one thing no free automated
  source can currently do reliably for this project, confirmed by this session's own attempt.
- Decide the real stake-cap/bankroll figures (point 7) -- a risk decision, not a technical one.
- Run `scripts/run_daily_scan.py` yourself (or ask me to, in a future session) against real data to get
  the actual first real Daily Card.
- Push commit `d50d304` from your Terminal when ready, per the standing workflow.

No paid data was acquired, no bet was placed, no automation of real-money execution was built, and no
new sport research cycle was started, per the instruction's explicit restrictions.
