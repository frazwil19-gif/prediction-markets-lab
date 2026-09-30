"""V2-8 offline analyser tests (research; outside the production gate). Builds a synthetic frozen V2-7 record set with the real
cer-2 logger, then analyses it read-only."""
from __future__ import annotations

import json
import shutil
import socket
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from prediction_markets_lab.card_engine import shadow as S
from prediction_markets_lab.research import portfolio as PF
from prediction_markets_lab.research import v2_8_analyser as A

from test_card_research_shadow import PRICE_COLS, PROB_COLS, SCAN, prob, price, write_csv, tree   # noqa: E402

REPO = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 2, 6, 45, tzinfo=timezone.utc)
WS = datetime(2026, 10, 2, 6, 35, tzinfo=timezone.utc)


def build_repo(tmp: Path, probs: list[dict], prices: list[dict]) -> Path:
    for rel in ("config/card_research_shadow.yaml", "config/bet_selection_v2.yaml", "config/v2_8_analyser.yaml",
                "research/platform_v2/card_engine_v2_7/RESULTS.json"):
        (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / rel, tmp / rel)
    write_csv(tmp / "tennis_predictions/exchange_probability_snapshots.csv", PROB_COLS, probs)
    write_csv(tmp / "tennis_predictions/price_snapshots.csv", PRICE_COLS, prices)
    cfg = S.load_config(tmp / "config/card_research_shadow.yaml", tmp)
    rec = S.run_shadow(tmp, cfg, S.ShadowStore(tmp / cfg.output_dir), NOW, {"run_id": "r1", "commit_sha": "abc"}, "PROSPECTIVE",
                       lambda p: 0.011, WS)
    assert rec["status"] == S.OK
    return tmp


def run(repo: Path, out: Path, *extra: str) -> dict:
    from scripts_loader_v28 import load_cli
    cli = load_cli()
    cli.REPO = repo
    assert cli.main(["--out", str(out), "--config", str(repo / "config/v2_8_analyser.yaml"), *extra]) == 0
    files = sorted(out.glob("analysis_*.json"))
    return json.loads(files[0].read_text()) if files else {}


@pytest.fixture
def poor_prices(tmp_path):
    """Five strong predictions, every bookmaker price below fair (EV < 0)."""
    probs = [prob(f"e{i}", p) for i, p in enumerate((0.91, 0.88, 0.84, 0.81, 0.78))]
    prices = [price(f"e{i}", bk, round(0.95 / p, 2), "5.0") for i, p in enumerate((0.91, 0.88, 0.84, 0.81, 0.78)) for bk in ("bk1", "bk2")]
    return build_repo(tmp_path / "repo", probs, prices)


def test_board_is_probability_first_and_keeps_strong_predictions_with_poor_prices(poor_prices, tmp_path):
    a = run(poor_prices, tmp_path / "out")
    board = a["stage_A_prediction_board"]
    assert [b["p"] for b in board] == sorted([b["p"] for b in board], reverse=True) and len(board) == 5
    assert all(s["label"] == "STRONG_PREDICTION_POOR_PRICE" and s["ev"] < 0 for s in a["stage_B_single_evaluation"])
    assert all("sigma" in b and "calibration_support" in b and b["model"].endswith("@1") for b in board)
    assert all(s["grade"].startswith("UNGRADED") for s in a["stage_B_single_evaluation"])
    blk = a["stage_B_structures"]["HIGH_P"]["N5"]
    assert blk["research_screen"]["structures_passing_ev_low_gt_0"] == [] and blk["research_screen"]["default_if_none"] == "NO BET"
    assert blk["structures"]["NO_BET"]["expected_return"] == 0.0


def test_large_disagreement_is_flagged_for_investigation_not_value(tmp_path):
    probs = [prob("e1", 0.91), prob("e2", 0.80)]
    prices = [price("e1", "bk1", 1.55, "2.4"), price("e1", "bk2", 1.55, "2.4"), price("e2", "bk1", 1.2, "4.0")]
    a = run(build_repo(tmp_path / "repo", probs, prices), tmp_path / "out")
    b1 = next(b for b in a["stage_A_prediction_board"] if b["event_id"] == "e1")
    assert b1["benchmark_flag"] == "INVESTIGATE_DISAGREEMENT" and b1["rank"] == 1          # still ranked by P, flagged, not hidden
    s1 = next(s for s in a["stage_B_single_evaluation"] if s["rank"] == 1)
    assert s1["ev"] > 0                                                                     # EV is computed but the flag says investigate


def test_high_p_set_fixes_strongest_predictions_before_choosing_a_book(tmp_path):
    probs = [prob(f"e{i}", p) for i, p in enumerate((0.92, 0.85, 0.80, 0.72))]
    prices = [price("e0", "full", 1.05), price("e1", "full", 1.12), price("e2", "full", 1.2),
              price("e1", "partial", 1.2), price("e2", "partial", 1.3), price("e3", "partial", 1.5)]     # longer odds, lacks e0
    a = run(build_repo(tmp_path / "repo", probs, prices), tmp_path / "out")
    blk = a["stage_B_structures"]["HIGH_P"]["N3"]
    assert blk["book"] == "full" and [l["selection"] for l in blk["legs"]] == ["Ae0", "Ae1", "Ae2"]


def test_pos_ev_population_separate_and_equal_capital_maths(tmp_path):
    probs = [prob(f"e{i}", p) for i, p in enumerate((0.60, 0.62, 0.75, 0.90))]
    prices = [price("e0", "bk1", 1.80), price("e1", "bk1", 1.70), price("e2", "bk1", 1.30), price("e3", "bk1", 1.05)]
    a = run(build_repo(tmp_path / "repo", probs, prices), tmp_path / "out")
    pe = a["stage_B_structures"]["POS_EV"]["N2"]
    assert pe["population"] == "POS_EV" and pe["leg_level_rule_all_legs_ev_gt_0"] is True
    assert {l["selection"] for l in pe["legs"]} == {"Ae0", "Ae1"}
    assert set(pe["structures"]) == {"SINGLES", "ACC_2", "FULL_COVER+SINGLES", "NO_BET"}                 # N = 2 duplicates removed
    evs = [l["leg_ev"] for l in pe["legs"]]
    assert pe["structures"]["SINGLES"]["expected_return"] == pytest.approx(sum(evs) / 2, abs=1e-4)
    assert pe["structures"]["ACC_2"]["expected_return"] == pytest.approx((1 + evs[0]) * (1 + evs[1]) - 1, abs=1e-4)
    hp = a["stage_B_structures"]["HIGH_P"]["N3"]
    assert "status" in hp or hp["population"] == "HIGH_P"


def test_minimum_stake_feasibility_never_scales_up(poor_prices, tmp_path):
    a = run(poor_prices, tmp_path / "out")
    s = a["stage_B_structures"]["HIGH_P"]["N5"]["structures"]
    assert s["SINGLES"]["stake_feasibility"]["GBP20|2%|min0.10"] == {"line_stake": 0.0, "lines": 5, "feasible": False}
    assert s["SINGLES"]["stake_feasibility"]["GBP20|5%|min0.10"]["feasible"] is True
    assert s["ACC_5"]["stake_feasibility"]["GBP20|5%|min1.00"]["feasible"] is True
    assert s["FULL_COVER+SINGLES"]["stake_feasibility"]["GBP100|5%|min1.00"]["feasible"] is False


def test_read_only_inputs_output_guard_and_no_network(poor_prices, tmp_path, monkeypatch):
    before = tree(poor_prices)
    monkeypatch.setattr(socket, "socket", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    run(poor_prices, tmp_path / "out")
    assert tree(poor_prices) == before
    for bad in ("tennis_predictions/x", "research/platform_v2/card_engine_v2_7/prospective/x", "paper_betting_v2"):
        with pytest.raises(PermissionError):
            A.guard_output(poor_prices / bad, poor_prices)


def test_only_valid_prospective_records_and_outcomes_off_by_default(poor_prices, tmp_path):
    root = poor_prices / "research/platform_v2/card_engine_v2_7/prospective"
    recs = A.valid_records(root, allow_dry_run=False)
    assert len(recs) == 1
    st = S.ShadowStore(root)
    st.append_unique("2026-10/scan_runs.csv", S.SCAN_FIELDS, "record_id",
                     [{**recs[0], "record_id": "failedrec", "status": S.FAILED}, {**recs[0], "record_id": "dry", "mode": "DRY_RUN_REPLAY"}])
    assert len(A.valid_records(root, allow_dry_run=False)) == 1 and len(A.valid_records(root, allow_dry_run=True)) == 2
    a = run(poor_prices, tmp_path / "out")
    assert "outcomes_research_only" not in a


def test_deterministic_output(poor_prices, tmp_path):
    run(poor_prices, tmp_path / "o1")
    run(poor_prices, tmp_path / "o2")
    assert tree(tmp_path / "o1") == tree(tmp_path / "o2")
