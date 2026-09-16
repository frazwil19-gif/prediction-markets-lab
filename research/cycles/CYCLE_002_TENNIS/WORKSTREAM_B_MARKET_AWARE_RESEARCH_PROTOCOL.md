# Workstream B -- Market-Aware Research Protocol (Tennis)

**Written 2026-09-15, immediately after Tennis Cycle 1's 2025 holdout closed
with VERDICT: PARTIAL** (see `TENNIS_CYCLE_1_PRE_HOLDOUT_FREEZE.md` section
13). This document is a pre-registered protocol, not a report of results --
it exists to freeze *how* market-aware research will be conducted BEFORE any
real Betfair price data has been obtained, exactly as
`TENNIS_CYCLE_1_PRE_HOLDOUT_FREEZE.md` froze the modelling spec before 2025
was opened. No step below has been executed against real data; several
explicitly cannot be until Fraser completes the one manual action in
section 1.

## 0. The research question has changed

Tennis Cycle 1 asked: **can Global Elo's win probability generalise
out-of-sample?** That question is now answered (PARTIAL -- see the freeze
doc) and closed. It is not reopened here.

The project's tennis research question is now:

> **Does the frozen Global Elo probability identify systematic, out-of-sample
> mispricing relative to obtainable historical Betfair prices?**

This is a different, harder question. A model can have real predictive skill
(as Global Elo does, per the 2024 validation and the 2025 holdout's
favourable-but-inconclusive point estimate) while adding zero value here, if
the market already prices in everything Elo captures. Conversely a weaker
model can still be valuable if it reliably spots a specific pricing error the
market makes. The objective function for everything downstream of this
document is **pricing-error detection, not predictive accuracy for its own
sake.**

## 1. The one manual action Fraser must perform

Nothing in this document can be executed against real data until this
happens. Per the account-creation steps already documented in
`reports/research/TENNIS_HISTORICAL_ODDS_SOURCE_AUDIT.md`:

1. Standard signup at Betfair.com (no separate "historical data" account
   type exists).
2. Confirm jurisdiction is not one of the excluded list (Brazil, Italy,
   Spain, Romania, Sweden -- shouldn't affect Fraser).
3. Log into historicdata.betfair.com with the same credentials.
4. Select **Tennis**, a **small date range** (a single day or single small
   tournament -- NOT the full 2021-2025 range yet), and the **BASIC** (free)
   tier.
5. Download that small sample and place it somewhere in the repo's `data/raw/`
   tree, e.g. `data/raw/tennis/betfair_sample/` (create the directory if
   needed) -- or tell this session where it landed so it can be moved there.

That's it. No payment is needed for this step. Bulk 2021-2025 acquisition is
explicitly NOT the next step -- see section 2.

## 2. Small-sample audit plan (before any bulk acquisition)

Once a small real sample exists, the audit (not yet run -- there is nothing
to audit yet) will check, item by item, per the operator's explicit list:

- Event identity: event ID, competition/tournament name, scheduled start.
- Runner/player names: exact string format used for tennis (full name?
  "Surname I."? "Surname, First"? something else entirely?) -- this
  directly determines whether `normalisation/tennis_betfair_linkage.py`'s
  three supported name conventions (section 4 below) are sufficient or need
  a fourth.
- Market ID, runner/selection IDs, market type string (expected
  `MATCH_ODDS`, per the existing exclusion-list research, but confirmed
  here against a real file for the first time).
- Price timestamps: what publish-time granularity the file actually
  contains (this determines section 5's snapshot design -- see that
  section's explicit non-freezing of horizons until this is known).
- Last-traded price, and whether back/lay ladders (`batb`/`batl`) are
  present at the BASIC tier or only at paid tiers (the odds-source audit
  doc's understanding is BASIC omits volume but the audit doc flagged this
  as still not 100% certain for tennis specifically -- confirm here).
- Market status values actually seen (`OPEN`/`SUSPENDED`/`CLOSED` expected;
  confirm no undocumented values appear).
- Pre-match vs. in-play distinction (the `inPlay` field, if present at this
  tier).
- Winner/result representation (how a market's final settled state is
  recorded).
- Achievable historical coverage: does the free BASIC tier actually cover
  2021-2025, or a narrower window in practice?

`src/prediction_markets_lab/ingestion/betfair_historical_schema.py` is
already written and unit-tested against a hand-built, schema-conformant
fixture matching Betfair's *documented* Stream API format -- but its
docstring is explicit that this is UNVERIFIED against a real file. The audit
above is exactly what re-validates (or corrects) that module once real data
exists. Expect to find and fix discrepancies; that is the audit's job, not a
sign the module was wasted effort.

## 3. Bulk acquisition (only after the small-sample audit passes)

Not started, not specified in detail here -- deliberately, since its exact
shape (which date ranges, what file layout, what rate limits) depends on
what the small-sample audit finds about the real historical-data portal's
mechanics. A follow-up document or an addendum to this one will freeze that
once the audit is done.

## 4. Match linkage design (built now -- doesn't depend on price data)

Unlike price-timestamp granularity, match linkage only needs match identity
(date + players), which is already fully known from TML-Database. This has
therefore been built and unit-tested now, in
`src/prediction_markets_lab/normalisation/tennis_betfair_linkage.py`:

- `classify_tennis_betfair_match(tml_match, betfair_candidates)` returns
  exactly one of **MATCHED** / **AMBIGUOUS** / **UNMATCHED** per TML match --
  never a silent guess, per project instructions section 9. AMBIGUOUS means
  two or more Betfair events plausibly cover the same match (both are
  reported, neither is picked); UNMATCHED means no candidate's date and
  player pair line up.
- Matching requires both a date-proximity check (configurable tolerance,
  default plus-or-minus 1 day) and a player-pair identity check.
- Player-pair identity currently tries three known real-world tennis-name
  conventions: exact full-name match, Tennis-data.co.uk-style "Surname I."
  (reusing `normalisation/player_names.py`'s already-tested logic), and
  "Surname, First" comma-inverted form. **Which of these Betfair actually
  uses for tennis is unconfirmed** -- section 2's audit answers this, and a
  fourth convention can be added to `names_are_equivalent` if none of the
  three fit, without changing the MATCHED/AMBIGUOUS/UNMATCHED contract.
- `classify_all(...)` runs this over every TML match and groups results by
  status, so a coverage report always states all three counts (per the
  explicit instruction not to report match-rate without also reporting the
  ambiguous/unmatched rate).

This code is tested only against synthetic data mirroring the three
conventions above -- it has the same "unverified against real data" caveat
as the schema module, and both modules' docstrings say so explicitly.

## 5. Price-time snapshot design (deliberately NOT frozen yet)

The operator's explicit instruction: **do not freeze snapshot horizons until
real timestamp coverage/granularity has been audited** (section 2). Candidate
horizons on file as *examples only*, not a commitment: 24h, 6h, 1h, and
near-start/closing before scheduled match time. Once section 2's audit shows
what publish-time granularity the real files actually contain, this section
will be rewritten with a frozen, specific snapshot design -- and that design
will explicitly investigate whether model-market disagreement is stable or
decays as the match approaches start (if it decays, execution timing becomes
part of any eventual strategy, not an afterthought).

## 6. Market probability pipeline

Two pieces of this already exist and are reused unchanged, since they are
pure odds-to-probability math with no exchange-specific assumptions baked
in:

- `probability/odds_conversion.py` (`decimal_odds_to_implied_probability`,
  `overround`) -- works identically for a Betfair back price as for a
  bookmaker's odds.
- `probability/margin_removal.py` (`proportional_margin_removal`) -- works
  the same way once both runners' raw implied probabilities are known.

What is genuinely new for an exchange (not yet built, deliberately deferred
until real data is in hand, per the same "don't build against a guessed
schema" reasoning as section 5):

- **Lay-side probability.** A back price alone gives one implied
  probability; Betfair also has a lay price, and a genuinely tradeable
  "fair" probability likely needs both, not just 1/back_odds treated as
  automatically executable (the operator's explicit warning against this).
- **Exchange commission.** `ev/commission.py` already validates a flat
  commission rate; what's new is that exchange commission is charged on net
  winnings from a single bet, not embedded in the odds the way a
  bookmaker's margin is -- net EV math for a back bet on an exchange needs
  its own function, not a reuse of the bookmaker-odds net EV path in
  `ev/expected_value.py` without checking its assumptions first.
- **Liquidity/available-size and staleness.** Fields Betfair provides
  (`batb`/`batl` sizes, publish timestamps) that bookmaker odds data never
  had -- these need new fields in whatever record structure eventually
  holds a research observation (section 7), and probably their own
  data-quality checks (a price with negligible size behind it is not
  really "obtainable").

These are named here as known future work, not built speculatively against
an unconfirmed schema.

## 7. The eligible-match observation record (frozen shape, not yet populated)

Once real prices exist, each eligible match/snapshot combination should
resolve to one record containing, at minimum:

    timestamp                          (which pre-match snapshot, section 5)
    match_id                           (TML match_id)
    betfair_market_id                  (via section 4's linkage)
    linkage_status                     (MATCHED only; AMBIGUOUS/UNMATCHED excluded)
    player_a_name / player_b_name
    global_elo_p_a_win                 (the frozen Cycle 1 model, unchanged)
    betfair_back_price_a / _b
    betfair_lay_price_a / _b           (if available at this snapshot)
    market_probability_a / _b          (margin-removed, section 6)
    model_minus_market_probability     (the core "disagreement" signal)
    available_size_back / _lay         (liquidity at the quoted price)
    estimated_gross_ev
    estimated_net_ev                   (after commission, section 6)
    closing_price_a / _b               (for CLV analysis later)
    outcome_a_won

This is a shape, not code -- it will be implemented once sections 2-6 are
resolved against real data, so its exact field types match what Betfair
actually provides rather than a guess.

## 8. Data-first analysis discipline (before any threshold is chosen)

Per the operator's explicit instruction, the first pass over real
model-market disagreement data is NOT "backtest a betting rule." It is:
does model-market disagreement have any stable, chronological,
out-of-sample relationship with:

- realised match outcomes;
- subsequent closing-line movement;
- realised returns (net of commission) if a bet had been placed;
- market liquidity at the time of the snapshot;
- time-to-match (does the relationship hold at 24h but not at 1h, or vice
  versa);
- surface, tournament level, ranking gap, favourite/underdog status (the
  same subgroups already used throughout Cycle 1, for consistency).

This is exploratory, chronologically walk-forward, and reported honestly
even if the answer is "no stable relationship exists" -- exactly the same
discipline that produced Cycle 1's honest nulls (step D, calibration) and
its honest PARTIAL. **Any subgroup or pattern found during this exploration
is a new hypothesis requiring its own fresh, pre-registered validation split
-- never an immediately tradable rule**, per the same anti-cherry-picking
principle already applied throughout this project.

## 9. Requirements before any edge is promoted

A betting rule is not promoted on positive historical ROI alone. Before any
rule reaches even a paper-trading candidate, it must show, together:

- Positive net EV after realistic commission and slippage assumptions.
- Acceptable calibration of the underlying probability estimate.
- Positive CLV (the price obtained beats the eventual closing price, on
  average) -- ROI against opening prices alone proves nothing if the whole
  effect is explained by the market moving predictably afterward.
- Stability across a genuine chronological out-of-sample split (found on
  one period, confirmed on a later, untouched one) -- not just an in-sample
  correlation.
- A large enough sample that its uncertainty interval is informative, with
  that interval reported alongside the point estimate every time.
- Sensitivity to reasonable execution/slippage assumptions (does the edge
  survive if the achieved price is slightly worse than the quoted one).
- Acceptable drawdown and risk-of-ruin under the project's staking
  discipline (fractional-Kelly-style, per the project's standing rules --
  not covered further here, that's the risk/staking module's job).
- Adequate liquidity at the sizes actually contemplated.
- Stability across time -- not a pattern confined to one season or one
  tournament tier.

Brier score and log loss are tracked alongside betting-specific metrics
throughout, not replaced by them -- predictive quality and profitability are
reported as two related but distinct questions.

## 10. What this document does NOT authorise

This document freezes a research protocol. It does not authorise: bulk
Betfair data acquisition beyond one small audit sample (section 1-2); paper
trading; live betting; or a decision that Global Elo's disagreement with
Betfair prices contains money -- that is exactly the open question this
protocol exists to answer honestly, in either direction. Football Cycle 2
and any new tennis modelling cycle remain queued and unstarted, per the
operator's explicit "do not start another major research cycle yet"
instruction.

## 11. Status

- Section 1 (Fraser's manual action): **done, 2026-09-16** -- Betfair
  BASIC tennis sample downloaded, Jan-Sep 2026.
- Section 2 (small-sample audit): **done, 2026-09-16** -- see
  `WORKSTREAM_B_SAMPLE_AUDIT_REPORT.md`. Two real parser bugs found and
  fixed; real linkage test on 137 January 2026 ATP matches scored 100%
  MATCHED, 0% AMBIGUOUS, 0% UNMATCHED. BASIC tier judged sufficient for
  the next research phase (section 8); not sufficient for sections 6/9's
  net-EV/execution-cost work, which needs a paid tier -- that decision is
  not yet needed.
- Section 3 (bulk acquisition): Fraser's download already covers Jan-Sep
  2026 at BASIC tier; effectively done for this window at zero cost.
  Ground-truth coverage (TML-Database's own 2026 season file) currently
  only extends to mid-January -- an external data-source lag, not a
  project blocker; re-check periodically to extend validated coverage.
- Section 4 (match linkage): **built, unit-tested, and now validated
  against a real sample** (100% match rate on real January 2026 data,
  after fixing the market-type-filter and date-revision bugs found during
  that validation).
- Section 5 (snapshot design): deliberately not frozen; real per-message
  timestamp granularity is now known (BASIC updates whenever `ltp`
  changes or a market definition is revised, no fixed interval) -- still
  awaiting a deliberate decision, not yet made.
- Section 6 (market probability pipeline): back-price math reused from
  existing modules; lay/commission/liquidity extensions confirmed
  genuinely unavailable at BASIC tier, still not built, not needed for
  the next phase.
- Section 7 (observation record): **implemented and tested, 2026-09-16**
  -- see `WORKSTREAM_B_JANUARY_2026_OBSERVATION_REPORT.md` and
  `src/prediction_markets_lab/research/market_observation.py`. Real
  timestamp-density audit run on January 2026 (24h coverage only 47.8%;
  >97% from 3h before start onward). A descriptive Elo-vs-market pass at
  the best-covered horizon (30min) found no relationship worth promoting
  at N=136 -- recorded as an unvalidated candidate observation only, per
  section 8's discipline.
- Sections 8-9 (analysis discipline, promotion requirements): followed
  exactly for the January pass above; nothing promoted. A chronological
  validation-split proposal (2021-2025 discovery, 2026-onward holdout) is
  on file, not yet confirmed or executed.
- Bulk 2021-2025 acquisition: sized (~2.7GB, ~1.07M files estimated),
  still not started -- proposal only, awaiting Fraser's repeat of the
  BASIC download for those years.

## 12. Operator confirmation and decision tree (2026-09-16)

The operator reviewed this protocol and confirmed the direction: stop
building predictive models, treat the Betfair small sample as the single
blocking task, and do not parallelise into Football Cycle 2, another tennis
cycle, or cricket acquisition until one candidate (tennis) has been pushed
all the way through the funnel (Betfair -> market matching -> EV research ->
OOS -> paper-trading decision) and either dies at a gate or survives to
become a genuine candidate.

**Explicit test discipline added to section 2's audit**: once a real sample
exists, the goal is to deliberately try to break `betfair_historical_schema.py`
against it -- feed it every edge case the real file actually contains, not
just the happy path -- before any trust is placed in it. Fixes are made
against what the real file contains, not against the documentation alone.

**Decision tree for the small-sample outcome**:
- Sample parses cleanly and contains usable back/lay/liquidity/timestamp
  fields -> validate the parser and match-linkage coverage against it, then
  proceed to bulk historical ATP price acquisition (section 3).
- Sample parses but the free BASIC tier lacks required pricing fields (e.g.
  no lay side, no liquidity) -> assess whether what IS available is
  sufficient before considering any paid tier or alternative source; do not
  default to paying.
- Betfair historical data doesn't work for this purpose at all -> return to
  `reports/research/TENNIS_HISTORICAL_ODDS_SOURCE_AUDIT.md` and reopen the
  Kaggle/BigDataBall/OddsWarehouse candidates already on file there.

No branch of this tree authorises tennis model optimisation, paper trading,
or live betting.

**Illustrative target shape (not a specification, not built)**: the operator
described the eventual per-match decision output this pipeline is aimed at --
model probability, market price (back/lay), net EV after costs, historical
OOS sample size and CLV, liquidity, calibration status, and a
BET/WATCH/REJECT-style decision, with REJECT expected to be the overwhelming
majority of markets. This is recorded here as the north star for section 10's
eventual decision-engine architecture, not as anything to build now -- every
threshold and every field in it is still contingent on data this project does
not yet have.

**Fraser's manual actions restated (unchanged from section 1, operator
re-confirmed 2026-09-16)**: push this session's local commits to GitHub from
his own Terminal (this session never pushes); sign into Betfair and reach the
historical-data download screen; before selecting a paid tier or downloading
anything beyond the small BASIC free sample, send a screenshot of that screen
for a second look, since there is no reason to spend money at this stage.
