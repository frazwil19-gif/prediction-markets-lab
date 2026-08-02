# Risk Management

## Bankroll and staking defaults (£10 bankroll)

See `config/bankroll.yaml` for the authoritative values (all
configurable):

| Setting | Default |
|---|---|
| Starting bankroll | £10.00 |
| Normal stake | £0.25 |
| Maximum stake | £0.50 |
| Maximum daily exposure | £0.75 |
| Maximum open bets | 3 |
| Daily loss stop | £0.75 |
| Weekly loss stop | £2.00 |
| Martingale | never allowed |
| Accumulators | never allowed |
| Chasing losses | never allowed |
| Automated execution | never allowed |

Implemented in `risk/bankroll.py` (`BankrollState`), `risk/staking.py`
(`StakingConfig`, `recommended_stake_gbp`), `risk/exposure.py`
(`ExposureState`), `risk/loss_locks.py` (`check_loss_locks`), and
combined in `risk/decision_gates.py` (`check_risk_gates`).

## Grading thresholds

See `config/thresholds.yaml` and `docs/MODEL_GOVERNANCE.md` for how
grades interact with model status. Summary (project instructions,
section 10):

| Grade | Net EV | Edge | Bookmakers | Stake | Outcome |
|---|---|---|---|---|---|
| A+ | ≥ 8% | ≥ 4pp | ≥ 5 | £0.50 max | Possible live trade |
| A | ≥ 5% | ≥ 3pp | ≥ 4 | £0.25 | Possible live trade |
| B | ~2–5% | — | — | £0 | Paper trade only |
| C | below B, ≥ 0% (assumed floor) | — | — | £0 | Watchlist only |
| Reject | < 0% (assumed floor), or any safety gate fails | — | — | £0 | No trade |

A+ and A additionally require: current price, adequate exchange
liquidity, no unresolved team-news issue, high data quality, high
confidence, and exact market-rule match. Any failure on these gates
forces a Reject regardless of the numeric EV/edge — implemented as
hard gates at the top of `decisions/grading.py::grade_opportunity`.

## Safety and failure conditions (project instructions, section 21)

The system must reject or halt when any of the following are true.
Stage 1 implements the ones marked ✅ as explicit checks; the rest
require Stage 2+ data ingestion to detect and are listed here so they
are not forgotten.

- ✅ Exchange price is no longer current (`exchange_price_current` gate)
- ✅ Market names/rules do not match (`market_rules_match` gate)
- ✅ Liquidity is insufficient (`liquidity_adequate` gate)
- ✅ Data quality is insufficient (`data_quality_ok` gate)
- ✅ Daily exposure limit reached (`risk.exposure.can_add_stake`)
- ✅ Daily loss stop reached (`risk.loss_locks.check_loss_locks`)
- ✅ Weekly loss stop reached (`risk.loss_locks.check_loss_locks`)
- ✅ Proposed stake exceeds configured maximum
  (`risk.decision_gates.check_risk_gates`)
- ⏳ Odds are missing (Stage 2 ingestion validation)
- ⏳ Outcomes do not sum to a valid market (Stage 2 ingestion validation)
- ⏳ Settlement rules differ (Stage 2 ingestion validation)
- ⏳ Bookmaker count is too low for the intended grade (partially
  covered today via the `bookmaker_count` grading input, but no
  automatic ingestion-time check yet)
- ⏳ Commission is unknown (Stage 2 config validation)
- ⏳ Bankroll data is inconsistent (Stage 2 storage validation)
- ⏳ Duplicate exposure exists (Stage 2 storage validation)
- ⏳ Data appears corrupted (Stage 2 ingestion validation)
- ⏳ Model version is unavailable (Stage 3+ model registry)
- ⏳ Unresolved withdrawal/injury information is material — Stage 1
  exposes this as the `no_material_info_risk` boolean input to grading,
  but does not yet automatically detect it from data.
