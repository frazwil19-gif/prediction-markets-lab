# Player SOT A / B / C market comparison — PRE-REGISTRATION FRAMEWORK

Written 2026-10-02, before any confirmatory Player SOT market data has been captured. The only Betfair
observation so far is the 2026-10-02 schema discovery: structure only, with no probabilities used.

**Status: FRAMEWORK. NOT ACTIVE.** It becomes a binding pre-registration (with the final numbers below confirmed and
committed) only after both of these:
1. modern Model A passes Cycle 2 (`player_sot/cycle2/PREREGISTRATION.md`, MODERN_VALIDATED);
2. the 10 October / later captures establish target-league Betfair SOT coverage and liquidity.

Any numeric gate still marked TBD below is fixed only from **non-outcome** liquidity data (spreads, sizes,
availability), never from match results or returns.

## Models
- **A:** the modern sports-only Player SOT model (Cycle 2 frozen). No odds of any kind.
- **B:** the Betfair market probability for each player and target (1+ and 2+), built per §1.
- **C:** logistic stacking, logit p_C = b0 + b1·logit p_B + b2·logit p_A.
  - Fitted on the first FIT block of eligible player-observations, in chronological event order. FIT is the first
    150 events, with all eligible players in them.
  - Then frozen with its SHA and applied unchanged afterwards.

## 1. Constructing B from Betfair back/lay (no invented probabilities)
- **Structure:** each player is one runner in `SHOTS_ON_TARGET_P1` or `SHOTS_ON_TARGET_P2`. That runner is a yes/no
  proposition: back means "yes", lay means "no". There is no cross-runner overround to remove; each runner stands
  alone.
- **B per runner:** p_B = 1 / mid, where mid = 2 / (1/back + 1/lay), using the best available back and lay.
- **B exists only if all of these hold:**
  - both back and lay exist;
  - spread lay/back − 1 ≤ S_max;
  - each side's available size ≥ size_min;
  - the quote snapshot is ≤ 5 minutes old at capture;
  - the market status is OPEN and not in-play.
- **One-sided runners** (back-only or lay-only) get NO B. They are counted as "no market probability" and never
  imputed.
- **Commission:** irrelevant to B, which is a probability. It applies only to executable net odds in the later
  financial study (Betfair rate from `config/bet_selection_v2.yaml`).
- **Lineups:** only confirmed starters at capture are eligible.
  - The capture happens after the official lineup is published, at about T−60 to T−5 minutes.
  - Substitutes and unconfirmed players are excluded.
- **Primary snapshot:** the latest capture ≥ 5 minutes before kickoff. Captures after kickoff are never used.
- **TBD from liquidity data only** (fixed before any outcome is joined):
  - S_max;
  - size_min;
  - minimum market matched.

  Rule for setting them: choose the values that keep roughly ≥ 50% of two-sided target-league runners, as observed in
  the 10 October and following liquidity captures. They are committed before outcomes are attached.

## 2. Unit, metrics, uncertainty
- **Unit:** player × target at the primary snapshot. The primary target is 1+.
- **Metrics:**
  - log loss (primary);
  - Brier;
  - calibration intercept and slope;
  - reliability bands;
  - N;
  - league, position and temporal breakdowns.
- **Uncertainty:** event-cluster bootstrap (2,000 resamples, seed 7), because players within a match are dependent.

## 3. Confirmatory tests (EVALUATION block = all events after FIT)
1. **A vs B:** Δ = LL(A) − LL(B). A wins iff the CI upper bound is < 0.
2. **C vs B:** Δ = LL(C) − LL(B). C wins iff the CI upper bound is < 0. This is the incremental information of A
   given B. The FIT-block likelihood-ratio test for b2 is reported.
3. **Stability (for any positive verdict):**
   - the same sign in ≥ 60% of leagues with ≥ 30 events;
   - the same sign for DF, MD and FW groups with n ≥ 300.
- **Evidence trigger:** ≥ 300 evaluation events with ≥ 1 eligible two-sided starter, plus INTERIM at 150 (reporting
  only, except an early null).
- **ROI is never used** to choose between A, B and C.

## 4. Decision tree
- **A beats B, or C beats B, robustly:** go to a separately pre-registered PROSPECTIVE_SHADOW financial study:
  - best executable net back odds (commission applied);
  - uncertainty-adjusted EV;
  - available-size and liquidity limits;
  - correlation across players in the same match;
  - no stakes.
- **Neither:** reject sports-only Player SOT as an independent edge source and record the null.
- **Paper betting and money:** each requires explicit approval from Fraser.

## 5. Capture tool
`python3 scripts/betfair_catalogue_audit.py --capture --max-hours-to-kickoff <h>`
- Gives per-runner back, lay, sizes, spread, side status, market matched and minutes to kickoff for corners, player
  SOT and cards in the project's leagues.
- Must run on Fraser's Mac (Betfair blocks US runner IP addresses).
- Raw per-runner prices stay private in `raw/` (gitignored). Only aggregates are committed.

## Addendum (2026-10-02): B construction is NOT yet frozen
This addendum supersedes §1's working definition of B. §1's definition is the candidate primary estimator, not a
final choice. It must be confirmed or replaced, and frozen, BEFORE any confirmatory A/B/C evidence is examined, using
mechanics and non-outcome microstructure data only.

**Contract mechanics, to be verified from the 10 October capture fields `number_of_winners` and `betting_type` and
from Betfair rules:**
- Each player is a single runner in a multi-winner market. Expected: `numberOfWinners` > 1, or each runner settles
  independently.
- There is no separate "No" runner. Backing the runner means "player records ≥ k SOT"; laying it means "player does
  not". If the capture shows a different structure, B is redefined accordingly before activation.
- Runner prices in such a market do not sum to 1 across players. B is therefore a per-runner probability with no
  cross-runner de-vig.

**Midpoint definitions (all computed; primary chosen before activation):**
- probability-space midpoint: p = (1/back + 1/lay) / 2. This is the current §1 candidate, since 1/[2/(1/b + 1/l)] is
  the same quantity.
- odds-space midpoint: p = 1 / ((back + lay) / 2);
- size-weighted microprice: p = (1/back·lay_size + 1/lay·back_size) / (back_size + lay_size);
- last traded price, as a diagnostic only.

**Selection rule for the primary B, fixed now and using no outcomes:**
- Probability space is the default, because B is evaluated with log loss and Brier score in probability space.
- Sensitivity is reported as the distribution of |p_method − p_primary| per runner.
- If the median absolute difference between methods is ≥ 0.02 on the target-league captures, every A/B/C result is
  reported under each method as well. The verdict still uses only the primary.

**Commission:** never enters B. It affects only executable net odds.

**One-sided, stale or suspended quotes:** no B, as in §1.

**Spread and size gates:** characterised from the 10 October and later captures (non-outcome data), then frozen
before outcomes are joined.
