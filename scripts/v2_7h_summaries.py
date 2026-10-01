"""Machine-readable CSV summaries from V2-7H RESULTS.json. Applies amendment A3 (reporting): a card-vs-singles comparison with
fewer than 30 days is reported as INSUFFICIENT_DAYS (the day-bootstrap CI is degenerate), never as a verdict."""
from __future__ import annotations

import csv
import json
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "research/platform_v2/card_backtest_v2_7h"
MIN_DAYS = 30


def w(name: str, rows: list[dict]) -> None:
    with (D / name).open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)


def main() -> int:
    r = json.loads((D / "RESULTS.json").read_text())
    cal = []
    for src, block in (("PROB_frozen", r["calibration_U1_PROB"]), ("priced_scenarios", r["priced_calibration_U1"])):
        for sp, d in block.items():
            for k in ("k1", "k2", "k3"):
                for per in ("development", "holdout"):
                    if per not in d[k]:
                        continue
                    for band, m in [("ALL", d[k][per]["overall"])] + list(d[k][per]["bands"].items()):
                        cal.append({"source": src, "sport_or_scenario": sp, "k": k[1], "period": per, "band": band, "n": m["n"],
                                    "pred": m["pred"], "actual": m["actual"], "bias": m["bias"], "ci_lo": m["bias_ci95"][0],
                                    "ci_hi": m["bias_ci95"][1], "ci_halfwidth": m["ci_halfwidth"], "recal_slope": m.get("recal_slope", ""),
                                    "brier": m["brier"], "brier_skill": m["brier_skill"], "log_loss": m["log_loss"],
                                    "n_eff_cluster": m["n_eff_cluster"], "sparse": m.get("sparse", False)})
    w("calibration_summary.csv", cal)
    sims = []
    for scen, S in r["simulations"].items():
        for key, v in S.items():
            if key == "label":
                continue
            st, k = key.split("|")
            for per in ("development", "holdout"):
                if per not in v:
                    continue
                x = v[per]
                for s, blk in x["stakes"].items():
                    for struct, m in blk.items():
                        if struct == "comparison":
                            continue
                        comp = blk.get("comparison", {})
                        verdict = comp.get("verdict", "")
                        if verdict and x["n_days"] < MIN_DAYS:
                            verdict = "INSUFFICIENT_DAYS"
                        sims.append({"scenario": scen, "strategy": st, "population": "HIGH_P" if st in ("S1", "S2", "S5") else "POS_EV",
                                     "k": k[1], "period": per, "stake": s, "structure": struct, "days": x["n_days"],
                                     "mean_p_joint": x["mean_p_joint"], "card_win_rate": x["realised_card_win_rate"],
                                     "calib_bias": x["calibration"]["bias"], "mean_model_card_ev": x["mean_model_card_ev"],
                                     "roi_per_unit": m["roi_per_unit"], "roi_ci_lo": m["roi_ci95"][0], "roi_ci_hi": m["roi_ci95"][1],
                                     "mean_log_return": m["mean_log_return"], "model_expected_log_growth": m["model_expected_log_growth"],
                                     "final_bankroll": m["final_bankroll"], "max_drawdown": m["max_drawdown"],
                                     "longest_losing_run": m["longest_losing_run"], "whole_stake_loss_share": m["whole_stake_loss_share"],
                                     "p_bankroll_below_half": m["p_bankroll_below_half_bootstrap"],
                                     "card_minus_singles_logret": comp.get("mean_diff_card_minus_singles", ""),
                                     "diff_ci_lo": comp.get("ci95", ["", ""])[0], "diff_ci_hi": comp.get("ci95", ["", ""])[1],
                                     "verdict": verdict})
    w("simulation_summary.csv", sims)
    mc = [{"scenario": s, "book": b, **v} for s, bb in r["margin_compounding"].items() for b, v in bb.items()]
    w("margin_compounding.csv", mc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
