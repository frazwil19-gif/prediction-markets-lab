# Engine Integration Audit (V2-5, 2026-09-24)

| engine | integrated how | credits | rows/event | status on board | notes |
|---|---|---|---|---|---|
| ATP match winner @1 | mirror of `tennis_predictions/ledger_predictions.csv` (IDs preserved) | 0 extra | winner | VALIDATED_HISTORICAL / COLLECTING | 0 ATP predictions so far (no covered ATP event since activation) |
| WTA match winner @1 | same | 0 extra | winner | VALIDATED_HISTORICAL / COLLECTING | 8 predictions, 0 settled (the first settlement run is due at the 22:30 tennis run) |
| NBA moneyline @1 | `collect-nba`: /sports + /events (free), then one h2h call per UTC day when games start within 36 h | ≤1/day odds + 2 per 3 days scores (cap 60) | favourite | VALIDATED_HISTORICAL / AWAITING_SEASON | activates 2026-10-20 (opening night); pre-season never collected; exchanges excluded |
| Football DC @1 | derived from the daily card's 1X2 triplet (renormalised) | **0** | 1X, X2, 12 | **PROVISIONAL_PROSPECTIVE** | synthetic DC price = dutch of best 1X2 prices (0 credits); explicit DC quotes are not fetched |
| Football 1X2 @1 | daily card consensus | 0 | H/D/A | VALIDATED_HISTORICAL | the production money engine; rarely ≥80% |
| Football O/U 2.5 @1 | daily card | 0 | favoured side | VALIDATED_HISTORICAL | almost never ≥80% |
| Football BTTS | not wired to live data | — | — | RESEARCH_VALIDATED / NOT_WIRED | not added: low value (0% ≥75%) and it would cost credits per event |

Football snapshot: the first daily scan within 48 h of kickoff. The Odds API feed in the 24 Sep card (and the 22 Sep card) has no league fixture before 9 Oct, so football rows start from about the 8 Oct scan. That is correct fail-closed behaviour, not a fault.
Frozen engines were not modified: tennis code, NBA method, 1X2 consensus and DC construction are untouched.
