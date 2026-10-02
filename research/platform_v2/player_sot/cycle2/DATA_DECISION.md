# Data-access decision: API-Football for Player SOT Cycle 2 (2026-10-02)

**Decision (Fraser, 2026-10-02):** proceed with API-Football, using our own reading of the published Terms of Service
(API-Football and API-SPORTS terms, last updated 21 May 2025). There is no confirmation from a human at API-Football.

**Evidence considered**
- **What the published terms forbid:** resale and redistribution, multiple accounts, and exceeding rate limits.
- **What they don't cover:** they are silent on private storage, research and derived models.
- **Betting clause:** the terms state that use "for betting platforms... may require additional licenses from the
  relevant rights holders". Our use is a private model for Fraser's own manual bets. There is no platform, no users,
  and no redistribution.
- **The dashboard AI chatbot:**
  - It said private storage and models are permitted and the betting clause targets platforms.
  - BUT it cited a section ("Internal storage, machine learning, and retention after subscription expiry") that does
    not exist in either published terms page.
  - So it is treated as non-authoritative.

**Conditions**
- One free account; no purchase.
- Requests stay within the free plan and are throttled.
- Only the pre-registered minimum: EPL seasons 2022, 2023 and 2024 (2024 as required by the cycle-2 sample rule),
  about 63 requests.
- Raw and player-level data stay private in `data/private/api_football/`, which is gitignored and never committed or
  published. Only aggregate research results are committed.
- If API-Football staff or a rights holder later object, stop using the data and record it here.
