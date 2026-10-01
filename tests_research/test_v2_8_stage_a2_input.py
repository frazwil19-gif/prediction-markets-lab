"""V2-16: the V2-8 analyser reads the complete stage-a-2 board (when it matches the scan); its Stage B allocation input
population and methodology are unchanged."""
from __future__ import annotations

import json
from pathlib import Path

from test_v2_8_analyser import build_repo, run   # noqa: E402
from test_card_research_shadow import SCAN, price, prob   # noqa: E402


def sa2_board(path: Path, scan: str, rows: list[dict], version: str = "stage-a-2") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"board_version": version, "predictions": rows}))


def row(eid, sel, opp, p, sport="tennis", observed=SCAN, sigma=0.013, status="POOR_PAYOUT"):
    key = f"tennis|k|{eid}" if sport == "tennis" else f"nba|{eid}"
    name = f"{sel} v {opp}" if sport == "tennis" else f"{opp} @ {sel}"
    return {"sport": sport, "event_key": key, "event_name": name, "selection": sel, "market": "match_winner", "probability": p,
            "probability_observed_at": observed if sport == "tennis" else "2026-10-02T06:00:00+00:00", "event_start": "2026-10-03T03:00:00+00:00",
            "sigma": sigma, "engine_id": "x", "strength": "STRONG_PREDICTION", "probability_band": "80%+", "calibration_status": "HOLDOUT_PASSED x",
            "probability_basis": "P_CURRENT_SCAN", "p_first_snapshot": p, "p_current_scan": p, "stage_a_label": f"STRONG_PREDICTION_{status}",
            "price_status": status, "exchange_width": 0.01}


def repo_with_board(tmp_path, extra_rows, version="stage-a-2", observed=SCAN):
    ps = (0.91, 0.88, 0.84, 0.81, 0.78)
    repo = build_repo(tmp_path / "repo", [prob(f"e{i}", p) for i, p in enumerate(ps)],
                      [price(f"e{i}", bk, round(0.95 / p, 2), "5.0") for i, p in enumerate(ps) for bk in ("bk1", "bk2")])
    legs_rows = [row(f"e{i}", f"A{i}", f"B{i}", p, observed=observed) for i, p in enumerate(ps)]
    sa2_board(repo / "reports/latest_stage_a_board.json", SCAN, legs_rows + extra_rows, version)
    return repo


def test_complete_board_used_and_strong_predictions_without_v27_legs_appear(tmp_path):
    extra = [row("wide1", "W", "X", 0.93, sigma=0.05, status="PRICE_QUALITY_FAIL"), row("nba1", "Boston Celtics", "Washington Wizards", 0.86,
                                                                                      sport="basketball", sigma=None, status="PRICE_UNAVAILABLE")]
    a = run(repo_with_board(tmp_path, extra), tmp_path / "out")
    assert a["stage_A_source"].startswith("stage-a-2")
    board = a["stage_A_prediction_board"]
    assert [b["event_id"] for b in board][:2] == ["wide1", "e0"] and len(board) == 7      # probability-first, nothing suppressed
    assert {b["sport"] for b in board} == {"tennis", "basketball"}
    nba = next(b for b in board if b["sport"] == "basketball")
    assert nba["sigma"] is None and nba["event"] == "Boston Celtics v Washington Wizards"


def test_allocation_input_and_results_unchanged_vs_v27_fallback(tmp_path):
    extra = [row("wide1", "W", "X", 0.93, sigma=0.05, status="PRICE_QUALITY_FAIL")]
    with_sa2 = run(repo_with_board(tmp_path / "a", extra), tmp_path / "out_a")
    fallback = run(repo_with_board(tmp_path / "b", extra, version="stage-a-1"), tmp_path / "out_b")
    assert fallback["stage_A_source"].startswith("V2-7")
    assert with_sa2["stage_B_structures"] == fallback["stage_B_structures"]      # same top-N population and maths


def test_board_from_another_scan_is_not_used(tmp_path):
    a = run(repo_with_board(tmp_path, [], observed="2026-10-01T13:45:31+00:00"), tmp_path / "out")
    assert a["stage_A_source"].startswith("V2-7")
