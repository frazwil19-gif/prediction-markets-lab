"""V2-8 OFFLINE portfolio analyser (research only; analyser v2-8a-1).

Probability-first, two stages (research/platform_v2/DECISION_PHILOSOPHY.md):
  Stage A  PREDICTION BOARD  -- every frozen HIGH_P prediction, ranked by probability (never by EV), with uncertainty, calibration
                                support, model, timestamp and the bookmaker-consensus BENCHMARK (disagreement => INVESTIGATE).
  Stage B  BETTING CARD      -- per prediction: prices, fair odds, payout, EV and its range, quote age; then equal-capital
                                structures (singles / doubles / trebles / 4-5 folds / mixed / systems / NO BET) for the strongest
                                N predictions, HIGH_P and POS_EV populations kept separate. Labels only -- no grades.

Reads frozen V2-7 records and append-only production prices READ-ONLY. No network, no API, no bets, no production writes.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import yaml

from prediction_markets_lab.card_engine import cards as C
from prediction_markets_lab.card_engine import shadow as S
from prediction_markets_lab.research import portfolio as PF

VALID = S.SUCCESS_STATUSES
PROTECTED_DIRS = ("tennis_predictions", "paper_betting_v2", "predictions", "reports", "research/platform_v2/card_engine_v2_7")


@dataclass(frozen=True)
class AnalyserConfig:
    version: str
    inputs: dict
    investigate_gt: float
    agree_le: float
    set_sizes: tuple[int, ...]
    pos_ev_set_sizes: tuple[int, ...]
    include_systems: bool
    deltas: tuple[float, ...]
    bankrolls: tuple[float, ...]
    fractions: tuple[float, ...]
    min_lines: tuple[float, ...]
    tick: float


def load_config(path: Path) -> AnalyserConfig:
    c = yaml.safe_load(path.read_text())
    return AnalyserConfig(c["analyser_version"], dict(c["inputs"]), float(c["board"]["investigate_if_abs_p_minus_book_consensus_gt"]),
                          float(c["board"]["agrees_if_abs_p_minus_book_consensus_le"]),
                          tuple(c["structures"]["set_sizes"]), tuple(c["structures"]["pos_ev_set_sizes"]),
                          bool(c["structures"]["include_systems"]), tuple(d / 100 for d in c["sensitivity_deltas_pp"]),
                          tuple(float(b) for b in c["bankroll"]["bankrolls_gbp"]), tuple(c["bankroll"]["daily_capital_fractions"]),
                          tuple(c["bankroll"]["min_line_stake_gbp"]), float(c["bankroll"]["stake_tick_gbp"]))


def read_csv(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_shards(root: Path, name: str) -> list[dict]:
    rows: list[dict] = []
    for d in sorted(q for q in root.glob("*/") if q.is_dir()):
        rows += read_csv(d / name)
    return rows


def file_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else ""


# ---------------------------------------------------------------- calibration support (V2-7 A1 holdout singles, read-only)
def calibration_support(results_path: Path) -> tuple[Callable[[float], float], Callable[[float], dict]]:
    r = json.loads(results_path.read_text())["A1_joint_calibration"]
    band = {}
    for lab in ("50-65%", "65-80%", "80%+"):
        rows = [r[sp]["holdout_years"]["singles"][lab] for sp in ("tennis_atp", "tennis_wta") if lab in r[sp]["holdout_years"]["singles"]]
        band[lab] = {"se": max((b["wilson95"][1] - b["wilson95"][0]) / 3.92 for b in rows),
                     "holdout_n": sum(b["n"] for b in rows),
                     "holdout_pred_vs_actual": [[round(b["pred"], 4), round(b["actual"], 4)] for b in rows]}

    def lab(p: float) -> str:
        return "80%+" if p >= 0.80 else "65-80%" if p >= 0.65 else "50-65%"
    return (lambda p: band[lab(p)]["se"]), (lambda p: {"band": lab(p), **band[lab(p)]})


# ---------------------------------------------------------------- scan selection
def valid_records(root: Path, allow_dry_run: bool) -> list[dict]:
    modes = ("PROSPECTIVE", "DRY_RUN_REPLAY") if allow_dry_run else ("PROSPECTIVE",)
    return [r for r in read_shards(root, "scan_runs.csv") if r["status"] in VALID and r["mode"] in modes]


# ---------------------------------------------------------------- Stage A: prediction board
def book_consensus(price_rows: list[dict], scan: str, event_id: str, selection: str, keys: tuple[str, ...]) -> tuple[float | None, int]:
    """Median over bookmakers (same scan) of the multiplicative de-vigged probability of `selection`. Benchmark only."""
    ps = []
    for r in price_rows:
        if r["scan_timestamp_utc"] != scan or r["event_id"] != event_id or S.is_exchange(r["bookmaker"], keys):
            continue
        try:
            oa, ob = float(r["odds_a"]), float(r["odds_b"])
        except ValueError:
            continue
        if oa <= 1 or ob <= 1:
            continue
        pa = (1 / oa) / (1 / oa + 1 / ob)
        ps.append(pa if r["player_a"] == selection else 1 - pa)
    return (statistics.median(ps), len(ps)) if ps else (None, 0)


def prediction_board(hp_legs: list[dict], price_rows: list[dict], scan: str, cfg: AnalyserConfig, keys: tuple[str, ...],
                     cal_se: Callable, support: Callable) -> list[dict]:
    board = []
    for l in hp_legs:
        p, w = float(l["p"]), float(l["exchange_width"])
        sig = C.leg_sigma(p, w, cal_se(p))
        cons, nb = book_consensus(price_rows, scan, l["event_id"], l["selection"], keys)
        dp = None if cons is None else p - cons
        flag = ("NO_BENCHMARK" if dp is None else "INVESTIGATE_DISAGREEMENT" if abs(dp) > cfg.investigate_gt
                else "AGREES_WITH_MARKET" if abs(dp) <= cfg.agree_le else "MILD_DISAGREEMENT")
        board.append({"sport": l["sport_key"], "event_id": l["event_id"], "event": f"{l['selection']} v {l['opponent']}",
                      "market": "match winner (h2h)", "selection": l["selection"], "start": l["start"], "p": round(p, 4),
                      "sigma": round(sig, 4), "p_range_1sigma": [round(max(p - sig, 0), 4), round(min(p + sig, 1), 4)],
                      "calibration_support": support(p), "exchange_width": round(w, 4),
                      "model": S.engine_of(l["sport_key"]), "scan": scan,
                      "market_benchmark_book_consensus_p": None if cons is None else round(cons, 4), "benchmark_books": nb,
                      "p_minus_benchmark": None if dp is None else round(dp, 4), "benchmark_flag": flag})
    board.sort(key=lambda r: (-r["p"], r["event_id"]))                 # PROBABILITY-FIRST ordering, never EV
    for i, r in enumerate(board, 1):
        r["rank"] = i
    return board


# ---------------------------------------------------------------- Stage B: single-bet evaluation
def price_label(ev: float | None, ev_low: float | None) -> str:
    if ev is None:
        return "NO_CLEAN_PRICE"
    if ev_low is not None and ev_low > 0:
        return "POSITIVE_VALUE_ROBUST_TO_1SIGMA"
    if ev > 0:
        return "POSITIVE_CENTRAL_BUT_UNCERTAIN"
    return "STRONG_PREDICTION_POOR_PRICE"


def single_evaluation(board: list[dict], quotes: list[C.Leg], scan_t: datetime) -> list[dict]:
    by_ev: dict[str, list[C.Leg]] = {}
    for q in quotes:
        if q.clean:
            by_ev.setdefault(q.event_id, []).append(q)
    out = []
    for b in board:
        qs = by_ev.get(b["event_id"], [])
        row = {"rank": b["rank"], "event": b["event"], "selection": b["selection"], "p": b["p"], "sigma": b["sigma"],
               "fair_odds": round(1 / b["p"], 4), "clean_books": len(qs), "grade": "UNGRADED (thresholds not set)"}
        if qs:
            best = max(qs, key=lambda q: (q.odds, q.book))
            ev = b["p"] * best.odds - 1
            lo, hi = (b["p"] - b["sigma"]) * best.odds - 1, (b["p"] + b["sigma"]) * best.odds - 1
            row.update({"best_book": best.book, "offered_odds": best.odds, "median_book_odds": statistics.median(q.odds for q in qs),
                        "payout_per_1gbp": round(best.odds, 4), "profit_if_win_per_1gbp": round(best.odds - 1, 4),
                        "downside_per_1gbp": -1.0, "ev": round(ev, 5), "ev_range_1sigma": [round(lo, 5), round(hi, 5)],
                        "quote_age_min": round((scan_t - S.ts(best.quote_last_update)).total_seconds() / 60, 1),
                        "label": price_label(ev, lo)})
        else:
            row.update({"label": price_label(None, None)})
        out.append(row)
    return out


# ---------------------------------------------------------------- Stage B: structures (equal capital)
def _distinct_top(legs: list, n: int, order: Callable) -> list:
    chosen, evs, parts = [], set(), set()
    for l in sorted(legs, key=order):
        ps = {l.selection.lower(), l.opponent.lower()}
        if l.event_id in evs or ps & parts:
            continue
        chosen.append(l)
        evs.add(l.event_id)
        parts |= ps
        if len(chosen) == n:
            break
    return chosen


def pick_high_p_set(board: list[dict], quotes_by_book: dict[str, list[C.Leg]], n: int) -> tuple[str, list[C.Leg]] | None:
    """PROBABILITY FIRST: the n strongest predictions on the board (distinct events/participants) are fixed first; then, among
    books pricing ALL n in this scan, the best price product is used (same bet, best available price). None if no book prices all."""
    class _B:  # adapter so _distinct_top can order board rows
        def __init__(self, r):
            self.event_id, self.selection, self.opponent, self.p = r["event_id"], r["selection"], r["event"].split(" v ", 1)[1], r["p"]
    top = [x.event_id for x in _distinct_top([_B(r) for r in board], n, lambda b: (-b.p, b.event_id))]
    if len(top) < n:
        return None
    best = None
    for book in sorted(quotes_by_book):
        m = {q.event_id: q for q in quotes_by_book[book]}
        if all(e in m for e in top):
            legs = [m[e] for e in top]
            prod = math.prod(l.odds for l in legs)
            if best is None or prod > best[0]:
                best = (prod, book, legs)
    return None if best is None else (best[1], best[2])


def pick_pos_ev_set(quotes_by_book: dict[str, list[C.Leg]], n: int) -> tuple[str, list[C.Leg]] | None:
    """POS_EV population: per book, the n highest-P legs with EV > 0; the book whose set has the highest JOINT PROBABILITY is
    used (probability first; ties by price product)."""
    best = None
    for book in sorted(quotes_by_book):
        legs = _distinct_top([l for l in quotes_by_book[book] if l.ev > 0], n, lambda l: (-l.p, l.event_id))
        if len(legs) < n:
            continue
        key = (math.prod(l.p for l in legs), math.prod(l.odds for l in legs))
        if best is None or key > best[0]:
            best = (key, book, legs)
    return None if best is None else (best[1], best[2])


def structure_block(legs: list[C.Leg], cfg: AnalyserConfig, cal_se: Callable, population: str, book: str) -> dict:
    legs = sorted(legs, key=lambda l: (-l.p, l.event_id))
    p = np.array([l.p for l in legs])
    o = np.array([l.odds for l in legs])
    sig = np.array([C.leg_sigma(l.p, l.exchange_width, cal_se(l.p)) for l in legs])
    n = len(legs)
    structs = PF.structures(n)
    if not cfg.include_systems:
        structs = {k: v for k, v in structs.items() if not k.startswith(("RR_", "FULL_COVER"))}
    seen, dedup = set(), {}
    for k, v in structs.items():                       # identical line sets (e.g. N = 2) are reported once, under the first name
        key = tuple(sorted(v))
        if key not in seen:
            seen.add(key)
            dedup[k] = v
    structs = dedup
    all_legs_pos = all(l.ev > 0 for l in legs)
    res = {"population": population, "book": book, "n": n, "prices": "INDICATIVE (product of one book's leg prices, same scan)",
           "legs": [{"rank": i + 1, "event": l.event_name, "selection": l.selection, "p": round(l.p, 4), "sigma": round(float(sig[i]), 4),
                     "odds": l.odds, "leg_ev": round(l.ev, 5), "quote_last_update": l.quote_last_update} for i, l in enumerate(legs)],
           "legs_correct_pmf": [round(float(x), 5) for x in PF.poisson_binomial(p)],
           "leg_level_rule_all_legs_ev_gt_0": all_legs_pos, "structures": {}}
    for name, lines in structs.items():
        d = PF.distribution(p, o, lines, f=0.02)
        lo = PF.distribution(np.clip(p - sig, 1e-4, 1), o, lines)["expected_return"]
        sens = {f"{dl*100:+.1f}pp": round(PF.distribution(np.clip(p - dl, 1e-4, 1 - 1e-4), o, lines)["expected_return"], 5)
                for dl in cfg.deltas}
        acc = len(lines) == 1
        pj = float(np.prod(p[list(lines[0])])) if acc else None
        oj = float(np.prod(o[list(lines[0])])) if acc else None
        feas = {}
        for b in cfg.bankrolls:
            for f in cfg.fractions:
                line = math.floor((f * b / len(lines)) / cfg.tick + 1e-9) * cfg.tick
                for mn in cfg.min_lines:
                    feas[f"GBP{int(b)}|{int(f*100)}%|min{mn:.2f}"] = {"line_stake": round(line, 2), "lines": len(lines),
                                                                       "feasible": line >= mn - 1e-9}
        res["structures"][name] = {
            "lines": len(lines), **PF.exposure(lines, n),
            "p_complete_win": round(pj, 5) if acc else None, "fair_odds": round(1 / pj, 4) if acc else None,
            "indicative_odds": round(oj, 4) if acc else None,
            "expected_return": round(d["expected_return"], 5), "expected_return_at_p_minus_sigma": round(lo, 5),
            "sd": round(d["sd"], 4), "p_any_loss_day": round(d["p_negative"], 5), "p_total_daily_loss": round(d["p_full_loss"], 5),
            "p_positive_day": round(d["p_positive"], 5), "max_loss": d["max_loss"],
            "exp_log_growth": {f"{int(f*100)}%": round(PF.distribution(p, o, lines, f=f)["exp_log_growth"], 7) for f in (0.01, 0.02, 0.05)},
            "sensitivity_expected_return": sens,
            "structure_level_screen_ev_low_gt_0": lo > 0,                     # research: structure-level qualification view
            "stake_feasibility": feas}
    res["structures"]["NO_BET"] = {"lines": 0, "expected_return": 0.0, "p_total_daily_loss": 0.0}
    passing = [k for k, v in res["structures"].items() if v.get("structure_level_screen_ev_low_gt_0")]
    res["research_screen"] = {"structures_passing_ev_low_gt_0": passing,
                              "default_if_none": "NO BET" if not passing else None,
                              "note": "Screen = expected return > 0 even with every leg at P - 1 sigma. Research label only; no grade, "
                                      "no paper bet. Leg-level rule (all legs EV > 0) shown separately."}
    return res


def betting_structures(board: list[dict], quotes: list[C.Leg], pos_ev_legs: list[C.Leg], cfg: AnalyserConfig,
                       cal_se: Callable) -> dict:
    hp_ids = {b["event_id"] for b in board}
    hp: dict[str, list[C.Leg]] = {}
    for q in quotes:
        if q.clean and q.event_id in hp_ids:
            hp.setdefault(q.book, []).append(q)
    pe: dict[str, list[C.Leg]] = {}
    for q in pos_ev_legs:
        pe.setdefault(q.book, []).append(q)
    out: dict[str, Any] = {"HIGH_P": {}, "POS_EV": {}}
    for n in cfg.set_sizes:
        s = pick_high_p_set(board, hp, n)
        out["HIGH_P"][f"N{n}"] = structure_block(s[1], cfg, cal_se, "HIGH_P", s[0]) if s else {"status": "NO_SINGLE_BOOK_PRICES_ALL_N"}
    for n in cfg.pos_ev_set_sizes:
        s = pick_pos_ev_set(pe, n)
        out["POS_EV"][f"N{n}"] = structure_block(s[1], cfg, cal_se, "POS_EV", s[0]) if s else {"status": "FEWER_THAN_N_POS_EV_LEGS_AT_ONE_BOOK"}
    return out


# ---------------------------------------------------------------- outcomes (OFF by default; needs approval)
def attach_outcomes(board: list[dict], ledger_preds: list[dict], ledger_settle: list[dict]) -> dict:
    from prediction_markets_lab.card_engine.shadow_settle import event_outcomes, leg_outcome
    oc = event_outcomes(ledger_preds, ledger_settle)
    res = {}
    for b in board:
        st, flags = leg_outcome([b["event_id"], b["selection"], b["event"].split(" v ", 1)[1], b["start"], b["p"]], oc.get(b["event_id"]))
        res[b["event_id"]] = {"outcome": st, "flags": flags}
    return res


# ---------------------------------------------------------------- one scan
def analyse_scan(rec: dict, v27_root: Path, repo: Path, cfg: AnalyserConfig, shadow_cfg: S.ShadowConfig, with_outcomes: bool) -> dict:
    month = rec["scan"][:7]
    leg_rows = [r for r in read_csv(v27_root / month / "legs.csv") if r["record_id"] == rec["record_id"]]
    hp_legs = [r for r in leg_rows if r["book"] == "*"]
    price_rows = read_csv(repo / cfg.inputs["prices"])
    cal_se, support = calibration_support(repo / cfg.inputs["calibration_results"])
    scan = rec["scan"]
    board = prediction_board(hp_legs, price_rows, scan, cfg, shadow_cfg.exchange_keys, cal_se, support)
    # per-book quotes for the frozen HIGH_P predictions, same scan, with the V2-7 (= bsv2-3) quality rules
    prob_rows = [{"scan_timestamp_utc": scan, "sport_key": l["sport_key"], "event_id": l["event_id"], "player_a": l["selection"],
                  "player_b": l["opponent"], "commence_time": l["start"], "source_validated": "True", "p_a": l["p"],
                  "exchange_spread_prob": l["exchange_width"]} for l in hp_legs]
    quotes, _ = S.load_scan_legs(prob_rows, price_rows, scan, S.ts(rec["logged_at"]), shadow_cfg)
    pos_ev = [C.Leg(scan, r["book"], r["sport_key"], r["event_id"], f"{r['selection']} v {r['opponent']}", r["start"], r["selection"],
                    r["opponent"], float(r["p"]), float(r["odds"]), r["quote_last_update"], float(r["exchange_width"]), S.engine_of(r["sport_key"]),
                    tuple(q for q in r["quality"].split("|") if q)) for r in leg_rows if r["book"] != "*"]
    out = {"analyser_version": cfg.version, "record_id": rec["record_id"], "scan": scan, "mode": rec["mode"],
           "v2_7_rule_version": rec["rule_version"], "v2_7_commit_sha": rec["commit_sha"], "run_id": rec["run_id"],
           "input_shas": {"prices": file_sha(repo / cfg.inputs["prices"]), "v2_7_legs": file_sha(v27_root / month / "legs.csv")},
           "stage_A_prediction_board": board,
           "stage_B_single_evaluation": single_evaluation(board, quotes, S.ts(scan)),
           "stage_B_structures": betting_structures(board, quotes, pos_ev, cfg, cal_se),
           "labels": {"prices": "multi prices INDICATIVE / NOT EXECUTION-VERIFIED", "grades": "not set (no thresholds)",
                      "status": "RESEARCH ONLY -- no bet placed, no paper bet created"}}
    if with_outcomes:
        out["outcomes_research_only"] = attach_outcomes(board, read_csv(repo / cfg.inputs["ledger_predictions"]),
                                                        read_csv(repo / cfg.inputs["ledger_settlements"]))
    return out


def guard_output(out_dir: Path, repo: Path) -> Path:
    o = out_dir.resolve()
    for d in PROTECTED_DIRS:
        pd_ = (repo / d).resolve()
        if o == pd_ or pd_ in o.parents:
            raise PermissionError(f"analyser refuses to write inside {d}")
    return o


def render_markdown(a: dict) -> str:
    L = [f"# Daily Bet Card -- RESEARCH PREVIEW (analyser {a['analyser_version']})", "",
         f"Scan {a['scan']} · mode {a['mode']} · V2-7 {a['v2_7_rule_version']} · NO BET PLACED · grades not set · multi prices INDICATIVE", "",
         "## Stage A -- Prediction board (ranked by probability)", "",
         "| # | event | selection | P ± σ | band (holdout n) | book consensus | ΔP | flag | model |", "|---|---|---|---|---|---|---|---|---|"]
    for b in a["stage_A_prediction_board"]:
        cs = b["calibration_support"]
        L.append(f"| {b['rank']} | {b['event']} | {b['selection']} | {b['p']:.3f} ± {b['sigma']:.3f} | {cs['band']} ({cs['holdout_n']}) | "
                 f"{b['market_benchmark_book_consensus_p']} | {b['p_minus_benchmark']} | {b['benchmark_flag']} | {b['model']} |")
    L += ["", "## Stage B -- Betting evaluation (singles)", "", "| # | selection | P | fair | best odds (book) | EV [±1σ] | label |",
          "|---|---|---|---|---|---|---|"]
    for s in a["stage_B_single_evaluation"]:
        if "offered_odds" in s:
            L.append(f"| {s['rank']} | {s['selection']} | {s['p']:.3f} | {s['fair_odds']:.2f} | {s['offered_odds']} ({s['best_book']}) | "
                     f"{s['ev']*100:+.1f}% [{s['ev_range_1sigma'][0]*100:+.1f}, {s['ev_range_1sigma'][1]*100:+.1f}] | {s['label']} |")
        else:
            L.append(f"| {s['rank']} | {s['selection']} | {s['p']:.3f} | {s['fair_odds']:.2f} | -- | -- | {s['label']} |")
    for pop, blocks in a["stage_B_structures"].items():
        for n, blk in blocks.items():
            L += ["", f"## Stage B -- {pop} {n} allocation options (equal daily capital)", ""]
            if "structures" not in blk:
                L.append(f"_{blk.get('status')}_")
                continue
            L += [f"Book {blk['book']} · all legs EV>0: {blk['leg_level_rule_all_legs_ev_gt_0']} · "
                  f"P(legs correct 0..N): {blk['legs_correct_pmf']}", "",
                  "| structure | lines | E[return] | E at P−σ | P(total loss) | P(positive day) | £20 @5% line (min £0.10) |", "|---|---|---|---|---|---|---|"]
            for name, v in blk["structures"].items():
                if name == "NO_BET":
                    L.append("| NO_BET | 0 | 0 | 0 | 0 | -- | -- |")
                    continue
                fz = v["stake_feasibility"]["GBP20|5%|min0.10"]
                L.append(f"| {name} | {v['lines']} | {v['expected_return']*100:+.2f}% | {v['expected_return_at_p_minus_sigma']*100:+.2f}% | "
                         f"{v['p_total_daily_loss']:.3f} | {v['p_positive_day']:.3f} | £{fz['line_stake']:.2f}{'' if fz['feasible'] else ' (NOT PLACEABLE)'} |")
            L.append(f"\nResearch screen (E at P−σ > 0): {blk['research_screen']['structures_passing_ev_low_gt_0'] or 'none -> NO BET'}")
    return "\n".join(L) + "\n"
