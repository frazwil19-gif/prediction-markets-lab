# V2-13 — Football prospective pre-registration (1X2 + Double Chance)

Fixed 2026-10-01, before any football row exists in `predictions/unified_ledger.csv` (0 rows to date). The first rows are expected automatically from about 7–8 Oct 2026, through the existing V2-5 wiring, when E0/E1/SC0 fixtures enter the 48h window.

Nothing below changes a threshold, a frozen engine or a historical record.

## 1. Estimator provenance: live ≠ validated

| | Validated (historical) | Live (prospective) |
|---|---|---|
| id | `football_1x2.market_consensus` v1 (ledger_version 1) | **`football_1x2.market_consensus@1-live`** (registry `estimator_id`; ledger_version unchanged, so prediction ids are unchanged) |
| Prices | **Closing** odds (football-data.co.uk) | UK Odds API h2h, **first scan within 48h** of kickoff (typically 24–48h before) |
| Books | B365/BW/PS (V2-1, DC) or ≥4 books (Gate 1) | About 20 UK books |
| Consensus | Mean (V2-1/DC) or median (Gate 1) of per-book de-vigged P | Median of per-book proportional de-vig (`probability/market_pipeline.compute_market_consensus`) |

**Rule:**
- Historical closing-estimator calibration is **not** attributed to the live estimator. The registry records `calibration_transfer: NOT_ASSUMED` and `calibration_status`.
- Every football prediction's `historical_support` text names the live estimator.
- The prospective ledger is the test of the live estimator, and only it.

## 2. 1X2 normalisation

**Audit.** Over all 413 complete H/D/A triplets on the committed daily cards (19–30 Sep), the per-outcome medians sum to 0.9915–1.0132 (median 0.99990). The reason is that medians of per-book de-vigged probabilities are taken outcome by outcome, so they are not jointly constrained.

**Rule (stage-a-2):**
- **Ledger rows keep the raw values** (provenance; never rewritten).
- **Stage A displays the normalised triplet** q_k = p_k / Σp. That is the mutually exclusive H/D/A distribution.
- Every derived identity uses q. The Double Chance engine already uses the renormalised triplet (`adapters.py`), so P(1X) = q_H + q_D exactly.
- Normalisation is applied only when all three rows of the same snapshot (same event, engine and prediction timestamp) are present. Otherwise the row is shown raw and flagged `TRIPLET_INCOMPLETE`.
- The maximum display change is about 1.3pp, and is reported per row (`p_raw` vs `probability`).

## 3. Stage A uncertainty for football (approximation; labelled)

- **Source sample:** `research/platform_v2/double_chance/DC_PRIMARY_PANEL_DERIVED.csv`.
  - 5,897 matches, E0/E1/SC0, 2020/21–2025/26; all exposed data.
  - Closing B365/BW/PS, multiplicative de-vig, mean, renormalised.
  - 1X2 P is recovered exactly as P(H) = 1 − P(X2), and so on.
- **Method:** per market (1X2 rows / DC rows) and band (<50, 50–65, 65–80, ≥80%, the same coarse bands as tennis), σ = the **match-clustered bootstrap SE** of the band's realised rate (1,000 resamples, seed 20261001).
  - This is the sampling precision of the historical calibration evidence, and it handles the dependence of 3 rows per match.
  - Wilson half-width/1.96 is reported alongside for reference.
- **Script and output:** `scripts/v2_13_football_sigma_evidence.py` → `FOOTBALL_SIGMA_EVIDENCE.json`.

| Market | Band | Rows | Effective N (matches) | Mean predicted → actual | σ |
|---|---|---|---|---|---|
| 1X2 | 50–65% | 1,691 | 1,691 | 56.5 → 55.9 | 1.26pp |
| 1X2 | 65–80% | 644 | 644 | 71.8 → 74.8 | 1.67pp |
| 1X2 | ≥80% | 191 | 191 | 83.8 → 89.0 | 2.16pp |
| DC | 50–65% | 3,460 | 3,323 | 58.1 → 57.6 | 0.81pp |
| DC | 65–80% | 9,100 | 5,147 | 72.5 → 72.7 | 0.38pp |
| DC | ≥80% | 2,605 | 1,855 | 85.8 → 86.7 | 0.64pp |

**Scope of σ:**
- The uncertainty is **band-specific, not event-specific**. The same σ applies to every prediction in a band.
- **It excludes:**
  - (a) the bias of the live 24–48h estimator relative to closing, which is unmeasured;
  - (b) the systematic calibration offsets visible above, which are reported, not corrected (e.g. 1X2 ≥80% realised +5pp above predicted).
- Stage A labels it `HIST_BAND_CLUSTERED_SE (closing estimator; live-timing bias excluded)`.
- O/U 2.5 has no evidence file, so its σ is `NOT_ESTIMATED`.

## 4. Double Chance scope

- **Approved 2026-10-01 for prospective SHADOW probability collection only.**
- **Not approved for:** real money, paper staking, or Stage B qualification using synthetic prices. This is recorded in the registry `approval` block.
- **Stage B status: DATA_BLOCKED.**
  - No executable DC prices are collected; per-event DC quotes cost 1 credit per event and are not approved.
  - `SYNTHETIC_DUTCH_BEST_1X2` is never parsed as an executable price; this is tested.
- **Sealed holdout:** protected by `DC_HOLDOUT_NO_PEEK.md`.

## 5. Evidence-based promotion (not elapsed time)

The V2-12 phrase "4–6 weeks of prospective rows" is **withdrawn**. Elapsed time is reported but is never evidence.

The pre-registered sample-triggered rules in `unified_board/PROSPECTIVE_PROTOCOL.md` §5–6 remain the authority:
- maturity counted in **matches/events, not rows**;
- an engine becomes reviewable at INTERMEDIATE: ≥ 300 settled events and ≥ 100 at ≥ 80%;
- the alarm rule is unchanged.

**Proposed amendment A1 (needs your approval; not active until approved).** The ≥80% count rarely binds where a bet can actually occur. 1X2 singles require fair odds ≥ 1.33, i.e. P ≤ 0.752. So a review intended to move an engine toward Stage B must also report, for the **probability bands in which Stage B can act**:
- effective N (independent events) and Wilson 95% precision of realised minus predicted, with the event-clustered calibration slope and CI;
- the 99.5% Wilson band check;
- stability (first half vs second half of the prospective sample);
- data-quality failure rate (rows lost to staleness, settlement mapping or missed scans);
- estimator consistency (live vs closing P on the same matches, once closing odds are available from football-data.co.uk);
- clustering (same matchday or league).

Promotion is decided on these quantities, never on the number of weeks elapsed.
