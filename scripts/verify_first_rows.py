"""V2-17 read-only verification of the FIRST prospective rows of a sport (football or basketball) after deployment.

Checks (each PASS / FAIL / PENDING, never fixes anything):
  provenance   engine id/version, live estimator named in historical_support, origin, prediction_valid
  timing       prediction_timestamp < event_start; minutes_to_event inside the engine's snapshot window; configured vs
               actual workflow start recorded
  event keys   one canonical row per (event, market, selection); football 1X2 complete H/D/A triplets; NBA one row per game
  stage A      every valid upcoming row of the sport is on latest_stage_a_board with probability basis, sigma method,
               calibration status and a price status; 1X2 normalised; DC price status never PRICE_VALID from a synthetic price
  stage B      bsv2 candidates exist for the rows (football 1X2/NBA) or are documented DATA_BLOCKED (DC)
  start times  est-1 resolution rows exist for the sport's rows
0 API calls. Usage: python scripts/verify_first_rows.py --sport football|basketball [--repo .]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

WINDOW_MIN = {"football": 48 * 60, "basketball": 36 * 60}
ENGINES = {"football": ("football_1x2.market_consensus", "football_double_chance.derived_1x2", "football_ou25.market"),
           "basketball": ("nba_moneyline.market",)}


def _rows(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def verify(repo: Path, sport: str, competition: str | None = None) -> dict:
    """competition: optional per-league verification (final football coverage: a league joins paper operation only
    after its own first-row PASS)."""
    led = [r for r in _rows(repo / "predictions/unified_ledger.csv")
           if r["sport"] == sport and (competition is None or r["competition"] == competition)]
    if not led:
        return {"sport": sport, "competition": competition, "status": "PENDING", "reason": "no prospective rows yet"}
    checks: dict[str, tuple[str, str]] = {}

    def chk(name: str, ok: bool, detail: str = "") -> None:
        checks[name] = ("PASS" if ok else "FAIL", detail)

    chk("engines_known", all(r["engine_id"] in ENGINES[sport] for r in led), str(Counter(r["engine_id"] for r in led)))
    chk("live_estimator_named", all("live estimator" in r["historical_support"] for r in led
                                    if r["engine_id"] in ("football_1x2.market_consensus", "football_double_chance.derived_1x2",
                                                          "nba_moneyline.market")))
    chk("prediction_before_start", all(_ts(r["prediction_timestamp"]) < _ts(r["event_start"]) for r in led))
    chk("inside_snapshot_window", all(0 < float(r["minutes_to_event"]) <= WINDOW_MIN[sport] for r in led))
    chk("workflow_timing_recorded", all(r["actual_workflow_start"] for r in led), "configured_scan_time may be MANUAL/cron")
    keys = Counter((r["event_key"], r["market"], r["selection"], r["engine_id"]) for r in led)
    chk("no_duplicate_rows", max(keys.values()) == 1)
    if sport == "football":
        trip = Counter((r["event_key"], r["prediction_timestamp"]) for r in led if r["market"] == "1x2")
        chk("1x2_triplets_complete", all(v == 3 for v in trip.values()), str(Counter(trip.values())))
        dc = [r for r in led if r["market"] == "double_chance"]
        chk("dc_price_synthetic_only", all(r["live_price_source"] == "SYNTHETIC_DUTCH_BEST_1X2" for r in dc))
    else:
        chk("nba_one_row_per_game", max(Counter(r["event_key"] for r in led).values()) == 1)
        chk("nba_actual_book_source", all(r["live_price_source"].startswith("odds_api:") for r in led))
    board = json.loads((repo / "reports/latest_stage_a_board.json").read_text()) if (repo / "reports/latest_stage_a_board.json").exists() else {}
    sa = [b for b in board.get("predictions", []) if b.get("sport") == sport
          and (competition is None or b.get("competition") == competition)]
    gen = _ts(board["generated_at"]) if board.get("generated_at") else None
    upcoming = {r["prediction_id"] for r in led if r["prediction_valid"] == "True" and gen and _ts(r["event_start"]) > gen}
    on_board = {b["prediction_id"] for b in sa}
    chk("stage_a_complete", upcoming <= on_board, f"missing {sorted(upcoming - on_board)[:5]}")
    chk("stage_a_fields", all(b.get("probability_basis") and b.get("sigma_method") and b.get("calibration_status")
                              and b.get("price_status") for b in sa))
    if sport == "football":
        chk("stage_a_1x2_normalised", all(b["normalisation"] in ("TRIPLET_NORMALISED", "TRIPLET_INCOMPLETE")
                                          for b in sa if b["market"] == "1x2"))
        chk("stage_a_dc_never_price_valid", all(b["price_status"] != "PRICE_VALID" for b in sa if b["market"] == "double_chance"))
    res = {r["prediction_id"] for r in _rows(repo / "reports/bet_selection_v2_start_time_resolution.csv")}
    chk("start_time_resolution_rows", {r["prediction_id"] for r in led} <= res or not res, "resolution written by evaluate runs only")
    cands = {r["prediction_id"] for r in _rows(repo / "reports/bet_selection_v2_candidates.csv")}
    bets = [r for r in led if r["market"] in ("1x2", "moneyline", "over_under_2_5") and r["prediction_id"] in upcoming]
    chk("stage_b_candidates_for_priced_markets", all(r["prediction_id"] in cands for r in bets) if cands else False,
        f"{sum(r['prediction_id'] in cands for r in bets)}/{len(bets)}")
    status = "PASS" if all(v[0] == "PASS" for v in checks.values()) else "FAIL"
    return {"sport": sport, "competition": competition, "status": status, "rows": len(led), "first_prediction_at": min(r["prediction_timestamp"] for r in led),
            "checks": {k: {"result": v[0], "detail": v[1]} for k, v in checks.items()}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", choices=sorted(WINDOW_MIN), required=True)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--competition", default=None, help="verify one league only (e.g. 'Eredivisie')")
    a = ap.parse_args()
    print(json.dumps(verify(a.repo, a.sport, a.competition), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
