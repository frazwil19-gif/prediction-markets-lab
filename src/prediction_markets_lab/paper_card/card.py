"""V2-20 Daily Paper Bet Card (pcard-1): grades, hypothetical stakes, append-only enrichment, paper dashboard.

Presentation/accounting only. bsv2-4 makes every decision; this module never changes a decision, a price or a
selection row. Pre-registration: research/platform_v2/v2_20_paper/PREREGISTRATION.md. Paper only: money_eligible is
always False here.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from prediction_markets_lab.bet_selection_v2 import paper_ledger as L
from prediction_markets_lab.bet_selection_v2 import report as R
from prediction_markets_lab.bet_selection_v2.bankroll import policy_stake

A_PLUS, A, B, C, REJECT, UNGRADED = "A+", "A", "B", "C", "REJECT", "UNGRADED_PRE_PCARD"
GRADE_ORDER = {A_PLUS: 0, A: 1, B: 2, C: 3, REJECT: 4, UNGRADED: 5}
STAKED_GRADES = (A_PLUS, A, B)
PAPER_BET, WATCH, MULTI = "PAPER_BET", "WATCH", "MULTI_RESEARCH_ELIGIBLE"
SKIP_BELOW_MIN, SKIP_DAILY_CAP, SKIP_ZERO_STAKE = "SKIP_BELOW_MIN", "SKIP_DAILY_CAP", "SKIP_ZERO_STAKE"


@dataclass(frozen=True)
class CardConfig:
    rule_version: str
    z_a: float
    z_a_plus: float
    a_plus_min_state: str
    states: tuple[str, ...]
    default_state: str
    engine_state: dict
    sim: dict                       # bsv2 bankroll_simulation block (single source of truth)
    paths: dict


def load_config(path: Path, repo: Path) -> CardConfig:
    c = yaml.safe_load(path.read_text())
    bs = yaml.safe_load((repo / c["bet_selection_config"]).read_text())
    states = tuple(c["evidence_states_order"])
    for s in [c["default_evidence_state"], c["grades"]["a_plus_min_evidence_state"], *c["engine_evidence_state"].values()]:
        if s not in states:
            raise ValueError(f"unknown evidence state {s!r}")
    for name, pol in bs["bankroll_simulation"]["policies"].items():
        if pol["kind"] not in ("fraction", "kelly", "min_stake"):
            raise ValueError(f"policy {name}: staking kind {pol['kind']!r} refused")
    paths = {k: repo / v for k, v in {**{k: c[k] for k in ("stage_a_board", "candidates", "paper_dir", "enrichment_ledger", "decision_shadow_ledger")},
                                      **c["outputs"]}.items()}
    return CardConfig(c["rule_version"], float(c["grades"]["z_grade_a"]), float(c["grades"]["z_grade_a_plus"]),
                      c["grades"]["a_plus_min_evidence_state"], states, c["default_evidence_state"],
                      dict(c["engine_evidence_state"]), bs["bankroll_simulation"], paths)


def ev(q: float, odds: float, commission: float) -> float:
    return q * (odds - 1.0) * (1.0 - commission) - (1.0 - q)


def _num(x) -> float | None:
    if x in (None, "", "None"):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def evidence_state(cfg: CardConfig, engine_id: str) -> str:
    return cfg.engine_state.get(engine_id, cfg.default_state)


def grade(cfg: CardConfig, decision: str, p: float | None, sigma: float | None, odds: float | None,
          commission: float, state: str) -> tuple[str, str, dict]:
    """Return (grade, reason, ev fields). Pure function of the pre-registered rule."""
    evs = {"ev_at_p": None, "ev_minus_1sigma": None, "ev_minus_1645sigma": None}
    if p is not None and odds is not None:
        evs["ev_at_p"] = round(ev(p, odds, commission), 6)
        if sigma is not None:
            evs["ev_minus_1sigma"] = round(ev(max(0.0, p - cfg.z_a * sigma), odds, commission), 6)
            evs["ev_minus_1645sigma"] = round(ev(max(0.0, p - cfg.z_a_plus * sigma), odds, commission), 6)
    if decision in (WATCH, MULTI):
        return C, f"bsv2 {decision}: information only", evs
    if decision != PAPER_BET:
        return REJECT, f"bsv2 {decision or 'NO_DECISION'}", evs
    if sigma is None or evs["ev_minus_1sigma"] is None:
        return B, "PAPER_BET; sigma unknown", evs
    supported = cfg.states.index(state) >= cfg.states.index(cfg.a_plus_min_state)
    if evs["ev_minus_1645sigma"] > 0 and supported:
        return A_PLUS, f"EV>0 at P-{cfg.z_a_plus}σ; evidence {state}", evs
    if evs["ev_minus_1sigma"] > 0:
        why = "" if supported else f" (A+ needs evidence ≥ {cfg.a_plus_min_state}; engine is {state})"
        return A, f"EV>0 at P-{cfg.z_a}σ{why}", evs
    return B, f"PAPER_BET but EV≤0 at P-{cfg.z_a}σ", evs


def rank_key(r: dict):
    return (GRADE_ORDER[r["grade"]], -(r["probability"] or 0.0), -(r["ev_at_p"] or -9.0), r["event_start"], r["prediction_id"])


def stake_columns(sim: dict) -> list[str]:
    return [f"stake_{int(b)}_{name}" for b in sim["bankrolls_gbp"] for name in sim["policies"]]


def hypothetical_stakes(rows: list[dict], sim: dict) -> None:
    """In-place: add stake_<bankroll>_<policy> (GBP float or a SKIP_* label) to ranked rows. Singles only."""
    for b in sim["bankrolls_gbp"]:
        bank = float(b)
        cap, day_cap = bank * sim["max_stake_fraction"], bank * sim["max_daily_exposure_fraction"]
        for name, pol in sim["policies"].items():
            col, used = f"stake_{int(b)}_{name}", defaultdict(float)
            for r in rows:
                if r["grade"] not in STAKED_GRADES:
                    r[col] = ""
                    continue
                min_stake = sim["practical_min_stake_gbp"]["exchange" if r["is_exchange"] else "bookmaker"]
                s = min(policy_stake(pol, bank, r["probability"], r["decimal_odds"], r["commission"], min_stake), cap)
                if s <= 0:
                    r[col] = SKIP_ZERO_STAKE
                    continue
                if s < min_stake:
                    if min_stake > cap:
                        r[col] = SKIP_BELOW_MIN
                        continue
                    s = min_stake
                day = r["event_start"][:10]
                if used[day] + s > day_cap + 1e-9:
                    r[col] = SKIP_DAILY_CAP
                    continue
                used[day] += s
                r[col] = round(s, 2)


def _competition(event_key: str) -> str:
    parts = str(event_key).split("|")
    return parts[1] if len(parts) > 2 else ""


def build_card(cfg: CardConfig, candidates: list[dict], stage_a: dict, selections: list[dict], now: datetime) -> dict:
    sa = {r["prediction_id"]: r for r in stage_a.get("predictions", [])}
    sel_by_pid = {s["prediction_id"]: s for s in selections}
    rows = []
    for c in candidates:
        s = sa.get(c["prediction_id"], {})
        p, odds, sigma = _num(c.get("probability")), _num(c.get("decimal_odds")), _num(s.get("sigma"))
        comm = _num(c.get("commission")) or 0.0
        state = evidence_state(cfg, c["engine_id"])
        g, why, evs = grade(cfg, c.get("decision", ""), p, sigma, odds, comm, state)
        sel = sel_by_pid.get(c["prediction_id"])
        # a selection is graded only by the run that decided it (decision_at == evaluated_at): first sight, never later
        same_run = bool(sel) and sel.get("decision_at") == c.get("evaluated_at")
        rows.append({"prediction_id": c["prediction_id"], "selection_id": sel["selection_id"] if same_run else "",
                     "sport": c["sport"], "competition": s.get("competition") or _competition(c["event_key"]),
                     "event_name": c["event_name"], "event_start": c["event_start"], "market": c["market"],
                     "selection": c["selection"], "engine_id": c["engine_id"], "engine_version": s.get("engine_version", ""),
                     "evaluated_at": c.get("evaluated_at", ""), "price_status": s.get("price_status", ""), "probability": p,
                     "p_first_snapshot": _num(s.get("p_first_snapshot")), "p_current_scan": _num(s.get("p_current_scan")),
                     "sigma": sigma, "sigma_method": s.get("sigma_method", ""),
                     "calibration_status": s.get("calibration_status", ""), "fair_odds": _num(c.get("fair_odds")),
                     "decimal_odds": odds, "source": c.get("source", ""), "is_exchange": str(c.get("is_exchange")) == "True",
                     "commission": comm, "price_observed_at": c.get("price_observed_at", ""),
                     "price_age_minutes": _num(c.get("price_age_minutes")), "net_ev": _num(c.get("net_ev")),
                     "bsv2_decision": c.get("decision", ""), "bsv2_reasons": c.get("reasons", ""),
                     "evidence_state": state, "grade": g, "grade_reason": why, **evs, "money_eligible": False})
    rows.sort(key=rank_key)
    hypothetical_stakes(rows, cfg.sim)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    counts = {g: sum(r["grade"] == g for r in rows) for g in GRADE_ORDER if g != UNGRADED}
    return {"product": "DAILY PAPER BET CARD (paper only -- not a real-money card)", "rule_version": cfg.rule_version,
            "generated_at": now.isoformat(), "real_money_enabled": False, "multis_enabled": False,
            "principle": "bsv2-4 decides; grades rank confidence in value; STRONG PREDICTION != VALID BET",
            "grade_counts": counts, "no_bet_today": not any(r["grade"] in STAKED_GRADES for r in rows),
            "candidates_evaluated_at": max((c.get("evaluated_at", "") for c in candidates), default=""),
            "stake_columns": stake_columns(cfg.sim), "rows": rows}


# ----------------------------------------------------------------------------------------------- decision shadow
# Directive s.7: ANALYTICAL SHADOW DATA of the whole decided space (every candidate, whatever its decision), so the
# frozen gates can be evaluated later. Never a paper bet, never staked; outcomes are joined at analysis time from
# predictions/unified_settlements.csv by prediction_id (nothing is written back). A new row only when the decided
# price/decision changes (same idea as the bsv2 price-snapshot id).
SHADOW_FIELDS = ["shadow_id", "card_rule_version", "evaluated_at", "prediction_id", "sport", "competition", "engine_id",
                 "engine_version", "event_start", "market", "selection", "probability", "sigma", "sigma_method",
                 "calibration_status", "fair_odds", "decimal_odds", "source", "is_exchange", "commission",
                 "price_observed_at", "price_age_minutes", "price_status", "net_ev", "ev_at_p", "ev_minus_1sigma",
                 "ev_minus_1645sigma", "bsv2_decision", "bsv2_reasons", "grade", "analytical_only"]


def shadow_rows(card: dict) -> list[dict]:
    out = []
    for r in card["rows"]:
        key = "|".join(str(r.get(k, "")) for k in ("prediction_id", "source", "decimal_odds", "price_observed_at", "bsv2_decision"))
        out.append({**{k: r.get(k, "") for k in SHADOW_FIELDS}, "shadow_id": L._h(key),
                    "card_rule_version": card["rule_version"], "analytical_only": True})
    return out


def append_shadow(path: Path, rows: list[dict]) -> int:
    return L._append(path, SHADOW_FIELDS, "shadow_id", rows)


ENRICH_FIELDS_BASE = ["selection_id", "prediction_id", "card_rule_version", "graded_at", "competition", "sigma",
                      "sigma_method", "calibration_status", "p_first_snapshot", "p_current_scan", "ev_at_p",
                      "ev_minus_1sigma", "ev_minus_1645sigma", "evidence_state", "grade", "grade_reason"]


def enrichment_rows(card: dict, selections: list[dict], cfg: CardConfig) -> list[dict]:
    """One row per paper selection: graded when the card was built by the run that decided it, else UNGRADED
    (e.g. selections decided before pcard-1 -- their decision-time sigma was never recorded; never back-filled)."""
    on_card = {r["selection_id"]: r for r in card["rows"] if r["selection_id"]}
    out = []
    for s in selections:
        r = on_card.get(s["selection_id"])
        base = {"selection_id": s["selection_id"], "prediction_id": s["prediction_id"], "card_rule_version": cfg.rule_version,
                "graded_at": card["generated_at"]}
        if r is None:
            out.append({**base, "competition": _competition(s["event_key"]), "evidence_state": evidence_state(cfg, s["engine_id"]),
                        "grade": UNGRADED, "grade_reason": "selection pre-dates pcard-1 or not on the card at first sight"})
        else:
            out.append({**base, **{k: r.get(k, "") for k in ENRICH_FIELDS_BASE[4:]}, **{k: r[k] for k in card["stake_columns"]}})
    return out


def append_enrichment(path: Path, rows: list[dict], stake_cols: list[str]) -> int:
    return L._append(path, ENRICH_FIELDS_BASE + stake_cols, "selection_id", rows)   # immutable, first sight wins


# ----------------------------------------------------------------------------------------------- dashboard
def _prediction_quality(rows: list[dict]) -> dict:
    s = [r for r in rows if r["status"] in ("WON", "LOST")]
    if not s:
        return {"n": 0}
    ys, ps = [1.0 if r["status"] == "WON" else 0.0 for r in s], [float(r["probability"]) for r in s]
    eps = 1e-12
    return {"n": len(s), "mean_p": round(sum(ps) / len(s), 4), "win_rate": round(sum(ys) / len(s), 4),
            "expected_wins": round(sum(ps), 3), "realised_wins": int(sum(ys)),
            "brier": round(sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(s), 5),
            "log_loss": round(-sum(y * math.log(max(p, eps)) + (1 - y) * math.log(max(1 - p, eps))
                                   for p, y in zip(ps, ys)) / len(s), 5)}


def dashboard(cfg: CardConfig, selections: list[dict], settlements: dict, enrichment: dict, annotations: dict,
              bs_rule_version: str, now: datetime) -> dict:
    headline = [s for s in selections if s["rule_version"] == bs_rule_version or annotations.get(s["selection_id"]) == "VALID_SAME_SNAPSHOT"]
    joined = []
    for s in selections:
        st, e = settlements.get(s["selection_id"]), enrichment.get(s["selection_id"], {})
        joined.append({**s, "status": st["status"] if st else "PENDING", "pnl_units": st["pnl_units"] if st else 0.0,
                       "grade": e.get("grade", UNGRADED), "competition": e.get("competition") or _competition(s["event_key"])})
    hid = {s["selection_id"] for s in headline}
    head_rows = [r for r in joined if r["selection_id"] in hid]
    fin = R.results(headline, settlements, cfg.sim)
    for r in joined:
        r["p_band"] = R.band(float(r["probability"]), R.P_BANDS)
        r["odds_band"] = R.band(float(r["decimal_odds"]), R.ODDS_BANDS)
    keys = {"sport": "sport", "competition": "competition", "market": "market", "engine": "engine_id",
            "rule_version": "rule_version", "grade": "grade", "probability_band": "p_band", "odds_band": "odds_band"}
    by = {}
    for name, k in keys.items():
        g: dict[str, list] = defaultdict(list)
        for r in joined:
            g[r[k]].append(r)
        by[name] = {v: {"financial": {**R._stats(rs), "mean_net_ev_at_decision": round(sum(float(x["net_ev"] or 0) for x in rs) / len(rs), 4)},
                        "prediction": _prediction_quality(rs)} for v, rs in sorted(g.items())}
    return {"product": "PAPER PERFORMANCE DASHBOARD (paper only; descriptive, no projections)", "generated_at": now.isoformat(),
            "card_rule_version": cfg.rule_version, "bsv2_rule_version": bs_rule_version, "real_money_enabled": False,
            "headline_set": f"bsv2 {bs_rule_version} selections + earlier rows annotated VALID_SAME_SNAPSHOT",
            "financial": fin, "prediction_quality_headline": _prediction_quality(head_rows),
            "all_selections": {"financial": R._stats(joined), "prediction": _prediction_quality(joined)},
            "clv": "NOT_AVAILABLE: no closing executable price is recorded for paper selections (not estimated)",
            "breakdowns_all_selections": by}


# ----------------------------------------------------------------------------------------------- markdown
def _fmt(x, nd=3):
    if x in (None, ""):
        return "—"
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def render_card_md(card: dict) -> str:
    out = [f"# Daily Paper Bet Card — {card['generated_at'][:16]}Z", "",
           "**PAPER ONLY. Not a real-money card. No bet here may be placed with real money without a "
           "MONEY_ELIGIBILITY_REVIEW and Fraser's explicit approval.**", "",
           f"Rule `{card['rule_version']}` on top of bsv2-4. {card['principle']}.",
           f"Candidates evaluated at {card.get('candidates_evaluated_at') or '—'}.", "",
           "Grades: " + ", ".join(f"{g} {n}" for g, n in card["grade_counts"].items()), ""]
    staked = [r for r in card["rows"] if r["grade"] in STAKED_GRADES]
    if card["no_bet_today"]:
        out += ["**NO PAPER BETS TODAY.** No candidate passed every bsv2-4 gate. That is a valid outcome.", ""]
    else:
        out += ["## Paper bets (A+/A/B)", "",
                "| # | Grade | Sport · competition | Event (start UTC) | Market · selection | P | σ | Odds (source, price time UTC) | Fair | EV | EV@P−1σ | £20 1% | £50 1% | £100 ⅛K | Model |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in staked:
            out.append(f"| {r['rank']} | {r['grade']} | {r['sport']} · {r['competition']} | {r['event_name']} ({r['event_start'][:16]}) "
                       f"| {r['market']} · {r['selection']} | {_fmt(r['probability'])} | {_fmt(r['sigma'])} "
                       f"| {_fmt(r['decimal_odds'], 2)} ({r['source']}, {str(r['price_observed_at'])[:16]}) "
                       f"| {_fmt(r['fair_odds'], 2)} | {_fmt(r['ev_at_p'])} | {_fmt(r['ev_minus_1sigma'])} "
                       f"| {r.get('stake_20_flat_1pct', '')} | {r.get('stake_50_flat_1pct', '')} | {r.get('stake_100_kelly_1_8', '')} "
                       f"| {r['engine_id']} v{r.get('engine_version') or '?'} |")
        out += ["", "Grade reasons: " + "; ".join(f"#{r['rank']} {r['grade_reason']}" for r in staked), ""]
    watch = [r for r in card["rows"] if r["grade"] == C]
    if watch:
        out += ["## Grade C (WATCH / multi research — information only, no stake)", ""]
        out += [f"- {r['sport']} · {r['event_name']} · {r['selection']} · P {_fmt(r['probability'])} · odds {_fmt(r['decimal_odds'], 2)} · {r['bsv2_reasons']}" for r in watch]
        out.append("")
    out += [f"Rejected candidates: {card['grade_counts'][REJECT]} (see reports/bet_selection_v2.md for reasons).", "",
            "Stakes are hypothetical, at the nominal bankroll, singles only, ≤5% per bet and ≤10% per day; no martingale/chasing."]
    return "\n".join(out) + "\n"


def render_dashboard_md(d: dict) -> str:
    f, pq = d["financial"]["overall"], d["prediction_quality_headline"]
    out = [f"# Paper Performance Dashboard — {d['generated_at'][:16]}Z", "", "Paper only. Descriptive; no projections.", "",
           f"Headline set: {d['headline_set']}.", "", "## Financial (units, 1 unit per paper bet)", "",
           f"Selections {f['selections']} · settled {f['settled']} · pending {f['pending']} · won {f['won']} · "
           f"expected P&L {f['expected_net_pnl_units']} · realised P&L {f['realised_net_pnl_units']} · ROI {f['roi_yield']} · "
           f"max DD {f['max_drawdown_units']} · longest losing run {f['longest_losing_streak']}", "",
           "## Prediction quality on settled paper bets (separate from money)", ""]
    out.append("No settled paper bets yet." if not pq["n"] else
               f"n {pq['n']} · mean P {pq['mean_p']} · win rate {pq['win_rate']} · expected wins {pq['expected_wins']} vs "
               f"realised {pq['realised_wins']} · Brier {pq['brier']} · log loss {pq['log_loss']}")
    out += ["", "## Hypothetical bankrolls (bsv2 replay)", "", "| Start £ | Policy | Bets | Final £ | Max DD % |", "|---|---|---|---|---|"]
    for s in d["financial"]["bankroll_simulations"]:
        out.append(f"| {s['bankroll_start']:.0f} | {s['policy']} | {s['bets']} | {s['final']:.2f} | {100 * s['max_drawdown_pct']:.1f} |")
    for name, groups in d["breakdowns_all_selections"].items():
        out += ["", f"## By {name} (all selections)", "", "| Group | Bets | Settled | Won | P&L u | Brier |", "|---|---|---|---|---|---|"]
        for k, v in groups.items():
            out.append(f"| {k or '—'} | {v['financial']['selections']} | {v['financial']['settled']} | {v['financial']['won']} "
                       f"| {v['financial']['realised_net_pnl_units']} | {v['prediction'].get('brier', '—')} |")
    return "\n".join(out) + "\n"
