# Multi-Sport Market-Inefficiency Discovery Framework

**Date:** 2026-09-16
**Authority:** Written per Fraser's own explicit instruction, given alongside the
operator's Football Cycle 2 direction change: this discovery-first process is not
football-specific. It is adopted as the project's standing methodology for every
sport/market stream — football, tennis, cricket, and whatever is added later.

**Status:** policy/process document. It defines *how* every future research stream
is run; it does not itself authorise acquisition, paper trading, or live betting for
any sport, and it changes nothing about tennis's frozen results or Football Cycle
1's closed status.

---

## 1. Why this exists as its own document

Football Cycle 1 and Tennis Workstream B independently arrived at very similar
disciplines (chronological splits, Bonferroni-corrected discovery passes, frozen
models, honest null reporting) without a shared, explicit statement that this is
*the* process for every sport, rather than something that happened to be built
twice. The operator's football direction change made the philosophy explicit for
football; Fraser's own addition extends it project-wide. This document is that
explicit, reusable statement, factored out of any one sport's cycle folder so it
does not need to be rewritten (or worse, silently drift) every time a new sport
starts.

This document does not replace any sport's own cycle documents (e.g.
`WORKSTREAM_B_CLOSURE.md`, `FOOTBALL_CYCLE_2_DIRECTION_CHANGE_REPORT.md`) — those
remain the authoritative record of what happened in that sport. This document is
the shared rulebook they all follow.

---

## 2. The standing pipeline

```
OBSERVE DATA -> AUDIT/UNDERSTAND DATA -> DISCOVER BEHAVIOURS -> FORM HYPOTHESES ->
BACKTEST (chronological development validation) -> OUT-OF-SAMPLE VALIDATE (sealed
holdout) -> PAPER TRADE -> SMALL LIVE VALIDATION -> SCALE ONLY IF EDGE PERSISTS
```

No sport skips a stage. No sport starts from an assumed-useful statistic ("xG
should work," "serve stats should work," "spin rate should work") — every stream
starts from §3's market-availability × data-availability audit, not from a
pre-decided hypothesis.

### 2.1 The hard gate: price × outcome

Before any statistic, market, or data family is ranked for a given sport, it must
clear the same gate used for football: **does a historical outcome/statistic
series exist, AND does a historical price series exist, for the same events?**
A family that fails this — however predictive it looks — is recorded as **NOT
RESEARCHABLE FOR BETTING EV YET**, though it may still be used as a *feature*
that helps price a market which does clear the gate. This is the direct,
sport-agnostic generalisation of football's corners/cards finding (raw corner and
card counts are freely available; a corners or cards market price is not, so
those statistics are usable only as inputs to markets we can actually price,
e.g. Asian Handicap, not as their own tradable bets).

### 2.2 The scoring formula (Research-Priority Matrix)

```
Score = Gate x [ w1*sample_size + w2*data_quality + w3*mechanism_plausibility
                 + w4*external_evidence + w5*ev_measurability ]
        - [ w6*acquisition_cost + w7*leakage_risk ]
```

- **Gate** ∈ {0, 0.5, 1}: 0 = BLOCKED (no known price archive at all), 0.5 =
  PARTIAL (one side confirmed, the other thin/unconfirmed/scrape-only), 1 =
  CLEAR (both outcome and price confirmed, ideally already in hand). This
  multiplies the whole bracket, so a family cannot claw its way to a high score
  through mechanism plausibility or literature support alone if it cannot
  support an EV calculation.
- Each sub-score and penalty is rated 0-5 against **stated evidence** (a cited
  source, a direct repo/data check, or an explicit "no evidence found" — never a
  bare intuition call), so the ranking can be audited line by line, per Fraser's
  explicit requirement. Football's worked example is in
  `research/cycles/CYCLE_003_FOOTBALL/FOOTBALL_CYCLE_2_DIRECTION_CHANGE_REPORT.md`
  §1.5.
- Suggested equal-ish default weights (w1=w2=w3=w4=w5=1, w6=w7=1) are a starting
  point, not dogma — a sport with a hard bankroll/time constraint could
  legitimately upweight acquisition cost (w6). Whatever weights are used for a
  given sport's matrix must be stated alongside the result, exactly as football's
  §1.5 does, so the ranking stays auditable rather than opaque.
- **The formula ranks where to research first. It never ranks what is
  profitable.** A family's score answers "is this worth spending research time
  on," never "does this make money" — that question is only ever answered by the
  full validation pipeline in §2, never by this matrix.

### 2.3 Data-first discovery, not hypothesis-first

Once a sport/family clears the gate and is prioritised, the same sequence
applies regardless of sport: build the dataset from data already in hand (extract
before you acquire, exactly as football's Over/Under/Asian-Handicap/match-stats
finding demonstrates — always check what existing acquisitions already contain
before assuming new acquisition is needed), apply strict leakage controls
(`.shift(1)`-lag every rolling feature; never let a same-match retrospective
field — cards given, xG, final lineup — leak into its own prediction), search
broadly across many pre-registered families with a Bonferroni-style multi-testing
correction, and only then formalise falsifiable hypotheses — before looking at
outcome data for the new features, exactly as football's discovery plan and
tennis's 13-family pass both already do independently. A pre-registered "pet
hypothesis" (football's Dominant-Side Mispricing; a tennis-equivalent might be
"elite servers are mispriced on faster surfaces") is always one family among
several, tested at the same bar, never given a lower threshold or a second look
after a null.

### 2.4 Reusable machinery (do not rebuild per sport)

Confirmed sport-agnostic and already built: margin-removal/consensus math
(`probability/margin_removal.py`, `consensus.py`, `market_pipeline.py`),
chronological split enforcement (`validation/time_splits.py::SplitPlan`,
`validate_test_period_untouched()`), generic leakage checks
(`validation/leakage_checks.py`), the mutually-exclusive PROMOTE/PARTIAL/REJECT
verdict logic (`research/holdout_verdict.py`), and the Bonferroni-corrected
bootstrap-CI discovery pattern (proven in Tennis Workstream B, directly adaptable
per football's §4 Step 3/§6). A new sport's genuinely new work is almost always
narrower than it first looks: new data acquisition/linkage for that sport's
specific sources, plus a fresh pre-registration — not new statistical or
validation infrastructure.

---

## 3. Cross-sport stop/pause/move-on criteria

Applies uniformly, replacing any sport-specific version of this rule:

- **Stop-on-a-family**: if a specific data family's own audit shows no credible
  incremental information, or coverage too thin to reach the sample-size floor,
  reject that family and move to the next-ranked one in that sport's matrix.
  Do not extend or rescue a rejected family by loosening its threshold or adding
  ad-hoc covariates after seeing its result — this is exactly the mining risk the
  operator flagged when declining to extend Tennis Workstream B (Option C).
- **Stop-on-a-sport**: if a sport's full discovery pass (all pre-registered
  families) returns a clean null — as Tennis Workstream B's 13-for-13 REJECT did
  — that sport's discovery under that information set is closed, not endlessly
  re-opened with new covariates. Record the closure explicitly (mirroring
  `WORKSTREAM_B_CLOSURE.md`'s format: frozen status table, families
  tested/promoted, explicit statement that this closes the information set, not
  the sport itself, and what a materially new information source would need to
  look like to justify reopening it) and move to the next-ranked sport in the
  project's priority order (§1 of `claude/cycle-2-research-roadmap.md`).
- **Move-on, not stall**: the project does not remain stuck indefinitely trying
  to force one sport to work (the operator's explicit instruction). Football,
  tennis, and cricket (queued, per the existing roadmap) form a rotation, not a
  strict sequence — if a genuinely new information source appears for a closed
  sport (e.g. tennis point-by-point data), it re-enters the priority ranking on
  its own merits via a fresh §2.2 scoring pass, exactly like any other new
  candidate family, never by unilaterally reopening the closed cycle's name.
- **No sport-specific exception to the validation gate order**: staking,
  paper trading, and live betting remain blocked project-wide until a candidate
  from any sport survives discovery, development validation, and a sealed final
  historical OOS confirmation — this document does not loosen that for a sport
  that looks promising early.

---

## 4. Applying this to the two sports already in motion

**Football (Cycle 2)**: fully reworked under this framework in
`research/cycles/CYCLE_003_FOOTBALL/FOOTBALL_CYCLE_2_DIRECTION_CHANGE_REPORT.md`
— the concrete, worked example of §2's audit/gate/matrix/discovery sequence.

**Tennis (Workstream B)**: already permanently closed
(`research/cycles/CYCLE_002_TENNIS/WORKSTREAM_B_CLOSURE.md`) under a process this
document formalises retroactively — the 13-family Bonferroni-corrected discovery
pass, the mutually-exclusive verdict logic, and the "closes the information set,
not the sport" framing were all already followed in practice before this document
existed to name them. No new tennis work is authorised by this document; §3's
stop-on-a-sport rule is exactly what was already applied.

**Cricket (queued, not yet started)**: when cricket becomes the active stream
(per the roadmap's priority order, next in line if Football Cycle 2 also nulls),
it starts from this document's §2 audit — a Cricket Market Availability × Data
Availability Audit, gated the same way football's was, before any ball-by-ball
model or hypothesis is assumed useful. The existing roadmap already flags
cricket's known gap (Cricsheet has rich free ball-by-ball outcome data but no
free bulk historical odds archive) — under this framework that gap is simply
cricket's Gate = 0/BLOCKED finding for most markets until an odds source is
found, exactly analogous to football's corners/cards finding, not a reason to
skip the audit.

---

## 5. What this document does not authorise

Mirroring every prior cycle document's closing convention: this document does not
authorise acquisition for any sport (each sport's own cycle report does that,
subject to its own GO/HOLD decision), does not authorise paper trading or live
betting for any sport, does not reopen Tennis Workstream B, does not modify
Football Cycle 1's frozen result, and does not itself constitute a pre-registration
for any specific hypothesis — it is the shared process those pre-registrations
must follow.
