"""Daily Prediction Board (JSON / CSV / Markdown). Ranked by estimated probability; no weighted score, no EV.

The Prediction Board answers "what is most likely?". It is not the Money Card and never stakes or qualifies bets.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from prediction_markets_lab.prediction_platform.schema import PREDICTION_FIELDS, THRESHOLDS

BOARD_SCHEMA_VERSION = 1
DEFAULT_VIEW = 0.80
EVIDENCE_ORDER = {"VALIDATED_HISTORICAL_AND_PROSPECTIVE": 0, "VALIDATED_HISTORICAL": 1, "PROVISIONAL_PROSPECTIVE": 2,
                  "RESEARCH_VALIDATED": 3}
JOINED = ["settlement_status", "result", "correct", "settlement_timestamp"]


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def rank_key(p: dict) -> tuple:
    """Probability first; evidence strength only breaks ties (transparent, not a blended score)."""
    return (-float(p["estimated_probability"]), EVIDENCE_ORDER.get(p["engine_status"], 9), p["event_start"], p["prediction_id"])


def build(preds: list[dict], settlements: dict[str, dict], registry_engines: dict[str, dict], active: list[str],
          health: dict, perf: dict, skips_last_run: dict, now: datetime) -> dict:
    upcoming = [p for p in preds if _ts(p["event_start"]) > now and str(p["prediction_valid"]) == "True"]
    upcoming.sort(key=rank_key)
    yday = (now - timedelta(days=1)).date().isoformat()
    settled_yday = [s for s in settlements.values() if str(s.get("settlement_timestamp", "")).startswith(yday)]
    counts = {f">={int(t * 100)}": sum(float(p["estimated_probability"]) >= t for p in upcoming) for t in (0.70,) + THRESHOLDS[3:]}
    evidence = {}
    for eid, e in registry_engines.items():
        m = perf.get("engines", {}).get(eid, {})
        hi = perf.get("ge80_decomposition", {}).get("by_engine", {}).get(eid, {})
        evidence[eid] = {"status": e["status"], "prospective_status": e["prospective_status"],
                         "money_eligible": e["money_eligible"], "predictions": m.get("predictions", 0),
                         "settled_rows": m.get("settled_rows", 0), "maturity": m.get("maturity", "COLLECTING"),
                         "ge80_settled": hi.get("n", 0), "ge80_mean_pred": hi.get("mean_pred"), "ge80_actual": hi.get("actual"),
                         "alarm_review_required": m.get("alarm_review_required", False)}
    rows = []
    for p in upcoming:
        s = settlements.get(p["prediction_id"], {})
        rows.append({**{k: p.get(k, "") for k in PREDICTION_FIELDS}, **{k: s.get(k, "") for k in JOINED}})
    return {"board_schema_version": BOARD_SCHEMA_VERSION, "product": "PREDICTION_BOARD (paper; not a betting card)",
            "generated_at": now.isoformat(), "date": now.date().isoformat(),
            "summary": {"upcoming_events": len({p["event_key"] for p in upcoming}), "valid_predictions": len(upcoming),
                        "sports_active": sorted({p["sport"] for p in upcoming}), "engines_active": active,
                        "threshold_counts": counts, "settled_yesterday": len(settled_yday),
                        "system": health["overall"], "api_credits_last_observed": health["api_credits"]["remaining"]},
            "default_view_min_probability": DEFAULT_VIEW, "health": health, "prospective_evidence": evidence,
            "skipped_last_run": skips_last_run, "predictions": rows}


def write(board: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest_prediction_board.json").write_text(json.dumps(board, indent=1, default=str))
    with (out_dir / "latest_prediction_board.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PREDICTION_FIELDS + JOINED)
        w.writeheader()
        w.writerows(board["predictions"])
    (out_dir / "latest_prediction_board.md").write_text(render_md(board))


def _pct(x) -> str:
    return "—" if x is None else f"{100 * float(x):.1f}%"


def render_md(b: dict) -> str:
    s, h = b["summary"], b["health"]
    lines = [f"# DAILY PREDICTION BOARD — {b['date']}", "",
             "_Paper research board: what is most likely to happen. Not a betting card (see the Money Card)._", ""]
    if h["overall"] == "DEGRADED":
        lines += ["> **SYSTEM DEGRADED: " + "; ".join(h["warnings"]) + ".** Predictions below may be incomplete or stale.", ""]
    lines += [f"Upcoming events: {s['upcoming_events']} · Valid predictions: {s['valid_predictions']} · "
              f"Sports: {', '.join(s['sports_active']) or '—'}",
              "Counts: " + " · ".join(f"{k}: {v}" for k, v in s["threshold_counts"].items()),
              f"Settled yesterday: {s['settled_yesterday']} · System: **{s['system']}** · API credits (last observed): "
              f"{s['api_credits_last_observed'] if s['api_credits_last_observed'] is not None else 'unknown'}", "",
              f"## Top predictions (P ≥ {int(b['default_view_min_probability'] * 100)}%)", "",
              "| Sport | Event | Start (UTC) | Market | Selection | P | Fair | Band | Engine | Evidence | Price (source) | Single | Multi-research |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    top = [p for p in b["predictions"] if float(p["estimated_probability"]) >= b["default_view_min_probability"]]
    for p in top:
        price = f"{float(p['live_price']):.2f} ({p['live_price_source']})" if p["live_price"] not in ("", None) else "—"
        lines.append(f"| {p['sport']} | {p['event_name']} | {p['event_start'][:16]} | {p['market']} | {p['selection']} | "
                     f"{_pct(p['estimated_probability'])} | {float(p['fair_odds']):.2f} | {p['probability_band']} | "
                     f"{p['engine_id']}@{p['engine_version']} | {p['engine_status']} | {price} | "
                     f"{'yes' if str(p['single_eligible']) == 'True' else 'no'} | {'yes' if str(p['multi_research_eligible']) == 'True' else 'no'} |")
    if not top:
        lines.append("| — | no upcoming prediction at this level | | | | | | | | | | | |")
    lines += ["", "## Prospective evidence", "", "| Engine | Status | Predictions | Settled | Maturity | ≥80% settled | ≥80% pred → actual |",
              "|---|---|---|---|---|---|---|"]
    for eid, e in b["prospective_evidence"].items():
        lines.append(f"| {eid} | {e['status']} / {e['prospective_status']} | {e['predictions']} | {e['settled_rows']} | {e['maturity']} | "
                     f"{e['ge80_settled']} | {_pct(e['ge80_mean_pred'])} → {_pct(e['ge80_actual'])} |")
    lines += ["", "## System health", ""]
    for k, v in h["components"].items():
        lines.append(f"- {k}: {v['flag']} (last {v['last'] or 'unknown'})")
    if h["warnings"]:
        lines.append("- Warnings: " + "; ".join(h["warnings"]))
    lines += ["", "Single = passes the engine money status and payout floor pre-filter only; the Money Card decides bets. "
              "Double Chance is PROVISIONAL_PROSPECTIVE (exposed-data history; sealed holdout opens 2027-01-03)."]
    return "\n".join(lines) + "\n"
