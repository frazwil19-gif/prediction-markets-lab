"""Settle paper tennis predictions from free published results and write the
prospective performance report. No API credits. See ATP_PROSPECTIVE_PROTOCOL.md."""
from __future__ import annotations

import csv
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from prediction_markets_lab.tennis_prospective.ledger import append_settlements, read_predictions, read_settlements
from prediction_markets_lab.tennis_prospective.performance import engine_performance
from prediction_markets_lab.tennis_prospective.settlement import parse_result_date, settle_one

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "tennis_predictions"
SOURCES = {
    # TML's GitHub repo stopped updating in Jan 2026 (updates moved to stats.tennismylife.org, which the
    # network allowlist blocks), so ATP results come from TennisCourtLog (weekly updates), like WTA.
    "ATP": [("TennisCourtLog ATP 2026", "https://media.githubusercontent.com/media/LuckyLoser91/TennisCourtLog/main/tennis_atp/atp_matches_2026.csv")],
    "WTA": [("TennisCourtLog 2026", "https://media.githubusercontent.com/media/LuckyLoser91/TennisCourtLog/main/tennis_wta/wta_matches_2026.csv")],
}


def fetch_results(tour: str) -> list[dict]:
    out = []
    for label, url in SOURCES[tour]:
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                text = r.read().decode("utf-8-sig")
        except Exception as exc:  # a source outage leaves predictions unsettled, never guessed
            print(f"WARNING: could not fetch {label}: {exc}")
            continue
        for row in csv.DictReader(io.StringIO(text)):
            try:
                out.append({"winner_name": row["winner_name"], "loser_name": row["loser_name"], "score": row.get("score", ""),
                            "result_date": parse_result_date(row["tourney_date"]), "source": label})
            except (KeyError, ValueError):
                continue
    return out


def main() -> int:
    preds = read_predictions(OUT / "ledger_predictions.csv")
    done = read_settlements(OUT / "ledger_settlements.csv")
    now = datetime.now(timezone.utc)
    pending = [p for p in preds if p["prediction_id"] not in done and datetime.fromisoformat(p["commence_time"]) < now]
    results = {t: fetch_results(t) for t in {p["tour"] for p in pending}}
    new = [s for s in (settle_one(p, results.get(p["tour"], []), now) for p in pending) if s]
    added = append_settlements(OUT / "ledger_settlements.csv", new)
    done = read_settlements(OUT / "ledger_settlements.csv")
    report = {"generated_at": now.isoformat(), "note": "PAPER prediction performance; Odds-API-covered universe only",
              "engines": {}}
    for eng in sorted({p["engine_id"] for p in preds}):
        report["engines"][eng] = engine_performance([p for p in preds if p["engine_id"] == eng], done)
    unresolved = [p["prediction_id"] for p in preds if p["prediction_id"] not in done
                  and (now - datetime.fromisoformat(p["commence_time"])).days > 21]
    report["unresolved_after_21_days"] = unresolved
    OUT.mkdir(exist_ok=True)
    (OUT / "performance.json").write_text(json.dumps(report, indent=1, default=float))
    print(json.dumps({"pending": len(pending), "settled_now": added,
                      "engines": {k: {x: v.get(x) for x in ("settled", "settled_ge_80", "maturity", "accuracy")} for k, v in report["engines"].items()}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
