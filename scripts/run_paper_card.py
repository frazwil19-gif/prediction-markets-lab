"""V2-20 Daily Paper Bet Card + paper dashboard (pcard-1; PAPER ONLY; 0 API credits).

Run after `run_bet_selection_v2.py evaluate` (or `settle`). Reads the bsv2 candidates of the latest run, the Stage A
board and the bsv2 paper ledgers; writes reports/daily_paper_card.{json,md}, reports/paper_dashboard.{json,md} and
appends first-sight grades to paper_betting_v2/card_enrichment.csv (never rewritten). Never changes a bsv2 decision.
Spec: research/platform_v2/v2_20_paper/PREREGISTRATION.md
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from prediction_markets_lab.bet_selection_v2 import paper_ledger as L
from prediction_markets_lab.paper_card import card as PC

REPO = Path(__file__).resolve().parents[1]


def run(repo: Path, now: datetime, cfg_path: Path | None = None) -> dict:
    cfg = PC.load_config(cfg_path or repo / "config/paper_card.yaml", repo)
    p = cfg.paths
    bs_rule = yaml.safe_load((repo / "config/bet_selection_v2.yaml").read_text())["rule_version"]
    stage_a = json.loads(p["stage_a_board"].read_text()) if p["stage_a_board"].exists() else {"predictions": []}
    sels = L.read_rows(p["paper_dir"] / "selections.csv")
    card = PC.build_card(cfg, L.read_rows(p["candidates"]), stage_a, sels, now)
    added = PC.append_enrichment(p["enrichment_ledger"], PC.enrichment_rows(card, sels, cfg), card["stake_columns"])
    enrich = {r["selection_id"]: r for r in L.read_rows(p["enrichment_ledger"])}
    ann = {r["selection_id"]: r["annotation"] for r in L.read_rows(p["paper_dir"] / "selection_annotations.csv")}
    sett = {r["selection_id"]: r for r in L.read_rows(p["paper_dir"] / "settlements.csv")}
    dash = PC.dashboard(cfg, sels, sett, enrich, ann, bs_rule, now)
    for key, obj, md in (("card", card, PC.render_card_md(card)), ("dashboard", dash, PC.render_dashboard_md(dash))):
        p[f"{key}_json"].parent.mkdir(parents=True, exist_ok=True)
        p[f"{key}_json"].write_text(json.dumps(obj, indent=1, default=str))
        p[f"{key}_md"].write_text(md)
    print(json.dumps({"grade_counts": card["grade_counts"], "no_bet_today": card["no_bet_today"],
                      "enrichment_rows_added": added}, indent=1))
    return {"card": card, "dashboard": dash, "enrichment_added": added}


def main() -> int:
    run(REPO, datetime.now(timezone.utc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
