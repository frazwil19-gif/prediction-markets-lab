"""V2-4 settlement migration -- SHADOW comparison of football-data.co.uk results against the
Odds API scores the existing settlement already fetches. Writes reports only; NEVER modifies
paper_ledger/. 0 Odds API credits (football-data.co.uk is free; it is reachable from GitHub runners).

Outputs:
  settlement_archive/shadow_fixture_comparison.csv  (one row per completed Odds API event seen)
  status/settlement_shadow.json                      (summary + migration-gate status)
"""
from __future__ import annotations

import csv
import json
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

from prediction_markets_lab.settlement import football_data_results as fd
from prediction_markets_lab.settlement.market_settlement import determine_result

REPO = Path(__file__).resolve().parents[1]
ARCHIVE = REPO / "settlement_archive"
SPORT_TO_FD = {"soccer_epl": "E0", "soccer_efl_champ": "E1", "soccer_spl": "SC0"}
COMP_TO_FD = {"Premier League": "E0", "Championship": "E1", "Scottish Premiership": "SC0"}
GATE_MIN_COMPARISONS = 100


def fetch_fd(code: str, today: date) -> tuple[str | None, str]:
    url = fd.fd_url(code, today)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.read().decode("utf-8-sig", errors="replace"), url
    except Exception as exc:  # recorded, never fatal
        return None, f"{url} ({exc})"


def main() -> int:
    today = datetime.now(timezone.utc).date()
    aliases = fd.load_settlement_aliases()
    results, sources = [], {}
    for code in sorted(set(SPORT_TO_FD.values())):
        text, src = fetch_fd(code, today)
        sources[code] = src if text else f"FAILED {src}"
        if text:
            results += fd.parse_fd_csv(text, code, aliases)
    # A. fixture-level comparison vs archived Odds API scores
    comp_path = ARCHIVE / "shadow_fixture_comparison.csv"
    seen = set()
    if comp_path.exists():
        seen = {r["odds_api_event_id"] for r in csv.DictReader(open(comp_path))}
    new_rows = []
    for f in sorted(ARCHIVE.glob("odds_api_scores_*.json")) if ARCHIVE.exists() else []:
        sport = next((k for k in SPORT_TO_FD if f.name.startswith(f"odds_api_scores_{k}_")), None)
        if sport is None:
            continue
        for ev in json.loads(f.read_text()):
            if not ev.get("completed") or ev.get("id") in seen or not ev.get("scores"):
                continue
            sc = {s["name"]: s["score"] for s in ev["scores"]}
            try:
                oh, oa = int(sc[ev["home_team"]]), int(sc[ev["away_team"]])
            except (KeyError, ValueError, TypeError):
                continue
            ko = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00")).date()
            m = fd.match_fixture(SPORT_TO_FD[sport], ev["home_team"], ev["away_team"], ko, results, aliases)
            row = {"odds_api_event_id": ev["id"], "competition": SPORT_TO_FD[sport], "kickoff": ko.isoformat(),
                   "home": ev["home_team"], "away": ev["away_team"], "odds_api_score": f"{oh}-{oa}",
                   "fd_status": m.status, "fd_score": f"{m.result.home_goals}-{m.result.away_goals}" if m.result else "",
                   "score_agree": (m.result is not None and (m.result.home_goals, m.result.away_goals) == (oh, oa)),
                   "result_agree": (m.result is not None and determine_result("1x2", m.result.home_goals, m.result.away_goals) == determine_result("1x2", oh, oa)),
                   "detail": m.detail, "compared_at": datetime.now(timezone.utc).isoformat()}
            seen.add(ev["id"])
            new_rows.append(row)
    if new_rows:
        ARCHIVE.mkdir(exist_ok=True)
        header = not comp_path.exists()
        with open(comp_path, "a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(new_rows[0].keys()))
            if header:
                w.writeheader()
            w.writerows(new_rows)
    allrows = list(csv.DictReader(open(comp_path))) if comp_path.exists() else []
    matched = [r for r in allrows if r["fd_status"] == "MATCHED"]
    # B. ledger: what football-data WOULD settle (never applied in shadow mode)
    ledger_view = []
    lp = REPO / "paper_ledger/paper_bets.csv"
    if lp.exists():
        for b in csv.DictReader(open(lp)):
            if b.get("status") != "pending" or " v " not in b.get("event", ""):
                continue
            ko = date.fromisoformat(b["kickoff"][:10])
            if ko >= today:
                continue
            h, a = b["event"].split(" v ", 1)
            code = COMP_TO_FD.get(b.get("competition", ""))
            m = fd.match_fixture(code, h, a, ko, results, aliases) if code else fd.FixtureMatch("UNRESOLVED_NAME", None, "competition")
            would = None
            if m.result is not None and b["market"] in ("1x2", "over_under_2_5"):
                would = determine_result(b["market"], m.result.home_goals, m.result.away_goals)
            ledger_view.append({"bet_id": b["bet_id"], "event": b["event"], "kickoff": b["kickoff"], "market": b["market"],
                                "selection": b["selection"], "fd_status": m.status, "fd_score": f"{m.result.home_goals}-{m.result.away_goals}" if m.result else "",
                                "would_win": (would == b["selection"]) if would else None, "detail": m.detail})
    status_counts = {}
    for r in allrows:
        status_counts[r["fd_status"]] = status_counts.get(r["fd_status"], 0) + 1
    disagreements = [r for r in matched if r["score_agree"] != "True"]
    gate = {"min_comparisons": GATE_MIN_COMPARISONS, "matched_comparisons": len(matched),
            "score_disagreements": len(disagreements),
            "passed": len(matched) >= GATE_MIN_COMPARISONS and not disagreements}
    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "mode": "SHADOW (no ledger writes)",
           "football_data_sources": sources, "fd_results_loaded": len(results),
           "fd_unresolved_names": sorted({r.home_raw for r in results if r.home is None} | {r.away_raw for r in results if r.away is None}),
           "fd_internal_inconsistencies": sum(1 for r in results if not fd.fd_consistent(r)),
           "fixture_comparisons_total": len(allrows), "fixture_status_counts": status_counts,
           "disagreement_examples": disagreements[:10], "migration_gate": gate,
           "ledger_pending_past_kickoff": ledger_view}
    (REPO / "status").mkdir(exist_ok=True)
    (REPO / "status/settlement_shadow.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: out[k] for k in ("football_data_sources", "fd_results_loaded", "fd_unresolved_names",
                                          "fixture_comparisons_total", "fixture_status_counts", "migration_gate")}, indent=1))
    print("ledger pending past kickoff:", json.dumps(ledger_view, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
