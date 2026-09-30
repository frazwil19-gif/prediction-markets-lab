"""V2-8 OFFLINE portfolio analyser CLI (RESEARCH ONLY). Reads frozen V2-7 records + production prices READ-ONLY; writes only to
--out (refused inside V2-7 / production directories). 0 API credits. Places nothing.

  python scripts/run_v2_8_analyser.py --out <dir> [--records <v2-7 dir>] [--scan <ts>] [--allow-dry-run] [--with-outcomes]

--allow-dry-run  also accept V2-7 DRY_RUN_REPLAY records (demonstration only; never prospective evidence)
--with-outcomes  attach leg outcomes from the verified settlement ledger (OFF by default: research settlement needs approval)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from prediction_markets_lab.card_engine import shadow as S
from prediction_markets_lab.research import v2_8_analyser as A

REPO = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--records", type=Path, default=None)
    ap.add_argument("--config", type=Path, default=REPO / "config/v2_8_analyser.yaml")
    ap.add_argument("--scan", default="")
    ap.add_argument("--allow-dry-run", action="store_true")
    ap.add_argument("--with-outcomes", action="store_true")
    a = ap.parse_args(argv)
    cfg = A.load_config(a.config)
    out = A.guard_output(a.out, REPO)
    root = a.records or REPO / cfg.inputs["v2_7_records"]
    shadow_cfg = S.load_config(REPO / cfg.inputs["shadow_config"], REPO)
    recs = A.valid_records(root, a.allow_dry_run)
    if a.scan:
        recs = [r for r in recs if r["scan"] == a.scan]
    if not recs:
        print(json.dumps({"status": "NO_VALID_V2_7_RECORDS", "records_dir": str(root)}))
        return 0
    out.mkdir(parents=True, exist_ok=True)
    summary = {"analyser_version": cfg.version, "scans": 0, "predictions": 0, "single_labels": Counter(), "benchmark_flags": Counter(),
               "structure_screen_passes": Counter(), "no_bet_scans": 0}
    for rec in sorted(recs, key=lambda r: r["scan"]):
        res = A.analyse_scan(rec, root, REPO, cfg, shadow_cfg, a.with_outcomes)
        tag = rec["scan"].replace(":", "").replace("+", "Z")[:17]
        (out / f"analysis_{tag}.json").write_text(json.dumps(res, indent=1, default=str))
        (out / f"daily_bet_card_{tag}.md").write_text(A.render_markdown(res))
        summary["scans"] += 1
        summary["predictions"] += len(res["stage_A_prediction_board"])
        summary["single_labels"].update(s["label"] for s in res["stage_B_single_evaluation"])
        summary["benchmark_flags"].update(b["benchmark_flag"] for b in res["stage_A_prediction_board"])
        passes = [f"{pop}|{n}|{s}" for pop, blocks in res["stage_B_structures"].items() for n, blk in blocks.items()
                  for s in blk.get("research_screen", {}).get("structures_passing_ev_low_gt_0", [])]
        summary["structure_screen_passes"].update(passes)
        summary["no_bet_scans"] += int(not passes)
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=dict))
    print(json.dumps(summary, default=dict))
    return 0


if __name__ == "__main__":
    sys.exit(main())
