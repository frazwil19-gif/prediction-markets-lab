# V2-6 Live-Money Gate — Pre-registration (2026-09-29, before any paper selection existed)

Real-money betting stays **disabled** (`real_money_enabled: false`). Passing this gate does **not** switch anything on. It
qualifies the system to *ask* Fraser for explicit approval of a tiny, capped live test. Positive estimated EV is not
profitability, and a small-sample positive P&L is not evidence of an edge.

All criteria are evaluated on paper selections recorded prospectively under a **single frozen rule_version**. Changing a
gate restarts the count.

| # | criterion | requirement |
|---|---|---|
| 1 | Sample size | ≥ **300** settled PAPER_BET singles, ≥ 60 calendar days, ≥ 2 sports or ≥ 2 engines contributing ≥ 50 each |
| 2 | Calibration | per engine at ≥ 100 settled: \|mean P − hit rate\| ≤ 3 pp, and hit rate inside the 95% Wilson CI of mean P; no −10 pp alarm |
| 3 | Pricing reality | ≥ 90% of selections priced ≤ 240 min before the decision; Fraser spot-checks ≥ 20 selections at decision time and confirms the price was really available at stake size (logged) |
| 4 | Closing value | median CLV (selection odds vs the last pre-start snapshot) ≥ 0 over ≥ 150 selections with a later snapshot |
| 5 | Positive value | mean estimated net EV ≥ 2%, **and** realised ROI > 0, **and** a one-sided bootstrap 90% lower bound on realised ROI > −2% (not significantly worse than break-even) |
| 6 | Operations | ≥ 95% of scheduled evaluation runs completed in the last 30 days; 0 immutability violations; median settlement lag ≤ 72 h; 0 unresolved settlement disagreements |
| 7 | Risk | the chosen policy on £30 (simulated) never hit the −30% drawdown stop and its max drawdown ≤ 20%; minimum-stake feasibility shown for the chosen bankroll |

If passed: a live test proposal (a separate document) with a hard cap (for example £20 total at risk), the same rule_version,
manual placement by Fraser only, and automatic stop conditions. It needs Fraser's explicit written approval before any
real stake. If a criterion fails at its sample threshold, the result is recorded as negative, not re-tuned on the same data.

**Economics note (context, not a target):** at a 2% net edge, £300/month of expected profit needs about £15,000 of monthly
turnover. On a £30 bankroll with ≤ 5% stakes, that is about 10,000 bets per month. A small bankroll can test whether an edge
exists; it cannot produce that income.
