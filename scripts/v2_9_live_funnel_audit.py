"""V2-9 READ-ONLY audit of the first two live V2-7 scans (30 Sep 2026): why many predictions/cards but zero candidates?

Reads committed production + research files at the two production commits (git show), never writes production, never uses
outcomes. Output: research/platform_v2/audit_v2_9_live_funnel/AUDIT_RESULTS.json
"""
from __future__ import annotations

import csv
import io
import json
import math
import statistics
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from prediction_markets_lab.card_engine import cards as C
from prediction_markets_lab.card_engine import shadow as S

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research/platform_v2/audit_v2_9_live_funnel"
SCANS = {"morning": {"run_id": "36717723414", "prod_commit": "e9cc1a4", "shadow_commit": "5c4db9d",
                     "scan": "2026-09-30T12:54:22.695202+00:00", "intended": "2026-09-30T06:30:00+00:00"},
         "afternoon": {"run_id": "36771315893", "prod_commit": "7e3ce99", "shadow_commit": "18f0747",
                       "scan": "2026-09-30T20:16:17.495727+00:00", "intended": "2026-09-30T15:30:00+00:00"}}
PREV_SCAN = "2026-09-29T20:11:50.324947+00:00"
EXCH = ("betfair_ex_uk", "betfair_ex_eu", "betfair", "smarkets", "matchbook")


def git_csv(commit: str, path: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(subprocess.check_output(["git", "show", f"{commit}:{path}"], text=True))))


def git_json(commit: str, path: str) -> dict:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], text=True))


def ts(s: str) -> datetime:
    return S.ts(s)


def raw_back_lay(raw: str):
    import re
    m = re.search(r"ex_back=([\d.]+)/([\d.]+);ex_lay=([\d.]+)/([\d.]+)", raw or "")
    return tuple(map(float, m.groups())) if m else None


def mult(o1: float, o2: float) -> float:
    return (1 / o1) / (1 / o1 + 1 / o2)


def audit_scan(name: str, meta: dict, shadow_cfg: S.ShadowConfig, cal_se) -> dict:
    pc, sc, scan = meta["prod_commit"], meta["shadow_commit"], meta["scan"]
    scan_t = ts(scan)
    board = git_json(pc, f"tennis_predictions/2026-09-30/board_{scan_t.strftime('%H%M')}.json")
    X = [r for r in git_csv(pc, "tennis_predictions/exchange_probability_snapshots.csv") if r["scan_timestamp_utc"] == scan]
    Q = [r for r in git_csv(pc, "tennis_predictions/price_snapshots.csv") if r["scan_timestamp_utc"] == scan]
    rec = [r for r in git_csv(sc, "research/platform_v2/card_engine_v2_7/prospective/2026-09/scan_runs.csv") if r["scan"] == scan][0]
    cards = [c for c in git_csv(sc, "research/platform_v2/card_engine_v2_7/prospective/2026-09/cards.csv") if c["record_id"] == rec["record_id"]]
    logged = ts(rec["logged_at"])
    res: dict = {"scan": scan, "run_id": meta["run_id"], "intended_cron": meta["intended"],
                 "delay_hours": round((scan_t - ts(meta["intended"])).total_seconds() / 3600, 2)}

    # ---------------- bug checks on raw data: orientation, back<=lay, midpoint and spread recomputation
    bugs = Counter()
    ev_rows = {}
    for r in X:
        bl = raw_back_lay(r["raw_prices"])
        if bl is None:
            bugs["unparseable_raw_prices"] += 1
            continue
        ba, bb, la, lb = bl
        if la < ba or lb < bb:
            bugs["lay_below_back_inversion"] += 1
        pa = mult((ba + la) / 2, (bb + lb) / 2)
        if abs(pa - float(r["p_a"])) > 1e-5:
            bugs["midpoint_recompute_mismatch"] += 1
        w = max(1 / ba - 1 / la, 1 / bb - 1 / lb)
        if abs(w - float(r["exchange_spread_prob"])) > 1e-5:
            bugs["spread_recompute_mismatch"] += 1
        if abs(float(r["p_a"]) + float(r["p_b"]) - 1) > 1e-5:
            bugs["p_not_summing_to_1"] += 1
        ev_rows[r["event_id"]] = {"back": (ba, bb), "lay": (la, lb), "width": w, "pa_midpoint_odds_avg": pa,
                                  "pa_prob_avg": ((1 / ba + 1 / la) / 2) / ((1 / ba + 1 / la) / 2 + (1 / bb + 1 / lb) / 2)}
    res["bug_checks_raw"] = dict(bugs) or {"none_found": True}
    diffs = [abs(v["pa_midpoint_odds_avg"] - v["pa_prob_avg"]) for v in ev_rows.values()]
    res["midpoint_definition_effect"] = {"note": "frozen engine averages DECIMAL ODDS (not probabilities) then de-vigs",
                                         "max_abs_diff_vs_probability_average_pp": round(100 * max(diffs), 3),
                                         "median_abs_diff_pp": round(100 * statistics.median(diffs), 3)}

    # ---------------- legs with V2-7 quality rules (identical to bsv2-3)
    legs, counts = S.load_scan_legs(X, Q, scan, logged, shadow_cfg)
    by_event: dict[str, list] = {}
    for l in legs:
        by_event.setdefault(l.event_id, []).append(l)
    fav = {}
    for r in X:
        pa = float(r["p_a"])
        fav[r["event_id"]] = {"selection": r["player_a"] if pa >= 0.5 else r["player_b"], "p": max(pa, 1 - pa),
                              "width": float(r["exchange_spread_prob"]) if r["exchange_spread_prob"] else None,
                              "event": f"{r['player_a']} v {r['player_b']}", "start": r["commence_time"], "validated": r["source_validated"]}

    # ---------------- WATERFALL (unique matches; quotes alongside)
    cov = board["coverage"]
    wf = []

    def step(label, events, quotes=None, rule=""):
        wf.append({"stage": label, "unique_matches": len(events), "bookmaker_quotes": quotes, "rule": rule})
    step("API events returned (3 active tennis keys)", range(cov["events_returned"]), rule="Odds API covered keys; max-keys 6 not binding")
    step("predictions (not started, has a source)", X, rule="engine.predict: event not started; exchange quote <= 6h old")
    validated = [e for e, f in fav.items() if f["validated"] == "True"]
    step("validated source (EXCHANGE_MID/BACK)", validated, rule="engine VALID_SOURCES")
    priced = [e for e in validated if by_event.get(e)]
    step("priced by >=1 UK bookmaker (non-exchange, same scan)", priced, sum(len(by_event.get(e, [])) for e in validated))
    width_ok = [e for e in priced if fav[e]["width"] is not None and fav[e]["width"] <= shadow_cfg.max_exchange_spread_prob]
    step("exchange width <= 0.03 (bsv2-3 data-quality gate)", width_ok, sum(len(by_event[e]) for e in width_ok),
         "EXCHANGE_BOOK_TOO_WIDE: midpoint P judged unreliable")
    clean_ev = [e for e in width_ok if any(l.clean for l in by_event[e])]
    step("fresh quote & not started (<=240 min; start after logging)", clean_ev, sum(sum(l.clean for l in by_event[e]) for e in clean_ev))
    pos = [e for e in clean_ev if any(l.clean and l.ev > 0 for l in by_event[e])]
    step("positive central EV at >=1 book (payout/value)", pos, sum(sum(l.clean and l.ev > 0 for l in by_event[e]) for e in pos))

    def best(e):
        return max((l for l in by_event[e] if l.clean), key=lambda l: l.ev)

    def ev_low(l):
        return (l.p - C.leg_sigma(l.p, l.exchange_width, cal_se(l.p))) * l.odds - 1

    robust = [e for e in pos if ev_low(best(e)) > 0]
    step("EV still > 0 at P - 1 sigma (uncertainty; V2-7 SHADOW_CANDIDATE rule)", robust)
    prod2 = [e for e in pos if best(e).ev >= 0.02]
    wf.append({"stage": "(parallel) production bsv2-3 paper gate: net EV >= 2% at a bookmaker", "unique_matches": len(prod2)})
    step("final candidates", [])
    res["waterfall_v2_7_single_legs"] = wf
    hp = [e for e in validated if fav[e]["p"] >= 0.70]
    res["high_p_funnel"] = {"board_ge_70": board["counts"]["ge_70"], "validated_ge_70": len(hp),
                            "ge_70_width_too_wide": sum(1 for e in hp if fav[e]["width"] is None or fav[e]["width"] > 0.03),
                            "ge_70_no_clean_quote_otherwise": sum(1 for e in hp if (fav[e]["width"] or 1) <= 0.03 and not any(l.clean for l in by_event.get(e, []))),
                            "v2_7_high_p_cohort_events": sum(1 for e in hp if any(l.clean for l in by_event.get(e, [])))}

    # ---------------- spread audit (unique matches)
    sp = []
    for e in validated:
        f = fav[e]
        if f["width"] is None or f["width"] <= 0.03:
            continue
        v = ev_rows[e]
        side = 0 if f["selection"] == X[[r["event_id"] for r in X].index(e)]["player_a"] else 1
        back, lay = v["back"][side], v["lay"][side]
        bks = [l for l in by_event.get(e, [])]
        bo = max((l.odds for l in bks), default=None)
        lo = None if bo is None else round(bo / lay - 1, 4)     # EV if true P were at the lay-implied (lower) end
        hi = None if bo is None else round(bo / back - 1, 4)    # EV if true P were at the back-implied (upper) end
        cls = ("NO_BOOK_PRICE" if bo is None else "POOR_EVEN_AT_TOP_OF_EXCHANGE_RANGE" if hi <= 0 else
               "POSITIVE_ACROSS_WHOLE_EXCHANGE_RANGE" if lo > 0 else "INDETERMINATE_WITHIN_EXCHANGE_RANGE")
        sp.append({"event": f["event"], "selection": f["selection"], "p_midpoint": round(f["p"], 4), "width": round(f["width"], 4),
                   "back": back, "lay": lay, "books_rejected": len(bks), "best_book_odds": bo,
                   "ev_range_across_exchange_book": [lo, hi], "classification": cls})
    res["spread_gate_unique_matches"] = sp
    res["spread_gate_summary"] = {"unique_matches_removed": len(sp), "quotes_removed": sum(s["books_rejected"] for s in sp),
                                  "classification": dict(Counter(s["classification"] for s in sp)),
                                  "p_ge_070_removed": sum(s["p_midpoint"] >= 0.70 for s in sp)}
    # sensitivity of the width threshold (descriptive; no outcomes)
    sens = {}
    for thr in (0.01, 0.02, 0.03, 0.04, 0.05, None):
        evs = [e for e in priced if thr is None or (fav[e]["width"] is not None and fav[e]["width"] <= thr)]
        ok = [e for e in evs if any(l.ev > 0 and set(l.quality) <= {"EXCHANGE_BOOK_TOO_WIDE"} for l in by_event[e])]
        sens["none" if thr is None else f"{thr:.2f}"] = {"matches_passing_width": len(evs),
                                                          "matches_with_pos_central_ev": len(ok)}
    res["spread_threshold_sensitivity"] = sens
    bins = Counter()
    for e in validated:
        w = fav[e]["width"]
        b = "unknown" if w is None else f"{min(int(w * 100), 10)}-{min(int(w * 100), 10) + 1}pp" if w < 0.10 else ">=10pp"
        bins[b] += 1
    res["width_distribution_unique_matches"] = dict(sorted(bins.items()))

    # ---------------- uncertainty audit: every positive-central-EV leg (clean) and card
    unc = []
    for e in pos:
        for l in sorted((l for l in by_event[e] if l.clean and l.ev > 0), key=lambda l: -l.ev):
            s_cal, s_w = cal_se(l.p), l.exchange_width / 2
            sig = C.leg_sigma(l.p, l.exchange_width, s_cal)
            unc.append({"event": l.event_name, "selection": l.selection, "book": l.book, "p": round(l.p, 4),
                        "sigma": round(sig, 4), "sigma_calibration": round(s_cal, 4), "sigma_half_width": round(s_w, 4),
                        "p_low": round(l.p - sig, 4), "odds": l.odds, "ev": round(l.ev, 4), "ev_low": round(ev_low(l), 4),
                        "break_even_p": round(1 / l.odds, 4), "p_margin_over_break_even_pp": round(100 * (l.p - 1 / l.odds), 2),
                        "why_not_candidate": "EV_LOW_LE_0" if ev_low(l) <= 0 else "PASSES"})
    res["uncertainty_positive_ev_legs"] = unc
    res["uncertainty_positive_ev_cards"] = [{"book": c["book"], "k": c["k"], "legset": c["legset"], "p_joint": c["p_joint"],
                                             "sigma_joint": c["sigma_joint"], "odds": c["odds_indicative"], "ev": c["ev"],
                                             "ev_low": c["ev_low"], "status": c["status"]} for c in cards if c["cohort"] == "POS_EV"]
    # one-gate-at-a-time counterfactuals on legs (counts of unique matches / quotes; NO outcomes)
    allq = [l for l in legs if set(l.quality) <= {"EXCHANGE_BOOK_TOO_WIDE"}]

    def count(pred_fn, pool):
        ls = [l for l in pool if pred_fn(l)]
        return {"unique_matches": len({l.event_id for l in ls}), "quotes": len(ls)}
    clean = [l for l in legs if l.clean]
    res["counterfactuals_one_gate_at_a_time"] = {
        "CURRENT (clean, EV_low>0 at 1 sigma)": count(lambda l: ev_low(l) > 0, clean),
        "central EV > 0 only (drop uncertainty rule)": count(lambda l: l.ev > 0, clean),
        "EV > 0 at P - 0.5 sigma": count(lambda l: (l.p - 0.5 * C.leg_sigma(l.p, l.exchange_width, cal_se(l.p))) * l.odds > 1, clean),
        "EV > 0 at P - 1.645 sigma (one-sided 95%)": count(lambda l: (l.p - 1.645 * C.leg_sigma(l.p, l.exchange_width, cal_se(l.p))) * l.odds > 1, clean),
        "sigma = calibration SE only (no half-width term), 1 sigma": count(lambda l: (l.p - cal_se(l.p)) * l.odds > 1, clean),
        "production bsv2-3 floor: EV >= 2%": count(lambda l: l.ev >= 0.02, clean),
        "NO spread gate (midpoint P treated as usable), central EV > 0 -- NOT A VALID ESTIMATE": count(lambda l: l.ev > 0, allq),
        "NO spread gate, EV_low > 0 -- NOT A VALID ESTIMATE": count(lambda l: ev_low(l) > 0, allq)}
    # top HIGH_P predictions, no-bet analysis
    top = []
    for e in sorted(validated, key=lambda e: -fav[e]["p"])[:15]:
        f = fav[e]
        bks = by_event.get(e, [])
        cl = [l for l in bks if l.clean]
        b = max(cl, key=lambda l: l.odds) if cl else (max(bks, key=lambda l: l.odds) if bks else None)
        reason = ("DATA_QUALITY: exchange width > 0.03" if f["width"] is None or f["width"] > 0.03 else
                  "NO_CLEAN_BOOK_PRICE" if not cl else
                  "HIGH_P + POOR PAYOUT (EV <= 0 at best book)" if b.p * b.odds - 1 <= 0 else
                  "HIGH_P + POSITIVE CENTRAL EV BUT UNCERTAINTY (EV_low <= 0)" if ev_low(b) <= 0 else "WOULD QUALIFY")
        top.append({"event": f["event"], "selection": f["selection"], "p": round(f["p"], 4),
                    "sigma": round(C.leg_sigma(f["p"], min(f["width"] or 1, 1), cal_se(f["p"])), 4), "width": f["width"],
                    "best_book": b.book if b else None, "best_odds": b.odds if b else None, "fair_odds": round(1 / f["p"], 3),
                    "payout_per_1gbp_profit": round(b.odds - 1, 3) if b else None,
                    "ev_at_best": round(f["p"] * b.odds - 1, 4) if b else None, "reason_not_staked": reason})
    res["high_p_no_bet"] = top
    # market agreement: P vs bookmaker consensus (same scan)
    agree = []
    for e in validated:
        ps = []
        for r in Q:
            if r["event_id"] != e or r["bookmaker"] in EXCH:
                continue
            try:
                pa = mult(float(r["odds_a"]), float(r["odds_b"]))
            except (ValueError, ZeroDivisionError):
                continue
            ps.append(pa if r["player_a"] == fav[e]["selection"] else 1 - pa)
        if ps:
            agree.append(fav[e]["p"] - statistics.median(ps))
    res["model_minus_book_consensus_pp"] = {"n": len(agree), "median": round(100 * statistics.median(agree), 2),
                                            "p10": round(100 * sorted(agree)[len(agree) // 10], 2),
                                            "p90": round(100 * sorted(agree)[9 * len(agree) // 10], 2),
                                            "abs_gt_3pp": sum(abs(a) > 0.03 for a in agree), "abs_gt_10pp": sum(abs(a) > 0.10 for a in agree)}
    # book margins per favourite leg (overround) and book coverage
    books_per_event = [len({l.book for l in by_event.get(e, [])}) for e in validated]
    ovr = []
    for r in Q:
        if r["bookmaker"] in EXCH:
            continue
        try:
            ovr.append(1 / float(r["odds_a"]) + 1 / float(r["odds_b"]) - 1)
        except (ValueError, ZeroDivisionError):
            pass
    ages = [(scan_t - ts(l.quote_last_update)).total_seconds() / 60 for l in legs if l.quote_last_update]
    res["coverage"] = {"active_keys": cov["active_keys"], "keys_over_cap": cov["keys_over_cap"], "skipped_credit": cov["skipped_for_credit_guard"],
                       "events_returned": cov["events_returned"], "credits_remaining_after": cov["credits_remaining_after"],
                       "bookmakers_per_match": {"min": min(books_per_event), "median": statistics.median(books_per_event), "max": max(books_per_event)},
                       "bookmaker_overround_median_pct": round(100 * statistics.median(ovr), 2),
                       "quote_age_min": {"median": round(statistics.median(ages), 1), "max": round(max(ages), 1)},
                       "distinct_bookmakers": sorted({r["bookmaker"] for r in Q})}
    # production bsv2-3 funnel (its own universe)
    pcands = git_csv(pc, "reports/bet_selection_v2_candidates.csv")
    reasons = Counter(x for c in pcands for x in c["reasons"].split("|") if x)
    res["production_bsv2_3"] = {"candidates": len(pcands), "unique_events": len({c["event_key"] for c in pcands}),
                                "decisions": dict(Counter(c["decision"] for c in pcands)), "reason_codes": dict(reasons),
                                "best_price_sources": dict(Counter(c["source"] for c in pcands)),
                                "self_source_exchange_best": sum(c["value_reference"].startswith("SELF_SOURCE") for c in pcands),
                                "duplicate_event_rows": sum(v - 1 for v in Counter(c["event_key"] for c in pcands).values() if v > 1)}
    # rescheduled-start defect: board events absent from the production evaluation universe
    U = git_csv(pc, "predictions/unified_ledger.csv")
    up = {u["event_id"] for u in U if ts(u["event_start"]) > scan_t}
    missing = []
    for r in X:
        if r["event_id"] in up:
            continue
        led = [u for u in U if u["event_id"] == r["event_id"]]
        missing.append({"event": f"{r['player_a']} v {r['player_b']}", "p_fav": round(max(float(r["p_a"]), float(r["p_b"])), 4),
                        "scan_commence_time": r["commence_time"], "ledger_event_start": sorted({u["event_start"] for u in led}),
                        "in_unified_ledger": bool(led)})
    res["defect_rescheduled_matches_dropped_from_production"] = {"count": len(missing), "of_board_matches": len(X), "matches": missing}
    # cards vs unique opportunities
    res["cards_vs_matches"] = {"raw_cards": len(cards), "by_cohort_k": dict(Counter(f"{c['cohort']}|k{c['k']}" for c in cards)),
                               "distinct_leg_sets": len({(c['cohort'], c['legset']) for c in cards}),
                               "high_p_matches": len({x.split(':')[0] for c in cards if c['cohort'] == 'HIGH_P' for x in c['legset'].split(';')}),
                               "pos_ev_matches": len({x.split(':')[0] for c in cards if c['cohort'] == 'POS_EV' for x in c['legset'].split(';')}),
                               "pos_ev_legs_book_quotes": sum(1 for c in cards if c['cohort'] == 'POS_EV' and c['k'] == '1')}
    return res


def scheduling(shadow_cfg) -> dict:
    """Matches that START between the intended cron time and the actual (delayed) scan were only ever priced by the previous
    scan (29 Sep 20:11) -- the delay removed a closer-to-start observation. No outcomes used."""
    X0 = [r for r in git_csv("e9cc1a4", "tennis_predictions/exchange_probability_snapshots.csv") if r["scan_timestamp_utc"] == PREV_SCAN]
    lo, hi = ts(SCANS["morning"]["intended"]), ts(SCANS["morning"]["scan"])
    missed = [r for r in X0 if lo <= ts(r["commence_time"]) < hi]
    lo2, hi2 = ts(SCANS["afternoon"]["intended"]), ts(SCANS["afternoon"]["scan"])
    Xm = [r for r in git_csv("e9cc1a4", "tennis_predictions/exchange_probability_snapshots.csv") if r["scan_timestamp_utc"] == SCANS["morning"]["scan"]]
    missed2 = [r for r in Xm if lo2 <= ts(r["commence_time"]) < hi2]
    return {"morning_delay_window": [lo.isoformat(), hi.isoformat()],
            "matches_starting_in_morning_delay_window": len(missed),
            "afternoon_delay_window": [lo2.isoformat(), hi2.isoformat()],
            "matches_starting_in_afternoon_delay_window": len(missed2),
            "note": "These matches lost their intended pre-match scan; they were last observed hours earlier."}


def main() -> int:
    shadow_cfg = S.load_config(REPO / "config/card_research_shadow.yaml", REPO)
    r = json.loads((REPO / "research/platform_v2/card_engine_v2_7/RESULTS.json").read_text())["A1_joint_calibration"]
    se = {b: max((r[sp]["holdout_years"]["singles"][b]["wilson95"][1] - r[sp]["holdout_years"]["singles"][b]["wilson95"][0]) / 3.92
                 for sp in ("tennis_atp", "tennis_wta")) for b in ("50-65%", "65-80%", "80%+")}
    cal_se = lambda p: se["80%+"] if p >= 0.80 else se["65-80%"] if p >= 0.65 else se["50-65%"]   # noqa: E731
    res = {"label": "READ-ONLY diagnostic audit; no outcomes used; nothing changed", "calibration_se_by_band": se,
           "scans": {k: audit_scan(k, v, shadow_cfg, cal_se) for k, v in SCANS.items()}, "scheduling": scheduling(shadow_cfg)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "AUDIT_RESULTS.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: {"waterfall": v["waterfall_v2_7_single_legs"], "spread": v["spread_gate_summary"],
                          "cf": v["counterfactuals_one_gate_at_a_time"], "hp": v["high_p_funnel"], "bugs": v["bug_checks_raw"],
                          "mid": v["midpoint_definition_effect"], "defect": v["defect_rescheduled_matches_dropped_from_production"]["count"],
                          "agree": v["model_minus_book_consensus_pp"], "cov": v["coverage"], "prod": v["production_bsv2_3"],
                          "sens": v["spread_threshold_sensitivity"], "wbins": v["width_distribution_unique_matches"]}
                      for k, v in res["scans"].items()} | {"sched": res["scheduling"], "se": se}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
