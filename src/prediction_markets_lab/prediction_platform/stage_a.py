"""Stage A -- probability-first Prediction Board (V2-10 fix B, board version from config: ``stage-a-1``).

DECISION_PHILOSOPHY.md: Stage A answers "what is most likely?"; Stage B (bet-selection bsv2-3) answers "is this a bet?".
V2-9 found that the Stage A HIGH_P view inherited a clean-price requirement from the V2-7 card logger, so strong
predictions with a wide/missing price disappeared (30 Sep: 24 -> 16 and 26 -> 17). Here every valid, upcoming
prediction is listed and ranked by probability ONLY; price/market quality is a descriptive label, never a filter.

    STRONG PREDICTION != VALID BET.  ``is_bet_recommendation`` is always False; Stage B alone decides bets.

Price status (smallest taxonomy; judged on the LATEST observed quote set using the unchanged bsv2-3 quality rules):
    PRICE_UNAVAILABLE    no executable quote                                    -> not financially assessable
    PRICE_QUALITY_FAIL   quotes exist, none passes the bsv2-3 quality checks    -> not financially assessable
    POOR_PAYOUT          clean quote(s), none with net EV above the WATCH floor -> assessable, descriptive only
    PRICE_VALID          clean quote with net EV above the WATCH floor          -> assessable; Stage B decides
Stage A never changes Stage B inputs, thresholds or outputs; it calls the bsv2-3 evaluator read-only.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import yaml

from prediction_markets_lab.bet_selection_v2 import prices as PR
from prediction_markets_lab.bet_selection_v2.evaluate import evaluate_prediction
from prediction_markets_lab.card_engine.cards import leg_sigma

PRICE_VALID, POOR_PAYOUT, QUALITY_FAIL, UNAVAILABLE = "PRICE_VALID", "POOR_PAYOUT", "PRICE_QUALITY_FAIL", "PRICE_UNAVAILABLE"
ASSESSABLE = (PRICE_VALID, POOR_PAYOUT)
STRONG, BELOW_STRONG = "STRONG_PREDICTION", "BELOW_STRONG_THRESHOLD"
# bsv2-3 reason codes that describe price / market QUALITY (not financial gates such as EV floors or odds floors)
QUALITY_REASONS = frozenset({"EXCHANGE_SPREAD_TOO_WIDE", "EXCHANGE_SPREAD_UNKNOWN", "PROBABILITY_NOT_SAME_SNAPSHOT",
                             "PRICE_STALE", "PRICE_AT_OR_AFTER_START", "COMMISSION_UNKNOWN", "PROBABILITY_OUT_OF_RANGE"})
NO_PRICE = "NO_EXECUTABLE_PRICE"
BASIS_SCAN, BASIS_LEDGER = "LATEST_VALIDATED_SAME_SCAN", "LEDGER_FIRST_OBSERVATION"

FIELDS = ["rank", "prediction_id", "sport", "competition", "event_key", "event_name", "event_start", "event_start_original",
          "start_time_status", "market", "selection", "probability", "probability_basis", "probability_observed_at",
          "ledger_probability", "sigma", "sigma_calibration", "sigma_half_width", "exchange_width", "probability_band",
          "engine_id", "engine_version", "engine_status", "prediction_timestamp", "historical_support", "strength",
          "price_status", "stage_a_label", "financially_assessable", "price_status_reasons", "best_clean_source",
          "best_clean_odds", "best_clean_net_ev", "n_quotes_latest", "n_clean_quotes_latest", "price_observed_at",
          "is_bet_recommendation", "board_version"]


@dataclass(frozen=True)
class StageAConfig:
    board_version: str
    strong_min_probability: float
    calibration_results: Path
    bet_selection_config: Path


def load_config(path: Path, repo: Path) -> StageAConfig:
    c = yaml.safe_load(path.read_text())
    return StageAConfig(c["board_version"], float(c["strong_prediction_min_probability"]),
                        repo / c["calibration_results"], repo / c["bet_selection_config"])


def calibration_se(results_path: Path) -> Callable[[float], float]:
    """Per-band calibration SE, identical formula to the V2-7 logger (scripts/run_card_shadow.py::cal_se_fn; a test
    asserts equality). Read-only."""
    r = json.loads(results_path.read_text())["A1_joint_calibration"]
    se = {}
    for band in ("50-65%", "65-80%", "80%+"):
        se[band] = max((b["wilson95"][1] - b["wilson95"][0]) / (2 * 1.96)
                       for sp in ("tennis_atp", "tennis_wta") if (b := r[sp]["holdout_years"]["singles"].get(band)))
    return lambda p: se["80%+"] if p >= 0.80 else se["65-80%"] if p >= 0.65 else se["50-65%"]


def current_probability(pred: dict, prob_rows: list[dict], now: datetime) -> tuple[float, str, str, float | None]:
    """(P, basis, observed_at, exchange width). Tennis: the latest VALIDATED same-scan engine P for the ledger selection
    (the probability Stage B also uses); otherwise the ledger's frozen P. The ledger P is always kept separately."""
    if pred.get("sport") == "tennis":
        det = {k: v for k, v in PR.same_scan_details(pred, prob_rows).items() if PR.ts(k) <= now}
        if det:
            k = max(det, key=PR.ts)
            p, width, _src = det[k]
            return p, BASIS_SCAN, k, width
    return float(pred["estimated_probability"]), BASIS_LEDGER, pred["prediction_timestamp"], None


def price_status(pred: dict, snaps: list[PR.PriceSnapshot], bs_cfg: dict, now: datetime,
                 exchange_width: float | None = None) -> dict:
    """exchange_width: same-scan Betfair book width behind the CURRENT probability. When it exceeds the bsv2-3 limit the
    probability itself is unreliable, so no quote can be financially assessed -- including the ledger's own exchange-back
    quote, which bsv2-3 checks without spread information (V2-10 finding; Stage B is deliberately not changed here)."""
    _best, cands = evaluate_prediction(pred, snaps, bs_cfg, now)     # read-only use of the bsv2-3 evaluator
    priced = [c for c in cands if NO_PRICE not in c.reasons and c.price_observed_at]
    if not priced:
        return {"price_status": UNAVAILABLE, "price_status_reasons": NO_PRICE, "n_quotes_latest": 0, "n_clean_quotes_latest": 0}
    latest = max((c.price_observed_at for c in priced), key=PR.ts)
    cur = [c for c in priced if c.price_observed_at == latest]
    clean = [c for c in cur if c.net_ev is not None and not (QUALITY_REASONS & set(c.reasons))]
    max_w = bs_cfg.get("data_quality", {}).get("max_exchange_spread_prob")
    if exchange_width is not None and max_w is not None and exchange_width > max_w:
        return {"n_quotes_latest": len(cur), "n_clean_quotes_latest": 0, "price_observed_at": latest,
                "price_status": QUALITY_FAIL, "price_status_reasons": "EXCHANGE_SPREAD_TOO_WIDE"}
    base = {"n_quotes_latest": len(cur), "n_clean_quotes_latest": len(clean), "price_observed_at": latest}
    if not clean:
        why = sorted({r for c in cur for r in c.reasons if r in QUALITY_REASONS})
        return {**base, "price_status": QUALITY_FAIL, "price_status_reasons": "|".join(why)}
    best = max(clean, key=lambda c: (c.net_ev, c.source))
    floor = bs_cfg["decision_gates"]["watch"]["min_net_ev_exclusive"]
    return {**base, "price_status": PRICE_VALID if best.net_ev > floor else POOR_PAYOUT,
            "price_status_reasons": "" if best.net_ev > floor else "NO_CLEAN_QUOTE_ABOVE_FAIR",
            "best_clean_source": best.source, "best_clean_odds": best.decimal_odds, "best_clean_net_ev": round(best.net_ev, 6)}


def build(eligible: list[dict], prob_rows: list[dict], snaps_for: Callable[[dict], list[PR.PriceSnapshot]], bs_cfg: dict,
          cfg: StageAConfig, cal_se: Callable[[float], float] | None, now: datetime) -> dict:
    """eligible: unified predictions already filtered by the est-1 start-time rule (current start overlaid)."""
    valid = [p for p in eligible if str(p.get("prediction_valid")) == "True"]
    by_sel: dict[tuple[str, str, str], dict] = {}
    dup = 0
    for p in valid:   # one row per (event, market, selection): the most recent prediction of record
        k = (p["event_key"], p["market"], p["selection"])
        if k in by_sel:
            dup += 1
            if p["prediction_timestamp"] <= by_sel[k]["prediction_timestamp"]:
                continue
        by_sel[k] = p
    rows = []
    for p in by_sel.values():
        prob, basis, obs_at, width = current_probability(p, prob_rows, now)
        cse = cal_se(prob) if (cal_se and p.get("sport") == "tennis") else None
        sig = leg_sigma(prob, width, cse) if (cse is not None and width is not None) else cse
        strength = STRONG if prob >= cfg.strong_min_probability else BELOW_STRONG
        ps = price_status(p, snaps_for(p), bs_cfg, now, width if basis == BASIS_SCAN else None)
        rows.append({"prediction_id": p["prediction_id"], "sport": p["sport"], "competition": p["competition"],
                     "event_key": p["event_key"], "event_name": p["event_name"], "event_start": p["event_start"],
                     "event_start_original": p.get("event_start_original", p["event_start"]),
                     "start_time_status": p.get("start_time_status", ""), "market": p["market"], "selection": p["selection"],
                     "probability": round(prob, 6), "probability_basis": basis, "probability_observed_at": obs_at,
                     "ledger_probability": float(p["estimated_probability"]),
                     "sigma": None if sig is None else round(sig, 6), "sigma_calibration": None if cse is None else round(cse, 6),
                     "sigma_half_width": None if width is None else round(width / 2, 6), "exchange_width": width,
                     "probability_band": p["probability_band"], "engine_id": p["engine_id"], "engine_version": p["engine_version"],
                     "engine_status": p["engine_status"], "prediction_timestamp": p["prediction_timestamp"],
                     "historical_support": p.get("historical_support", ""), "strength": strength,
                     "price_status": ps["price_status"], "stage_a_label": f"{strength}_{ps['price_status']}"
                     if strength == STRONG else ps["price_status"],
                     "financially_assessable": ps["price_status"] in ASSESSABLE,
                     "price_status_reasons": ps.get("price_status_reasons", ""),
                     "best_clean_source": ps.get("best_clean_source", ""), "best_clean_odds": ps.get("best_clean_odds"),
                     "best_clean_net_ev": ps.get("best_clean_net_ev"), "n_quotes_latest": ps["n_quotes_latest"],
                     "n_clean_quotes_latest": ps["n_clean_quotes_latest"], "price_observed_at": ps.get("price_observed_at", ""),
                     "is_bet_recommendation": False, "board_version": cfg.board_version})
    rows.sort(key=lambda r: (-r["probability"], r["event_start"], r["prediction_id"]))   # probability first, only
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    strong = [r for r in rows if r["strength"] == STRONG]
    count = lambda rs, k: {v: sum(r[k] == v for r in rs) for v in sorted({r[k] for r in rs})}   # noqa: E731
    return {"board_version": cfg.board_version, "product": "STAGE A PREDICTION BOARD (probability first; NOT a betting card)",
            "principle": "STRONG PREDICTION != VALID BET. Stage B (bet-selection) alone decides bets.",
            "generated_at": now.isoformat(), "strong_prediction_min_probability": cfg.strong_min_probability,
            "summary": {"predictions": len(rows), "strong_predictions": len(strong),
                        "strong_unique_events": len({r["event_key"] for r in strong}),
                        "strong_by_price_status": count(strong, "price_status"),
                        "all_by_price_status": count(rows, "price_status"), "duplicate_prediction_rows_collapsed": dup},
            "predictions": rows}


def write(board: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest_stage_a_board.json").write_text(json.dumps(board, indent=1, default=str))
    with (out_dir / "latest_stage_a_board.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(board["predictions"])
    (out_dir / "latest_stage_a_board.md").write_text(render_md(board))


def _pct(x) -> str:
    return "—" if x in (None, "") else f"{100 * float(x):.1f}%"


def render_md(b: dict) -> str:
    s = b["summary"]
    lines = [f"# STAGE A PREDICTION BOARD — {b['generated_at'][:16]}Z ({b['board_version']})", "",
             "_Probability first. Ranked by estimated probability only. **A strong prediction is not a bet** — "
             "price status is descriptive; Stage B (bet-selection) alone decides bets._", "",
             f"Predictions: {s['predictions']} · strong (P ≥ {int(100 * b['strong_prediction_min_probability'])}%): "
             f"{s['strong_predictions']} on {s['strong_unique_events']} events · strong by price status: "
             + (" · ".join(f"{k} {v}" for k, v in s["strong_by_price_status"].items()) or "—"), "",
             "| # | Event | Start (UTC) | Selection | P | σ | Basis | Engine | Stage A status | Why not assessable | Best clean price | Net EV |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    strong = [r for r in b["predictions"] if r["strength"] == STRONG]
    for r in strong:
        price = f"{float(r['best_clean_odds']):.2f} ({r['best_clean_source']})" if r["best_clean_odds"] else "—"
        why = "" if r["financially_assessable"] else (r["price_status_reasons"] or r["price_status"])
        resched = " ⟳" if r["start_time_status"] == "RESCHEDULED" else ""
        lines.append(f"| {r['rank']} | {r['event_name']} | {r['event_start'][:16]}{resched} | {r['selection']} | {_pct(r['probability'])} | "
                     f"{_pct(r['sigma'])} | {r['probability_basis']} | {r['engine_id']} | {r['stage_a_label']} | {why} | {price} | "
                     f"{_pct(r['best_clean_net_ev'])} |")
    if not strong:
        lines.append("| — | no strong prediction | | | | | | | | | | |")
    lines += ["", "⟳ = start time rescheduled since first observation (est-1: the current provider start is used).",
              "PRICE_VALID means only that a clean quote above fair exists; it is NOT a bet. See reports/bet_selection_v2.md."]
    return "\n".join(lines) + "\n"
