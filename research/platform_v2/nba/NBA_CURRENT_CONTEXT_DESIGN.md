# NBA Current-Context Design (not implemented)

| context | historically modelled? | live source (future) | how it would enter |
|---|---|---|---|
| rest / back-to-back / 7-day load | **yes** (in `data_logit`; small effect) | schedule from the odds feed's commence_time | already a feature |
| home court / neutral | yes (Elo HCA, neutral flag) | feed venue | already |
| injuries / rest days for stars / late scratches | **no** (no reachable historical source) | official NBA injury report (published at fixed times on game days); lineups ~30 min pre-tip | only as a separately validated adjustment. First archive live injury reports prospectively, then test whether they add information *beyond the market* (which already prices announced injuries) |
| trades / roster changes | no | transaction feeds | via Elo resets only if tested |
| starting lineups | no | ~30 min pre-tip | same as injuries |
Rules: no subjective or AI adjustments to probabilities. A context input earns a place only through the promotion
standard (pre-registered, chronological, sealed). Until then the board shows `context: NONE`. Important practical
note: the validated estimator is the *closing* market, which already embeds news up to tip-off. A morning scan sees
earlier prices that may not yet reflect late injury news. This is the main live-compatibility risk for NBA, so a
prospective NBA board should snapshot as close to tip-off as the credit budget allows.
