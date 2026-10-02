"""Settlement completeness report (diagnostic only; 0 credits; never writes a ledger).

Reads the unified prediction ledger, the legacy football paper ledger and the bet-selection-v2 paper selections, and
writes status/settlement_completeness.json + reports/settlement_completeness.md. Emits a GitHub ::warning:: line for
every group with records UNRESOLVED_AFTER_EXPECTED_LAG or SOURCE_UNAVAILABLE so nothing stays PENDING silently.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from prediction_markets_lab.prediction_platform.settle import COMP_TO_FD
from prediction_markets_lab.settlement import completeness as C

REPO = Path(__file__).resolve().parents[1]


def rows(p: Path) -> list[dict]:
    return list(csv.DictReader(open(p, newline=""))) if p.exists() else []


def source_for(sport: str, competition: str, cfg: dict) -> str | None:
    src = cfg["sources"].get(sport)
    if sport == "football" and competition not in COMP_TO_FD:
        return None
    return src


def collect(repo: Path, cfg: dict) -> list[C.Record]:
    out: list[C.Record] = []
    settled_ids = {r["prediction_id"] for r in rows(repo / "predictions/unified_settlements.csv") if r.get("settlement_status") == "SETTLED"}
    for p in rows(repo / "predictions/unified_ledger.csv"):
        out.append(C.Record("unified_ledger", p["prediction_id"], p["sport"], p["competition"], p["event_name"], C.parse_ts(p["event_start"]),
                            p["prediction_id"] in settled_ids, source_for(p["sport"], p["competition"], cfg)))
    for b in rows(repo / "paper_ledger/paper_bets.csv"):
        out.append(C.Record("legacy_paper_ledger", b["bet_id"], b["sport"], b["competition"], b["event"], C.parse_ts(b["kickoff"]),
                            b.get("status") == "settled", cfg["legacy_paper_ledger_source"]))
    comp_of = {p["prediction_id"]: p["competition"] for p in rows(repo / "predictions/unified_ledger.csv")}
    bsv2_settled = {r.get("selection_id") for r in rows(repo / "paper_betting_v2/settlements.csv")}
    for s in rows(repo / "paper_betting_v2/selections.csv"):
        if s.get("decision") not in ("PAPER_BET", "PAPER"):
            continue
        comp = comp_of.get(s["prediction_id"], "")
        out.append(C.Record("bsv2_paper_selections", s["selection_id"], s["sport"], comp, s["event_name"], C.parse_ts(s["event_start"]),
                            s["selection_id"] in bsv2_settled, source_for(s["sport"], comp, cfg)))
    return out


def markdown(res: dict) -> str:
    t = res["totals"]
    lines = [f"# Settlement completeness ({res['generated_at'][:16]} UTC)", "",
             "Diagnostic only; does not change any decision, grade, stake or settlement.", "",
             " · ".join(f"{k} {v}" for k, v in t.items()), "", "| ledger | sport | competition | source | " + " | ".join(C.STATUSES) + " |",
             "|" + "---|" * (4 + len(C.STATUSES))]
    lines += [f"| {g['ledger']} | {g['sport']} | {g['competition']} | {g['source']} | " + " | ".join(str(g[s]) for s in C.STATUSES) + " |" for g in res["groups"]]
    if res["flagged"]:
        lines += ["", "## Flagged", ""] + [f"- {f['status']}: {f['ledger']} {f['id']} ({f['event']}, start {f['start'][:16]}, {f['hours_since_start']}h ago)" for f in res["flagged"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    cfg = C.load_config()
    res = C.summarise(collect(REPO, cfg), datetime.now(timezone.utc), cfg["expected_lag_hours"])
    (REPO / "status").mkdir(exist_ok=True)
    (REPO / "status/settlement_completeness.json").write_text(json.dumps(res, indent=1) + "\n")
    (REPO / "reports").mkdir(exist_ok=True)
    (REPO / "reports/settlement_completeness.md").write_text(markdown(res))
    print(json.dumps(res["totals"]))
    for g in res["groups"]:
        bad = g["UNRESOLVED_AFTER_EXPECTED_LAG"] + g["SOURCE_UNAVAILABLE"]
        if bad:
            print(f"::warning::settlement completeness: {bad} record(s) unresolved/unsourced in {g['ledger']} {g['sport']} {g['competition']} ({g['source']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
