"""V2-13 DRY football Stage A reconstruction from the latest committed daily card (E0/E1/SC0 fixtures 9-19 Oct 2026).

NOT prospective evidence: nothing is appended to any ledger; the 48h first-scan window is widened IN MEMORY only so
that the fixtures (all > 48h away at card time) can be shown; probabilities are the card's (data timestamp shown).
No outcomes. 0 API calls. Output: research/platform_v2/v2_13_football/DRY_STAGE_A_RECONSTRUCTION.{json,md}
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from prediction_markets_lab.bet_selection_v2 import prices as PR
from prediction_markets_lab.bet_selection_v2.evaluate import load_config as load_bs
from prediction_markets_lab.prediction_platform import adapters as A
from prediction_markets_lab.prediction_platform import stage_a as SA
from prediction_markets_lab.prediction_platform.registry import Registry
from prediction_markets_lab.prediction_platform.schema import to_row

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/v2_13_football"


def main() -> int:
    days = sorted(d for d in (REPO / "daily_cards").iterdir() if (d / "card.json").exists())
    card_path = days[-1] / "card.json"
    card = json.loads(card_path.read_text())
    data_ts = A._ts(card["data_timestamp"])
    reg = Registry.load()
    A.FOOTBALL_WINDOW_MIN = 30 * 24 * 60          # DRY RUN ONLY: show every fixture on the card (in memory)
    ctx = A.RunContext(None, None, 1.33)
    preds, skips = A.football_from_card(card, reg, ctx, data_ts, origin=f"DRY:{card_path.relative_to(REPO)}")
    rows = [to_row(p) for p in preds]
    cfg = SA.load_config(REPO / "config/prediction_board_stage_a.yaml", REPO)
    bs = load_bs(cfg.bet_selection_config)
    status = {eid: e["calibration_status"] for eid, e in reg.engines.items()}
    board = SA.build(rows, [], lambda p: PR.football_from_card(p, card), bs, cfg, None, data_ts,
                     SA.football_sigma(cfg.football_sigma_evidence), status)
    by_ev: dict[str, dict] = defaultdict(dict)
    for r in board["predictions"]:
        by_ev[r["event_key"]][(r["market"], r["selection"])] = r
    fixtures = []
    for key, d in sorted(by_ev.items(), key=lambda kv: kv[0].split("|")[-1]):
        any_r = next(iter(d.values()))
        x = {s: d.get(("1x2", s)) for s in ("home", "draw", "away")}
        top = max((r for r in x.values() if r), key=lambda r: r["probability"], default=None)
        dc = {s: d.get(("double_chance", s)) for s in ("1X", "X2", "12")}
        best_dc = max((r for r in dc.values() if r), key=lambda r: r["probability"], default=None)
        fixtures.append({
            "fixture": any_r["event_name"], "league": any_r["competition"], "kickoff": any_r["event_start"],
            "raw_hda": [x[s]["ledger_probability"] if x[s] else None for s in ("home", "draw", "away")],
            "normalised_hda": [x[s]["probability"] if x[s] else None for s in ("home", "draw", "away")],
            "normalisation": x["home"]["normalisation"] if x["home"] else "",
            "top_1x2": top and {"selection": top["selection"], "p": top["probability"], "sigma": top["sigma"],
                                 "price_status": top["price_status"], "best_clean_odds": top["best_clean_odds"]},
            "dc": {s: (dc[s]["probability"] if dc[s] else None) for s in ("1X", "X2", "12")},
            "best_dc": best_dc and {"selection": best_dc["selection"], "p": best_dc["probability"], "sigma": best_dc["sigma"],
                                     "price_status": best_dc["price_status"]},
            "probability_basis": any_r["probability_basis"],
            "calibration_status": {"1x2": status["football_1x2.market_consensus"],
                                   "double_chance": status["football_double_chance.derived_1x2"]}})
    week = lambda k: datetime.fromisoformat(k).isocalendar()[1]   # noqa: E731
    vol: dict[int, Counter] = defaultdict(Counter)
    for f in fixtures:
        w = week(f["kickoff"])
        vol[w]["fixtures"] += 1
        vol[w]["prediction_rows"] += sum(v is not None for v in f["normalised_hda"]) + sum(v is not None for v in f["dc"].values())
        for t in (0.70, 0.80):
            vol[w][f"1x2_top_ge{int(t * 100)}"] += int(bool(f["top_1x2"]) and f["top_1x2"]["p"] >= t)
            vol[w][f"dc_best_ge{int(t * 100)}"] += int(bool(f["best_dc"]) and f["best_dc"]["p"] >= t)
    out = {"label": "DRY RUN - not prospective evidence; no ledger written; 48h window widened in memory; no outcomes",
           "card": str(card_path.relative_to(REPO)), "card_data_timestamp": card["data_timestamp"],
           "skips": [s.__dict__ for s in skips], "stage_a_summary": board["summary"], "volume_by_iso_week": {w: dict(c) for w, c in sorted(vol.items())},
           "fixtures": fixtures}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "DRY_STAGE_A_RECONSTRUCTION.json").write_text(json.dumps(out, indent=1, default=str))
    pct = lambda v: "—" if v is None else f"{100 * v:.1f}"   # noqa: E731
    md = ["# DRY football Stage A reconstruction (NOT prospective evidence)", "",
          f"Card `{out['card']}` (data {card['data_timestamp'][:16]}Z). No ledger rows written; the 48h first-scan window was widened "
          "in memory only. P basis = P_FIRST_SNAPSHOT (card snapshot). Calibration status: 1X2 = historical closing estimator "
          "only (live estimator not validated); DC = exposed data only (sealed holdout pending). σ = historical band clustered "
          "SE (closing estimator; live-timing bias excluded). Price status from the card's own 1X2 quotes; DC has no "
          "executable price (Stage B DATA BLOCKED).", "",
          "| Kickoff (UTC) | League | Fixture | Raw H/D/A | Normalised H/D/A | Top 1X2 (P, σ, price status) | DC 1X/X2/12 | Best DC (P, σ) |",
          "|---|---|---|---|---|---|---|---|"]
    for f in fixtures:
        t, b = f["top_1x2"], f["best_dc"]
        md.append(f"| {f['kickoff'][:16]} | {f['league']} | {f['fixture']} | {'/'.join(pct(v) for v in f['raw_hda'])} | "
                  f"{'/'.join(pct(v) for v in f['normalised_hda'])} | "
                  f"{t['selection']} {pct(t['p'])} ±{pct(t['sigma'])} {t['price_status']} | "
                  f"{'/'.join(pct(f['dc'][s]) for s in ('1X', 'X2', '12'))} | {b['selection']} {pct(b['p'])} ±{pct(b['sigma'])} |")
    md += ["", "## Expected volume (predictions, not bets)", "", "| ISO week | Fixtures | Rows | 1X2 top ≥70 | 1X2 top ≥80 | DC best ≥70 | DC best ≥80 |",
           "|---|---|---|---|---|---|---|"]
    for w, c in sorted(vol.items()):
        md.append(f"| {w} | {c['fixtures']} | {c['prediction_rows']} | {c['1x2_top_ge70']} | {c['1x2_top_ge80']} | {c['dc_best_ge70']} | {c['dc_best_ge80']} |")
    (OUT / "DRY_STAGE_A_RECONSTRUCTION.md").write_text("\n".join(md) + "\n")
    print(json.dumps({"fixtures": len(fixtures), "summary": board["summary"], "volume": out["volume_by_iso_week"]}, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
