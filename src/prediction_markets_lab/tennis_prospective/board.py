"""Render the paper tennis Prediction Board (JSON + Markdown). Ranked by validated
probability; no odds-derived value, EV, stake or bet language."""
from __future__ import annotations

from dataclasses import asdict

from prediction_markets_lab.tennis_prospective.engine import TennisPrediction

THRESHOLDS = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)


def build_board(date_str: str, preds: list[TennisPrediction], registry: dict, coverage: dict) -> dict:
    valid = sorted([p for p in preds if p.source_validated], key=lambda p: (-p.predicted_probability, p.commence_time))
    research = [p for p in preds if not p.source_validated]
    rows = []
    for p in valid:
        eng = registry["engines"][p.engine_id.split(".")[0]]
        band = eng["bands"].get(p.probability_band, {})
        rows.append({**asdict(p), "historical_band_n": band.get("n"), "historical_band_actual_rate": band.get("actual_rate"),
                     "historical_band_wilson95": band.get("wilson95"), "engine_holdout_n": eng["holdout_n"]})
    return {
        "board_date": date_str, "layer": "PREDICTION (paper) -- not a bet recommendation",
        "coverage": coverage,
        "counts": {"events_scanned": coverage.get("events_returned", 0), "valid_predictions": len(valid),
                   "research_only_predictions": len(research),
                   **{f"ge_{int(t*100)}": sum(p.predicted_probability >= t for p in valid) for t in THRESHOLDS}},
        "predictions": rows,
        "research_only": [asdict(p) for p in research],
    }


def render_markdown(board: dict) -> str:
    c = board["counts"]
    lines = [f"# TENNIS PREDICTION BOARD — {board['board_date']} (PAPER)", "",
             "Prediction layer only: no stakes, no bets, not part of the Daily Money Card.", "",
             f"Covered tournaments: {', '.join(board['coverage'].get('active_keys', [])) or 'none active'}  ",
             f"Matches scanned {c['events_scanned']} · valid predictions {c['valid_predictions']} · research-only {c['research_only_predictions']}  ",
             " · ".join(f"≥{k[3:]}%: {v}" for k, v in c.items() if k.startswith("ge_")), ""]
    if not board["predictions"]:
        lines.append("_No validated predictions today (no covered matches with a valid exchange quote)._")
    else:
        lines += ["| # | Tour | Tournament | Match | Predicted winner | P | Band | Unseen-data band hit rate | Source | Start (UTC) |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for i, r in enumerate(board["predictions"], 1):
            hist = (f"{r['historical_band_actual_rate']:.1%} (n={r['historical_band_n']})"
                    if r.get("historical_band_actual_rate") is not None else "—")
            lines.append(f"| {i} | {r['tour']} | {r['tournament']} | {r['player_a']} v {r['player_b']} | {r['predicted_winner']} | "
                         f"{r['predicted_probability']:.1%} | {r['probability_band']} | {hist} | {r['source']} | {r['commence_time'][:16]} |")
    return "\n".join(lines) + "\n"
