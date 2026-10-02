"""Corners prospective collector run (zero API credits; research only).

Downloads football-data.co.uk results (current + previous season) and fixtures.csv, writes corners-A-1.0
predictions for the 10 leagues' fixtures in the next HORIZON_DAYS, and records outcomes of predicted events.
Outputs (append-only): research_shadow/corners/model_a_predictions.csv, research_shadow/corners/outcomes.csv.
No price adapter is enabled (market_status = NO_PRICE_SOURCE_ENABLED).
"""
from __future__ import annotations

import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from prediction_markets_lab.research_shadow import corners_collector as CC
from prediction_markets_lab.settlement.football_data_results import FD_BASE, season_code

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research_shadow/corners"
PARAMS = REPO / "research/platform_v2/corners_abc/corners_A_v1_params.json"
FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"
HORIZON_DAYS = 7
TIMEOUT = 30
RUN_LOG_FIELDS = ["run_ts", "played_rows", "fixtures_listed_10_leagues", "fixtures_in_horizon", "next_fixture_date",
                  "predictions_written", "outcomes_written", "download_warnings"]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "prediction-markets-lab research (non-commercial)"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", errors="replace")


def main() -> int:
    now = CC.utcnow()
    today = now.date()
    model = CC.ModelA.load(PARAMS)
    c = model.params["constants"]
    frames, warnings = [], []
    for div in CC.DIVS + CC.HISTORY_DIVS:
        for d in (today - timedelta(days=365), today):
            url = f"{FD_BASE}/{season_code(d)}/{div}.csv"
            try:
                frames.append(CC.parse_fd(fetch(url), div))
            except Exception as exc:          # one missing file never stops the run
                warnings.append(f"{url}: {type(exc).__name__}")
    played = pd.concat([f for f in frames if not f.empty], ignore_index=True).drop_duplicates(["Division", "MatchDate", "HomeTeam", "AwayTeam"])
    fx_all = CC.parse_fixtures(fetch(FIXTURES_URL))
    fx = fx_all[(fx_all.MatchDate.dt.date >= today) & (fx_all.MatchDate.dt.date <= today + timedelta(days=HORIZON_DAYS))]
    state, div_fill, league = CC.team_states(played, c["MINP"], c["LEAGUE_WIN"], c["LEAGUE_MINP"])
    feats = CC.fixture_features(fx, state, div_fill, league)
    pred_path, out_path = OUT / "model_a_predictions.csv", OUT / "outcomes.csv"
    have = {(r["event_key"], r["run_ts"][:10]) for r in CC.read_csv(pred_path)}
    rows = [r for r in CC.prediction_rows(feats, model, now) if (r["event_key"], today.isoformat()) not in have]
    n_pred = CC.append_csv(pred_path, CC.PRED_FIELDS, rows)
    predicted = {r["event_key"] for r in CC.read_csv(pred_path)}
    known = {r["event_key"] for r in CC.read_csv(out_path)}
    outs = [o for o in CC.outcome_rows(played, date(2026, 10, 1), known, now) if o["event_key"] in predicted]
    n_out = CC.append_csv(out_path, CC.OUTCOME_FIELDS, outs)
    CC.append_csv(OUT / "run_log.csv", RUN_LOG_FIELDS, [{
        "run_ts": now.isoformat(), "played_rows": len(played), "fixtures_listed_10_leagues": len(fx_all),
        "fixtures_in_horizon": len(fx), "next_fixture_date": fx_all.MatchDate.min().date().isoformat() if len(fx_all) else "",
        "predictions_written": n_pred, "outcomes_written": n_out, "download_warnings": len(warnings)}])
    print(f"fixtures in horizon: {len(fx)}; predictions written: {n_pred}; outcomes written: {n_out}; warnings: {len(warnings)}")
    for w in warnings:
        print("warning:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
