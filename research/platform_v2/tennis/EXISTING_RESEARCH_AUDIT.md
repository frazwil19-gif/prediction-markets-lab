# Tennis — Existing Research Audit (read before any new work; 2026-09-23)

| item | what it established | status |
|---|---|---|
| TML-Database ATP 2021–2025 (+2026 partial) | canonical matches `cycle_002_canonical_matches.csv` (2021: 2,713 · 2022: 2,900 · 2023: 2,975 · 2024: 3,055 · 2025: 2,921) | preserved, reused |
| Tennis Cycle 1 A4 baselines | ranking baseline, **Global Elo (k = 32, trained 2021–23, validated 2024)**, Surface Elo V1 **NEGATIVE** | frozen, reused |
| A4 calibration research | a training-fit recalibration of Elo was ≈ identity (intercept 0.027, slope 0.978) and did not help on 2024 | cited, **not re-run** |
| A4 step D | recent form, surface form, congestion/rest beyond Elo: all **NOT PROMOTED** | null results kept |
| Cycle 1 sealed 2025 holdout | Global Elo vs ranking, verdict **PARTIAL** (Elo 0.6325 vs ranking 0.6399, CI crosses 0) | Elo's 2025 already exposed |
| Workstream B (Betfair BASIC, 2021–23 discovery) | 13 pre-registered market-edge families, **all REJECT**; 2024 and 2025 market tests **NOT OPENED** | closed; not reopened here |
| Betfair linkage | 12,956 of 14,564 TML matches linked 2021–25 (MATCHED); names never guessed | reused unchanged |

**What V2-1 did differently:** it asked a *probability* question (are market and Elo probabilities calibrated,
especially at the top?), not an edge question. It used the never-opened 2024–25 market-vs-outcome data as a sealed
holdout (`TENNIS_ENGINE_PROTOCOL.md`, `HOLDOUT_SPEC.json`, SHA-256 committed in `8ca4264` before opening). No
Workstream B family and no step-D feature was re-tested.

**Data rebuild:** the old Parquet index lived in an ephemeral VM home and was gone. The 12,952 linked markets were
re-extracted from Fraser's untouched `data.tar` (every row carries its source member's SHA-256), giving 12,202 matches
with fresh prices on both sides 30 minutes before the start. The 2021–23 subset reproduces Workstream B's discovery
dataset **exactly** (7,136 matches; market and Elo probabilities identical to the stored values, max difference 0.0).

## Feature-family classification (for a future cycle; nothing launched)
| family | status |
|---|---|
| Global Elo | tested; overconfident at the top on unseen data (below) |
| Surface Elo V1 | tested, negative. A shrinkage/hierarchical version is untested (needs a fresh pre-registration) |
| Recent form / surface form / rest / congestion | tested, null (step D) |
| Ranking | tested (baseline) |
| Market-aware disagreement / movement families (13) | tested, rejected (Workstream B) |
| Serve / return performance | **available, untested.** TML carries per-match serve stats (post-match; usable only as shifted rolling features) |
| Opponent-adjusted performance, age, match format, tournament level | available, untested as model inputs (level/format appear only as subgroups) |
| Injury / withdrawal, workload beyond rest | unavailable historically in structured form |
| Point-by-point / in-play | requires new data |
