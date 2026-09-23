# WTA Data Audit (Phase V2-2, 2026-09-23). Availability only; no outcome statistics

| item | finding |
|---|---|
| Result source | TennisCourtLog `tennis_wta/wta_matches_YYYY.csv` (Git LFS via media.githubusercontent.com); Sackmann-derived to 2024, tennis-data.co.uk-derived from 2025; CC BY-NC-SA 4.0 (non-commercial, attribution). SHA-256 manifest committed |
| Why not TML | TML's WTA files are published only at `stats.tennismylife.org`, which both the Mac VM and the cloud sandbox proxy reject (organisation allowlist). They are not in the TML GitHub repo |
| Years | 2018–2026 downloaded; 2018–2020 used only for Elo warm-up; 2021–2025 evaluated; 2026 partial (no Betfair archive coverage) |
| Rows (non-walkover) | 2018 2,742 · 2019 2,732 · 2020 1,268 (COVID) · 2021 2,570 · 2022 2,567 · 2023 2,788 · 2024 2,561 · 2025 2,487 |
| Walkovers / retirements (raw) | W/O 8–27 per year (excluded); RET 18–91 per year (kept, official winner) |
| Duplicates | 0 exact duplicate rows in every file |
| Identifiers | **no player ids**, only full names (case-folded for keys; 2025 capitalisation such as "Mcnally" is handled by folding) |
| Ranks | winner/loser rank and points present (not used as a model this cycle) |
| Surfaces | Hard / Clay / Grass (no Carpet) |
| Levels | coding changes in 2025 (I/P/PM → WTA250/500/1000); normalised in the builder (`LEVEL_MAP`) |
| Format | best-of-3 throughout |
| Match order | tournament start date + round order (no match number in this source) |
| Betfair archive | 169,062 singles MATCH_ODDS markets with prices (all tennis 2021–2025). The ATP completeness check covered 12,952 of 12,952 |
| Linkage (MATCHED / AMBIGUOUS / UNMATCHED) | 2021 2,152 / 56 / 362 · 2022 2,121 / 71 / 375 · 2023 2,218 / 63 / 507 · 2024 2,280 / 63 / 218 · 2025 2,326 / 71 / 90 |
| Fresh two-sided price at T−30 min | 2021 2,009 · 2022 1,982 · 2023 2,022 · **2024 2,116 · 2025 2,223** (dataset 10,352) |
| Elo | k = 32 selected on 2021–23 (grid 16…64; same value ATP chose) |

UNMATCHED is highest in 2023 (507), mostly team events and naming differences; the linker never guesses. The name-based
identity is a known limitation: two players with an identical full name would merge (none observed to matter at tour level).
