# V2-7H pre-registration amendments

**A1 (2026-09-30, written before any V2-7H result was computed).** An exchange cannot price a multi. football-data's `BF` column
(2024/25 only) is also of uncertain identity (exchange or sportsbook, per V2-6H). So `BF` is used for **singles only**: priced
cards with k ≥ 2 use the UK sportsbooks B365, WH and BW. Nothing else changes.

**A2 (2026-09-30, written before results).** Clarifies how HIGH_P strategies (S1, S2, S5) are priced in scenarios that have
real prices. The legs are chosen on probability first. Then, among the books that price every chosen leg in that snapshot, the
book with the highest card price is used. The book is chosen at decision time; no outcome is involved. If no single book prices
every leg, that day has no priced card for the strategy, and the day is counted.

**A3 (2026-09-30, written AFTER the first full run; reporting and disclosure only. No analysis was re-specified and nothing was re-run to change a result.)**
1. **Short comparisons.** A card-vs-singles comparison with fewer than 30 days is reported as `INSUFFICIENT_DAYS`. A day-bootstrap CI from 1–29 days is degenerate; for example, one day produced a "CARD" verdict. This is applied in `simulation_summary.csv`, and the raw per-day comparison values stay in `RESULTS.json`.
2. **S2 is empty in every sport and scenario.** No development-period 5-pp singles band met |bias| ≤ 1 pp **and** a CI half-width ≤ 1.5 pp. The half-width alone needs roughly 4,000 legs per band; development bands hold roughly 100–3,700. S2 is recorded as a null result caused by an over-strict pre-registered criterion. It is **not** re-specified here. Any wider-band variant would be a new, labelled exploratory analysis.
3. **Singles precision threshold.** The code uses a P1 precision threshold of 2.0 pp for k = 1. The pre-registration stated thresholds only for k = 2 (2.0 pp) and k = 3 (3.0 pp). Disclosed here; it changes no verdict, since every k = 1 cell is either ≤ 1.8 pp or clearly above 2.0 pp (football 3.0 pp).
