# Prospective Football DC Paper Board: design (NOT ACTIVATED)

- **Where:** extra rows produced by the existing `daily_scan` from the h2h odds it **already fetches** (0 extra credits),
  under engine `football_double_chance.derived_1x2@1`. No separate workflow.
- **What is logged** (append-only, the first snapshot is canonical, id = sha256(engine@version|event|selection)[:16]): event, competition,
  kickoff, selection (1X/X2/12), P(DC), fair odds, **synthetic DC price** from the best h2h prices (1/(1/o_a + 1/o_b), a
  dutched bet, 0 credits), book count, prediction timestamp, **configured schedule time, actual run start, minutes to kickoff**.
- **Which rows:** every match's best DC at ≥ 70% (≥80 flagged). This is a probability board, not a bet list.
- **Real DC quotes (optional):** at most 4 events/week from `double_chance` (1 credit each), taken from the reserve only if the
  per-consumer guard allows. This measures how synthetic prices compare with quoted ones. Off by default.
- **Settlement:** from the football-data.co.uk adapter once migrated (the DC outcome follows from FTR); otherwise the Odds API fallback.
- **Performance:** bands / thresholds / slope as in the protocol, by league and type; reviewed at 100 and 300 settled rows.
- **Activation needs Fraser's approval** plus the settlement migration gate.
