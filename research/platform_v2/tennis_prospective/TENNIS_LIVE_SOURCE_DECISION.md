# Tennis Live-Source Decision (V2-2): **A — The Odds API is sufficient for initial ATP prospective validation**

| criterion | The Odds API (built, running) | Betfair Delayed (designed) |
|---|---|---|
| Coverage | Slams, ATP 1000, ATP 500; WTA 1000/500 (≈45% of priced ATP matches, holding 61% of ATP ≥80% predictions on the 2024–25 holdout). No 250s, Challengers or ITF | all tennis |
| Probability-source compatibility | `betfair_ex_uk` back + lay quotes → midpoint (EXCHANGE_MID). Close to, **not identical to**, the historical last-traded price. Verified live: the first run returned back and lay for all 6 matches | identical data type (LTP) and identical ids |
| Reliability | already runs unattended for football | needs certificate login; untested |
| Cost | free tier, 1 credit per active key per scan (first live call: exactly 1 credit) | free (delayed), £499 Live not justified |
| Automation | GitHub Actions ✔ | **GitHub-hosted runners are blocked (USA is a restricted IP region)**; local-only |

Decision **A**: prospective validation starts now with The Odds API in GitHub Actions. Betfair Delayed is a
**later local complement** (option B), useful for widening coverage to 250s once Fraser chooses to create a delayed
key and certificate. It is not needed to start, and production never depends on it.
