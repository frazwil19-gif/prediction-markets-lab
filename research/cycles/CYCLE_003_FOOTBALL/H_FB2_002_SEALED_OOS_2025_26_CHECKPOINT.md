# H-FB2-002 Sealed 2025/26 Out-of-Sample Evaluation — Decision-Grade Checkpoint

**Date:** 2026-09-18
**Cycle:** Football Cycle 2 (CYCLE_003_FOOTBALL)
**Hypothesis:** H-FB2-002 — SOT differential x extreme-favourite price band
**Authorisation:** Operator GO instruction, "FOOTBALL CYCLE 2 — AUTHORISE SEALED 2025/26 OOS FOR H-FB2-002" (relayed 2026-09-17)
**Verdict: FAIL. H-FB2-002 is now CLOSED (terminal REJECTED status).**

This document answers the operator's required 25-point checkpoint return in full, in order.

---

### 1. Commit-precedence confirmation

The sealed-OOS classifier (`src/prediction_markets_lab/research/oos_verdict.py`) and its 21-test
regression suite (`tests/unit/test_oos_verdict.py`) were implemented, tested (all passing), and
committed as **`936699a`** ("Football Cycle 2: freeze sealed 2025/26 OOS classifier for H-FB2-002
(pre-acquisition)") *before* any 2025/26 file was downloaded, opened, or inspected. No 2025/26 raw
file exists on disk with a modification time earlier than this commit. Phase 0 of the protocol was
satisfied exactly as required.

### 2. Raw file hashes / provenance

Manually downloaded by Fraser via `curl -L` from football-data.co.uk (network egress to this host
was blocked from every automated path available to this session — device shell, cloud container,
and browser pane all failed independently; this was a genuine external blocker, escalated and
resolved by the user downloading manually, consistent with the project's earlier Betfair-sample
precedent):

| Competition | File | SHA-256 | Bytes | Rows (excl. header) | Date range |
|---|---|---|---|---|---|
| E0 (Premier League) | `E0.csv` | `3e3a8352f9ada6789c508d6ca184424421fed56a30400904a4a327c583407e62` | 203,438 | 380 | 2025-08-15 to 2026-05-24 |
| E1 (Championship) | `E1.csv` | `98954c319950f19158624b17a154ef1c56eb7b8d169ef317f28f06d11d0b9a74` | 294,390 | 552 | 2025-08-08 to 2026-05-02 |
| SC0 (Scottish Premiership) | `SC0.csv` | `be3c45e08f09a327e3fd5289dd0b362b200f430ed5845cb18df1aca7e3ced2ee` | 118,594 | 228 | 2025-08-02 to 2026-05-17 |

Total raw matches: 1,160. Source: `https://www.football-data.co.uk/mmz4281/2526/{E0,E1,SC0}.csv`,
acquired 2026-09-18. Provenance recorded in full in
`data/processed/football/h_fb2_002_sealed_oos_2025_26_data_audit.json`.

### 3. Exact date coverage

E0: 2025-08-15 → 2026-05-24. E1: 2025-08-08 → 2026-05-02. SC0: 2025-08-02 → 2026-05-17. All three
spans run a full English/Scottish domestic season (August through May).

### 4. Season-completeness

**Confirmed COMPLETE, not partial.** Row counts match full-season expectations exactly: E0 = 380
(20 teams x 19 double round-robin), E1 = 552 (24 teams), SC0 = 228 (12 teams x 3 rounds). Today's
real calendar date (2026-09-18) plus football-data.co.uk's own site listing (which shows "Season
2026/2027" as the current season and "Season 2025/2026" as the prior, completed one) independently
confirm this. The operator's stated concern about a possible partial season did not materialise —
the min-N rule was never tested against a partial sample.

### 5. Data-only audit result

Audit performed strictly before any hypothesis-related figure was computed (schema, columns, row
counts, duplicates, missing-critical-field counts, date coverage, competition coverage, SOT-field
availability, opening-price-field availability, malformed-record scan, join compatibility against
the frozen 2020/21-2024/25 corpus, and a header diff against the 2024/25 schema). No duplicate
match rows found. No malformed records found. All critical fields (date, teams, FTR, SOT columns,
1X2 opening odds) present with negligible missingness at the field level. Full audit output is in
`h_fb2_002_sealed_oos_2025_26_data_audit.json`.

### 6. Schema drift / defects found

**One genuine, hypothesis-independent defect found and fixed.** Football-Data.co.uk's individual
per-bookmaker odds panel for 1X2/O-U/AH changed between the 2024/25 and 2025/26 seasons:
- 2024/25 panel: `B365, BW, BF, PS, WH, 1XB`
- 2025/26 panel: `B365, BFD, BMGM, BV, BW, CL, LB, PS`
- Only `B365`, `BW`, `PS` persist across both seasons.

The hardcoded `KNOWN_BOOKMAKER_PREFIXES` constant (documented as verified specifically against
2024/25 data) yielded only 3 usable bookmakers under the 2025/26 panel — below the
`MIN_BOOKMAKERS_FOR_CONSENSUS = 4` floor — producing **zero** consensus rows on the first
evaluation run (0 eligible matches, cascading to a false-reason FAIL). This was discovered during
the data-only canonicalisation step, strictly before any win-rate/SOT-effect/hypothesis figure
existed, and was root-caused by a direct header diff against the real files (not guessed).

**Fix, per the operator's Phase 0 protocol (stop → document → fix only the general problem → add a
regression test → commit separately → confirm independence → resume):** added a new, separately
documented constant `BOOKMAKER_PREFIXES_2025_26 = ("B365","BFD","BMGM","BV","BW","CL","LB","PS")`
in `football_bookmaker_extraction.py`. The historical `KNOWN_BOOKMAKER_PREFIXES` constant was left
completely unchanged. Three new regression tests were added using committed excerpt fixtures from
the real 2025/26 files, and the full suite (718/718) was run and passed before proceeding. Committed
separately as **`adcc1aa`** — before the corrected evaluation script produced any hypothesis-related
number. This fix is independent of H-FB2-002's outcome: it is a data-availability/schema fact about
the bookmaker panel Football-Data.co.uk publishes, unrelated to SOT differentials, price bands, or
home-win rates.

### 7. Confirmation audit preceded hypothesis analysis

Confirmed by construction and by commit ordering: `adcc1aa` (the schema-drift fix, discovered during
data-only canonicalisation) predates the corrected run of
`scripts/run_h_fb2_002_sealed_oos_evaluation.py` that produced any effect-size, CI, or verdict
figure. The audit phase (Phase B in the script) never inspects a win-rate, SOT-effect, or
hypothesis-related column; it only inspects schema/counts/hashes/coverage.

### 8. Exact OOS sample construction

Raw matches acquired: 1,160 (E0=380, E1=552, SC0=228). Cross-season rolling SOT features were built
by combining the frozen 2020/21-2024/25 `TeamMatchInput` corpus with the new 2025/26 rows into a
single call to the already-tested `compute_rolling_features()` function, which sorts internally per
team by `(match_date, match_id)` — this makes each team's first 2025/26 rolling snapshot correctly
inherit its 2024/25 tail history rather than resetting to zero at the season boundary. Verified
mechanically: 1,157/1,160 matches had a full 10-match rolling SOT history on both sides.

Exclusions from the 1,160 raw matches to reach the eligible set:
- 1 match excluded: missing 1X2 opening consensus (insufficient bookmaker coverage after the panel
  fix, i.e. a genuine <4-bookmaker case, not the schema-drift artefact)
- 3 matches excluded: missing full 10-match rolling SOT history for one or both sides (early-season
  fixtures for teams promoted from a division not covered by the frozen historical corpus)

**Eligible N = 1,156.** Eligible-dataset fingerprint (SHA-256 of sorted match IDs):
`d018b1156eba8b7c01b8bb84c82ef2bf0ccea0193efb9fad3c13e82eaf1aded5`.

### 9. Total / eligible N

Total raw: 1,160. Eligible: 1,156. Excluded: 4 (breakdown in item 8).

### 10. N by competition

Eligible: E0 = 379, E1 = 550, SC0 = 227 (sums to 1,156).
Price-quintile-4 subset (the primary test population — top 20% by 1X2 opening home-win probability,
recomputed fresh on the 2025/26 eligible sample per protocol section 9, not carried over from
development): N = 232 total, of which E0 = 100, E1 = 76, SC0 = 56.

### 11. Primary effect

Home-win-rate difference (high vs low rolling-last-10 SOT differential, median split), within price
quintile 4: **high-SOT-diff home-win rate = 0.7241, low-SOT-diff home-win rate = 0.6034, difference
= +0.1207** (n = 232).

### 12. Bootstrap CI

95% percentile bootstrap CI (seed=42, n=2000, identical method to development):
**[0.0000, 0.2414]**. The lower bound is exactly 0.0 — the CI touches zero.

### 13. Mechanical PASS / PARTIAL / FAIL verdict

**FAIL.**

### 14. Exact classifier reason

`"primary 95% CI does not lie entirely above zero (includes, touches, or is entirely below zero) --
there is no inconclusive category for this one-shot test"` — produced by
`oos_verdict.classify_sealed_oos_result`. Per the frozen classifier's ordered logic (population
completeness checked first — satisfied, all three competitions present; then the CI-favourability
gate `ci_lower <= 0.0` → FAIL), a CI that merely touches zero is FAIL, not PARTIAL. There is no
inconclusive category for a one-shot sealed test, as pre-registered.

### 15. Development-vs-OOS comparison

| | Development (2020/21-2024/25) | Sealed OOS (2025/26) |
|---|---|---|
| N (price quintile 4) | 1,147 | 232 |
| Effect | +0.0999 | +0.1207 |
| 95% CI | [0.0511, 0.1557] | [0.0000, 0.2414] |
| Excludes zero? | Yes | No (touches zero) |

The OOS point estimate is *larger* than development's, but the CI is far wider (smaller N, single
season) and touches zero. A larger point estimate does not rescue a CI that fails the pre-registered
gate — the classifier does not weight point-estimate magnitude against development's result, by
design.

### 16. Competition diagnostics (DIAGNOSTIC, NOT PRIMARY EVIDENCE — never gating)

- E0: n=100, diff=+0.04, 95% CI=[-0.14, 0.24] — weak, CI includes zero.
- E1: n=76, diff=+0.2105, 95% CI=[0.00, 0.4211] — directionally strong, CI touches zero.
- SC0: n=56, diff=+0.1429, 95% CI=[-0.0714, 0.3571] — moderate, CI includes zero.

No single competition drives or rescues the aggregate result; none is treated as gating, per
protocol section 17.3 (a deliberate design decision, not an oversight).

### 17. Continuous diagnostic

Pearson r (continuous SOT differential vs. outcome, quintile-4 subset), OOS: **r = 0.1057** (n=232).
Development reference: r = 0.0212. Per the frozen interpretive pre-registration (protocol section
17.5), this is descriptive only — it does not override, upgrade, or downgrade the mechanical
verdict. Of the three pre-registered interpretive possibilities (A: nonlinear/threshold effect; B:
broad effect under-measured by the correlation stat; C: development-sample artefact), the OOS
correlation is higher than development's but still far below the magnitude implied by the
median-split effect in either sample — most consistent with interpretation A or B, though this
remains genuinely undetermined and is not resolved by a FAILed primary test.

### 18. Every adverse / null result

- **Primary verdict is FAIL** (CI touches zero).
- **E0 diagnostic is weak and CI-null** (+0.04, CI includes zero).
- **Within-season time-slice diagnostic shows an unexplained reversal**, reported honestly and not
  explained away: first half of the 2025/26 season (n=116) diff=+0.2241, 95% CI=[0.0517, 0.3966]
  (excludes zero, strongly positive); second half (n=116) diff=**-0.0517**, 95% CI=[-0.2241, 0.1034]
  (negative point estimate, CI includes zero). This instability across a single season is a genuine,
  unresolved inconsistency and is one of the clearest pieces of evidence that the development-phase
  effect does not replicate robustly out of sample.
- SC0 and E1 diagnostics, while directionally positive, both have confidence intervals that include
  or touch zero individually.

No result was suppressed, softened, or omitted. All of the above are reported in
`data/processed/football/h_fb2_002_sealed_oos_2025_26_results.json`.

### 19. Confirmation no thresholds / specs changed

Confirmed. The H-FB2-002 specification (price-quintile-4 definition, SOT-differential median split,
bootstrap method, seed=42, n=2000) is unchanged from the pre-registration frozen at commit
`4757031`. No threshold, window, or price-source was altered at any point during acquisition,
audit, feature construction, or evaluation.

### 20. Confirmation no post-result hypothesis mining occurred

Confirmed. H-FB2-002 was the only hypothesis evaluated against 2025/26 data. No alternative
threshold, window, competition subset, or new hypothesis was scanned for, mined, or tested against
the 2025/26 corpus at any point. The primary test was run exactly once; diagnostics run afterward
were the pre-registered set only (competition breakdown, continuous correlation, favourite-price
distribution, within-season time-slice), none of which altered or could alter the primary verdict.

### 21. 2025/26 EXPOSED classification

**2025/26 (E0/E1/SC0) is now classified EXPOSED for football**, in the same sense as Tennis's
January 2026 exposure: this data has been used for a sealed-OOS hypothesis test and can never again
serve as a clean holdout for any football hypothesis, including a future H-FB2-002 replacement or
any newly discovered behaviour. This applies specifically to E0/E1/SC0 2025/26; it does not affect
other leagues, other seasons, or other sports.

### 22. Prospective continuation plan (N/A)

Not applicable. The verdict is FAIL, not PARTIAL-from-insufficient-N — the eligible sample
(n=1,156 total, n=232 in price quintile 4) comfortably exceeded the min-N floor of 100. No
prospective continuation plan is proposed, per the operator's own branching logic (a continuation
plan is only for a PARTIAL verdict caused specifically by insufficient N).

### 23. Tests passing

718/718 unit tests passing as of commit `adcc1aa` (the schema-drift fix). No additional test-suite
changes were required for the sealed-OOS evaluation script itself, which is a standalone research
script (following the project's established per-script duplication convention) rather than library
code requiring its own unit tests; its correctness rests on the already-tested
`compute_rolling_features`, `extract_bookmaker_triplets`, `classify_sealed_oos_result`, and the
verbatim-copied `top_price_band`/`median_split_diff`/`bootstrap_ci_mean_diff` functions.

### 24. Commits / reports created this phase

- `936699a` — froze the sealed-OOS classifier and its 21-test suite, and the corrected protocol
  (section 17), before any 2025/26 data access.
- `adcc1aa` — fixed the bookmaker-panel schema drift (independent of any hypothesis outcome), added
  regression tests and committed excerpt fixtures for the new 2025/26 raw files.
- (Pending, this checkpoint) — commit adding `scripts/run_h_fb2_002_sealed_oos_evaluation.py`, the
  updated `research/hypotheses/hypothesis_registry.csv` (H-FB2-002 → REJECTED), and this checkpoint
  document.
- `data/processed/football/h_fb2_002_sealed_oos_2025_26_data_audit.json` and
  `h_fb2_002_sealed_oos_2025_26_results.json` (untracked, per the project's data-hygiene
  convention — full data outputs are not git-tracked).

### 25. Exact next decision gate

**H-FB2-002 is now CLOSED (REJECTED).** Both formal Football Cycle 2 hypotheses (H-FB2-001,
H-FB2-002) are now closed — H-FB2-001 under DEVELOPMENT-REJECT (never reached sealed OOS),
H-FB2-002 under sealed-OOS FAIL. Per the operator's own FAIL-branch instruction, this returns to
the Research Pipeline level: the next decision is whether Football Cycle 2 closes entirely, or
whether a new, independently-justified information family deserves a fresh cycle. This checkpoint
does not make that decision — it is explicitly deferred to the operator/research-pipeline review,
consistent with "do not mine 2025/26 for a replacement hypothesis" and "a FAIL closes the hypothesis
... run the experiment once and accept the answer."

No other workstream is affected. BEH-008, xG/weather/injuries, new leagues, Betfair football, paid
vendor data, Cricket, Tennis Workstream B, paper trading, and live betting all remain on HOLD as
before.
