# Targeted Production Change -- Daily Money Window + Money/Paper Separation (2026-09-22)

Operator instruction: "TARGETED PRODUCTION CHANGE -- DAILY MONEY WINDOW
+ MONEY/PAPER SEPARATION," explicitly framed as a targeted engineering
change, NOT a rebuild of the production infrastructure built 2026-09-20
(`PRODUCTION_INFRASTRUCTURE_AUDIT.md`). This document is the KEEP/
MODIFY/ADD audit for that change plus its 13-point return checkpoint.

## Why

Fraser's own framing: high/strong probability + credible confidence +
statistical support + meaningful payout + acceptable value + acceptable
risk -- NOT "highest probability regardless of price" and NOT "any
positive-EV selection regardless of probability." Two real candidates
from the first live card (2026-09-20) were the concrete trigger: Ipswich
(away) v Manchester City at 14.00 (~7.8% estimated probability) and
Leeds (away) v Arsenal at 10.00 (~10.9%) -- legitimate research/paper
candidates, never something Fraser should risk real money on. The
existing A+/A/B/C/Reject grade conflated "statistically/EV-interesting"
with "bet Fraser should actually place"; this change separates them.

## KEEP / MODIFY / ADD

### KEEP (unchanged)
- `decisions/grading.py` -- the A+/A/B/C/Reject research classification
  and its thresholds. Never touched, never recomputed by the new gate.
- `decisions/payout_policy.py` -- the existing payout floor. Reused (not
  duplicated) by the new money-qualification gate for its own odds
  check, and for the Medium-confidence "preferred odds range" check.
- `decisions/confidence.py`, `decisions/data_quality.py` -- reused as-is,
  per the instruction's own "use the existing deterministic confidence/
  data-quality framework."
- `storage/paper_ledger.py`'s immutability model (`settle_paper_bet`,
  `_SETTLEMENT_FIELDS`) -- unchanged; the new `money_qualified` column is
  a core decision field like every other, never touched by settlement.
- `reports/daily_bet_card.py`'s `card.json`/`card.csv`/`card.md` contract
  -- unchanged in meaning; only additive trailing fields (see MODIFY).
- `.github/workflows/*.yml` -- no changes needed. `run_daily_scan.py`
  already writes everything from inside one script call; the workflows
  just commit whatever files exist under `daily_cards/`, which now
  includes `money_card.json`/`money_card.md` automatically.

### MODIFY (additive; full suite re-run after each)
- `config/thresholds.yaml` -- appended a `money_qualification` section.
  Nothing existing removed or renumbered.
- `ingestion/the_odds_api_loader.py` -- `market_metadata` now also
  carries the full ISO `commence_time` alongside the existing date-only
  `event_date` (untouched). This closes the KNOWN LIMITATION
  `storage/paper_ledger.py` already documented ("kickoff is currently
  only the fixture's date").
- `storage/schemas.MarketRecord` -- five new optional fields
  (`research_grade`, `money_decision`, `money_qualified`,
  `money_rejection_reason`, `kickoff_time`), all defaulted so every
  existing construction call keeps working.
- `decisions/recommendation.build_recommendation` -- two new optional
  kwargs (`money_qualification_thresholds`, `kickoff_iso`), applied
  AFTER the existing payout-floor demotion, so `research_grade` already
  reflects any payout-floor demotion exactly as `grade` always did.
- `reports/daily_bet_card.py` -- the candidate contract row and
  `_CSV_FIELDS` gained the five new fields, appended at the end (column
  POSITION for every existing field is unchanged).
- `storage/paper_ledger.py` -- one new trailing CSV column
  (`money_qualified`); `kickoff` now prefers the real timestamp when the
  scan supplied one, falling back to the date-only value otherwise (old
  rows are unaffected).
- `performance/paper_performance.py` -- every existing top-level key
  (`overall`, `by_grade`, `by_sport`, `by_competition`, `by_market`,
  `by_odds_band`, `pending_bet_count`, `current_paper_bankroll_gbp`)
  keeps its exact existing meaning: the broad paper-research universe.
  A new sibling key, `money_strategy`, mirrors the same shape computed
  only over money-qualified rows. The two are never combined.
- `reports/system_status.py` / `scripts/generate_system_status.py` --
  five new optional `SystemStatus` fields (`research_candidates`,
  `money_qualified_count`, `paper_money_pending`,
  `paper_research_pending`, `money_card_status`), populated from today's
  `money_card.json` and the paper ledger's money_qualified split.
- `scripts/run_daily_scan.py` -- loads the new config section, threads
  `kickoff_iso`/`money_qualification_thresholds` through every
  `build_recommendation` call, and writes `money_card.json`/
  `money_card.md` alongside the unchanged `card.json`/`card.csv`/
  `card.md`.

### ADD (new)
- `decisions/money_qualification.py` -- the deterministic money-
  qualification gate itself (`MoneyQualificationThresholds`,
  `assess_money_qualification`). See its module docstring for the full
  gate order and rationale.
- `reports/money_card.py` -- builds/renders/writes the Daily Money Card
  (`build_money_card_contract`, `render_money_card_markdown`,
  `write_money_card_outputs`), filtered from the already-built full
  contract; never recomputes probability/EV/grading/money-qualification.
- Test files: `tests/unit/test_money_qualification.py`,
  `tests/unit/test_recommendation_money_qualification.py`,
  `tests/unit/test_money_card.py`,
  `tests/unit/test_paper_ledger_money_qualified.py`, plus additions to
  `tests/unit/test_paper_performance.py`, `tests/unit/test_system_status.py`,
  and `tests/unit/test_the_odds_api_loader.py`.

## Money-qualification gate -- exact logic

`decisions/money_qualification.assess_money_qualification` checks, for
one already-graded candidate, in order (every failure recorded, not just
the first):

1. **Horizon**: `kickoff_iso` must be present, after `scan_timestamp_iso`,
   and within `event_horizon_hours` (default 24.0) of it. A missing
   kickoff (manual-mode scans) always fails this check -- a money bet is
   never approved on an unverifiable kickoff time.
2. **Research grade**: must be in `{A+, A, B}` (the existing actionable
   set) -- Reject/C are never money-eligible at all (`money_decision =
   "REJECT"`).
3. **Confidence**: "High" is eligible outright; "Medium" is eligible only
   if probability/value also clear a STRICTER floor (see below) and,
   optionally, odds sit inside `payout_policy`'s preferred range; "Low"
   is never eligible for real money.
4. **Data quality**: the existing mechanical `data_quality_ok` check must
   pass.
5. **Probability**: `estimated_probability >= min_probability` (default
   0.50 for High confidence, 0.60 for Medium).
6. **Payout/odds**: `decimal_odds >= payout_policy.normal_min_decimal_odds`
   (the existing 1.33 floor, reused, not duplicated).
7. **Value**: `net_ev >= min_net_ev` (default 0.02 for High confidence,
   0.05 for Medium) -- value is checked explicitly, never assumed from
   the research grade alone.

Result: `money_qualified: bool`, `money_decision: "BET"|"WATCH"|
"PAPER_ONLY"|"REJECT"`, `money_rejection_reasons: list[str]`. `"WATCH"`
is used only when every other requirement is strong and the sole failure
is the horizon (a fixture worth resurfacing as it approaches);
`"REJECT"` only when the underlying research grade itself was never
actionable; everything else is `"PAPER_ONLY"`.

## Configuration values (config/thresholds.yaml's money_qualification section)

```yaml
money_qualification:
  event_horizon_hours: 24.0
  min_probability: 0.50
  min_probability_medium_confidence: 0.60
  min_net_ev: 0.02
  min_net_ev_medium_confidence: 0.05
  eligible_confidence_labels: ["High"]
  conditional_confidence_labels: ["Medium"]
  require_preferred_odds_band_for_conditional_confidence: true
```

Every value is the operator's own initial, explicitly-NOT-assumed-optimal
starting point. None of this is hard-coded into the money-qualification
module itself -- `scripts/run_daily_scan.py`'s
`build_money_qualification_thresholds` reads this section, exactly
mirroring the existing `payout_policy` pattern.

## Paper vs money separation

`storage/paper_ledger.py`'s `paper_bets.csv` is still the single
append-only ledger (Grade A+/A/B threshold, unchanged) -- every research
candidate that clears the existing paper-bet threshold is still recorded
whether or not it passes money qualification, per the instruction
("do NOT stop recording useful research candidates merely because they
fail the money gate"). Each row now carries one additional column,
`money_qualified`, set once at creation time from
`decisions.money_qualification`'s result and never touched by
settlement (it is a core decision field like every other).

`performance/paper_performance.build_performance_report`'s existing
top-level keys are computed over the FULL ledger (the broad paper-
research universe) exactly as before this change. A new `money_strategy`
key mirrors the identical breakdown shape (`overall`, `by_grade`,
`by_sport`, `by_competition`, `by_market`, `by_odds_band`,
`pending_bet_count`) computed only over rows where `money_qualified` is
true. The two are never combined in any calculation -- a
`paper_universe_note` field states this explicitly in the JSON output
itself, so ChatGPT never has to infer it.

## Money-card schema and path

New, alongside (never replacing) the existing `card.json`/`card.csv`/
`card.md`:

- `daily_cards/<date>/money_card.json` -- machine-readable: header
  fields (bankroll, money horizon, fixture/candidate counts, recommended
  exposure), `best_bet` (top-ranked money-qualified candidate or null),
  `money_qualified_candidates` (the full list, same shape as
  `card.json`'s candidate rows), `optional_multi: null` (unbuilt, same
  convention as the full card).
- `daily_cards/<date>/money_card.md` -- the human/ChatGPT-readable
  Markdown card in the operator's specified format, including the
  literal `NO MONEY BETS QUALIFIED TODAY` message (with a one-line
  explanation) when the list is empty -- never a fabricated bet, and
  thresholds are never loosened to manufacture one.

## Example: empty money card

```
DAILY MONEY CARD -- 2026-09-22

Bankroll: £10.00
Money horizon: next 24h
Fixtures scanned: 32
Research candidates: 158
Money-qualified bets: 0
Recommended exposure: £0.00

NO MONEY BETS QUALIFIED TODAY

158 candidate(s) analysed; none satisfied the combined horizon/probability/confidence/payout/value/risk gate. Thresholds are never loosened to manufacture a bet.
```

## Tests

37 new tests added (852 -> 889), covering every named scenario in the
operator's Section 14: kickoff inside/outside/past the horizon; timezone
handling (Z-suffix, naive, non-UTC offset); a low-probability high-odds
longshot staying research/paper-only; a high-probability tiny-payout
candidate failing the payout gate; a high-probability acceptable-payout
candidate qualifying; a low-confidence candidate never qualifying (and a
Medium-confidence candidate qualifying only when every other requirement
is strong); a negative-value high-probability candidate failing;
research grade preserved after a money rejection; a money card
containing only money-qualified candidates; paper-research and paper-
money performance computed and reported separately; and an empty money
card being valid output. No existing test was weakened -- the full
existing suite (852 tests) still passes unchanged, and the manual
`_row`/`_build`/`_common_kwargs`-style helper conventions already used
throughout `tests/unit/` were followed rather than introducing a new
style.

## Commissioning (Section 15)

1. Full suite: 889/889 passed.
2. `scripts/run_daily_scan.py --source manual` run locally (no secrets
   involved) against a constructed 5-bookmaker fixture -- confirmed
   `money_card.json`/`money_card.md` are written alongside the unchanged
   `card.json`/`card.csv`/`card.md`, with every new field present and
   correctly populated (verified via direct JSON/CSV inspection); no live
   Odds API credits were spent.
3. A representative fixture set (near-term qualifying vs weeks-away vs
   longshot vs low-confidence vs negative-EV) was exercised through
   `decisions.money_qualification` and `decisions.recommendation`
   directly in the test suite (see Tests above) rather than spending
   live API credits on a second manual scan -- this is stronger,
   repeatable evidence than one more ad hoc dry run.
4. Confirmed (by test and by direct module logic) that a fixture weeks
   away from the scan timestamp never appears in `money_qualified_candidates`
   regardless of grade/probability, while still being retained in the
   full `card.json`/paper ledger.
5. Confirmed a low-probability high-odds longshot (the Ipswich/Leeds-
   style example) is never money-qualified regardless of its EV.
6. No existing threshold (grading, payout floor, data quality,
   confidence) was loosened anywhere in this change.

## Blockers

None. This change needed no new external dependency, credential, or API
call.
