# Gate 1b (Football O/U 2.5) -- Betting Overlay Report (Stage B)

Per Section 25 of the Phase 4 instruction ("Betting overlay only after model freeze") and Section 9's
two-stage validation model, Stage B is addressed only after Stage A (outcome prediction, above) is
complete and its Decision is reached.

## Stage A outcome

Market consensus (even the thin, research-grade 2-3-bookmaker panel available in the historical
archive) is the strongest of the four architectures tested, on every metric, in every partition (pooled,
validation, holdout) -- see `VALIDATION_REPORT.md` / `HOLDOUT_REPORT.md`. No new frozen probability
model beat or usefully complemented market consensus for this market, mirroring the 1X2 result.

## Historical (retrospective) Stage B: BLOCKED BY DATA, as already established

Backtest-Phase-1-style historical replay against production money-qualification thresholds requires a
production-grade multi-bookmaker consensus (`min_bookmakers=3`). The historical football-data.co.uk
archive provides only 2-3 bookmakers per match for O/U 2.5 -- below that floor, a measured fact from
Phase 3 (`research/data_expansion/EXHAUSTED_VS_OPEN_RESEARCH.md`), not re-derived or second-guessed
here. Running a retrospective money-qualification backtest on this thin panel would silently understate
the real production consensus's quality (fewer bookmakers -> noisier de-vigged estimate) and was
therefore correctly NOT attempted, exactly as Section 20's "if historical odds are insufficient for
Stage B, complete Stage A honestly and mark Stage B blocked" instructs.

## Prospective (live) Stage B: ALREADY RUNNING, not something this cycle needed to build

Unlike 1X2, which needed a purpose-built historical replay harness (Backtest Phase 1) to get ANY
betting-performance evidence, Over/Under 2.5 is already LIVE in production (since 2026-09-19) using
real Odds API multi-bookmaker consensus (typically 20+ bookmakers for EPL), and at least one real O/U
2.5 candidate has already been recorded in the live paper ledger (`paper_ledger/paper_bets.csv`, per the
Phase 3 data inventory). This means Stage B for O/U 2.5 is being answered prospectively, continuously,
by the system already running unattended -- this cycle's job was only to confirm, via Stage A, that
using market consensus (rather than a new fundamentals model) for this market's probability input was
and remains the right choice, which it has now done with actual evidence rather than assumption.

## No production change

No threshold, grading rule, staking parameter, or the live scanner's probability source was touched or
needs to be touched -- production already does what this cycle's evidence supports.
