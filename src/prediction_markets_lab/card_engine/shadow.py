"""V2-7 prospective SHADOW card logging (cer-2). RESEARCH ONLY.

Pure functions that turn ONE same-scan tennis snapshot (engine probabilities + per-book prices the tennis board already
wrote in the same workflow run) into bounded research records. No network access, no API client, no production ledger
writes: all file writes go through `ShadowStore`, which refuses any path outside its research output directory.

Cohorts (never merged):
  HIGH_P  book-agnostic unique leg sets of clean P >= min_leg_p favourites (probability research, any EV);
          singles + doubles all logged, trebles a fixed 10% hash sample (weight 10). Per-book prices summarised.
  POS_EV  per-book cards whose every leg is clean and +EV at that book in the same scan. All logged (bounded).
All multi prices are INDICATIVE / NOT EXECUTION-VERIFIED (product of one book's leg prices in one snapshot).
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from prediction_markets_lab.card_engine import cards as C

HIGH_P, POS_EV = C.HIGH_P, C.POS_EV

# ---------------------------------------------------------------- status vocabulary (scan records)
OK = "OK"
OK_ZERO = "OK_ZERO_CANDIDATES"               # scan present and processed; genuinely no candidate leg
NO_SCAN = "NO_SCAN_THIS_RUN"                 # production produced no scan in this run (explicit, not a zero-card scan)
LATE = "LATE_SCAN_NOT_LOGGED"                # scan too old to log prospectively (no backfilling)
INPUT_MISSING = "INPUT_MISSING"
INPUT_INVALID = "INPUT_INVALID"
CAP_EXCEEDED = "OUTPUT_CAP_EXCEEDED"
FAILED = "FAILED_EXCEPTION"
RESEARCH_TESTS_FAILED = "RESEARCH_TESTS_FAILED"
PROD_TESTS_FAILED = "PRODUCTION_TESTS_FAILED_NO_SCAN"
SUCCESS_STATUSES = (OK, OK_ZERO)

SCAN_FIELDS = ["record_id", "status", "failure_reason", "scan", "mode", "logged_at", "run_id", "commit_sha", "trigger",
               "workflow_start", "production_tests", "rule_version", "config_sha", "bsv2_rule_version", "engines",
               "input_shas", "counts_json", "legs_logged", "cards_logged"]
# book "*" rows are event-level HIGH_P legs (P is per event); their per-book prices stay in the production
# price_snapshots.csv (append-only; its sha is in the scan record) and are summarised on each HIGH_P card.
LEG_FIELDS = ["leg_id", "record_id", "scan", "book", "sport_key", "event_id", "start", "selection", "opponent",
              "p", "exchange_width", "odds", "ev", "quote_last_update", "n_books_clean", "quality"]
CARD_FIELDS = ["card_id", "record_id", "scan", "rule_version", "cohort", "book", "k", "legset", "leg_ids", "status", "reasons",
               "dependence", "dependence_flags", "calibration_support", "p_joint", "sigma_joint", "sample_weight",
               "odds_indicative", "ev", "ev_low", "ev_high", "n_books_priced", "odds_min", "odds_median", "odds_max",
               "ev_median", "best_book", "equal_capital_json"]


# ---------------------------------------------------------------- configuration
@dataclass(frozen=True)
class ShadowConfig:
    rule_version: str
    logging_enabled: bool
    settlement_enabled: bool
    output_dir: str
    inputs: dict
    max_quote_age_minutes: float
    max_exchange_spread_prob: float
    max_scan_to_log_minutes: float
    high_p_min_leg_p: float
    high_p_max_events: int
    high_p_log_k: tuple[int, ...]
    treble_sample_rate: float
    treble_sample_salt: str
    pos_ev_max_legs_per_book: int
    pos_ev_max_cards_per_scan: int
    max_k: int
    doubles_verified_below_p: float
    trebles_verified_below_p: float
    equal_capital_stakes: tuple[float, ...]
    max_rows_per_scan: int
    overdue_days: float
    exchange_keys: tuple[str, ...]
    bsv2_rule_version: str
    config_sha: str


def load_config(path: Path, repo: Path) -> ShadowConfig:
    raw = path.read_bytes()
    c = yaml.safe_load(raw)
    bs = yaml.safe_load((repo / c["inputs"]["bet_selection_config"]).read_text())
    q = c["quality"]
    # never weaker than the deployed bsv2-3 data-quality gates
    if float(q["max_quote_age_minutes"]) > float(bs["decision_gates"]["paper_bet"]["max_price_age_minutes"]):
        raise ValueError("shadow quote-age rule is weaker than bsv2")
    if float(q["max_exchange_spread_prob"]) > float(bs["data_quality"]["max_exchange_spread_prob"]):
        raise ValueError("shadow exchange-width rule is weaker than bsv2")
    hp, pe = c["cohorts"]["HIGH_P"], c["cohorts"]["POS_EV"]
    return ShadowConfig(
        rule_version=c["rule_version"], logging_enabled=bool(c["logging_enabled"]),
        settlement_enabled=bool(c["settlement_enabled"]), output_dir=c["output_dir"], inputs=dict(c["inputs"]),
        max_quote_age_minutes=float(q["max_quote_age_minutes"]), max_exchange_spread_prob=float(q["max_exchange_spread_prob"]),
        max_scan_to_log_minutes=float(c["max_scan_to_log_minutes"]),
        high_p_min_leg_p=float(hp["min_leg_p"]), high_p_max_events=int(hp["max_events"]),
        high_p_log_k=tuple(int(k) for k in hp["log_k"]), treble_sample_rate=float(hp["treble_sample_rate"]),
        treble_sample_salt=str(hp["treble_sample_salt"]), pos_ev_max_legs_per_book=int(pe["max_legs_per_book"]),
        pos_ev_max_cards_per_scan=int(pe["max_cards_per_scan"]), max_k=int(c["max_k"]),
        doubles_verified_below_p=float(c["calibration_support"]["doubles_verified_below_p"]),
        trebles_verified_below_p=float(c["calibration_support"]["trebles_verified_below_p"]),
        equal_capital_stakes=tuple(float(s) for s in c["equal_capital_stakes"]),
        max_rows_per_scan=int(c["max_rows_per_scan"]), overdue_days=float(c["settlement"]["overdue_days"]),
        exchange_keys=tuple(bs["exchange_keys"]), bsv2_rule_version=str(bs["rule_version"]),
        config_sha=hashlib.sha256(raw).hexdigest()[:16])


# ---------------------------------------------------------------- helpers
def ts(s: str) -> datetime:
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def h16(*parts: object) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def leg_id(scan: str, book: str, event_id: str, selection: str) -> str:
    return h16("leg", scan, book, event_id, selection)


def legset_key(pairs: list[tuple[str, str]]) -> str:
    """Canonical book-agnostic leg set: sorted event_id:selection."""
    return ";".join(sorted(f"{e}:{s}" for e, s in pairs))


def sample_unit(key: str, salt: str) -> float:
    """Deterministic uniform [0,1) from the leg set only -- fixed before outcomes, independent of order, prices and
    results, identical across reruns and scans (a leg set is either always in or always out of the treble sample)."""
    return int(hashlib.sha256(f"{salt}|{key}".encode()).hexdigest()[:12], 16) / float(16 ** 12)


def is_exchange(book: str, keys: tuple[str, ...]) -> bool:
    return book in keys or book.startswith(C.EXCHANGES)


def calibration_support(k: int, p_joint: float | None, cfg: ShadowConfig) -> str:
    if p_joint is None:
        return "NOT_ESTIMABLE"
    if k == 1:
        return "VERIFIED_SINGLES"
    if k == 2:
        return "VERIFIED_DOUBLES_PM1.5PP" if p_joint < cfg.doubles_verified_below_p else "UNTESTED_DOUBLES_HIGH_BAND"
    return "WEAK_TREBLES_PM4PP" if p_joint < cfg.trebles_verified_below_p else "UNTESTED_TREBLES_HIGH_BAND"


def _f(v: float | None, nd: int = 6) -> Any:
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else round(v, nd)


# ---------------------------------------------------------------- leg loading (same scan only)
def load_scan_legs(prob_rows: list[dict], price_rows: list[dict], scan: str, logged_at: datetime,
                   cfg: ShadowConfig) -> tuple[list[C.Leg], dict]:
    """Favourite side of every VALIDATED engine prediction in `scan` x every non-exchange book quote in the SAME scan.
    Returns legs (with quality codes) and population counts. Never reads another scan's price or probability."""
    scan_t = ts(scan)
    counts: dict[str, Any] = {"prob_rows_in_scan": 0, "price_rows_in_scan": 0, "validated_events": 0, "not_validated_events": 0,
                              "duplicate_event_rows": 0, "events_without_book_quote": 0, "exchange_quotes_skipped": 0,
                              "name_mismatch_quotes": 0, "leg_quality": {}}
    prices: dict[str, list[dict]] = {}
    for r in price_rows:
        if r.get("scan_timestamp_utc") != scan:
            continue
        counts["price_rows_in_scan"] += 1
        if is_exchange(r["bookmaker"], cfg.exchange_keys):
            counts["exchange_quotes_skipped"] += 1
            continue
        prices.setdefault(r["event_id"], []).append(r)
    seen: set[str] = set()
    legs: list[C.Leg] = []
    for x in prob_rows:
        if x.get("scan_timestamp_utc") != scan:
            continue
        counts["prob_rows_in_scan"] += 1
        if str(x.get("source_validated")) != "True":
            counts["not_validated_events"] += 1
            continue
        if x["event_id"] in seen:                     # one validated P per event per scan; duplicates never double-count
            counts["duplicate_event_rows"] += 1
            continue
        seen.add(x["event_id"])
        counts["validated_events"] += 1
        pa = float(x["p_a"])
        sel, opp, p = (x["player_a"], x["player_b"], pa) if pa >= 0.5 else (x["player_b"], x["player_a"], 1 - pa)
        w_raw = x.get("exchange_spread_prob", "")
        width = float(w_raw) if w_raw not in ("", None) else float("nan")
        quotes = prices.get(x["event_id"], [])
        if not quotes:
            counts["events_without_book_quote"] += 1
        for r in quotes:
            if {r["player_a"], r["player_b"]} != {x["player_a"], x["player_b"]}:
                counts["name_mismatch_quotes"] += 1
                continue
            try:
                odds = float(r["odds_a"] if r["player_a"] == sel else r["odds_b"])
            except (TypeError, ValueError):
                odds = float("nan")
            q = []
            if width != width:
                q.append("EXCHANGE_WIDTH_UNKNOWN")
            elif width > cfg.max_exchange_spread_prob:
                q.append("EXCHANGE_BOOK_TOO_WIDE")
            lu = r.get("last_update") or ""
            try:
                age = scan_t - ts(lu) if lu else None
            except ValueError:
                age = None
            if age is None or age > timedelta(minutes=cfg.max_quote_age_minutes) or age < timedelta(minutes=-5):
                q.append("QUOTE_STALE_OR_UNTIMED")
            start = ts(x["commence_time"])
            if start <= scan_t:
                q.append("EVENT_STARTED")
            elif start <= logged_at:
                q.append("STARTED_BEFORE_LOGGING")
            if not (odds == odds) or odds <= 1.0:
                q.append("INVALID_ODDS")
            for code in q:
                counts["leg_quality"][code] = counts["leg_quality"].get(code, 0) + 1
            legs.append(C.Leg(scan, r["bookmaker"], x["sport_key"], x["event_id"], f"{x['player_a']} v {x['player_b']}",
                              x["commence_time"], sel, opp, p, odds if odds == odds else 0.0, lu,
                              width if width == width else 1.0, engine_of(x["sport_key"]), tuple(q)))
    counts["legs_total"] = len(legs)
    counts["legs_clean"] = sum(1 for l in legs if l.clean)
    return legs, counts


def engine_of(sport_key: str) -> str:
    return ("atp_match_winner.betfair_market@1" if sport_key.startswith("tennis_atp_") else
            "wta_match_winner.betfair_market@1" if sport_key.startswith("tennis_wta_") else f"unknown:{sport_key}")


# ---------------------------------------------------------------- cohort builders
def _price_summary(legsets_by_book: dict[str, tuple[C.Leg, ...]], p_joint: float | None) -> dict:
    """Same-book indicative prices for one leg set: every value is ONE book's product of its own leg prices."""
    if not legsets_by_book:
        return {"n_books_priced": 0, "odds_min": None, "odds_median": None, "odds_max": None, "ev_median": None,
                "best_book": ""}
    od = {b: math.prod(l.odds for l in ls) for b, ls in legsets_by_book.items()}
    vals = sorted(od.values())
    best = max(sorted(od), key=lambda b: od[b])
    med = statistics.median(vals)
    return {"n_books_priced": len(od), "odds_min": vals[0], "odds_median": med, "odds_max": vals[-1],
            "ev_median": (p_joint * med - 1) if p_joint is not None else None, "best_book": best}


def build_high_p(legs: list[C.Leg], cfg: ShadowConfig, cal_se: Callable[[float], float]) -> tuple[list[dict], dict, dict[str, int]]:
    """Book-agnostic HIGH_P cohort. Returns card dicts, counts, and ids of the per-book legs to store."""
    clean_by_event: dict[str, dict[str, C.Leg]] = {}
    for l in legs:
        if l.clean and l.p >= cfg.high_p_min_leg_p:
            clean_by_event.setdefault(l.event_id, {})[l.book] = l
    events = sorted(clean_by_event, key=lambda e: (-next(iter(clean_by_event[e].values())).p, e))
    kept = events[:cfg.high_p_max_events]
    counts: dict[str, Any] = {"eligible_events": len(events), "kept_events": len(kept),
                              "truncated_events": len(events) - len(kept),
                              "enumerated": {}, "logged": {}, "sampling_excluded": {}, "dependence_unverified": {}}
    out, store_legs = [], {e: len(clean_by_event[e]) for e in kept}     # event -> number of clean books
    for k in range(1, cfg.max_k + 1):
        n_enum = n_log = n_excl = n_unv = 0
        for combo in itertools.combinations(kept, k):
            n_enum += 1
            rep = tuple(next(iter(clean_by_event[e].values())) for e in combo)  # P and names are per event, not per book
            key = legset_key([(l.event_id, l.selection) for l in rep])
            weight = 1.0
            if k not in cfg.high_p_log_k:
                if sample_unit(key, cfg.treble_sample_salt) >= cfg.treble_sample_rate:
                    n_excl += 1
                    continue
                weight = 1.0 / cfg.treble_sample_rate
            card = C.build_card(cfg.rule_version, HIGH_P, rep, cal_se)
            if card.dependence != C.INDEPENDENT:
                n_unv += 1
            books = sorted(set.intersection(*(set(clean_by_event[e]) for e in combo)))
            per_book = {b: tuple(clean_by_event[e][b] for e in combo) for b in books}
            ps = _price_summary(per_book, card.p_joint)
            status = "RESEARCH_HIGH_P" if card.dependence == C.INDEPENDENT else "RESEARCH_ONLY_UNVERIFIED"
            reasons = []            # implicit for every HIGH_P row: ODDS_INDICATIVE_NOT_EXECUTION_VERIFIED, book-agnostic
            if card.dependence != C.INDEPENDENT:
                reasons.append("JOINT_P_NOT_ESTIMABLE")
            if not per_book:
                reasons.append("NO_SINGLE_BOOK_PRICES_ALL_LEGS")
            if weight != 1.0:
                reasons.append("TREBLE_HASH_SAMPLE")
            out.append({
                "card_id": h16("card", cfg.rule_version, rep[0].scan, HIGH_P, "*", key), "cohort": HIGH_P, "book": "*",
                "k": k, "legset": key, "leg_ids": "", "status": status, "reasons": "|".join(reasons),
                "dependence": card.dependence, "dependence_flags": "|".join(card.dependence_flags),
                "calibration_support": calibration_support(k, card.p_joint, cfg), "p_joint": _f(card.p_joint),
                "sigma_joint": _f(card.sigma_joint), "sample_weight": weight, "odds_indicative": "", "ev": "",
                "ev_low": "", "ev_high": "", "n_books_priced": ps["n_books_priced"], "odds_min": _f(ps["odds_min"], 4),
                "odds_median": _f(ps["odds_median"], 4), "odds_max": _f(ps["odds_max"], 4), "ev_median": _f(ps["ev_median"]),
                "best_book": ps["best_book"], "equal_capital_json": "", "_legs": card.legs})
            n_log += 1
        counts["enumerated"][k], counts["logged"][k] = n_enum, n_log
        counts["sampling_excluded"][k], counts["dependence_unverified"][k] = n_excl, n_unv
    return out, counts, store_legs


def build_pos_ev(legs: list[C.Leg], cfg: ShadowConfig, cal_se: Callable[[float], float]) -> tuple[list[dict], dict, set[str]]:
    """Per-book POS_EV cohort: every leg clean and +EV at that book in this scan. All distinct cards, bounded."""
    by_book: dict[str, list[C.Leg]] = {}
    for l in legs:
        if l.clean and l.ev > 0:
            by_book.setdefault(l.book, []).append(l)
    counts: dict[str, Any] = {"books_with_pos_ev_legs": len(by_book), "pos_ev_legs": sum(map(len, by_book.values())),
                              "truncated_legs": 0, "enumerated": {1: 0, 2: 0, 3: 0}, "dropped_by_card_cap": {1: 0, 2: 0, 3: 0},
                              "same_event_combos_skipped": 0, "anomaly": ""}
    built: list[C.Card] = []
    for book in sorted(by_book):
        pool = sorted(by_book[book], key=lambda l: (-l.ev, l.event_id))
        kept = pool[:cfg.pos_ev_max_legs_per_book]
        counts["truncated_legs"] += len(pool) - len(kept)
        for k in range(1, cfg.max_k + 1):
            for combo in itertools.combinations(kept, k):
                if len({l.event_id for l in combo}) < k:
                    counts["same_event_combos_skipped"] += 1
                    continue
                counts["enumerated"][k] += 1
                built.append(C.build_card(cfg.rule_version, POS_EV, combo, cal_se))
    if len(built) > cfg.pos_ev_max_cards_per_scan:        # anomalous scan (e.g. a broken feed): keep singles, count the rest
        counts["anomaly"] = "POS_EV_CARD_CAP_EXCEEDED_SINGLES_ONLY"
        for c in built:
            if c.k > 1:
                counts["dropped_by_card_cap"][c.k] += 1
        built = [c for c in built if c.k == 1]
    out, store = [], set()
    for c in built:
        ids = [leg_id(l.scan, l.book, l.event_id, l.selection) for l in c.legs]
        store.update(ids)
        eq = ([{kk: (round(v, 8) if isinstance(v, float) else v) for kk, v in C.equal_capital(c.legs, s).items()}
               for s in cfg.equal_capital_stakes] if c.k > 1 and c.p_joint is not None else [])
        out.append({
            "card_id": h16("card", cfg.rule_version, c.scan, POS_EV, c.book, legset_key([(l.event_id, l.selection) for l in c.legs])),
            "cohort": POS_EV, "book": c.book, "k": c.k,
            "legset": legset_key([(l.event_id, l.selection) for l in c.legs]), "leg_ids": "|".join(ids),
            "status": c.status, "reasons": "|".join(c.reasons), "dependence": c.dependence,
            "dependence_flags": "|".join(c.dependence_flags), "calibration_support": calibration_support(c.k, c.p_joint, cfg),
            "p_joint": _f(c.p_joint), "sigma_joint": _f(c.sigma_joint), "sample_weight": 1.0,
            "odds_indicative": round(c.odds_indicative, 4), "ev": _f(c.ev), "ev_low": _f(c.ev_low), "ev_high": _f(c.ev_high),
            "n_books_priced": 1, "odds_min": "", "odds_median": "", "odds_max": "", "ev_median": "", "best_book": c.book,
            "equal_capital_json": json.dumps(eq, sort_keys=True) if eq else "", "_legs": c.legs})
    counts["logged"] = {k: sum(1 for r in out if r["k"] == k) for k in (1, 2, 3)}
    counts["status"] = {s: sum(1 for r in out if r["status"] == s) for s in sorted({r["status"] for r in out})}
    return out, counts, store


# ---------------------------------------------------------------- exposure / dependence diagnostics
def card_correlation(a: tuple[tuple[str, str, float], ...], b: tuple[tuple[str, str, float], ...]) -> float:
    """Model-implied correlation of two card win indicators when legs on distinct events are independent.
    Legs are (event_id, selection, p). Same event + same selection is one shared leg; same event + opposite selection
    makes joint winning impossible."""
    pa = math.prod(p for _, _, p in a)
    pb = math.prod(p for _, _, p in b)
    da = {e: (s, p) for e, s, p in a}
    both = 1.0
    for e, s, p in b:
        if e in da:
            if da[e][0] != s:
                both = 0.0
                break
        else:
            both *= p
    both = both * pa if both else 0.0
    va, vb = pa * (1 - pa), pb * (1 - pb)
    if va <= 0 or vb <= 0:
        return 0.0
    return (both - pa * pb) / math.sqrt(va * vb)


def effective_n(cards: list[tuple[tuple[tuple[str, str, float], ...], float]]) -> float:
    """Kish-type effective sample size of (weighted) card outcomes: (sum w)^2 / sum_ij w_i w_j rho_ij."""
    if not cards:
        return 0.0
    num = sum(w for _, w in cards) ** 2
    den = 0.0
    for i, (ci, wi) in enumerate(cards):
        den += wi * wi
        for cj, wj in cards[i + 1:]:
            if {e for e, _, _ in ci} & {e for e, _, _ in cj}:
                den += 2 * wi * wj * card_correlation(ci, cj)
    return num / den if den > 0 else 0.0


def exposure_diagnostics(card_rows: list[dict]) -> dict:
    out: dict[str, Any] = {"note": "Cards sharing legs are NOT independent observations; use effective_n, not card counts."}
    for cohort in (HIGH_P, POS_EV):
        rows = [r for r in card_rows if r["cohort"] == cohort and r["p_joint"] != ""]
        d: dict[str, Any] = {}
        for k in (1, 2, 3):
            ks = [r for r in rows if r["k"] == k]
            if not ks:
                continue
            ev_count: dict[str, float] = {}
            pl_count: dict[str, float] = {}
            legsets = set()
            spec = []
            for r in ks:
                L = r["_legs"]
                legsets.add(r["legset"])
                for l in L:
                    ev_count[l.event_id] = ev_count.get(l.event_id, 0) + r["sample_weight"]
                    pl_count[l.selection] = pl_count.get(l.selection, 0) + r["sample_weight"]
                spec.append((tuple((l.event_id, l.selection, l.p) for l in L), float(r["sample_weight"])))
            wsum = sum(r["sample_weight"] for r in ks)
            top = sorted(ev_count.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
            pairs = sum(1 for i in range(len(ks)) for j in range(i + 1, len(ks))
                        if {l.event_id for l in ks[i]["_legs"]} & {l.event_id for l in ks[j]["_legs"]})
            npairs = len(ks) * (len(ks) - 1) // 2
            books_per_set: dict[str, int] = {}
            for r in ks:
                books_per_set[r["legset"]] = books_per_set.get(r["legset"], 0) + 1
            d[f"k{k}"] = {"cards_logged": len(ks), "weighted_cards": round(wsum, 2), "unique_leg_sets": len(legsets),
                          "unique_matches": len(ev_count),
                          "max_event_share_of_cards": round(top[0][1] / wsum, 4) if top else 0.0,
                          "top_event_exposure": [[e, round(v, 2)] for e, v in top],
                          "max_player_cards": max(pl_count.values()) if pl_count else 0,
                          "share_of_card_pairs_sharing_a_match": round(pairs / npairs, 4) if npairs else 0.0,
                          "max_books_repeating_one_leg_set": max(books_per_set.values()),
                          "effective_n_model_implied": round(effective_n(spec), 2)}
        out[cohort] = d
    return out


# ---------------------------------------------------------------- one scan -> records
def process_scan(prob_rows: list[dict], price_rows: list[dict], scan: str, logged_at: datetime, cfg: ShadowConfig,
                 cal_se: Callable[[float], float]) -> dict:
    """Returns {"status", "counts", "legs": [...], "cards": [...], "diagnostics": {...}} for one scan. Pure."""
    legs, counts = load_scan_legs(prob_rows, price_rows, scan, logged_at, cfg)
    hp_cards, hp_counts, hp_store = build_high_p(legs, cfg, cal_se)
    pe_cards, pe_counts, pe_store = build_pos_ev(legs, cfg, cal_se)
    counts["HIGH_P"], counts["POS_EV"] = hp_counts, pe_counts
    leg_rows, done_events = [], set()
    for l in sorted(legs, key=lambda l: (l.event_id, l.book)):
        base = {"scan": l.scan, "sport_key": l.sport_key, "event_id": l.event_id, "start": l.start, "selection": l.selection,
                "opponent": l.opponent, "p": round(l.p, 6), "exchange_width": round(l.exchange_width, 6)}
        if l.event_id in hp_store and l.event_id not in done_events:
            done_events.add(l.event_id)
            leg_rows.append({"leg_id": leg_id(l.scan, "*", l.event_id, l.selection), "book": "*", "odds": "", "ev": "",
                             "quote_last_update": "", "n_books_clean": hp_store[l.event_id], "quality": "", **base})
        lid = leg_id(l.scan, l.book, l.event_id, l.selection)
        if lid in pe_store:
            leg_rows.append({"leg_id": lid, "book": l.book, "odds": l.odds, "ev": round(l.ev, 6),
                             "quote_last_update": l.quote_last_update, "n_books_clean": "", "quality": "|".join(l.quality), **base})
    cards = hp_cards + pe_cards
    counts["legs_stored"], counts["cards_stored"] = len(leg_rows), len(cards)
    diag = exposure_diagnostics(cards)
    eq = [json.loads(r["equal_capital_json"]) for r in pe_cards if r["equal_capital_json"]]
    diag["equal_capital_pos_ev_multis"] = {
        "n": len(eq), "assumptions": EQUAL_CAPITAL_ASSUMPTIONS,
        "card_better_growth_by_stake": {str(s): sum(1 for e in eq for x in e if x["stake_fraction"] == s and x["better_growth"] == "CARD")
                                        for s in cfg.equal_capital_stakes}}
    if counts["validated_events"] > 0 and counts["price_rows_in_scan"] == 0:
        status = INPUT_INVALID                         # probabilities without the same scan's prices: a data fault, not zero
    elif counts["validated_events"] == 0 or counts["legs_clean"] == 0:
        status = OK_ZERO
    else:
        status = OK
    if status == INPUT_INVALID or len(leg_rows) + len(cards) > cfg.max_rows_per_scan:
        status = status if status == INPUT_INVALID else CAP_EXCEEDED
        leg_rows, cards = [], []
    for c in cards:
        c.pop("_legs", None)
    for c in hp_cards + pe_cards:
        c.pop("_legs", None)
    return {"status": status, "counts": counts, "legs": leg_rows, "cards": cards, "diagnostics": diag}


EQUAL_CAPITAL_ASSUMPTIONS = (
    "One period; total stake s (fraction of the bankroll at the start of the period) on the card vs s/k on each of the "
    "same k legs as singles placed at the same time; leg outcomes independent; model P treated as the true P; each leg "
    "win or lose (no voids, dead heats or partial settlement); no rebalancing between legs; indicative same-book prices; "
    "log utility. Hypothetical, NOT evidence of live profitability.")


# ---------------------------------------------------------------- append-only research store (write guard)
class ShadowStore:
    """The ONLY writer. Every path must resolve inside `root` (the research output directory)."""

    def __init__(self, root: Path):
        self.root = root.resolve()

    def path(self, name: str) -> Path:
        p = (self.root / name).resolve()
        if self.root not in p.parents and p != self.root:
            raise PermissionError(f"research store refuses to write outside {self.root}: {p}")
        return p

    def read(self, name: str) -> list[dict]:
        p = self.path(name)
        if not p.exists():
            return []
        with p.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def append_unique(self, name: str, fields: list[str], key: str, rows: list[dict]) -> int:
        p = self.path(name)
        existing = {r[key] for r in self.read(name)}
        before = p.read_bytes() if p.exists() else b""
        new = []
        for r in rows:
            if r[key] not in existing:
                existing.add(r[key])
                new.append({f: r.get(f, "") for f in fields})
        if new:
            p.parent.mkdir(parents=True, exist_ok=True)
            header = not p.exists()
            with p.open("a", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=fields)
                if header:
                    w.writeheader()
                w.writerows(new)
            if not p.read_bytes().startswith(before):
                raise RuntimeError(f"immutability violation in {p}")
        return len(new)

    def read_all(self, name: str) -> list[dict]:
        """Concatenate `<YYYY-MM>/<name>` across monthly shards (sorted)."""
        rows: list[dict] = []
        for d in sorted(q for q in self.root.glob("*/") if q.is_dir()):
            rows += self.read(f"{d.name}/{name}")
        return rows

    def append_jsonl(self, name: str, obj: dict) -> None:
        p = self.path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        before = p.read_bytes() if p.exists() else b""
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, sort_keys=True, default=str) + "\n")
        if not p.read_bytes().startswith(before):
            raise RuntimeError(f"immutability violation in {p}")


def scan_record(status: str, reason: str, scan: str, mode: str, logged_at: datetime, prov: dict, cfg: ShadowConfig,
                counts: dict | None = None, legs: int = 0, cards: int = 0, engines: str = "") -> dict:
    return {"record_id": h16("scanrec", cfg.rule_version, scan, mode, prov.get("run_id", ""), status),
            "status": status, "failure_reason": reason, "scan": scan, "mode": mode, "logged_at": logged_at.isoformat(),
            "run_id": prov.get("run_id", ""), "commit_sha": prov.get("commit_sha", ""), "trigger": prov.get("trigger", ""),
            "workflow_start": prov.get("workflow_start", ""), "production_tests": prov.get("production_tests", ""),
            "rule_version": cfg.rule_version, "config_sha": cfg.config_sha, "bsv2_rule_version": cfg.bsv2_rule_version,
            "engines": engines, "input_shas": json.dumps(prov.get("input_shas", {}), sort_keys=True),
            "counts_json": json.dumps(counts or {}, sort_keys=True, default=str), "legs_logged": legs, "cards_logged": cards}


def select_scan(prob_rows: list[dict], workflow_start: datetime | None, now: datetime,
                cfg: ShadowConfig) -> tuple[str | None, str]:
    """The scan this run produced: the latest scan timestamp at/after the workflow start. Never an older scan."""
    scans = sorted({r["scan_timestamp_utc"] for r in prob_rows if r.get("scan_timestamp_utc")})
    if workflow_start is not None:
        scans = [s for s in scans if ts(s) >= workflow_start - timedelta(minutes=1)]
    if not scans:
        return None, NO_SCAN
    s = scans[-1]
    if now - ts(s) > timedelta(minutes=cfg.max_scan_to_log_minutes):
        return s, LATE
    return s, OK


def run_shadow(repo: Path, cfg: ShadowConfig, store: ShadowStore, now: datetime, prov: dict, mode: str,
               cal_se: Callable[[float], float], workflow_start: datetime | None, scan_override: str | None = None) -> dict:
    """Log the scan produced by this run. Always writes exactly one scan record (success or explicit failure) unless
    the scan was already logged successfully (idempotent rerun -> nothing written)."""
    scan = ""

    def shard(name: str) -> str:              # monthly shards keep every file far below GitHub's 50/100 MB limits
        return f"{(scan or now.isoformat())[:7]}/{name}"
    try:
        pf, qf = repo / cfg.inputs["probabilities"], repo / cfg.inputs["prices"]
        if not pf.exists() or not qf.exists():
            rec = scan_record(INPUT_MISSING, f"missing: {[str(p.name) for p in (pf, qf) if not p.exists()]}", "", mode, now, prov, cfg)
            store.append_unique(shard("scan_runs.csv"), SCAN_FIELDS, "record_id", [rec])
            return rec
        prob, price = read_csv(pf), read_csv(qf)
        prov = {**prov, "input_shas": {"probabilities": file_sha(pf), "prices": file_sha(qf),
                                       "calibration": file_sha(repo / cfg.inputs["calibration_results"])}}
        if scan_override:
            scan, st = scan_override, OK
        else:
            s, st = select_scan(prob, workflow_start, now, cfg)
            scan = s or ""
            if st == NO_SCAN and workflow_start is not None and any(
                    r.get("scan_timestamp_utc") and ts(r["scan_timestamp_utc"]) >= workflow_start - timedelta(minutes=1) for r in price):
                rec = scan_record(INPUT_INVALID, "prices written this run but no same-scan probabilities", "", mode, now, prov, cfg)
                store.append_unique(shard("scan_runs.csv"), SCAN_FIELDS, "record_id", [rec])
                return rec
        if st in (NO_SCAN, LATE):
            rec = scan_record(st, "no scan at/after workflow start" if st == NO_SCAN else "scan older than max_scan_to_log_minutes",
                              scan, mode, now, prov, cfg)
            store.append_unique(shard("scan_runs.csv"), SCAN_FIELDS, "record_id", [rec])
            return rec
        if any(r["scan"] == scan and r["mode"] == mode and r["status"] in SUCCESS_STATUSES for r in store.read(shard("scan_runs.csv"))):
            return {"status": "ALREADY_LOGGED", "scan": scan}
        for col in ("scan_timestamp_utc", "event_id", "player_a", "player_b", "p_a", "source_validated", "commence_time"):
            if prob and col not in prob[0]:
                raise KeyError(f"probability file lacks column {col}")
        res = process_scan(prob, price, scan, now, cfg, cal_se)
        engines = "|".join(sorted({engine_of(r["sport_key"]) for r in prob if r.get("scan_timestamp_utc") == scan}))
        reason = {CAP_EXCEEDED: "rows > max_rows_per_scan", INPUT_INVALID: "no same-scan price rows"}.get(res["status"], "")
        rec = scan_record(res["status"], reason, scan, mode, now,
                          prov, cfg, res["counts"], len(res["legs"]), len(res["cards"]), engines)
        for r in res["legs"]:
            r["record_id"] = rec["record_id"]
        for r in res["cards"]:
            r["record_id"], r["scan"], r["rule_version"] = rec["record_id"], scan, cfg.rule_version
        store.append_unique(shard("legs.csv"), LEG_FIELDS, "leg_id", res["legs"])
        store.append_unique(shard("cards.csv"), CARD_FIELDS, "card_id", res["cards"])
        store.append_jsonl(shard("scan_diagnostics.jsonl"), {"record_id": rec["record_id"], "scan": scan, **res["diagnostics"]})
        store.append_unique(shard("scan_runs.csv"), SCAN_FIELDS, "record_id", [rec])   # written LAST: success only when all data landed
        return rec
    except Exception as exc:  # research failure is recorded explicitly, never as a zero-card scan
        rec = scan_record(FAILED, f"{type(exc).__name__}: {exc}"[:300], scan, mode, now, prov, cfg)
        try:
            store.append_unique(shard("scan_runs.csv"), SCAN_FIELDS, "record_id", [rec])
        except Exception:
            pass
        return rec


def read_csv(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def file_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else ""


def asdict_leg(l: C.Leg) -> dict:
    return asdict(l)
