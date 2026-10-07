"""Daily Prediction Board + Daily Bet Card V1 (card-v1).

One user-facing report built from existing, unchanged components:
  * Stage A board (reports/latest_stage_a_board.json): every valid prediction, probability first, sigma, engine status,
    price status;
  * bet-selection bsv2-4 decisions (reports/bet_selection_v2_candidates.csv): the ONLY source of bet decisions;
  * research predictors (corners-A-1.0 collector rows): shown with model fair odds and "RESEARCH -- NOT MONEY ELIGIBLE",
    never with a betting instruction.
Sections: BEST PREDICTIONS TODAY -> BEST BETS TODAY -> STRONG PREDICTIONS, PRICE TOO LOW -> RESEARCH PREDICTIONS.
Stakes follow config live_policy; real money is OFF unless explicitly enabled.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

PAPER_BET = "PAPER_BET"
PRICE_TEXT = {"PRICE_QUALITY_FAIL": "price not usable (stale/wide/unknown commission)", "POOR_PAYOUT": "price below fair",
              "PRICE_UNAVAILABLE": "no price", "PRICE_VALID": "price above fair"}
RESEARCH_STATUS = "RESEARCH — NOT MONEY ELIGIBLE"


@dataclass(frozen=True)
class CardConfig:
    raw: dict

    @classmethod
    def load(cls, path: Path) -> "CardConfig":
        return cls(yaml.safe_load(path.read_text()))

    def __getitem__(self, k):
        return self.raw[k]


def ts(s: str) -> datetime:
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def band(p: float, bands: list[float]) -> str:
    for b in sorted(bands, reverse=True):
        if p >= b:
            return f"{int(round(100 * b))}%+"
    return f"<{int(round(100 * min(bands)))}%"


def fair_odds(p: float) -> float:
    return round(1 / p, 2)


def in_window(start: str, now: datetime, hours: float) -> bool:
    t = ts(start)
    return now < t <= now + timedelta(hours=hours)


def evidence_label(row: dict, labels: dict) -> str:
    return labels.get(row.get("engine_status", ""), row.get("engine_status", "UNKNOWN"))


def best_decisions(candidates: list[dict]) -> dict[str, dict]:
    """prediction_id -> the candidate row bsv2-4 decided on (PAPER_BET preferred, then highest net EV)."""
    out: dict[str, dict] = {}
    for c in candidates:
        k = c["prediction_id"]
        key = (c.get("decision") == PAPER_BET, float(c["net_ev"]) if c.get("net_ev") not in (None, "", "None") else -9)
        cur = out.get(k)
        if cur is None or key > (cur.get("decision") == PAPER_BET,
                                 float(cur["net_ev"]) if cur.get("net_ev") not in (None, "", "None") else -9):
            out[k] = c
    return out


def money_eligible_engines(repo: Path) -> set[str]:
    from prediction_markets_lab.prediction_platform.registry import Registry
    reg = Registry.load(repo / "research/platform_v2/PROBABILITY_ENGINE_REGISTRY.json")
    return {eid for eid, e in reg.engines.items() if e.get("money_eligible")}


def assign_stakes(bets: list[dict], policy: dict) -> list[dict]:
    """Default stake to each bet in probability order, one per event, until the daily exposure cap. The £2 rule is
    disabled until a quantitatively justified rule is approved (no confidence-based doubling)."""
    used, events, out = 0.0, set(), []
    for b in sorted(bets, key=lambda r: (-r["probability"], -r["net_ev"])):
        stake = policy["default_stake_gbp"]
        if not b.get("money_eligible", True):
            note, stake = "PAPER ONLY — engine not money-eligible", 0.0
        elif b["event_key"] in events:
            note = "SKIP — one bet per event"
            stake = 0.0
        elif used + stake > policy["max_daily_exposure_gbp"] + 1e-9:
            note = "SKIP — daily exposure cap"
            stake = 0.0
        else:
            note = ""
            used += stake
            events.add(b["event_key"])
        out.append({**b, "stake_gbp": stake, "stake_note": note})
    return out


def corners_research(rows: list[dict], lines: list[float], now: datetime, hours: float, model: str, evidence: str) -> list[dict]:
    """Latest corners-A prediction per event inside the window; for each primary line the more likely side."""
    latest: dict[str, dict] = {}
    for r in rows:
        if r.get("kickoff_date") and (r["event_key"] not in latest or r["run_ts"] > latest[r["event_key"]]["run_ts"]):
            latest[r["event_key"]] = r
    out = []
    for r in latest.values():
        start = f"{r['kickoff_date']}T{(r.get('kickoff_time') or '12:00')[:5]}:00+00:00"
        if not in_window(start, now, hours + 24):     # kickoff time is UK local and may be missing: one extra day of slack
            continue
        for L in lines:
            col = f"p_total_over_{L}"
            if r.get(col) in (None, ""):
                continue
            p_over = float(r[col])
            side, p = ("over", p_over) if p_over >= 0.5 else ("under", 1 - p_over)
            out.append({"sport": "football", "competition": r["competition"], "event_name": f"{r['home']} v {r['away']}",
                        "event_start": start, "market": "total_corners", "selection": f"{side} {L}", "probability": round(p, 4),
                        "fair_odds": fair_odds(p), "model": model, "status": RESEARCH_STATUS, "evidence": evidence})
    return sorted(out, key=lambda x: -x["probability"])


def build(board: dict, candidates: list[dict], research_rows: list[dict], cfg: CardConfig, now: datetime,
          money_engines: set[str] | None = None) -> dict:
    """money_engines: engine ids with money_eligible=true. None = every engine (paper mode has no real stakes)."""
    hours, labels, bands = cfg["horizon_hours"], cfg["evidence_labels"], cfg["probability_bands"]
    dec = best_decisions(candidates)
    preds = []
    for r in board.get("predictions", []):
        if not in_window(r["event_start"], now, hours):
            continue
        p = float(r["probability"])
        d = dec.get(r["prediction_id"], {})
        preds.append({"prediction_id": r["prediction_id"], "sport": r["sport"], "competition": r["competition"],
                      "event_key": r["event_key"], "event_name": r["event_name"], "event_start": r["event_start"], "market": r["market"],
                      "selection": r["selection"], "probability": p, "band": band(p, bands), "sigma": r.get("sigma"),
                      "evidence": evidence_label(r, labels), "engine_id": r["engine_id"], "fair_odds": fair_odds(p),
                      "price_status": r["price_status"], "best_odds": r.get("best_clean_odds"), "best_source": r.get("best_clean_source"),
                      "best_net_ev": r.get("best_clean_net_ev"), "decision": d.get("decision", "NOT_EVALUATED"),
                      "decision_reasons": d.get("reasons", ""), "decision_odds": d.get("decimal_odds"), "decision_source": d.get("source"),
                      "decision_net_ev": d.get("net_ev"), "price_observed_at": d.get("price_observed_at")})
    preds.sort(key=lambda x: (-x["probability"], x["event_start"]))
    best_preds = [p for p in preds if p["probability"] >= cfg["best_predictions_min_probability"]][: cfg["best_predictions_max_rows"]]
    live = bool(cfg["live_policy"]["real_money_enabled"])
    bets = [{**p, "net_ev": float(p["decision_net_ev"]), "odds": float(p["decision_odds"]),
             "money_eligible": (not live) or money_engines is None or p["engine_id"] in money_engines}
            for p in preds if p["decision"] == PAPER_BET]
    bets = assign_stakes(bets, cfg["live_policy"])
    bet_ids = {b["prediction_id"] for b in bets}
    poor_price = [p for p in preds if p["probability"] >= cfg["strong_probability"] and p["prediction_id"] not in bet_ids]
    pol = cfg["live_policy"]
    staked = sum(b["stake_gbp"] for b in bets)
    return {"card_version": cfg["card_version"], "generated_at": now.isoformat(), "stage_a_generated_at": board.get("generated_at"),
            "real_money_enabled": bool(pol["real_money_enabled"]),
            "mode": "LIVE — manual £1 bets (you place them; nothing is automated)" if pol["real_money_enabled"] else "PAPER — live betting not activated",
            "summary": {"predictions_in_window": len(preds), "best_predictions_shown": len(best_preds), "bets": sum(b["stake_gbp"] > 0 for b in bets),
                        "total_stake_gbp": staked, "exposure_pct_of_bankroll": round(100 * staked / pol["bankroll_gbp"], 1),
                        "strong_price_too_low": len(poor_price), "research_predictions": len(research_rows)},
            "best_predictions": best_preds, "best_bets": bets, "strong_price_too_low": poor_price, "research": research_rows,
            "live_policy": pol}


def _pct(x) -> str:
    return "—" if x in (None, "", "None") else f"{100 * float(x):.1f}%"


def _odds(x) -> str:
    return "—" if x in (None, "", "None") else f"{float(x):.2f}"


def render_md(c: dict) -> str:
    s = c["summary"]
    L = [f"# Daily Prediction Board & Bet Card — {c['generated_at'][:16]}Z ({c['card_version']})", "",
         f"**Mode: {c['mode']}** · bankroll £{c['live_policy']['bankroll_gbp']:.0f} · default stake £{c['live_policy']['default_stake_gbp']:.0f} · "
         f"daily cap £{c['live_policy']['max_daily_exposure_gbp']:.0f}", "",
         f"Predictions in the next window: {s['predictions_in_window']} · bets: {s['bets']} (£{s['total_stake_gbp']:.0f}, "
         f"{s['exposure_pct_of_bankroll']}% of bankroll) · strong predictions with poor price: {s['strong_price_too_low']} · "
         f"research predictions: {s['research_predictions']}", "",
         "## 1. Best predictions today", "", "_Ranked by probability. A strong prediction is not automatically a bet._", "",
         "| # | Sport | Event | Start (UTC) | Market | Selection | P | Band | σ | Evidence | Fair odds | Best price | Bet? |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, p in enumerate(c["best_predictions"], 1):
        price = f"{_odds(p['best_odds'])} ({p['best_source']})" if p["best_odds"] not in (None, "") else PRICE_TEXT.get(p["price_status"], p["price_status"])
        L.append(f"| {i} | {p['sport']} | {p['event_name']} | {p['event_start'][:16]} | {p['market']} | {p['selection']} | {_pct(p['probability'])} | "
                 f"{p['band']} | {_pct(p['sigma'])} | {p['evidence']} | {p['fair_odds']:.2f} | {price} | {'YES' if p['decision'] == PAPER_BET else 'no'} |")
    if not c["best_predictions"]:
        L.append("| — | | no predictions in the window | | | | | | | | | | |")
    L += ["", "## 2. Best bets today", ""]
    if c["best_bets"]:
        L += ["| Event | Selection | P | Fair odds | Odds (source) | Price time | EV after costs | Stake | Note |", "|---|---|---|---|---|---|---|---|---|"]
        for b in c["best_bets"]:
            L.append(f"| {b['event_name']} ({b['event_start'][:16]}) | {b['market']}: {b['selection']} | {_pct(b['probability'])} | {b['fair_odds']:.2f} | "
                     f"{b['odds']:.2f} ({b['decision_source']}) | {str(b['price_observed_at'])[:16]} | {_pct(b['net_ev'])} | £{b['stake_gbp']:.0f} | {b['stake_note']} |")
        L += ["", "_How to bet: only rows with a £ stake. Check your bookmaker/exchange price is at least the odds shown — if it is lower, skip. "
              "Place it, then log it in your Bet Log (bookmaker, card odds, odds taken, stake, time). Rows marked PAPER ONLY are not live bets._"]
    else:
        L.append("No bet today — no prediction currently clears the bet rules (probability ≥ 50%, EV after costs ≥ +2%, clean fresh price). "
                 "That is a valid outcome, not a failure.")
    L += ["", "## 3. Strong predictions — price too low (no bet)", ""]
    if c["strong_price_too_low"]:
        L += ["| Event | Selection | P | Fair odds | Best clean price | Why no bet |", "|---|---|---|---|---|---|"]
        for p in c["strong_price_too_low"]:
            why = p["decision_reasons"] or PRICE_TEXT.get(p["price_status"], p["price_status"])
            L.append(f"| {p['event_name']} ({p['event_start'][:16]}) | {p['market']}: {p['selection']} | {_pct(p['probability'])} | {p['fair_odds']:.2f} | "
                     f"{_odds(p['best_odds'])} | {why.replace('|', ', ')} |")
    else:
        L.append("None in the window.")
    L += ["", "## 4. Research predictions — not money eligible", "",
          "_Model probabilities from research engines. Shown for information and to build a prospective record; they are NOT betting recommendations._", ""]
    if c["research"]:
        L += ["| Event | Start | Market | Selection | P | Model fair odds | Model | Status |", "|---|---|---|---|---|---|---|---|"]
        for r in c["research"]:
            L.append(f"| {r['event_name']} ({r['competition']}) | {r['event_start'][:10]} | {r['market']} | {r['selection']} | {_pct(r['probability'])} | "
                     f"{r['fair_odds']:.2f} | {r['model']} | {r['status']} |")
    else:
        L.append("None in the window (corners collector lists no covered-league fixtures yet).")
    return "\n".join(L) + "\n"


def read_csv(p: Path) -> list[dict]:
    return list(csv.DictReader(open(p, newline="", encoding="utf-8"))) if p.exists() else []


def run(repo: Path, cfg_path: Path, now: datetime) -> dict:
    cfg = CardConfig.load(cfg_path)
    board_p = repo / "reports/latest_stage_a_board.json"
    board = json.loads(board_p.read_text()) if board_p.exists() else {"predictions": []}
    cand = read_csv(repo / "reports/bet_selection_v2_candidates.csv")
    cc = cfg["research"]["corners"]
    research = corners_research(read_csv(repo / cc["predictions"]), cc["lines"], now, cfg["horizon_hours"], cc["model"], cc["evidence"])
    card = build(board, cand, research, cfg, now, money_eligible_engines(repo))
    out = repo / "reports"
    out.mkdir(exist_ok=True)
    (out / "daily_card_v1.json").write_text(json.dumps(card, indent=1, default=str) + "\n")
    (out / "daily_card_v1.md").write_text(render_md(card))
    return card
