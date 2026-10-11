from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from prediction_markets_lab.execution import broker as B
from prediction_markets_lab.execution.guards import DayState, Quote, Signal
from prediction_markets_lab.paper_orders import ledger as LG
from prediction_markets_lab.paper_orders import report as RP

REPO = Path(__file__).resolve().parents[2]
CFG = yaml.safe_load((REPO / "config/execution.yaml").read_text())
NOW = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)


def sig(key="s1", ev="e1", eng="tennis", stake=1.0, mn=1.5):
    return Signal(key, ev, "m1", "A", eng, 0.7, mn, stake)


def quote(ev="e1", odds=1.6, age=10, open_=True):
    return Quote(ev, "m1", "A", odds, NOW - timedelta(seconds=age), open_)


def test_live_environment_is_refused():
    with pytest.raises(B.LiveExecutionDisabled):
        B.broker_for({**CFG, "environment": "LIVE"})
    assert CFG["environment"] == "PAPER"


def test_guards_cover_every_rejection(tmp_path):
    a = tmp_path / "audit.csv"
    st = DayState()
    run = lambda s, q: B.execute(s, q, st, CFG, NOW, tmp_path, a).reason
    assert run(sig(), quote()) == "SIMULATED_FULL_FILL"
    assert run(sig(), quote()) == "DUPLICATE"
    assert run(sig("s2"), quote()) == "EVENT_LIMIT"
    assert run(sig("s3", "e3"), quote("e3", age=500)) == "STALE_PRICE"
    assert run(sig("s4", "e4"), quote("e4", odds=1.49)) == "BELOW_MIN_ODDS"
    assert run(sig("s5", "e5"), quote("e5", open_=False)) == "MARKET_CLOSED"
    assert run(sig("s6", "e6", stake=2.0), quote("e6")) == "STAKE_LIMIT"
    assert run(sig("s7", "e7"), quote("e8")) == "IDENTITY_MISMATCH"
    assert run(sig("n1", "n1", eng="nfl_moneyline.market"), quote("n1")) == "SIMULATED_FULL_FILL"
    assert run(sig("n2", "n2", eng="nfl_moneyline.market"), quote("n2")) == "ENGINE_LIMIT"
    for i in range(3):
        run(sig(f"c{i}", f"c{i}"), quote(f"c{i}"))
    assert run(sig("c9", "c9"), quote("c9")) == "DAILY_STAKE_CAP"
    st2 = DayState(realised_pnl_gbp=-5.0)
    assert B.execute(sig("l1", "l1"), quote("l1"), st2, CFG, NOW, tmp_path, a).reason == "DAILY_LOSS_LOCK"
    (tmp_path / "data/private").mkdir(parents=True)
    (tmp_path / CFG["kill_switch_file"]).write_text("stop")
    assert B.execute(sig("k1", "k1"), quote("k1"), DayState(), CFG, NOW, tmp_path, a).reason == "KILL_SWITCH"
    assert len(a.read_text().strip().splitlines()) == 1 + 16     # every attempt audited


def test_paper_order_ledger_on_repo_data():
    cfg = yaml.safe_load((REPO / "config/paper_mode.yaml").read_text())
    orders = LG.build(REPO, cfg, NOW)
    assert orders and all(o["simulated_fill_odds"] == o["available_odds"] for o in orders)   # fill = decision price
    assert {o["execution_class"] for o in orders} <= {"BOOKMAKER_ONLY", "EXCHANGE_EXECUTABLE", "API_EXECUTABLE"}
    assert {o["tier_now"] for o in orders} <= {"PAPER_ONLY", "PROVISIONAL_LIVE", "LIVE_ELIGIBLE"}
    r = RP.build(REPO, orders, cfg, NOW)
    assert set(r["windows"]) == {"weekly", "monthly", "all"} and r["mode"].startswith("PAPER")
    assert LG.min_odds(0.75) == 1.36 and LG.ev_band(0.015) == "1-2"
