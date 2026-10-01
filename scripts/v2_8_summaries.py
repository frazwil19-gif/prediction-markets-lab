"""CSV summaries from V2-8 RESULTS.json (portfolio metrics, marginal leg, bankroll realism, near-miss)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "research/platform_v2/portfolio_v2_8"


def w(name, rows):
    with (D / name).open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)


def main() -> int:
    r = json.loads((D / "RESULTS.json").read_text())
    port, marg, bank, nm = [], [], [], []
    for key, b in r["blocks"].items():
        for per in ("development", "holdout", "all"):
            P = b.get(f"portfolios_{per}")
            if not P:
                continue
            for s, v in P.items():
                if s == "NO_BET":
                    continue
                m = v["model_mean"]
                port.append({"block": key, "period": per, "structure": s, "n_lines": v["n_lines"],
                             "max_share_on_one_leg": round(v["max_share_on_one_leg"], 3), "model_expected_return": m["expected_return"],
                             "model_sd": m["sd"], "model_p_full_loss": m["p_full_loss"], "model_p_positive": m["p_positive"],
                             "model_exp_log_growth_2pct": m["exp_log_growth"], "realised_return": v["realised_mean_return_per_unit"],
                             "realised_ci_lo": v["realised_ci95"][0], "realised_ci_hi": v["realised_ci95"][1],
                             "delta_star_pp": v["delta_star_to_zero_ev_pp"],
                             **{f"vs_singles_f{f}": v[f"vs_singles_f{f}"]["verdict"] for f in (0.01, 0.02, 0.05)},
                             "maxdd_f2pct": v["realised_f0.02"]["max_drawdown"], "p_below_half_f5pct": v["realised_f0.05"]["p_bankroll_below_half"]})
        for a, v in b.get("marginal_leg", {}).items():
            marg.append({"block": key, "acc": a, **{k: v.get(k) for k in ("p_joint", "odds", "ev", "sigma", "implied_margin", "growth_at_s",
                                                                          "kelly_fraction", "kelly_growth", "p_full_loss",
                                                                          "share_days_leg_improves_kelly_growth")}})
        for k, v in b.get("bankroll_realism_all_days", {}).items():
            s, bb, f, mn = k.split("|")
            bank.append({"block": key, "structure": s, "bankroll0": bb[1:], "daily_fraction": f[1:], "min_line": mn[3:], **v})
        if b.get("near_miss"):
            x = b["near_miss"]
            nm.append({"block": key, "sets": b["sets"], "failed": x["failed_cards"], **{f"one_loser_{k}": v for k, v in x["exactly_one_loser"].items()},
                       **{f"lowest_lost_{k}": v for k, v in x["lowest_p_leg_lost"].items()},
                       "gof_p_sim": b["legs_correct_gof"]["p_sim"]})
    w("portfolio_summary.csv", port)
    w("marginal_leg.csv", marg)
    w("bankroll_realism.csv", bank)
    w("near_miss.csv", nm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
