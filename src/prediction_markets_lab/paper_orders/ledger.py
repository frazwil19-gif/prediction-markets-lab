"""Paper-order ledger: one row per bsv2 PAPER_BET, joined to registry, CLV capture and settlement.

Derived and rebuilt every run from append-only sources, so it is auditable and never retro-fitted:
  decision  paper_betting_v2/selections.csv  (P, odds, source and time frozen at decision; fill = decision price)
  close     research_shadow/clv/captures.csv (target "sel:<selection_id>"); else H2 pre-close if present
  result    paper_betting_v2/settlements.csv
Execution class: BOOKMAKER_ONLY / EXCHANGE_EXECUTABLE / API_EXECUTABLE (config/paper_mode.yaml).
"""
from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

FIELDS = ["order_id", "prediction_id", "event_id", "sport", "event", "event_start", "market", "selection", "engine_id",
          "model_version", "engine_status_at_decision", "tier_now", "rule_version", "probability", "fair_odds",
          "source", "execution_class", "available_odds", "min_acceptable_odds", "commission", "estimated_ev",
          "ev_band", "decision_at", "price_age_minutes", "simulated_stake_gbp", "simulated_fill_odds",
          "qualification", "close_at", "close_minutes_before_start", "closing_same_book_odds", "closing_best_uk_odds",
          "closing_fair_p", "clv_price", "clv_fair", "result", "status", "paper_pnl_gbp", "settled_at", "dq_flags"]


def _rows(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _ts(s: str) -> datetime:
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def min_odds(p: float) -> float:
    return max(1.33, math.ceil(1.02 / p * 100) / 100)


def ev_band(ev: float) -> str:
    return "<0" if ev < 0 else "0-1" if ev < .01 else "1-2" if ev < .02 else "2-4" if ev < .04 else "4+"


def execution_class(source: str, cfg: dict) -> str:
    if source in cfg["api_executable_sources"]:
        return "API_EXECUTABLE"
    return "EXCHANGE_EXECUTABLE" if source in cfg["exchange_sources"] else "BOOKMAKER_ONLY"


def build(repo: Path, cfg: dict, now: datetime) -> list[dict]:
    reg = {e["engine_id"]: e for e in json.loads((repo / "research/platform_v2/PROBABILITY_ENGINE_REGISTRY.json").read_text())["engines"]}
    sel = _rows(repo / "paper_betting_v2/selections.csv")
    settle = {r["selection_id"]: r for r in _rows(repo / "paper_betting_v2/settlements.csv")}
    caps = {r["target_id"]: r for r in _rows(repo / "research_shadow/clv/captures.csv")}
    h2 = {r["selection_id"]: r for r in _rows(repo / "research_shadow/h2_pre_close/pre_close_value.csv")}
    stake = float(cfg["simulated_stake_gbp"])
    out = []
    for s in sel:
        p, o, c = float(s["probability"]), float(s["decimal_odds"]), float(s.get("commission") or 0)
        e = reg.get(s["engine_id"], {})
        tier = "PAPER_ONLY" if not e.get("money_eligible") else ("PROVISIONAL_LIVE" if e.get("live_tier") == "PROVISIONAL_LIVE" else "LIVE_ELIGIBLE")
        cap, pre = caps.get(f"sel:{s['selection_id']}"), h2.get(s["selection_id"])
        net = 1 + (o - 1) * (1 - c)
        close = {}
        if cap:
            same = cap.get("close_same_book_odds") or None
            close = {"close_at": cap["capture_at"], "close_minutes_before_start": cap["minutes_before_start"],
                     "closing_same_book_odds": same or "", "closing_best_uk_odds": cap.get("close_best_uk_odds") or "",
                     "closing_fair_p": cap["p_close"], "clv_price": round(o / float(same) - 1, 5) if same else "",
                     "clv_fair": round(net * float(cap["p_close"]) - 1, 5)}
        elif pre:
            close = {"close_at": pre["capture_at"], "close_minutes_before_start": pre["minutes_before_start"],
                     "closing_same_book_odds": "", "closing_best_uk_odds": pre.get("best_uk_odds") or "",
                     "closing_fair_p": pre["p_ref"], "clv_price": "",
                     "clv_fair": round(net * float(pre["p_ref"]) - 1, 5)}
        st = settle.get(s["selection_id"])
        flags = []
        if not close and _ts(s["event_start"]) < now:
            flags.append("NO_CLOSE_CAPTURED")
        if not st and _ts(s["event_start"]) + timedelta(hours=cfg["settlement_overdue_hours"]) < now:
            flags.append("SETTLEMENT_OVERDUE")
        try:
            if float(s.get("price_age_minutes") or 0) > cfg["max_price_age_minutes_flag"]:
                flags.append("OLD_PRICE_AT_DECISION")
        except ValueError:
            flags.append("PRICE_AGE_UNKNOWN")
        pnl = round(float(st["pnl_units"]) * stake, 4) if st and st.get("pnl_units") not in (None, "") else ""
        out.append({"order_id": s["selection_id"], "prediction_id": s["prediction_id"],
                    "event_id": s["event_key"], "sport": s["sport"], "event": s["event_name"], "event_start": s["event_start"],
                    "market": s["market"], "selection": s["selection"], "engine_id": s["engine_id"],
                    "model_version": e.get("ledger_version", ""), "engine_status_at_decision": s.get("engine_status", ""),
                    "tier_now": tier, "rule_version": s["rule_version"], "probability": p, "fair_odds": round(1 / p, 4),
                    "source": s["source"], "execution_class": execution_class(s["source"], cfg), "available_odds": o,
                    "min_acceptable_odds": min_odds(p), "commission": c, "estimated_ev": float(s["net_ev"]),
                    "ev_band": ev_band(float(s["net_ev"])), "decision_at": s["decision_at"],
                    "price_age_minutes": s.get("price_age_minutes", ""), "simulated_stake_gbp": stake,
                    "simulated_fill_odds": o, "qualification": s.get("reasons", ""),
                    **{k: close.get(k, "") for k in ("close_at", "close_minutes_before_start", "closing_same_book_odds",
                                                       "closing_best_uk_odds", "closing_fair_p", "clv_price", "clv_fair")},
                    "result": st.get("result", "") if st else "", "status": st["status"] if st else "OPEN",
                    "paper_pnl_gbp": pnl, "settled_at": st.get("settled_at", "") if st else "", "dq_flags": "|".join(flags)})
    return out


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
