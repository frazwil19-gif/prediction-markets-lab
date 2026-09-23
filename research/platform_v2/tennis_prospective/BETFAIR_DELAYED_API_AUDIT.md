# Betfair Delayed API Audit (official documentation only; checked 2026-09-23)

| question | official finding | source |
|---|---|---|
| What is the Delayed key for? | "development purposes and any functional testing"; runs on the **production** Exchange; "delayed Betfair price data. The delay is variable between 1 and 180 second snapshots" | Developer Program: *When should I use the Delayed or Live Application Key?* |
| Read-only collection | "If your intention is not to place bets … you should use the delayed rather than the live application key"; read-only use of a Live key is **not permitted** | *What is read-only Betfair API access?* |
| Cost | Delayed: **free** "for development purposes" (private betting customers and licensed vendors). Live: **£499 one-off activation fee**, non-refundable (updated 12 Sep 2026). The £299 in a blog is outdated | *Are there any costs associated with API access?* |
| Authentication | Non-interactive (bot) login: a **self-signed 2048-bit RSA certificate** uploaded to the Betfair account, plus username/password and the `X-Application` app key, at `identitysso-cert.betfair.com/api/certlogin`. 2-step authentication does not interfere | *Non-Interactive (bot) login* |
| Sessions | UK/IE sessions last **24 h**, extended by Keep Alive (not by activity); logins capped at 100/min | *Login & Session Management* |
| **IP restrictions** | API requests from restricted regions are **automatically blocked**. The list **includes the USA** (also Germany, France, Netherlands, Singapore and others) | *Which IP regions are restricted from accessing the Betfair API?* |
| Coverage / ids | all Exchange tennis (ATP, WTA, Challenger, ITF); market and selection ids identical to the historical BASIC archive the engines were validated on | archive inspection (V2-1/V2-2) |

## Consequences
1. **Cost policy:** do not buy the £499 Live key. Nothing here justifies it.
2. **GitHub Actions:** hosted runners run in (mostly US) Azure regions, so **Betfair would block them**, apart from the
   certificate/secret-handling burden. A Betfair feed can therefore run **only locally** (Fraser's UK Mac, online
   at scan time) or on a UK-hosted runner, which is not free.
3. **Terms:** the delayed key is officially for development/testing. A small local research collector sits within the
   spirit of "development"; a standing production feed is a grey area to confirm with Betfair before relying on it.
4. **Credentials:** none exist in the repo `.env` (checked by variable name only). **No adapter was tested; no secret
   was requested.**

## Research adapter design (not built)
`ingestion/betfair_delayed_tennis.py` (local only): certlogin (cert and key paths from env) → `listMarketCatalogue`
(eventTypeId 2, marketTypeCodes MATCH_ODDS, next 36 h, RUNNER_DESCRIPTION, EVENT, COMPETITION) → `listMarketBook`
(priceProjection EX_BEST_OFFERS + lastPriceTraded) → the existing engine's source hierarchy with a new top level
`BETFAIR_LTP` (same data type as the validated estimator) → the same append-only ledger, tagged `source=BETFAIR_LTP`.
Rate limits: well inside Betfair's weight limits (one catalogue call plus about 1 book call per 40 markets). A
cold-start local test would need Fraser to create the key and certificate and put their paths in `.env`.
