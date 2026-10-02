# Betfair read-only catalogue audit — what Fraser does, what happens next

Script: `scripts/betfair_catalogue_audit.py` (stdlib only, no installs needed).

## Safety properties (tested in `tests/unit/test_betfair_catalogue_audit.py`)
- **Read-only.** The client refuses any method outside listCompetitions, listMarketTypes, listEvents,
  listMarketCatalogue and listMarketBook, before a request is even built. The script contains no order code at all.
- **Credentials.**
  - Read at run time from the terminal environment; the password is typed at a getpass prompt.
  - Never written to disk, logs or git.
  - Raw API responses go to a gitignored `raw/` folder.
  - Only aggregate coverage (`COVERAGE.csv` / `COVERAGE.json`) is committed.
- **Network.** About 60–120 API calls per run, all read-only. A delayed key costs nothing.

## Why it must run on Fraser's Mac (not GitHub Actions)
Betfair blocks API requests from IP addresses in restricted regions, and the USA is one of them. GitHub-hosted
runners are US-based, so a GitHub secret would not work. The audit therefore runs once, by hand, from a UK machine.

## Manual steps for Fraser (no values are ever shared with Claude)
1. Log in to your own verified Betfair account at betfair.com. Claude cannot create or operate accounts.
2. Create the application keys:
   - Open the Betfair developer portal's **Accounts API Visualiser** (developer.betfair.com → API tools).
   - Run `createDeveloperAppKeys` with any application name, e.g. `pml-research`.
   - This creates two keys: a **Delayed** key (active, free) and a **Live** key (inactive). Live activation costs
     £499 and is NOT wanted.
   - Copy the **Delayed** key's Application Key value. If keys already exist, `getDeveloperAppKeys` shows them.
3. In Terminal, inside the project folder `~/Projects/prediction-markets-lab`, run:
   ```
   export BETFAIR_APP_KEY='<your DELAYED application key>'
   export BETFAIR_USERNAME='<your Betfair username>'
   python3 scripts/betfair_catalogue_audit.py
   ```
   - Type your password at the prompt; it is not echoed or stored.
   - If two-step authentication is on, type the password immediately followed by the current 6-digit code.
4. Expected run time is under 2 minutes. It writes
   `research/platform_v2/price_execution/betfair_audit/COVERAGE.csv` and `COVERAGE.json`.
5. Tell Claude it has run. Claude reads the coverage files through the linked folder, commits only the aggregates,
   and reports.

Names used, never values:
- `BETFAIR_APP_KEY`
- `BETFAIR_USERNAME`
- `BETFAIR_PASSWORD` (optional, prompt preferred)

No GitHub secret is needed.

## What happens immediately after
1. The coverage matrix (10 leagues × families: match odds, corners, bookings/cards, player SOT, player to score,
   player card, GK saves, other) is classified as GOOD / PARTIAL / RARE / ABSENT / UNRESOLVED. It uses the real
   marketTypeCodes and names Betfair returns, not assumed ones.
2. For each family it reports:
   - number of markets;
   - runner structure;
   - share of markets with both back and lay prices;
   - median spread;
   - matched volume, if the delayed key returns it;
   - time to kickoff.
3. Decisions this changes:
   - **Corners:** whether the A/B/C comparison can use the Betfair Exchange as its price source.
   - **Player SOT:** whether the market exists beyond the EPL.
   - **Cards:** whether it stays queued.
4. Recurring Betfair price capture is not started by the audit. It would be a separate, pre-registered step
   requiring Fraser's approval, and it is also constrained by where it can legally run (a UK machine, not US
   runners).
