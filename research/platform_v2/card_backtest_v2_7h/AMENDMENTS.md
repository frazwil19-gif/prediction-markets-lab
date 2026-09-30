# V2-7H pre-registration amendments

**A1 (2026-09-30, written before any V2-7H result was computed).** An exchange cannot price a multi. football-data's `BF` column
(2024/25 only) is also of uncertain identity (exchange or sportsbook, per V2-6H). So `BF` is used for **singles only**: priced
cards with k ≥ 2 use the UK sportsbooks B365, WH and BW. Nothing else changes.

**A2 (2026-09-30, written before results).** Clarifies how HIGH_P strategies (S1, S2, S5) are priced in scenarios that have
real prices. The legs are chosen on probability first. Then, among the books that price every chosen leg in that snapshot, the
book with the highest card price is used. The book is chosen at decision time; no outcome is involved. If no single book prices
every leg, that day has no priced card for the strategy, and the day is counted.
