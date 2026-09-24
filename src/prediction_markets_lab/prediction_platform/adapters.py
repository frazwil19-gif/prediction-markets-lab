"""Engine adapters -> canonical Predictions. Frozen methods only; nothing is fitted here.

Every adapter fails closed: invalid inputs produce a Skip (reason), never a fabricated prediction.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from prediction_markets_lab.prediction_platform.registry import Registry
from prediction_markets_lab.prediction_platform.schema import (
    HIGH_P, Prediction, band_of, fair_odds, make_prediction_id, validate)

STALE_AFTER = timedelta(hours=6)
FOOTBALL_WINDOW_MIN = 48 * 60
NBA_WINDOW_MIN = 36 * 60
TRIPLET_TOLERANCE = 0.03
MIN_NBA_BOOKS = 3
CONTEXT_STATUS = "NOT_MODELLED"   # frozen market engines use no team/player context


@dataclass(frozen=True)
class RunContext:
    configured_scan_time: str | None
    actual_workflow_start: str | None
    single_min_odds: float        # payout floor from config/thresholds.yaml


@dataclass(frozen=True)
class Skip:
    engine_id: str
    event_key: str
    reason: str


def _ts(s: str) -> datetime:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _iso(d: datetime) -> str:
    return d.astimezone(timezone.utc).isoformat()


def _build(reg: Registry, ctx: RunContext, engine_id: str, *, sport: str, competition: str, event_id: str | None,
           event_key: str, event_name: str, event_start: datetime, market: str, selection: str, p: float,
           pred_ts: datetime, live_price: float | None, live_src: str | None, paper_status: str = "PAPER",
           valid: bool = True, origin: str, origin_id: str | None = None, pid: str | None = None) -> Prediction:
    e = reg.get(engine_id)
    fo = fair_odds(p)
    single = bool(e["money_eligible"]) and fo >= ctx.single_min_odds and valid
    reason = None if single else ("engine not money-eligible" if not e["money_eligible"]
                                  else f"fair odds {fo:.2f} below payout floor {ctx.single_min_odds}" if fo < ctx.single_min_odds
                                  else "prediction not valid")
    return Prediction(
        prediction_id=pid or make_prediction_id(engine_id, e["ledger_version"], event_key, market, selection),
        engine_id=engine_id, engine_version=e["ledger_version"], sport=sport, competition=competition, event_id=event_id,
        event_key=event_key, event_name=event_name, event_start=_iso(event_start), market=market, selection=selection,
        estimated_probability=float(p), fair_odds=fo, probability_band=band_of(p), probability_source=e["probability_source"],
        historical_support=reg.support_text(engine_id), engine_status=e["status"], data_quality="OK" if valid else "RESEARCH_ONLY",
        current_context_status=CONTEXT_STATUS, configured_scan_time=ctx.configured_scan_time,
        actual_workflow_start=ctx.actual_workflow_start, prediction_timestamp=_iso(pred_ts),
        minutes_to_event=round((event_start - pred_ts).total_seconds() / 60, 1), live_price=live_price, live_price_source=live_src,
        paper_status=paper_status, prediction_valid=valid, single_eligible=single, single_ineligible_reason=reason,
        multi_research_eligible=bool(e["multi_research_eligible"]) and valid and p >= HIGH_P,
        snapshot_rule=e["snapshot_rule"], origin=origin, origin_prediction_id=origin_id)


# ---------------------------------------------------------------- football (daily card; 0 credits)
FOOTBALL_1X2, FOOTBALL_OU, FOOTBALL_DC = ("football_1x2.market_consensus", "football_ou25.market",
                                          "football_double_chance.derived_1x2")


def football_event_key(competition: str, event: str, kickoff: str) -> str:
    return f"football|{competition}|{event}|{_iso(_ts(kickoff))}"


def football_from_card(card: dict, reg: Registry, ctx: RunContext, now: datetime,
                       origin: str) -> tuple[list[Prediction], list[Skip]]:
    preds: list[Prediction] = []
    skips: list[Skip] = []
    data_ts = _ts(card["data_timestamp"])
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for c in card.get("candidates", []):
        if c.get("sport") == "football" and c.get("kickoff_time"):
            groups[(c["competition"], c["event"], c["kickoff_time"])].append(c)
    if now - data_ts > STALE_AFTER:
        return [], [Skip("football", "*", f"STALE: card data {data_ts.isoformat()} older than {STALE_AFTER}")]
    for (comp, event, ko), rows in sorted(groups.items()):
        key = football_event_key(comp, event, ko)
        start = _ts(ko)
        mins = (start - data_ts).total_seconds() / 60
        if mins <= 0:
            skips.append(Skip("football", key, "EVENT_STARTED"))
            continue
        if mins > FOOTBALL_WINDOW_MIN:
            skips.append(Skip("football", key, "OUTSIDE_48H_WINDOW"))
            continue
        by_sel: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for r in rows:
            by_sel[(r["market"], r["selection"])].append(r)
        if any(len(v) > 1 for v in by_sel.values()):
            skips.append(Skip("football", key, "REVIEW_REQUIRED: duplicate selection rows for one event"))
            continue
        common = dict(sport="football", competition=comp, event_id=None, event_key=key, event_name=event,
                      event_start=start, pred_ts=data_ts, origin=origin)
        trip = [by_sel.get(("1x2", s), [None])[0] for s in ("home", "draw", "away")]
        if all(trip):
            ps = [float(t["estimated_probability"]) for t in trip]
            tot = sum(ps)
            if abs(tot - 1) > TRIPLET_TOLERANCE or any(not 0 < x < 1 for x in ps):
                skips.append(Skip(FOOTBALL_1X2, key, f"DATA_INVALID: 1X2 sum {tot:.3f}"))
            else:
                if reg.collectable(FOOTBALL_1X2, now):
                    for t, sel in zip(trip, ("home", "draw", "away")):
                        preds.append(_build(reg, ctx, FOOTBALL_1X2, market="1x2", selection=sel, p=float(t["estimated_probability"]),
                                            live_price=float(t["available_odds"]), live_src=f"odds_api:{t['bookmaker']}", **common))
                if reg.collectable(FOOTBALL_DC, now):
                    q = [x / tot for x in ps]
                    o = [float(t["available_odds"]) for t in trip]
                    for sel, (i, j) in (("1X", (0, 1)), ("X2", (1, 2)), ("12", (0, 2))):
                        synth = 1.0 / (1.0 / o[i] + 1.0 / o[j])
                        preds.append(_build(reg, ctx, FOOTBALL_DC, market="double_chance", selection=sel, p=q[i] + q[j],
                                            live_price=round(synth, 4), live_src="SYNTHETIC_DUTCH_BEST_1X2", **common))
        elif any(trip):
            skips.append(Skip(FOOTBALL_1X2, key, "DATA_INVALID: incomplete 1X2 triplet"))
        ou = [by_sel.get(("over_under_2_5", s), [None])[0] for s in ("over", "under")]
        if all(ou) and reg.collectable(FOOTBALL_OU, now):
            fav = max(ou, key=lambda r: float(r["estimated_probability"]))
            p = float(fav["estimated_probability"])
            if 0 < p < 1:
                preds.append(_build(reg, ctx, FOOTBALL_OU, market="over_under_2_5", selection=fav["selection"], p=p,
                                    live_price=float(fav["available_odds"]), live_src=f"odds_api:{fav['bookmaker']}", **common))
    return _checked(preds, skips)


# ---------------------------------------------------------------- tennis (mirror of the frozen tennis ledger)
_BACK = re.compile(r"ex_back=([\d.]+)/([\d.]+)")


def _match_run(pred_ts: datetime, run_log: list[dict]) -> dict | None:
    best = None
    for r in run_log:
        try:
            d = abs((_ts(r["scan_timestamp_utc"]) - pred_ts).total_seconds())
        except (KeyError, ValueError):
            continue
        if d <= 300 and (best is None or d < best[0]):
            best = (d, r)
    return best[1] if best else None


def tennis_from_ledger(rows: list[dict], run_log: list[dict], reg: Registry, single_min_odds: float,
                       origin: str) -> tuple[list[Prediction], list[Skip]]:
    preds, skips = [], []
    for r in rows:
        eid = r["engine_id"]
        try:
            reg.get(eid)
        except KeyError:
            skips.append(Skip(eid, r.get("event_id", ""), "ENGINE_UNKNOWN"))
            continue
        pts = _ts(r["prediction_timestamp"])
        run = _match_run(pts, run_log)
        ctx = RunContext(configured_scan_time=(run or {}).get("configured_schedule_utc") or None,
                         actual_workflow_start=(run or {}).get("scan_timestamp_utc") or None, single_min_odds=single_min_odds)
        winner, p = r["predicted_winner"], float(r["predicted_probability"])
        live = None
        m = _BACK.search(r.get("raw_prices", ""))
        if m:
            live = float(m.group(1) if winner == r["player_a"] else m.group(2))
        valid = str(r.get("source_validated")) in ("True", "true", "1")
        preds.append(_build(reg, ctx, eid, sport="tennis", competition=r["tournament"], event_id=r["event_id"],
                            event_key=f"tennis|{r['sport_key']}|{r['event_id']}", event_name=f"{r['player_a']} v {r['player_b']}",
                            event_start=_ts(r["commence_time"]), market="match_winner", selection=winner, p=p, pred_ts=pts,
                            live_price=live, live_src="betfair_ex_uk back (odds_api)" if live else None,
                            paper_status="PAPER" if valid else "RESEARCH_ONLY_SOURCE", valid=valid,
                            origin=origin, origin_id=r["prediction_id"], pid=r["prediction_id"]))
    return _checked(preds, skips)


# ---------------------------------------------------------------- NBA (frozen: mean decimal odds per side, proportional)
NBA = "nba_moneyline.market"


def nba_from_odds(raw: list[dict], reg: Registry, ctx: RunContext, now: datetime,
                  origin: str) -> tuple[list[Prediction], list[Skip]]:
    preds, skips = [], []
    if not reg.collectable(NBA, now):
        return [], [Skip(NBA, "*", "NOT_ACTIVE (awaiting season activation date)")]
    for ev in raw:
        key = f"nba|{ev['id']}"
        start = _ts(ev["commence_time"])
        mins = (start - now).total_seconds() / 60
        if mins <= 0 or mins > NBA_WINDOW_MIN:
            skips.append(Skip(NBA, key, "EVENT_STARTED" if mins <= 0 else "OUTSIDE_36H_WINDOW"))
            continue
        prices: dict[str, list[float]] = {ev["home_team"]: [], ev["away_team"]: []}
        for b in ev.get("bookmakers", []):
            if b["key"].startswith("betfair_ex"):
                continue
            for mk in b.get("markets", []):
                if mk["key"] == "h2h" and len(mk["outcomes"]) == 2:
                    for o in mk["outcomes"]:
                        if o["name"] in prices and float(o["price"]) > 1.0:
                            prices[o["name"]].append(float(o["price"]))
        h, a = prices[ev["home_team"]], prices[ev["away_team"]]
        if min(len(h), len(a)) < MIN_NBA_BOOKS or len(h) != len(a):
            skips.append(Skip(NBA, key, f"DATA_INVALID: books home={len(h)} away={len(a)} (need >= {MIN_NBA_BOOKS}, paired)"))
            continue
        ih, ia = 1 / (sum(h) / len(h)), 1 / (sum(a) / len(a))
        ph = ih / (ih + ia)
        sel, p, live = (ev["home_team"], ph, max(h)) if ph >= 0.5 else (ev["away_team"], 1 - ph, max(a))
        preds.append(_build(reg, ctx, NBA, sport="basketball", competition="NBA", event_id=ev["id"], event_key=key,
                            event_name=f"{ev['away_team']} @ {ev['home_team']}", event_start=start, market="moneyline",
                            selection=sel, p=p, pred_ts=now, live_price=live, live_src="odds_api best book", origin=origin))
    return _checked(preds, skips)


def _checked(preds: list[Prediction], skips: list[Skip]) -> tuple[list[Prediction], list[Skip]]:
    ok = []
    for p in preds:
        errs = validate(p)
        if errs:
            skips.append(Skip(p.engine_id, p.event_key, "DATA_INVALID: " + "; ".join(errs)))
        else:
            ok.append(p)
    return ok, skips
