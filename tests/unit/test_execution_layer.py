"""Price/execution layer: consensus vs best executable kept separate; commission never assumed zero; staleness."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from prediction_markets_lab.research_shadow.execution import Policy, Quote, assess, consensus, net_odds

NOW = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)
T = NOW - timedelta(minutes=2)
POL = Policy(commission={"betfair_ex_uk": 0.05, "matchbook": None}, max_quote_age_minutes=30, max_exchange_spread=0.10)
SIDES = ("over", "under")


def test_directive_example_best_executable_is_exchange_net():
    q = [Quote("bookA", "over", 1.50, observed_at=T), Quote("bookB", "over", 1.58, observed_at=T), Quote("bookC", "over", 1.63, observed_at=T),
         Quote("betfair_ex_uk", "over", 1.705, 1.72, observed_at=T, is_exchange=True)]
    a = assess("over", 0.64, 0.61, q, SIDES, POL, NOW)
    assert a.fair_odds == pytest.approx(1.5625)
    assert a.best_venue == "betfair_ex_uk" and a.best_net_odds == pytest.approx(net_odds(1.705, 0.05), abs=1e-4)
    assert a.central_ev == pytest.approx(0.64 * net_odds(1.705, 0.05) - 1, abs=1e-4)
    assert a.ev_at_lower_p < a.central_ev
    assert a.decision_price is None                   # never filled by the execution layer


def test_unknown_commission_and_stale_quotes_excluded_with_reason():
    q = [Quote("matchbook", "over", 2.2, 2.22, observed_at=T, is_exchange=True), Quote("bookA", "over", 2.0, observed_at=NOW - timedelta(hours=2)),
         Quote("bookB", "over", 1.9, observed_at=T)]
    a = assess("over", 0.55, None, q, SIDES, POL, NOW)
    assert {e["reason"] for e in a.excluded} == {"COMMISSION_UNKNOWN", "STALE_OR_UNTIMED"}
    assert a.best_venue == "bookB" and a.ev_at_lower_p is None


def test_consensus_needs_both_sides_and_tight_exchange_spread():
    q = [Quote("bookA", "over", 1.9, observed_at=T), Quote("bookA", "under", 1.9, observed_at=T),
         Quote("bookB", "over", 1.8, observed_at=T),                                            # one-sided: excluded
         Quote("betfair_ex_uk", "over", 2.0, 2.6, observed_at=T, is_exchange=True), Quote("betfair_ex_uk", "under", 1.9, 2.0, observed_at=T, is_exchange=True)]
    cons, venues = consensus(q, SIDES, POL, NOW)
    assert venues == ["bookA"] and cons["over"] == pytest.approx(0.5)
