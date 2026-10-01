"""V2-17 first-row verifier: PASS on a well-formed synthetic football deployment, FAIL on duplicates / missing Stage A."""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import timedelta
from pathlib import Path

from prediction_markets_lab.bet_selection_v2 import prices as PR
from prediction_markets_lab.bet_selection_v2.evaluate import evaluate_prediction, load_config as load_bs
from prediction_markets_lab.prediction_platform import adapters as A
from prediction_markets_lab.prediction_platform import stage_a as SA
from prediction_markets_lab.prediction_platform.registry import Registry
from prediction_markets_lab.prediction_platform.schema import PREDICTION_FIELDS, to_row

REPO = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location("verify_first_rows_t", REPO / "scripts/verify_first_rows.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def _write(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def deploy(tmp: Path, duplicate: bool = False, drop_from_board: bool = False) -> Path:
    card = json.loads(sorted((REPO / "daily_cards").glob("*/card.json"))[-1].read_text())
    first_ko = min(A._ts(c["kickoff_time"]) for c in card["candidates"] if c.get("kickoff_time"))
    now = first_ko - timedelta(hours=30)
    card = {**card, "data_timestamp": now.isoformat()}
    reg = Registry.load()
    preds, _ = A.football_from_card(card, reg, A.RunContext("30 6 * * *", now.isoformat(), 1.33), now, origin="test")
    rows = [to_row(p) for p in preds]
    if duplicate:
        rows.append(dict(rows[0]))
    _write(tmp / "predictions/unified_ledger.csv", PREDICTION_FIELDS, rows)
    cfg = SA.load_config(REPO / "config/prediction_board_stage_a.yaml", REPO)
    bs = load_bs()
    board = SA.build(rows, [], lambda p: PR.football_from_card(p, card), bs, cfg, None, now, SA.football_sigma(cfg.football_sigma_evidence),
                     {e: x["calibration_status"] for e, x in reg.engines.items()})
    if drop_from_board:
        board["predictions"] = board["predictions"][1:]
    (tmp / "reports").mkdir(parents=True, exist_ok=True)
    (tmp / "reports/latest_stage_a_board.json").write_text(json.dumps(board, default=str))
    cands = [evaluate_prediction(r, PR.football_from_card(r, card), bs, now)[0].row() for r in rows]
    _write(tmp / "reports/bet_selection_v2_candidates.csv", list(cands[0]), cands)
    return tmp


def test_pending_without_rows(tmp_path):
    assert _load().verify(tmp_path, "football")["status"] == "PENDING"


def test_pass_on_wellformed_football_rows(tmp_path):
    r = _load().verify(deploy(tmp_path), "football")
    assert r["status"] == "PASS", {k: v for k, v in r["checks"].items() if v["result"] != "PASS"}


def test_fail_on_duplicate_and_missing_board_row(tmp_path):
    r = _load().verify(deploy(tmp_path / "a", duplicate=True), "football")
    assert r["checks"]["no_duplicate_rows"]["result"] == "FAIL"
    r2 = _load().verify(deploy(tmp_path / "b", drop_from_board=True), "football")
    assert r2["checks"]["stage_a_complete"]["result"] == "FAIL"
