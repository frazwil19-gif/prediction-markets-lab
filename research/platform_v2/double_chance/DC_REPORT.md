# V2-4 Football Double Chance — Results (exposed data; protocol `DC_PROTOCOL.md`, committed first as `217c7fb`)

Estimator: the frozen production 1X2 consensus (per-book proportional de-vig, mean of B365/BW/PS closing), DC = pairwise
sums. Nothing fitted. Script `scripts/run_v2_4_double_chance_study.py`; outputs `DC_RESULTS.json`, `DC_THRESHOLDS.csv`,
`DC_BANDS.csv`, `DC_SPLITS.csv`, `DC_PRIMARY_PANEL_DERIVED.csv`.

## Untouched data
**None locally.** Every season 2020/21–2025/26 was used for 1X2 work, so these are **exposed-data** results.
2026/27 Aug–Dec is sealed (`HOLDOUT_SPEC.json` + sha256) and opens once, on or after 2027-01-03.

## Verifying the earlier descriptive figure (32.6% ≥80; 86.4 vs 86.4; n = 1,885)
**Not reproduced exactly.** The code that produced it was never saved (a provenance gap, recorded here). Closest reproducible:
| construction | ≥80 n | share | pred → won | ≥90 share | pred → won |
|---|---|---|---|---|---|
| stored median consensus (closing, renormalised), 5,763 matches | 1,875 | 32.54% | 86.39 → 86.40 | 8.42% | 92.83 → 94.43 |
| all-books closing, multiplicative mean, 5,800 | 1,879 | 32.40% | 86.42 → 86.43 | 8.34% | 92.83 → 94.42 |
| **primary panel (pre-registered), 5,897** | **1,855** | **31.46%** | **86.3 → 87.1** | **7.78%** | **92.8 → 95.0** |
The "n = 1,885" was the ≥80 count, not the panel size. The substance holds within 0.2–1.1 pp; **the pre-registered primary-panel
numbers replace the descriptive figure.**

## Headline (best DC selection per match, primary panel)
| threshold | all seasons n (share) | pred → won | validation | confirmation 2025/26 |
|---|---|---|---|---|
| ≥60 / ≥65 | 5,897 (100%) | 77.5 → 78.3 | 78.1 → 78.9 | 76.5 → 80.0 |
| ≥70 | 5,480 (92.9%) | 78.1 → 78.5 | 78.5 → 79.0 | 76.8 → 80.5 |
| ≥75 | 3,067 (52.0%) | 82.7 → 83.2 | 82.7 → 83.8 | 81.4 → 84.0 |
| **≥80** | **1,855 (31.5%)** | **86.3 → 87.1** | 86.5 → 88.0 (n 631) | 85.2 → 89.1 (n 129) |
| ≥85 | 967 (16.4%) | 89.9 → 91.7 | 90.1 → 92.1 | 88.7 → 94.8 |
| ≥90 | 459 (7.8%) | 92.8 → 95.0 | 92.7 → 94.8 | 92.6 → 93.8 (n 16) |
| ≥95 | 71 (1.2%) | 95.8 → 98.6 | 95.9 → 100 (n 27) | n = 1 |
The best DC is always ≥ 2/3, so bands below 65% are empty for that view. Every band with n ≥ 200 (all events and best
selection) has its predicted mean inside the 99.5% Wilson interval in validation and confirmation.

## Calibration (all 3 events per match; match-level bootstrap, 1,000 draws)
development slope 1.062 [0.98, 1.15] · validation 1.088 [0.98, 1.20] · confirmation 0.949 [0.74, 1.18]; log loss 0.580 / 0.568 / 0.599;
AUC 0.69 / 0.71 / 0.65. **A consistent pattern: slight under-confidence at the top.** ≥85 and ≥90 realise about 1.5–2 pp
above prediction in every period (inherited from the 1X2 slope > 1). It is reported, not corrected (frozen method, no
upward recalibration).

## Structure
- **Selection type:** 1X (home side) is the best DC in 48% of matches and 73% of ≥80 picks (1,353). X2 (away side): 502 ≥80
  picks, 86.2 → 86.9. **12 is never the best selection at ≥80.** P(12) itself reaches 94%, but a high P(12) needs a strong favourite, whose side-plus-draw DC is higher still. As a separate binary event, 12 is covered in the all-events bands.
- **League:** ≥80 share is E0 ~40–45%, SC0 ~36–44%, E1 ~16–26%. Calibration is fine in each league-season, within the noise of small n.
  E1 2021/22 (84.2 → 79.2, n 130) is the weakest cell.
- **Season stability:** ≥80 share 30–35% per season, but **2025/26 is 24%** (partial season, n = 536). Every gate season ≥ 15%.
- **Sensitivity:** odds-ratio and Shin de-vig raise the ≥80 share to 32.7–33.0% at similar calibration; all-books panels
  agree to within 1 pp.

## Live DC price availability (probe 2026-09-24, 1 credit, `DC_LIVE_PRICE_PROBE_2026-09-24.json`)
The Odds API `double_chance` market is live on the per-event endpoint: 4 UK books (William Hill, Paddy Power, Virgin, LiveScore)
for Arsenal v Leeds. Arsenal-or-Draw was quoted at 1.05–1.08, Leeds-or-Draw at 3.0–3.3 and No-Draw at 1.12–1.18. Cost is **1 credit per
event per region**; the bulk endpoint doesn't serve it. The book margin on each DC line is ~5% (WH sum of implied = 2.106 vs 2).
**Economic consequence:** a ≥80% DC has fair odds ≤ 1.25, below the production 1.33 payout floor. As singles,
strong DC selections can never qualify under the current policy. Their use is (a) a probability product (what is
likely), and (b) multi legs, which are always dependent on other markets of the same match.

## Decision gate: **A (provisional)**
Slope CIs include 1 (validation and confirmation), every n ≥ 200 band is inside the 99.5% Wilson interval, and ≥80 share is ≥ 15% every season.
**Qualifier: exposed data.** It becomes a confirmed engine only after the sealed 2026/27 holdout and prospective evidence.
Not money-eligible.
