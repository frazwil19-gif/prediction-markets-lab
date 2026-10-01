"""V2-13 football readiness: aliases, universe guard, estimator provenance, DC approval scope, sigma evidence,
sealed-holdout no-peek masking and the guarded one-shot DC holdout opener (never opened here)."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

from prediction_markets_lab.prediction_platform import performance as P
from prediction_markets_lab.prediction_platform.registry import Registry
from prediction_markets_lab.prediction_platform.settle import COMP_TO_FD
from prediction_markets_lab.settlement.football_data_results import load_settlement_aliases
from prediction_markets_lab.normalisation.team_names import normalise_team_name
from prediction_markets_lab.ingestion.the_odds_api_loader import TheOddsApiConfig

REPO = Path(__file__).resolve().parents[2]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"{name}_t13", REPO / f"scripts/{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------- settlement aliases / universe
def test_bolton_and_lincoln_resolve_from_both_sources():
    a = load_settlement_aliases()
    assert normalise_team_name("Bolton", a) == normalise_team_name("Bolton Wanderers", a) == "Bolton Wanderers"
    assert normalise_team_name("Lincoln", a) == normalise_team_name("Lincoln City", a) == "Lincoln City"


def test_every_team_on_the_daily_cards_resolves():
    a = load_settlement_aliases()
    names = set()
    for f in (REPO / "daily_cards").glob("*/card.json"):
        for c in json.loads(f.read_text()).get("candidates", []):
            if c.get("sport") == "football":
                names |= set(c["event"].split(" v ", 1))
    assert names and not [n for n in names if normalise_team_name(n, a) is None]


def test_active_competitions_have_odds_key_and_settlement_mapping():
    comps = yaml.safe_load((REPO / "config/competitions.yaml").read_text())["football"]
    keyed = set(TheOddsApiConfig().sport_keys.values())
    for c in comps["competitions"]:
        assert c in keyed and c in COMP_TO_FD, c
    assert "Champions League" in [d["name"] for d in comps["disabled_competitions"]]


# ---------------------------------------------------------------- registry provenance / approval
def test_live_estimators_are_named_and_calibration_not_transferred():
    reg = Registry.load()
    assert not reg.validate()
    x = reg.get("football_1x2.market_consensus")
    assert x["estimator_id"] == "football_1x2.market_consensus@1-live" and x["calibration_transfer"] == "NOT_ASSUMED"
    assert x["ledger_version"] == "1"                      # prediction ids unchanged
    assert "live estimator football_1x2.market_consensus@1-live" in reg.support_text("football_1x2.market_consensus")
    assert all(e.get("calibration_status") for e in reg.engines.values())


def test_double_chance_approval_scope():
    dc = Registry.load().get("football_double_chance.derived_1x2")
    assert dc["status"] == "PROVISIONAL_PROSPECTIVE" and dc["money_eligible"] is False
    assert dc["approval"]["scope"] == "prospective shadow probability collection only"
    assert set(dc["approval"]["not_approved"]) == {"real money", "paper staking",
                                                   "Stage B financial qualification using synthetic prices"}
    assert dc["stage_b_status"].startswith("DATA_BLOCKED")
    assert "not active" not in dc["prospective"]


def test_synthetic_dc_price_is_never_executable():
    from prediction_markets_lab.bet_selection_v2 import prices as PR
    row = {"live_price": "1.20", "live_price_source": "SYNTHETIC_DUTCH_BEST_1X2", "prediction_timestamp": "2026-10-08T07:00:00+00:00",
           "estimated_probability": "0.85", "prediction_valid": "True", "prediction_id": "x", "sport": "football"}
    assert PR.from_ledger_row(row) is None
    assert PR.football_from_card({**row, "market": "double_chance", "selection": "1X", "event_key": "k"}, {"candidates": []}) == []


# ---------------------------------------------------------------- sigma evidence
def test_sigma_evidence_is_reproducible_and_consistent():
    ev = json.loads((REPO / "research/platform_v2/v2_13_football/FOOTBALL_SIGMA_EVIDENCE.json").read_text())
    assert ev["matches"] == 5897 and ev["exposed_data"] is True
    x = {b["band"]: b for b in ev["markets"]["1x2"]}
    d = {b["band"]: b for b in ev["markets"]["double_chance"]}
    assert x["80%+"]["rows"] == 191 and d["80%+"]["effective_n_matches"] == 1855   # = DC_REPORT / registry figures
    assert sum(b["effective_n_matches"] for b in ev["markets"]["1x2"] if b["band"] != "<50%") <= 5897
    for bs in ev["markets"].values():
        for b in bs:
            assert 0 < b["sigma_clustered_se"] < 0.05


# ---------------------------------------------------------------- no-peek masking
def _row(eid, start, pid, p=0.85, y=1):
    return ({"prediction_id": pid, "engine_id": eid, "engine_version": "1", "sport": "football", "market": "double_chance",
             "event_key": f"k{pid}", "event_start": start, "estimated_probability": str(p), "prediction_valid": "True",
             "minutes_to_event": "1500"},
            {"prediction_id": pid, "settlement_status": "SETTLED", "correct": str(y)})


def test_dc_rows_inside_closed_holdout_window_are_masked_everywhere():
    dc, x12 = "football_double_chance.derived_1x2", "football_1x2.market_consensus"
    pairs = [_row(dc, "2026-10-10T14:00:00+00:00", "a"), _row(dc, "2027-01-10T14:00:00+00:00", "b"),
             _row(x12, "2026-10-10T14:00:00+00:00", "c")]
    preds, sett = [p for p, _ in pairs], {s["prediction_id"]: s for _, s in pairs}
    g = [P.HoldoutGuard(dc, "2026-08-01", "2026-12-31", opened=False)]
    r = P.report(preds, sett, g)
    assert r["pooled"]["n"] == 2 and r["holdout_masked"]["settled_rows_masked_by_engine"] == {dc: 1}
    assert r["by"]["engine_id"][dc]["n"] == 1 and r["engines"][dc]["settled_rows_masked_no_peek"] == 1
    opened = P.report(preds, sett, [P.HoldoutGuard(dc, "2026-08-01", "2026-12-31", opened=True)])
    assert opened["pooled"]["n"] == 3


def test_repo_guard_config_is_closed_and_points_at_the_sealed_spec():
    g = P.load_guards(REPO)
    assert [(x.engine_id, x.date_from, x.date_to, x.opened) for x in g] == \
        [("football_double_chance.derived_1x2", "2026-08-01", "2026-12-31", False)]
    assert not (REPO / "research/platform_v2/double_chance/HOLDOUT_RESULTS.json").exists()


# ---------------------------------------------------------------- guarded opener (synthetic; the real holdout is never touched)
def _spec(tmp: Path, **over) -> tuple[Path, Path, Path]:
    spec = json.loads((REPO / "research/platform_v2/double_chance/HOLDOUT_SPEC.json").read_text())
    spec.update(over)
    s, h, r = tmp / "HOLDOUT_SPEC.json", tmp / "HOLDOUT_SPEC.sha256", tmp / "HOLDOUT_RESULTS.json"
    s.write_text(json.dumps(spec))
    h.write_text(hashlib.sha256(s.read_bytes()).hexdigest() + "  HOLDOUT_SPEC.json\n")
    return s, h, r


def test_real_spec_hash_still_matches():
    s = REPO / "research/platform_v2/double_chance/HOLDOUT_SPEC.json"
    assert hashlib.sha256(s.read_bytes()).hexdigest() == \
        (REPO / "research/platform_v2/double_chance/HOLDOUT_SPEC.sha256").read_text().split()[0]


def test_opener_refuses_before_open_date_on_tamper_and_on_second_run(tmp_path):
    m = _load("open_dc_holdout")
    s, h, r = _spec(tmp_path)
    with pytest.raises(m.Refused, match="not before 2027-01-03"):
        m.check_guards(s, h, r, date(2027, 1, 2))
    assert m.check_guards(s, h, r, date(2027, 1, 3))["season"] == "2026_27"
    s.write_text(s.read_text().replace("2026_27", "2026_28"))
    with pytest.raises(m.Refused, match="frozen hash"):
        m.check_guards(s, h, r, date(2027, 2, 1))
    s, h, r = _spec(tmp_path)
    r.write_text("{}")
    with pytest.raises(m.Refused, match="opened once"):
        m.check_guards(s, h, r, date(2027, 2, 1))


def test_real_opener_refuses_today():
    m = _load("open_dc_holdout")
    with pytest.raises(m.Refused):
        m.main(["--data-dir", "/nonexistent"], today=date(2026, 10, 1))


def test_opener_loads_only_window_and_complete_closing_books(tmp_path):
    m = _load("open_dc_holdout")
    spec = json.loads((REPO / "research/platform_v2/double_chance/HOLDOUT_SPEC.json").read_text())
    cols = ["Date", "HomeTeam", "AwayTeam", "FTR"] + [f"{b}C{o}" for b in m.PRIMARY_BOOKS for o in "HDA"]
    import numpy as np
    rng = np.random.default_rng(1)
    n_good = 0
    for code in spec["competitions"]:
        rows = []
        for i in range(80):   # synthetic, varied closing books inside the window
            ph = rng.uniform(0.2, 0.75)
            pd_ = rng.uniform(0.18, 0.3) * (1 - ph)
            pa = 1 - ph - pd_
            odds = [round(1 / (x * 1.05), 2) for x in (ph, pd_, pa)]
            res = "HDA"[rng.choice(3, p=[ph, pd_, pa])]
            rows.append([f"{1 + i % 28:02d}/{9 + i % 4:02d}/2026", f"H{i}", f"A{i}", res] + [str(o) for o in odds] * 3)
        n_good += len(rows)
        rows.append(["10/01/2027", "C", "D", "A"] + ["1.5", "4.2", "6.5"] * 3)                  # outside the window
        rows.append(["16/09/2026", "E", "F", "D"] + ["1.5", "4.2", "6.5"] * 2 + ["", "", ""])   # incomplete books
        with (tmp_path / f"{code}.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
    df, shas = m.load_matches(tmp_path, spec)
    assert len(df) == n_good and set(shas) == set(spec["competitions"])
    res = m.evaluate(df)
    assert res["matches"] == n_good and res["events"] == 3 * n_good and isinstance(res["passed"], bool)


def test_v2_19_expansion_leagues_wired_and_holdout_guard_scoped():
    from prediction_markets_lab.ingestion.the_odds_api_loader import TheOddsApiConfig
    keys = TheOddsApiConfig().sport_keys
    assert keys["soccer_netherlands_eredivisie"] == "Eredivisie" and keys["soccer_germany_bundesliga"] == "Bundesliga"
    assert COMP_TO_FD["Eredivisie"] == "N1" and COMP_TO_FD["Bundesliga"] == "D1"
    g = P.load_guards(REPO)[0]
    assert set(g.competitions) == {"Premier League", "Championship", "Scottish Premiership"}
    row = {"engine_id": g.engine_id, "event_start": "2026-10-10T14:00:00+00:00", "competition": "Eredivisie"}
    assert not P.masked(row, [g]) and P.masked({**row, "competition": "Premier League"}, [g])


def test_v2_19_new_leagues_never_money_qualify_on_legacy_card():
    from prediction_markets_lab.decisions.recommendation import RecommendationResult
    from prediction_markets_lab.storage.schemas import MarketRecord
    spec = importlib.util.spec_from_file_location("run_daily_scan_v219", REPO / "scripts/run_daily_scan.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    allowed = m.money_card_competitions()
    assert allowed == {"Premier League", "Championship", "Scottish Premiership"}
    def rec(comp):   # model_construct: only the money fields matter here
        r = MarketRecord.model_construct(competition=comp, money_qualified=True, money_decision="BET", money_rejection_reason="")
        return RecommendationResult(market_record=r, stake_gbp=1.0)
    for comp in ("Eredivisie", "Bundesliga"):
        out = m.restrict_money_competition(rec(comp), allowed).market_record
        assert out.money_qualified is False and out.money_decision == "PAPER_ONLY" and "paper-only" in out.money_rejection_reason
    kept = m.restrict_money_competition(rec("Premier League"), allowed).market_record
    assert kept.money_qualified is True and kept.money_decision == "BET"            # existing leagues unchanged
