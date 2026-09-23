# Platform V2 Roadmap (sequential; each phase needs Fraser's go-ahead; production stays live throughout)

| # | phase | type | builds | exit criterion |
|---|---|---|---|---|
| 0 | **This blueprint** | design | `research/platform_v2/` | Fraser approves or edits it |
| 1 | **Evidence plumbing** | additive production | raw per-bookmaker quote archive + near-kickoff closing snapshot + three EV references logged (Phase 3 rec + Phase 5 R1); wire existing risk gates into the scan (log-only first) | 2 weeks of clean archives; nothing in decisions changed |
| 2 | **Engine registry + Prediction Board** | additive | engine ids/versions, evidence records, band-reliability intervals, support grade; `prediction_board.{json,md}`; board-level calibration tracking | board generated daily; money card unchanged |
| 3 | **Cycle V2-1: margin-removal calibration** | research | power/Shin/odds-ratio vs proportional, pre-registered, chronological, football + tennis | frozen verdict; if better, the engine upgrade enters PAPER |
| 4 | **Cycle V2-2: Tennis market engine** | research + live audit | holdout validation (2024–25) + live-source decision (Betfair Delayed key vs Odds API) | engine at PAPER, or a documented block |
| 5 | **Probability-first grading** | production refactor (approval) | grade = probability tier × support × uncertainty; value becomes a gate; old grade kept as `research_grade` | parity tests; card shows both for 2 weeks |
| 6 | **Multi engine in PAPER** | additive | eligibility, dependency screen, joint P + interval, per-book combined odds, exposure rules; historical cross-event replay | ≥ 100 paper multis; joint calibration report |
| 7 | **Breadth** | additive | more football leagues on existing engines; BTTS paper wiring; AH Stage A | per-market PAPER criteria |
| 8 | **Current context** | research | lineups/injuries/rest as auditable adjustments, each tested like a feature | only proven adjustments enter |
| 9 | **Money-eligibility reviews** | decision | per engine / multi type, per the promotion standard | Fraser approval |
| later | other sports, fractional Kelly, execution automation | — | only per V2 §40–44 | — |

Phases 1–2 are the highest-leverage next steps. Every other phase needs the evidence they create, and every day
without them is lost live data.
