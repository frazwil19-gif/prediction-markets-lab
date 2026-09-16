# Football Cycle 2 — Direction Change: Data-First Market-Inefficiency Discovery

**Date:** 2026-09-16
**Authority:** Operator direction change, relayed by Fraser, extended by Fraser's own
explicit instruction that the framework below is not football-only — it is adopted as
the project's standing, reusable cross-sport methodology. This report supersedes the
acquisition-first framing of `FOOTBALL_CYCLE_2_INITIATION_REPORT.md` (2026-09-16,
earlier the same day). Nothing in that report's factual findings (Cycle 1 result,
reusable assets, xG coverage gap) is discarded — this report re-derives the plan
around them using the new discovery-first philosophy.

**Companion document:** `research/RESEARCH_FRAMEWORK_MULTI_SPORT.md` — the generalised,
sport-agnostic version of sections 4 and 6 below, written per Fraser's explicit
instruction that this process governs tennis and cricket too, not only football.

**Status: NO ACQUISITION HAS STARTED.** This report is read-only research and
planning against the existing repository plus external literature/data-source
research. Per the operator's explicit instruction, this precedes any xG, weather, or
new acquisition work.

---

## 0. What changed and why

Football Cycle 1 (`STAGE_3B_FINAL_REPORT.md`) tested whether simple public-data models
(Elo, Poisson, blends) beat closing Match Odds. They didn't — the best candidate
(`elo_poisson`) lost to the market by a log-loss delta of +0.0169, 95% CI
[+0.0066, +0.0274], entirely above zero. The `FOOTBALL_CYCLE_2_INITIATION_REPORT.md`
written earlier today treated the next step as "acquire a new information source
(xG) and test whether it beats the market" — the same shape of test that Cycle 1 ran,
with a different feature.

The operator's direction change rejects starting from an assumed-useful statistic at
all. The instruction: do not decide in advance that xG, shots-on-target, corners, or
handicaps contain the edge. Instead, run this project's own strongest process — the
one used in the quant/algo-trading side of the project — for football (and, per
Fraser's addition, for every sport going forward):

```
OBSERVE DATA -> AUDIT DATA -> DISCOVER BEHAVIOURS -> FORM HYPOTHESES ->
BACKTEST -> OUT-OF-SAMPLE VALIDATE -> PAPER TRADE -> SMALL LIVE VALIDATION ->
SCALE ONLY IF EDGE PERSISTS
```

Two things follow from this that are not just relabelling:

1. **A market/statistic without a matching historical price cannot produce a
   betting hypothesis, no matter how predictive it is.** Section 1 below applies
   this as a hard gate before anything is ranked.
2. **The single most important finding of today's audit is not about xG.** It is
   that this project already possesses match statistics (shots, shots-on-target,
   corners, fouls, cards) and additional market prices (Over/Under 2.5 goals, one
   Asian Handicap line, both opening and closing, across all three competitions and
   all five seasons) that were downloaded during Cycle 1's acquisition but never
   extracted into the processed dataset. This is a zero-cost, zero-new-acquisition
   discovery opportunity that existed in the repository the whole time. See §1.2
   and §6.

---

## 1. Market Availability × Data Availability Audit

### 1.1 Method and the hard gate

Per the operator's instruction, no market is scored until it clears a hard gate:
**does a historical OUTCOME/STATISTIC series exist, AND does a historical PRICE
series exist, for the same matches?** A market that fails this gate cannot support
an EV calculation and is recorded as **NOT RESEARCHABLE FOR BETTING EV YET** —
though it may still be researchable as a *feature* that helps price a market that
does clear the gate (e.g. corner counts as an input to an Asian Handicap model,
even with no corners-market price to bet against).

Gate status key: **CLEAR** (both sides confirmed and already in hand or cheaply
obtainable), **PARTIAL** (one side confirmed, the other unconfirmed/thin/scrape-only),
**BLOCKED** (no known bulk price archive at all, free or paid).

### 1.2 What is already in hand — the headline finding

Direct inspection of the raw Football-Data.co.uk files this project downloaded for
Cycle 1 (`data/raw/football/football_data_co_uk/{E0,E1,SC0}/<season>/*.csv`) shows
they contain far more than what Cycle 1's canonicalisation pipeline extracted.
Spot-checked on `E0/2023_24/E0.csv` (380 matches): every one of `HC`, `AC` (corners),
`HST`, `AST` (shots on target), `HS`, `AS` (shots), `HF`, `AF` (fouls), `HY`, `AY`,
`HR`, `AR` (cards), `Referee`, `AHh`/`B365AHH` (Asian Handicap line and price), and
`B365>2.5`/`B365C>2.5` (Over/Under 2.5, opening and closing) is **100% populated**
(380/380 rows), for all three competitions, confirmed identical schema across
2020/21-2024/25 (minor bookmaker-column additions in later seasons, e.g. `1XBH`,
`BFEH`, do not affect the columns above).

`src/prediction_markets_lab/ingestion/football_data_loader.py` (the acquisition
module) only downloads and hashes the raw files — it does not parse match statistics
at all. The canonicalisation step that produced `cycle_001_matches_full.csv` (5,800
rows: match identity, date, teams, `full_time_result`, bookmaker counts) and
`cycle_001_bookmaker_markets_full.csv` (49,673 rows: 1X2 home/draw/away odds at
opening and closing only) confirms, by its own column headers, that it never touched
`HC/AC/HST/AST/HS/AS/HF/AF/HY/AY/HR/AR/Referee/AHh/B365AHH/B365>2.5/B365C>2.5`.

**This means shots, shots-on-target, corners, cards, fouls, and referee identity —
for every match in the existing 5,800-match dataset — are sitting on disk, already
downloaded, already hashed, fully populated, and have simply never been extracted.**
So are Over/Under 2.5 and (single-line) Asian Handicap prices, at both opening and
closing, from the same bookmakers already used for 1X2. Re-extracting them is a
canonicalisation-code change, not an acquisition — zero new network access, zero new
cost, zero new provenance risk (the raw files are already hashed and frozen under
`cycle_001_v1.0.0-20260910T234139`).

### 1.3 Per-market audit

**Match Odds / 1X2 — CLEAR (already fully processed).** Outcome: `FTR` in the raw
files. Price: multi-bookmaker (`B365`, `BW`, `PS`=Pinnacle, `WH`, plus others added
in later seasons), opening and closing, already canonicalised into
`cycle_001_bookmaker_markets_full.csv`/`cycle_001_consensus_full.csv`. 5,800 matches,
2020/21-2024/25, E0/E1/SC0. This is what Cycle 1 already tested and found dominated
by the market. Free. Already acquired. CLV note: only `proxy_clv`
(opening-to-closing bookmaker movement) is available, never `true_execution_clv`
(no exchange time series exists) — this project already has a dedicated document
enforcing that distinction, `docs/HISTORICAL_PRICE_AND_CLV_LIMITATIONS.md`.

**Over/Under 2.5 goals — CLEAR (in hand, unextracted).** Outcome: total goals,
derivable from `FTHG`+`FTAG`, already in the raw files. Price: `B365>2.5`/`B365<2.5`
(and closing `B365C>2.5`/`B365C<2.5`), confirmed 100% populated, same 5,800-match
coverage. Free, zero new acquisition. Single line only (2.5) — no 1.5/3.5 lines in
this source (confirmed by external survey, §2). Extraction is the only new work.

**Asian Handicap (single line) — CLEAR (in hand, unextracted).** Outcome: goal
margin, derivable from `FTHG`-`FTAG`. Price: `AHh` (the line) + `B365AHH`/`B365AHA`
(opening) + `B365CAHH`/`B365CAHA` (closing), confirmed 100% populated, same
coverage. This is exactly the market the operator flagged as most likely to hide
"magnitude of dominance" mispricing (§3) — and it is **already fully paid for and on
disk**, just one handicap line per match rather than a full ladder. Free, zero new
acquisition.

**Match statistics as features (shots, SOT, corners, fouls, cards) — CLEAR as
features, BLOCKED/PARTIAL as their own tradable markets.** The raw counts are fully
in hand (§1.2) and free to extract. But a corners-count statistic is not the same
thing as a corners-market price: today's external survey (§2) found no confirmed,
reliable bulk historical price archive for corners or cards markets (Betfair's
Exchange Rules confirm such markets have existed, but no source confirms sustained
historical coverage in the downloadable archive, and there are indications Betfair
has trimmed thin-liquidity football markets over time). **Practical consequence:**
shots/SOT/corners/cards can be used *now*, at zero cost, as candidate explanatory
features for the markets we do have prices for (1X2, O/U 2.5, AH) — e.g. "does a
team's shot-quality superiority predict a bigger margin than the Asian Handicap line
implies?" — but cannot yet be tested as their own betting markets, because we cannot
compute EV against a corners or cards price. Referee identity is in the same
"free feature, not yet a market" bucket (no referee-market prices exist).

**Both Teams To Score (BTTS) — PARTIAL/BLOCKED.** Confirmed absent from
Football-Data.co.uk (verified directly against `notes.txt`). Outcome is
computable from goals already in hand. Price: plausible on Betfair's exchange
(BTTS is a live Betfair market) but not confirmed present/complete in the
downloadable historical archive; otherwise viewable only per-match on
OddsPortal/BetExplorer with no bulk export. **Not acquirable today without either
an unconfirmed Betfair check or scraping against sites whose terms likely restrict
bulk use** — the latter is not something this project does.

**Draw No Bet — BLOCKED.** No dedicated bulk historical price archive found,
free or paid. Viewable per-match on odds-comparison sites only. Derivable in
principle from 1X2 prices already in hand (DNB is a mechanical transform of 1X2
odds with the draw stake refunded) — meaning a *proxy* DNB price can actually be
computed from data already in hand, even without a dedicated DNB archive. Worth
noting as a "free by construction" market for exactly this reason.

**European Handicap — BLOCKED.** No known bulk historical archive, free or paid,
found anywhere. Not researchable.

**Multi-line Over/Under (1.5, 3.5, etc.), multi-line Asian Handicap, Correct
Score — PARTIAL, Betfair-dependent.** Confirmed present in Betfair's Historical
Data (BASIC/free tier) for Over/Under across several lines and for Correct Score,
based on a third-party walkthrough and a dedicated community tool respectively.
Multi-line Asian Handicap and BTTS are plausible on Betfair (both are listed
current Betfair markets, and the historical archive is described as covering
"nearly all markets offered on the Exchange") but not independently confirmed. This
would require the same kind of account/download step Workstream B already used for
tennis (BASIC tier, free) — **a genuinely new acquisition**, not a re-extraction,
and would need its own coverage-confirmation pass before any commitment, mirroring
the "audit before acquire" discipline used throughout Workstream B.

**Team goals, Clean sheets, Winning margin (as its own market, distinct from AH),
Player shots/SOT props — BLOCKED.** No known bulk historical price archive, free or
paid, found for any of these. Winning margin as a *concept* is well covered by the
Asian Handicap line already in hand (an AH line is, functionally, the market's
statement about expected margin) — a dedicated "winning margin" market would be
additive at best, not a new capability. Player shot props are confirmed to barely
exist as a live market at all (Betfair only trialled adjacent player props — First
Goalscorer, Player To Score — from March 2025) — there is essentially no historical
price data to acquire even in principle.

**xG / shot-quality data — PARTIAL, coverage-gated (carried over from the earlier
initiation report).** Outcome/stat: confirmed present via FBref for the Premier
League (E0), confirmed absent for the Championship (E1); Understat excludes both
the Championship and Scottish Premiership. Price: none of its own (xG is not a
bet-able market) — it would only ever be a feature for the markets already in
hand (1X2, O/U 2.5, AH). Because it requires new scraping infrastructure, is
coverage-gated to E0 only pending confirmation, and adds a feature rather than
unlocking a new tradable market, it is **not** the first thing to acquire under
this new discovery-first ordering — see §6.

**Weather, fixture congestion/rest — CLEAR as features (not markets).** Same
status as before: fixture congestion is a zero-cost feature engineering exercise on
data already in hand; weather is a free Open-Meteo API call away, needing a
one-time stadium-coordinate table. Neither is a market, both remain candidate
features for the markets that are already gated CLEAR.

### 1.4 Audit summary table

| Market/family | Outcome data | Price data | Gate | Cost to use | Notes |
|---|---|---|---|---|---|
| Match Odds (1X2) | In hand | In hand | CLEAR | £0 (already processed) | Cycle 1 already tested this — market dominates |
| Over/Under 2.5 goals | In hand | In hand, unextracted | CLEAR | £0 (extraction only) | Single line only |
| Asian Handicap (1 line) | In hand | In hand, unextracted | CLEAR | £0 (extraction only) | Best-suited existing market for Dominant-Side Mispricing (§3) |
| Shots/SOT/corners/cards/fouls/referee | In hand, unextracted | N/A (feature, not a market) | CLEAR as feature | £0 (extraction only) | Cannot become their own tradable markets without new price acquisition |
| BTTS | Derivable from goals | Unconfirmed/thin | PARTIAL | Unknown, needs Betfair coverage check | No Football-Data coverage |
| Draw No Bet | Derivable | Computable proxy from 1X2 | CLEAR (proxy) | £0 | Mechanical transform, not a separate archive |
| Multi-line O/U, multi-line AH, Correct Score | Derivable/scoreline | Confirmed present on Betfair (O/U, Correct Score); AH multi-line plausible | PARTIAL | New acquisition (Betfair BASIC, free tier, real effort) | Would mirror Workstream B's tennis approach |
| European Handicap, team goals, clean sheets, winning margin (standalone), player shot props | Mostly derivable | BLOCKED — no known archive | BLOCKED | N/A | Not researchable now |
| Corners/cards as their own markets | In hand (counts) | BLOCKED/unconfirmed | BLOCKED for EV | N/A | Usable only as features on other markets |
| xG / shot quality | PARTIAL (E0 only likely) | N/A (feature only) | PARTIAL | New scraping infra | Coverage check needed before commitment |
| Weather | N/A | N/A (feature only) | CLEAR as feature | £0 (Open-Meteo) | Needs stadium-coordinate table |
| Fixture congestion/rest | In hand | N/A (feature only) | CLEAR as feature | £0 | Pure feature engineering |

---

## 1.5 Research-Priority Matrix (scored)

Formula defined in full, with worked derivation, in
`research/RESEARCH_FRAMEWORK_MULTI_SPORT.md` §2 (the general, sport-agnostic
version). Summary of the method: **Score = Gate × Σ(weighted sub-scores) −
Σ(weighted penalties)**, where Gate ∈ {0, 0.5, 1} per §1.1 (0 = BLOCKED, 0.5 =
PARTIAL, 1 = CLEAR) and multiplies the whole score — a family that cannot
support an EV calculation cannot outrank one that can, no matter how appealing
its other factors look. Sub-scores and penalties are each rated 0-5 by the
undersigned research process against the stated evidence, not intuition; every
score below states the evidence it is based on so it can be audited line by line.

| Family | Gate | Sample size (0-5) | Data quality (0-5) | Mechanism plausibility (0-5) | External evidence (0-5) | EV-measurable (0-5) | Acquisition cost (0-5, lower=cheaper) | Leakage risk (0-5, lower=safer) | **Weighted score** |
|---|---|---|---|---|---|---|---|---|---|
| 1X2 (already tested) | 1.0 | 5 (5,800 matches) | 5 (fully audited, Cycle 1) | 3 (Cycle 1 already found null) | 4 (strong FLB/overreaction literature) | 5 | 5 (already in hand) | 1 | **Re-test only inside new features, not alone — already REJECTed as a standalone model in Cycle 1** |
| Over/Under 2.5 + match-stat features | 1.0 | 5 | 5 (spot-checked 100% populated) | 4 (shots/SOT literature is the strongest evidence base found, §2) | 4 | 5 | 5 (extraction only) | 2 (lag discipline needed) | **21/25 — highest-ranked actionable family** |
| Asian Handicap + Dominant-Side Mispricing | 1.0 | 5 | 5 | 4 (direct match to the operator's priority question, but weakest literature support, §2) | 2 (magnitude-mispricing literature is thin) | 5 | 5 (extraction only) | 2 | **19/25 — second-ranked, and the pre-registered priority family** |
| Recent-form/outcome-bias (`proxy_clv`-adjacent) | 1.0 | 5 | 5 | 5 (two independent peer-reviewed studies, §2) | 5 | 5 | 5 (feature engineering only) | 2 | **23/25 — highest literature support of any family, zero new cost** |
| Fixture congestion/rest | 1.0 | 5 | 5 | 3 (sports-science evidence for injury/fatigue; no market-pricing evidence, §2) | 2 | 5 | 5 (zero cost) | 2 | **18/25** |
| Weather | 1.0 | 5 | 4 (needs stadium-coordinate table) | 1 (best available evidence suggests no effect to price, §2) | 1 | 4 | 4 (one API integration) | 2 | **12/25 — deprioritised on the evidence, not on cost** |
| Referee tendency | 1.0 | 4 (fewer distinct referees than matches) | 4 | 2 (no direct literature found) | 1 | 4 | 5 (feature from data in hand) | 3 (tendency stats need careful lagging) | **13/25** |
| xG / shot quality | 0.5 (E1/SC0 coverage unconfirmed) | 3 (E0 only, pending check) | 3 (retrospective-revision risk noted in the earlier report) | 4 | 3 (2026 study shows only a modest residual edge) | 4 | 2 (new scraping infra) | 3 | **~9/25 after the 0.5 gate — correctly ranked below every zero-cost family above** |
| BTTS / multi-line AH / multi-line O-U / Correct Score (Betfair) | 0.5 (coverage unconfirmed) | 3 | 2 (unconfirmed depth/continuity) | 3 | 2 | 3 | 2 (new account/download effort) | 2 | **~7/25 after the 0.5 gate** |
| Corners/cards as standalone markets | 0 (BLOCKED — no confirmed price archive) | — | — | — | — | 0 | — | — | **0 — cannot support an EV calculation today** |
| European handicap, team goals, clean sheets, winning margin (standalone), player-shot props | 0 (BLOCKED) | — | — | — | — | 0 | — | — | **0** |

This produces the same ordering as §6's prose recommendation by construction
(extraction-based families cluster at the top on cost and evidence; anything
gated below 1.0 is mechanically suppressed regardless of how interesting it
looks) — the matrix is a transparency device to let the ranking be audited, not
a separate opinion.

## 2. External Football Market-Inefficiency Literature Review

Full literature review conducted via web search across academic/industry sources;
this section is a condensed synthesis. Per the operator's instruction, this is used
to generate candidate questions, not treated as proof anything will replicate in
this project's own data. Every claim below is external evidence, clearly separated
from this project's own (currently zero, for these markets) empirical findings.

**Areas with genuinely strong, convergent, peer-reviewed evidence:**

- **Favourite-longshot bias exists in 1X2, is absent in Asian Handicap.** Whelan
  et al. (*Review of Behavioral Finance*, 2024, 84,230 matches/22 leagues
  2011-2022 plus a Pinnacle sample) and the companion CEPR/VoxEU piece both find
  clean FLB in 1X2 and none in AH, attributed to AH being a lower-margin,
  professional-friendly ("sharp") market. Directly relevant: our AH data (§1.3) is
  the market the literature says is *already* efficient on this specific bias —
  a reason not to expect an easy FLB-style edge there, but not a reason to skip AH,
  since the same literature finds a *different* AH inefficiency (below).
- **Asian Handicap has a documented, mechanism-explained inefficiency around
  handicap sub-type, not win probability.** The same Whelan et al. paper finds
  bettors lose money at different rates depending on whether the AH line is a
  whole-goal (refundable), half-goal (no refund), or quarter-goal (split-stake)
  line — a genuine, recent (2024), mechanism-backed finding, not lore.
- **Markets overreact to recent form / "outcome bias."** Two independent,
  peer-reviewed, large-sample studies converge: Wheatcroft (*Journal of
  Quantitative Analysis in Sports*, 2019/2020, 136,011 matches/20 leagues,
  2005/06-2017/18) finds teams that recently underperformed relative to their
  own odds-implied expectation get systematically more generous odds afterward;
  Flepp, Merz & Franck (*Economic Inquiry*, 2024) use xG as a "luck-adjusted"
  benchmark and find betting-exchange prices overrate teams that recently
  overperformed relative to xG and underrate those that underperformed. This is
  the single best-evidenced "beat the market" finding in the whole review and
  does not require any new data acquisition to test — it only needs rolling
  recent-form/recent-luck features against the odds we already have.
- **Betting exchanges price at least as accurately as fixed-odds bookmakers.**
  Established in the academic literature (Franck, Verbeek & Nüesch, *International
  Journal of Forecasting*, 2010, and later in-play work). Relevant mainly as
  background: this project's football consensus benchmark uses bookmaker closing
  prices (no exchange history exists for football, per Cycle 1's
  `DECISION_LOG.md` H-FB-003), so the benchmark is a slightly softer target than
  an exchange close would be — a point already understood, not new.
- **Home advantage collapsed during closed-doors COVID football, and bookmakers
  were briefly slow to reprice it.** Multiple studies (Bundesliga ghost-games
  natural experiment, arXiv 2020; Fischer & Haucap, *Kyklos*, 2022) find a
  real, short-run, since-resolved inefficiency. Not exploitable today (the
  correction happened years ago), but methodologically useful: it shows the
  project's own home-advantage feature should be checked for period-stability
  rather than assumed constant.
- **Shots-on-target adds predictive information beyond odds-implied probability**
  (Wheatcroft, *Journal of Sports Analytics*/arXiv, 2021, 22 leagues,
  2000/01-2018/19, 49,884 matches) — but the same paper reports the edge shrinking
  over its sample, i.e. a fading, not permanent, signal. Directly actionable: this
  is exactly the shots/SOT data already sitting unextracted in our own raw files
  (§1.2).

**Areas that are mixed, partial, or league/model-dependent (real academic work
exists, but no single clean bias):**

- Over/Under and BTTS market efficiency — real studies exist (*International
  Journal of Forecasting*, several 2018-2021 papers) but findings vary by league
  and model; no universal directional bias.
- xG's edge over the market — a 2026 study (Wilkens, 11 Bundesliga seasons) finds
  bookmaker odds retain *better overall calibration* than a simple xG model, with
  only a modest, asymmetric (home-bets-only) residual edge. This tempers the
  "just add xG" instinct the earlier initiation report was at risk of following,
  and independently supports the operator's decision to not assume xG is where
  the edge lives.

**Areas that are mostly lore, unverified, or genuinely absent from the credible
literature — flagged honestly rather than treated as evidence:**

- **The exact question the operator asked us to prioritise — whether markets
  misprice the MAGNITUDE of a dominant team's expected win (correct score,
  winning margin, deep handicap lines) — has the thinnest direct evidence of
  anything in this review.** A plausible practitioner mechanism exists (thin
  liquidity on extreme lines, most modelling effort targets win-probability
  markets rather than margin distributions) but no rigorous published study
  directly tests it. This is precisely why Dominant-Side Mispricing belongs in
  this project as a genuine research question, not a pre-decided answer — see §3.
- Corners-market efficiency: the best available source is a single
  non-peer-reviewed university thesis, whose own conclusion is that any
  inefficiency found (English Premier League) did not replicate out-of-sample
  (Bundesliga). Everything else found online on corners betting is
  undifferentiated tipster/SEO content.
- Fixture-congestion pricing by markets: the underlying performance/injury effect
  is well-established in sports-science journals, but no credible study connects
  it to betting-market pricing specifically.
- Weather effects: the best available football-specific analysis (a
  methodologically transparent, if non-peer-reviewed, analytics blog, ~7,500
  English matches) found **no significant effect** of rain on goals or draw
  probability — undercutting the premise that there is a weather mispricing to
  find in England specifically, though this doesn't rule it out elsewhere.
- Cross-competition efficiency differences (top-5 leagues vs. Championship/
  Scottish Premiership): essentially unstudied for these specific leagues; the one
  adjacent finding (German multi-tier data) actually suggests markets handle tier
  differences reasonably well, contradicting common "lower leagues are softer"
  bettor lore.
- **Closing Line Value (CLV) as a validated predictive construct**: no
  independent academic validation for football was found — it is an imported
  practitioner heuristic from US sports betting, with a plausible market-
  microstructure rationale but no rigorous football-specific evidence. This
  project already has infrastructure that treats this correctly
  (`docs/HISTORICAL_PRICE_AND_CLV_LIMITATIONS.md`'s `proxy_clv` vs
  `true_execution_clv` distinction) — the literature gap is a reason to keep
  using `proxy_clv` as one candidate discovery signal among several, not as a
  privileged one.

A general methodological caution surfaced by the review deserves repeating here
because it validates this project's own process: Winkelmann et al. (*Journal of
Sports Economics*, 2024) show that many published "profitable inefficiency"
findings in this literature can be backtest artifacts rather than genuine
mispricing — exactly the failure mode this project's Bonferroni-corrected,
walk-forward, sealed-holdout discipline exists to prevent.

---

## 3. Dominant-Side Mispricing — Research Specification

**Status: one pre-registered research family among several, not an assumed
strategy.** It must be capable of returning a null result, exactly like every
other family in this project's history (13/13 REJECT in Tennis Workstream B).

**Concept.** The market plausibly prices *whether* a strong side wins correctly
(favourite-longshot bias literature says 1X2/AH win-probability pricing is broadly
sound, §2) but may misprice the *magnitude or expression* of that dominance — how
many goals, how large a winning margin, how much territorial/shot dominance is
implied relative to what the price says. This is not "will Barcelona beat Celtic"
but "does the market correctly price how much Barcelona should beat Celtic by,
given Celtic's specific defensive characteristics, not just Barcelona's attacking
reputation."

**Required inputs — mandatory two-sided modelling.** Per the operator's explicit
instruction, the dominant side is never modelled in isolation. Every candidate
observation must combine:

- Dominant-side attacking/output characteristics (rolling goals-for, shots, SOT,
  Elo attacking component if decomposed).
- Opponent defensive characteristics (rolling goals-against, shots-against,
  SOT-against faced).
- A relative-strength/asymmetry measure (Elo gap, rank/table-position gap,
  bookmaker-implied win-probability gap).
- Match context (home/away, competition/league strength, rest days, congestion).
- The market's own price for the magnitude question — which today means the
  single Asian Handicap line already in hand (§1.3), and the Over/Under 2.5 price
  as a secondary total-goals magnitude signal. Multi-line AH/O-U (if acquired
  later per §1.3's PARTIAL row) would sharpen this considerably.

**Candidate markets, in order of what we can actually test today:** Asian
Handicap (primary — the market most directly about margin), Over/Under 2.5
(secondary — total-goals magnitude), 1X2 win margin implied via the AH line
(same data, different framing). Corners/team-goals/clean-sheet/winning-margin-
as-a-standalone-market are excluded for now per §1.3's BLOCKED/PARTIAL status —
they may become testable if the Betfair multi-market acquisition in §1.3 is later
approved.

**Falsifiability — what a null looks like.** If, controlling for the AH line
already quoted, no combination of dominant-side/opponent/asymmetry/context
features predicts the actual margin better than the market's own line (measured
by out-of-sample calibration/log-loss on an AH-cover outcome, or margin-regression
residual analysis vs. the market's implied margin), this family is REJECTed — the
same standard applied to all 13 Tennis Workstream B families. A promising point
estimate with a CI that includes zero is PARTIAL, not PROMOTE, per the same
mutually-exclusive verdict logic already built and tested in
`src/prediction_markets_lab/research/holdout_verdict.py` (reusable as-is, it is
sport-agnostic).

**Explicit guardrail against biasing the wider search (operator's instruction,
§3 of the direction-change message).** Dominant-Side Mispricing is one of
approximately a dozen families this cycle should test (see §5's discovery-family
list), pre-registered alongside the others, tested with the same Bonferroni-style
multiple-testing correction already used in Tennis Workstream B's 13-family
discovery pass. It does not get a lower bar, a second look after a null, or
priority in reporting over a family that turns out to matter more. If the wider
discovery pass (§5) turns up a stronger signal in, say, favourite/underdog framing,
price bands, or a completely different mechanism, that finding is reported with
equal weight, not suppressed in favour of the pre-declared hypothesis.

---

## 4. Data-First Discovery Plan

Mirrors the behavioural-discovery methodology already proven in this project (the
quant/algo-trading side, and Tennis Workstream B's 13-family discovery pass), with
the same anti-mining controls that already exist in this codebase.

**Step 1 — build the enriched dataset (extraction, not acquisition).** Re-run
canonicalisation over the already-downloaded raw files to extract
`HS/AS/HST/AST/HC/AC/HF/AF/HY/AY/HR/AR/Referee/AHh/B365AHH/B365AHA/B365CAHH/
B365CAHA/B365>2.5/B365<2.5/B365C>2.5/B365C<2.5` alongside the existing 1X2 fields,
for the same 5,800 matches, same hashed raw files, same `data_version`. This is a
canonicalisation-code change plus a new minor `data_version`, not a new acquisition
— zero new network access.

**Step 2 — leakage-safe feature construction.** Every rolling feature (recent
form, recent shots/SOT/corners-for/against, rest days, congestion) must be
`.shift(1)`-lagged before any rolling window, exactly as Tennis Workstream B's
discovery dataset build already enforces. Referee identity is known pre-match
(fixture/officials are typically confirmed before kickoff) so it is not inherently
leaky, but any *referee tendency* statistic (e.g. average cards given) must be
computed only from matches strictly before the one being predicted.

**Step 3 — search broadly, not narrowly, for behaviour.** Per the operator's
explicit instruction not to let Dominant-Side Mispricing bias the search, the
discovery pass tests relationships between: dominant/underdog framing, price
bands, rank/Elo gap, recent-form and recent-luck (xG-style outcome-bias proxy
computable from goals vs. shot/SOT quality, per §2's Flepp et al. finding),
home/away, rest/congestion, competition tier, referee identity, shots/SOT/corners
differentials, `proxy_clv` (opening-to-closing bookmaker movement), and — as its
own pre-registered family, not a privileged one — Dominant-Side Mispricing (§3).

**Step 4 — controls against false discovery**, reusing exactly the machinery
already built and proven: Bonferroni-style correction across all pre-registered
families (as used for tennis's 13-family pass), paired-bootstrap CIs, a minimum
sample-size floor before any bucket is eligible, year-by-year stability checks,
bin-sensitivity checks, and the arbitrary-label symmetry-cancellation check that
caught a real methodological error in Tennis Workstream B's surface/tournament
families (§17 of the roadmap) — the equivalent risk here is testing a feature
uncorrelated with home/away or favourite/underdog framing without first
established which side is which, which would cancel a real asymmetric effect to
zero exactly as it did for tennis surfaces.

**Step 5 — only then, hypothesise.** Each candidate behaviour that survives Step 4
becomes a formally pre-registered hypothesis (mechanism, exact population, exact
market, exact feature/condition, expected direction, minimum sample, validation
period, OOS period, EV requirement, rejection criteria) before any chronological
validation begins — exactly the discipline already used for tennis.

**Chronological structure (frozen before any outcome is examined, mirroring the
tennis 2021-2023/2024/2025/2026+ structure, adapted to football's calendar):**
2020/21-2022/23 = discovery; 2023/24 = development validation; 2024/25 = final
historical OOS **pending resolution of the exposure question already flagged in
the earlier initiation report** (Cycle 1's Stage 3B already computed pooled
model-vs-market numbers on 2024/25 — this still needs a decision, restated in §7);
2025/26-onward = genuine prospective holdout.

---

## 5. Pre-Registered Discovery Families (first pass)

To be frozen in a dedicated pre-registration document before Step 5 above is ever
run against real outcomes, following the same pattern as
`WORKSTREAM_B_HISTORICAL_SCALEUP_AND_DISCOVERY_PROTOCOL.md`'s 13 tennis families:

1. Model/market disagreement (any candidate model vs. consensus, general).
2. Favourite/underdog framing (by market-implied probability, not team identity).
3. Price bands (fine-grained probability buckets).
4. Rank/table-position gap.
5. Elo gap (reusing Cycle 1's frozen Elo, not retuned).
6. Recent-form / recent-luck (outcome-bias) — goals vs. shot/SOT-quality proxy.
7. Home/away.
8. Rest/fixture congestion.
9. Competition tier / cross-league.
10. Referee identity (tendency, computed leakage-safely).
11. Shots/SOT/corners differential (dominant vs. opponent).
12. `proxy_clv` (opening-to-closing bookmaker movement).
13. **Dominant-Side Mispricing** (§3) — combined dominant + opponent + asymmetry
    + context features against the Asian Handicap line specifically.

Thirteen families, matching the tennis precedent's scale — not a coincidence, a
deliberate reuse of a process already proven to produce an honest result either
way.

---

## 6. Recommended First Step

**Not xG. Extraction of data already on disk (§1.2), first.** This is the fastest,
zero-cost, zero-new-acquisition-risk route to a materially richer discovery
dataset, and it directly answers the operator's "map what can be measured and
priced before guessing the edge" principle better than any new acquisition could —
because it requires no new judgement calls about what to acquire at all; the data
is already paid for in acquisition effort and sitting unused.

Concretely, in order:

1. Extend the football canonicalisation module to extract the columns identified
   in §1.2/§4 Step 1, bump `data_version`, re-validate against the existing
   5,800-match count and existing tests (no raw re-acquisition, so file counts and
   hashes must be unchanged).
2. Build the leakage-safe rolling features (§4 Step 2) and the 13-family
   pre-registration document (§5).
3. Run the discovery-period (2020/21-2022/23) analysis with the existing
   Bonferroni-corrected bootstrap framework, adapted from
   `run_discovery_analysis_2021_2023.py` (sport-agnostic statistical core).
4. **Only after that discovery pass returns its result** — regardless of what it
   finds — revisit whether xG, weather, or a Betfair multi-market acquisition
   (§1.3's PARTIAL rows) is worth acquiring, informed by which families (if any)
   showed genuine signal. Acquiring xG now, before knowing whether shots/SOT/
   corners/AH-line features already explain what xG would add, risks the same
   "assume the statistic matters" mistake the operator is explicitly correcting.

This reorders, but does not discard, the earlier initiation report's plan — xG,
weather, and fixture-congestion features remain valid future work, they simply
move to *after* the free re-extraction and discovery pass rather than before it.

---

## 7. What We Deliberately Should Not Acquire Yet

- No xG scraping (FBref/Understat) — pending both the discovery-pass result above
  and the still-unresolved E1/SC0 coverage question.
- No Betfair football historical download — the multi-market coverage (BTTS,
  multi-line AH, corners, cards) is unconfirmed, and nothing in §1.3's CLEAR rows
  requires it yet.
- No paid vendor data (OddsMatrix, TxOdds, SportsData.io, The Odds API,
  BigDataBall) — none published market-level detail confirming they cover the
  BLOCKED markets in §1.3 either; a sales conversation would be needed, and
  nothing has justified that cost yet.
- No scraping of OddsPortal/BetExplorer for DNB/BTTS/multi-line AH — both sites'
  data is browse-only with no official bulk export, and third-party scrapers
  operate against terms this project does not test.
- The 2024/25-exposure question flagged in the earlier initiation report is
  **still open and still unresolved** — restated here rather than decided
  unilaterally: Cycle 1's Stage 3B already computed pooled model-vs-market
  numbers on 2024/25, so it may not be a pristine final holdout for this
  discovery-first Cycle 2 either. The two options remain: fold 2024/25 into
  development and use 2025/26 as the new sealed holdout, or accept the weaker
  aggregate-only exposure as immaterial. Needs a decision before Step 4's
  chronological split in §4 is frozen.

---

## 8. Expected Sample Size / Coverage, Cost, Risks

**Sample size**: unchanged from Cycle 1 — 5,800 matches across E0/E1/SC0,
2020/21-2024/25 — since §6's recommended first step is extraction, not new
acquisition. Per-family discovery-period samples will mirror Cycle 1's
2020/21-2022/23 subset (roughly 3,480 matches across the three competitions,
proportionally).

**Cost**: £0 for the recommended first step (extraction only). Weather
(Open-Meteo) and fixture-congestion remain £0. xG and any Betfair football
acquisition remain deferred, cost unknown pending a coverage check.

**Scientific risks**: (a) the same 2024/25-exposure risk carried over from the
earlier report, unresolved (§7); (b) a new leakage risk specific to this plan —
referee-tendency features must never leak the current match's own cards/fouls
into its own prediction, guarded by strict lagging (§4 Step 2); (c) the
arbitrary-label symmetry-cancellation risk that hit tennis's surface families
recurs here for any feature tested without first fixing a favourite/underdog or
home/away frame (§4 Step 4); (d) Dominant-Side Mispricing specifically risks
becoming a self-fulfilling search if not held to the same bar as the other twelve
families — guarded explicitly in §3's guardrail section.

**Repo architecture changes required**: one canonicalisation-module extension
(§6 step 1); one new pre-registration document (§5, frozen before outcomes are
examined); reuse, unmodified, of `probability/margin_removal.py`,
`consensus.py`, `market_pipeline.py`, `validation/time_splits.py`,
`validation/leakage_checks.py`, and the Bonferroni-bootstrap statistical core from
the tennis discovery script. No new ingestion module is needed for the
recommended first step (the raw files are already downloaded); a new ingestion
module would only be needed if the Betfair multi-market or xG acquisitions are
later approved.

---

## 9. GO / HOLD Decision

**GO** on: extracting the already-downloaded raw columns (§6 step 1), building the
leakage-safe features (§4 step 2), freezing the 13-family pre-registration (§5),
and running the discovery-period analysis (§4 step 3) — none of this is new
acquisition, all of it is read/audit/extract work on data already fully paid for
and hashed.

**HOLD** on: any xG scraping, any Betfair football historical download, any paid
vendor engagement, and freezing the final chronological split (§4) until the
2024/25-exposure question (§7) is answered by Fraser/the operator.

Nothing beyond this report, its companion multi-sport framework document, and the
read-only repository/literature research behind it has been executed. No new data
has been acquired, downloaded, linked, or analysed.

---

## Answers to the operator's 15-point return list

1. **Genuinely researchable football markets with historical prices + outcomes,
   today**: Match Odds (1X2), Over/Under 2.5 goals, Asian Handicap (single line)
   — all three already fully in hand for 5,800 matches, E0/E1/SC0,
   2020/21-2024/25, opening and closing prices. Draw No Bet is computable as a
   proxy from 1X2 already in hand.
2. **Statistics/features available for each**: shots, shots-on-target, corners,
   fouls, cards, and referee identity are available as pre-match-safe (lagged)
   features for all three markets above, once extracted (§1.2/§6); xG is
   available only for the Premier League pending an E1/SC0 coverage check.
3. **What external research suggests may contain inefficiencies**: market
   overreaction to recent form/luck (strong, two independent studies), Asian
   Handicap's handicap-sub-type mispricing (strong, recent), shots-on-target's
   incremental predictive value (strong but fading over time). The magnitude-of-
   dominance question itself (§3) has the thinnest direct evidence of anything
   reviewed — a real gap in the literature, not a refutation.
4. **Objective priority ranking**: (1) extract and mine data already in hand
   (1X2/O-U-2.5/AH + match stats) — zero cost, zero acquisition risk, unlocks 12
   of 13 discovery families immediately; (2) weather + fixture-congestion
   features (zero/near-zero cost, additive to the same markets); (3) a Betfair
   football multi-market acquisition (BTTS, multi-line AH/O-U, corners, cards) —
   real but unconfirmed coverage, would need its own audit-before-acquire pass;
   (4) xG scraping — highest infrastructure cost, coverage-gated, and the
   literature (Wilkens 2026) suggests the market has already absorbed most of its
   value.
5. **Where Dominant-Side Mispricing ranks and why**: it is one of 13 co-equal
   pre-registered discovery families (§5), tested against the Asian Handicap line
   already in hand — rankable now, at zero acquisition cost, but not privileged
   over the other twelve.
6. **Recommended FIRST market/data family**: not a market at all — extraction of
   the already-downloaded shots/SOT/corners/cards/fouls/referee/O-U-2.5/AH data
   from the raw Football-Data.co.uk files already on disk (§6).
7. **Exactly what data should be acquired next**: nothing needs to be *acquired*
   next — the immediate next step is extraction of existing raw data. The first
   genuinely new acquisition candidate, if the discovery pass justifies it
   afterward, is Open-Meteo weather data (free) alongside fixture-congestion
   features (free, already in hand).
8. **What we deliberately should NOT acquire yet**: xG, any Betfair football
   download, any paid vendor data, any scraping of OddsPortal/BetExplorer — see
   §7 in full.
9. **Expected sample size/coverage**: 5,800 matches, E0/E1/SC0,
   2020/21-2024/25, unchanged from Cycle 1 (§8).
10. **Free/paid status and storage requirements**: the recommended first step is
    entirely free (data already downloaded and hashed); storage impact is
    negligible (a few new columns per row, not new files).
11. **Scientific risks**: the unresolved 2024/25-exposure question; leakage risk
    on referee-tendency features; the arbitrary-label symmetry-cancellation risk
    recurring for any un-framed feature; Dominant-Side Mispricing search bias —
    all four detailed in §8.
12. **Exact next experimental stage**: canonicalisation extension → leakage-safe
    feature build → 13-family pre-registration freeze → discovery-period
    (2020/21-2022/23) analysis (§4/§6), exactly mirroring Tennis Workstream B's
    already-proven Phase 2 process.
13. **Repo architecture changes required**: one canonicalisation-module
    extension and one new pre-registration document; all statistical/validation
    machinery is reused unmodified (§8).
14. **Tests/commits/documents created**: this report, the companion
    `RESEARCH_FRAMEWORK_MULTI_SPORT.md`, and (pending Fraser/operator sign-off on
    §9's GO items) the canonicalisation extension and its tests, in a follow-up
    session. Nothing has been coded yet — this report itself required no `src/`
    changes and no new tests.
15. **Clear GO / HOLD decision**: see §9 — GO on extraction/feature-build/
    pre-registration/discovery-run against data already in hand; HOLD on every
    new acquisition (xG, Betfair football, paid vendors) and on freezing the
    final chronological split until the 2024/25-exposure question is resolved.
