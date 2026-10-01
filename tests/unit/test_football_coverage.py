"""Final football coverage: observation != paper eligibility != real money; tier throttle protects Tier 1; shadow
leagues never become paper bets; legacy V1 (paid /scores) scope unchanged; config is the single source."""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from prediction_markets_lab.bet_selection_v2.evaluate import load_config as load_bs
from prediction_markets_lab.ingestion import the_odds_api_loader as L
from prediction_markets_lab.ops import football_coverage as FC
from prediction_markets_lab.prediction_platform import adapters as A
from prediction_markets_lab.prediction_platform import settle as S
from prediction_markets_lab.prediction_platform.registry import Registry

REPO = Path(__file__).resolve().parents[2]
LEAGUES = FC.load()
BUDGET = FC.load_budget()
NOW = datetime(2026, 10, 3, 7, 0, tzinfo=timezone.utc)
TARGET = {"E0", "E1", "E2", "E3", "SC0", "SC1", "SP1", "SP2", "D1", "D2", "I1", "I2", "F1", "F2", "N1", "P1", "B1"}


def _scan():
    spec = importlib.util.spec_from_file_location("run_daily_scan_cov", REPO / "scripts/run_daily_scan.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def test_every_target_league_has_a_recorded_state():
    by = {lg.code: lg for lg in LEAGUES}
    assert set(by) == TARGET
    assert not by["SC1"].observe and "DATA_BLOCKED" in by["SC1"].evidence           # no Odds API key
    tier1 = {"E0", "E1", "SC0", "N1", "D1", "F1"}
    assert {lg.code for lg in LEAGUES if lg.tier == 1} == tier1
    # approved Tier-1 paper leagues all wait for their own first-row PASS; none is ACTIVE yet
    assert {lg.code for lg in LEAGUES if lg.paper_state == FC.PENDING} == tier1
    assert not any(lg.paper_eligible for lg in LEAGUES)
    assert "APPROVED" in by["F1"].evidence
    for code in ("SP1", "I1", "P1", "B1", "E2", "E3", "SP2", "D2", "I2", "F2"):
        assert by[code].paper_state == FC.SHADOW


def test_real_money_allowlist_untouched():
    comp = yaml.safe_load((REPO / "config/competitions.yaml").read_text())["football"]
    assert comp["money_card_competitions"] == ["Premier League", "Championship", "Scottish Premiership"]
    assert set(comp["competitions"]) == {lg.name for lg in FC.observed(LEAGUES)}


def test_loader_and_settlement_follow_the_config():
    cfg = L.TheOddsApiConfig()
    assert cfg.sport_keys == FC.sport_keys(LEAGUES) and len(cfg.sport_keys) == 16
    assert cfg.markets_for("soccer_epl") == ("h2h", "totals") and cfg.markets_for("soccer_spain_la_liga") == ("h2h",)
    assert cfg.markets_for("soccer_netherlands_eredivisie") == ("h2h",)            # O/U not paid outside the legacy trio
    assert all(S.COMP_TO_FD[lg.name] == lg.code for lg in LEAGUES)


def test_tier_floors_throttle_tier3_first_and_never_tier1():
    hard = BUDGET["consumers"]["football_daily_scan"]["hard_floor_remaining"]
    for day in (1, 10, 20, 31):
        f = FC.tier_floors(BUDGET, LEAGUES, NOW.replace(day=day))
        t1, t2, t3 = ({f[lg.sport_key] for lg in FC.observed(LEAGUES) if lg.tier == t} for t in (1, 2, 3))
        assert t1 == {hard} and len(t2) == len(t3) == 1
        assert min(t3) > min(t2) > hard
        assert min(t2) >= max(BUDGET["global_reserve_remaining"],
                              max(c.get("min_remaining", 0) for c in BUDGET["consumers"].values()))


def test_gate_applies_tier_floor(monkeypatch):
    monkeypatch.setenv("THE_ODDS_API_KEY", "test-key-not-real")
    cfg = L.TheOddsApiConfig(gate_horizon_hours=48, hard_floor_remaining=25,
                             floor_by_sport={"soccer_epl": 25, "soccer_spain_la_liga": 300.0, "soccer_france_ligue_two": 400.0})

    def events(sk, c, h=None):
        h.update({"x-requests-remaining": "350"})
        return [{"id": "x", "commence_time": (NOW + timedelta(hours=10)).isoformat()}]
    monkeypatch.setattr(L, "fetch_events_raw", events)
    assert L.fixture_gate("soccer_epl", cfg, NOW).pay
    assert L.fixture_gate("soccer_spain_la_liga", cfg, NOW).pay
    g = L.fixture_gate("soccer_france_ligue_two", cfg, NOW)
    assert not g.pay and "tier throttle" in g.reason


def test_daily_scan_config_and_ledger_consumers():
    m = _scan()
    c = m.gated_odds_config(NOW)
    assert c.floor_by_sport["soccer_epl"] == 25 == c.floor_by_sport["soccer_france_ligue_one"]
    assert c.floor_by_sport["soccer_spain_la_liga"] > 25
    assert m.consumer_for_call("odds:soccer_epl") == "football_daily_scan"
    assert m.consumer_for_call("odds:soccer_italy_serie_a") == "football_shadow_scan"


def test_legacy_v1_ledger_scope_stays_e0_e1_sc0():
    from prediction_markets_lab.decisions.recommendation import RecommendationResult
    from prediction_markets_lab.storage.schemas import MarketRecord
    m = _scan()
    recs = [RecommendationResult(MarketRecord.model_construct(competition=c), 1.0) for c in ("Premier League", "La Liga", "Bundesliga")]
    kept = m.legacy_ledger_scope(recs, m.money_card_competitions())
    assert [r.market_record.competition for r in kept] == ["Premier League"]


def _card(comp):
    ko = (NOW + timedelta(hours=30)).isoformat()
    rows = [{"sport": "football", "competition": comp, "event": "Home v Away", "market": "1x2", "selection": s,
             "estimated_probability": p, "available_odds": o, "bookmaker": "BookA", "kickoff_time": ko}
            for s, p, o in zip(("home", "draw", "away"), (0.74, 0.16, 0.10), (1.40, 6.0, 9.0))]
    return {"data_timestamp": (NOW - timedelta(minutes=5)).isoformat(), "candidates": rows}


def _coverage(active=()):
    from dataclasses import replace
    return {lg.name: (replace(lg, paper_state=FC.ACTIVE, first_row_pass="test") if lg.name in active else lg) for lg in LEAGUES}


@pytest.mark.parametrize("comp,active,paper", [("Premier League", (), False), ("Ligue 1", (), False),
                                               ("Premier League", ("Premier League",), True), ("Ligue 1", ("Ligue 1",), True),
                                               ("La Liga", (), False), ("League Two", (), False), ("Unknown League", (), False)])
def test_only_first_row_passed_leagues_can_paper_bet(comp, active, paper):
    reg = Registry.load()
    ctx = A.RunContext(None, None, 1.33)
    preds, _ = A.football_from_card(_card(comp), reg, ctx, NOW, "t", coverage=_coverage(active))
    one = [p for p in preds if p.market == "1x2"]
    assert len(one) == 3                                                                  # observed either way
    paper_statuses = load_bs(REPO / "config/bet_selection_v2.yaml")["decision_gates"]["paper_bet"]["engine_statuses"]
    for p in one:
        assert (p.engine_status in paper_statuses) is paper
        assert (p.engine_status == FC.SHADOW_LEAGUE_STATUS) is (not paper)
        assert "live estimator" in p.historical_support                                    # engine provenance kept
        if not paper:
            assert p.single_eligible is False
    if comp in ("Premier League", "Ligue 1") and not paper:
        assert "PENDING FIRST-ROW PASS" in one[0].historical_support
    base, _ = A.football_from_card(_card(comp), reg, ctx, NOW, "t")                        # same frozen estimator
    assert [p.estimated_probability for p in base if p.market == "1x2"] == [p.estimated_probability for p in one]


def test_config_validation_refuses_unsafe_states(tmp_path):
    bad = yaml.safe_load((REPO / "config/football_coverage.yaml").read_text())
    for lg in bad["leagues"]:
        if lg["code"] == "SP1":
            lg["paper_state"] = "PENDING_FIRST_ROW_PASS"                                 # a Tier 2 league cannot be paper
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(bad))
    with pytest.raises(ValueError, match="paper-eligible"):
        FC.load(p)
    good = yaml.safe_load((REPO / "config/football_coverage.yaml").read_text())
    good["leagues"][0]["paper_state"] = "ACTIVE"                                          # ACTIVE without a recorded PASS
    p.write_text(yaml.safe_dump(good))
    with pytest.raises(ValueError, match="first_row_pass"):
        FC.load(p)
