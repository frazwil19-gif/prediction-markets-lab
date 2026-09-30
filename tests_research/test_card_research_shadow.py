"""V2-7 prospective shadow (cer-2) tests. Offline; no network; never touches production ledgers.

Kept OUTSIDE tests/ on purpose: the production workflow's `pytest -q` gate collects tests/ only, so a research test
failure can never block the production tennis board. The shadow workflow step runs these first and records
RESEARCH_TESTS_FAILED explicitly if any fails.
"""
from __future__ import annotations

import csv
import itertools
import json
import math
import shutil
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from prediction_markets_lab.card_engine import cards as C
from prediction_markets_lab.card_engine import shadow as S
from prediction_markets_lab.card_engine import shadow_settle as SS

REPO = Path(__file__).resolve().parents[1]
SCAN = "2026-10-02T06:40:00+00:00"
LATER = "2026-10-02T15:40:00+00:00"
NOW = datetime(2026, 10, 2, 6, 45, tzinfo=timezone.utc)
WS = datetime(2026, 10, 2, 6, 35, tzinfo=timezone.utc)
CAL = lambda p: 0.011   # noqa: E731
PROB_COLS = ["scan_timestamp_utc", "sport_key", "event_id", "player_a", "player_b", "commence_time", "source",
             "source_validated", "p_a", "p_b", "raw_prices", "exchange_spread_prob"]
PRICE_COLS = ["scan_timestamp_utc", "sport_key", "event_id", "player_a", "player_b", "bookmaker", "market", "odds_a", "odds_b",
              "last_update"]


# ---------------------------------------------------------------- fixtures
def prob(ev, pa, scan=SCAN, a=None, b=None, width="0.01", validated="True", start="2026-10-02T12:00:00+00:00", sk="tennis_wta_x"):
    return {"scan_timestamp_utc": scan, "sport_key": sk, "event_id": ev, "player_a": a or f"A{ev}", "player_b": b or f"B{ev}",
            "commence_time": start, "source": "EXCHANGE_MID", "source_validated": validated, "p_a": str(pa),
            "p_b": str(round(1 - pa, 6)), "raw_prices": "", "exchange_spread_prob": width}


def price(ev, book, oa, ob="3.0", scan=SCAN, a=None, b=None, lu="2026-10-02T06:39:00+00:00"):
    return {"scan_timestamp_utc": scan, "sport_key": "tennis_wta_x", "event_id": ev, "player_a": a or f"A{ev}",
            "player_b": b or f"B{ev}", "bookmaker": book, "market": "h2h", "odds_a": str(oa), "odds_b": str(ob), "last_update": lu}


def write_csv(p: Path, cols, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


@pytest.fixture
def repo(tmp_path):
    """Minimal isolated repo copy: configs + calibration results + synthetic same-scan inputs."""
    for rel in ("config/card_research_shadow.yaml", "config/bet_selection_v2.yaml",
                "research/platform_v2/card_engine_v2_7/RESULTS.json"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / rel, tmp_path / rel)
    c = yaml.safe_load((tmp_path / "config/card_research_shadow.yaml").read_text())
    c["logging_enabled"] = c["settlement_enabled"] = True
    (tmp_path / "config/card_research_shadow.yaml").write_text(yaml.safe_dump(c))
    probs = [prob("e1", 0.80), prob("e2", 0.75), prob("e3", 0.72), prob("e4", 0.60), prob("e5", 0.30)]
    prices = [price(e, bk, o) for e, o in (("e1", 1.2), ("e2", 1.3), ("e3", 1.35), ("e4", 1.80)) for bk in ("bk1", "bk2")]
    prices += [price("e5", "bk1", "3.0", "1.60"), price("e1", "betfair_ex_uk", 1.25)]
    write_csv(tmp_path / "tennis_predictions/exchange_probability_snapshots.csv", PROB_COLS, probs)
    write_csv(tmp_path / "tennis_predictions/price_snapshots.csv", PRICE_COLS, prices)
    return tmp_path


def cfg_of(repo: Path, **over) -> S.ShadowConfig:
    cfg = S.load_config(repo / "config/card_research_shadow.yaml", repo)
    return S.ShadowConfig(**{**cfg.__dict__, **over})


def run(repo, cfg=None, now=NOW, ws=WS, scan_override=None):
    cfg = cfg or cfg_of(repo)
    store = S.ShadowStore(repo / cfg.output_dir)
    return S.run_shadow(repo, cfg, store, now, {"run_id": "r1", "commit_sha": "abc"}, "PROSPECTIVE", CAL, ws,
                        scan_override), store


def tree(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


# ---------------------------------------------------------------- config and quality parity with bsv2-3
def test_shipped_config_quality_equals_deployed_bsv2_and_is_not_weaker():
    cfg = S.load_config(REPO / "config/card_research_shadow.yaml", REPO)
    bs = yaml.safe_load((REPO / "config/bet_selection_v2.yaml").read_text())
    assert cfg.max_exchange_spread_prob == bs["data_quality"]["max_exchange_spread_prob"]
    assert cfg.max_quote_age_minutes == bs["decision_gates"]["paper_bet"]["max_price_age_minutes"]
    assert cfg.treble_sample_rate == 0.10 and cfg.high_p_log_k == (1, 2)


def test_weaker_quality_rule_is_refused(repo):
    p = repo / "config/card_research_shadow.yaml"
    c = yaml.safe_load(p.read_text())
    c["quality"]["max_exchange_spread_prob"] = 0.05
    p.write_text(yaml.safe_dump(c))
    with pytest.raises(ValueError):
        S.load_config(p, repo)


# ---------------------------------------------------------------- same-scan alignment, staleness, quality
def test_same_scan_alignment_ignores_other_scans_prices_and_probs():
    cfg = cfg_of_default()
    probs = [prob("e1", 0.8), prob("e1", 0.9, scan=LATER)]
    prices = [price("e1", "bk1", 1.2), price("e1", "bk1", 9.9, scan=LATER)]
    legs, counts = S.load_scan_legs(probs, prices, SCAN, NOW, cfg)
    assert len(legs) == 1 and legs[0].odds == 1.2 and legs[0].p == pytest.approx(0.8)
    assert counts["prob_rows_in_scan"] == 1 and counts["price_rows_in_scan"] == 1


def cfg_of_default() -> S.ShadowConfig:
    return S.load_config(REPO / "config/card_research_shadow.yaml", REPO)


def test_stale_untimed_future_quotes_and_started_events_are_rejected():
    cfg = cfg_of_default()
    q = lambda **kw: S.load_scan_legs([prob("e1", 0.8, **{k: v for k, v in kw.items() if k == "start"})],  # noqa: E731
                                      [price("e1", "bk1", 1.2, **{k: v for k, v in kw.items() if k == "lu"})], SCAN, NOW, cfg)[0][0].quality
    assert q() == ()
    assert "QUOTE_STALE_OR_UNTIMED" in q(lu="2026-10-02T02:39:00+00:00")        # 241 min old
    assert "QUOTE_STALE_OR_UNTIMED" in q(lu="")
    assert "QUOTE_STALE_OR_UNTIMED" in q(lu="2026-10-02T07:40:00+00:00")        # future-dated quote
    assert "EVENT_STARTED" in q(start="2026-10-02T06:00:00+00:00")
    assert "STARTED_BEFORE_LOGGING" in q(start="2026-10-02T06:42:00+00:00")     # after scan, before logging: not prospective


def test_width_rules_and_validation_and_duplicates():
    cfg = cfg_of_default()
    legs, c = S.load_scan_legs([prob("e1", 0.8, width="0.031"), prob("e2", 0.8, width=""), prob("e3", 0.8, validated="False"),
                                prob("e4", 0.8), prob("e4", 0.8)],
                               [price(e, "bk1", 1.2) for e in ("e1", "e2", "e3", "e4")], SCAN, NOW, cfg)
    q = {l.event_id: l.quality for l in legs}
    assert q["e1"] == ("EXCHANGE_BOOK_TOO_WIDE",) and q["e2"] == ("EXCHANGE_WIDTH_UNKNOWN",) and "e3" not in q
    assert c["duplicate_event_rows"] == 1 and sum(l.event_id == "e4" for l in legs) == 1


def test_exchange_prices_never_become_legs():
    cfg = cfg_of_default()
    legs, c = S.load_scan_legs([prob("e1", 0.8)], [price("e1", b, 1.3) for b in ("betfair_ex_uk", "matchbook", "smarkets")],
                               SCAN, NOW, cfg)
    assert legs == [] and c["exchange_quotes_skipped"] == 3


# ---------------------------------------------------------------- joint probability / EV / same-book
def test_pos_ev_cards_are_same_book_with_correct_joint_math(repo):
    cfg = cfg_of(repo)
    legs, _ = S.load_scan_legs([prob("e1", 0.6), prob("e2", 0.7)],
                               [price("e1", "bk1", 1.8), price("e2", "bk1", 1.5), price("e1", "bk2", 1.8), price("e2", "bk2", 1.3)],
                               SCAN, NOW, cfg)
    cards, counts, _ = S.build_pos_ev(legs, cfg, CAL)
    dbl = [c for c in cards if c["k"] == 2]
    assert len(dbl) == 1 and dbl[0]["book"] == "bk1"                                   # bk2's e2 leg is -EV: no bk2 double
    assert dbl[0]["p_joint"] == pytest.approx(0.42) and dbl[0]["odds_indicative"] == pytest.approx(2.7)
    assert dbl[0]["ev"] == pytest.approx(0.42 * 2.7 - 1)
    assert "ODDS_INDICATIVE_NOT_EXECUTION_VERIFIED" in dbl[0]["reasons"]
    eq = json.loads(dbl[0]["equal_capital_json"])
    assert [e["stake_fraction"] for e in eq] == list(cfg.equal_capital_stakes)


def test_high_p_price_summary_uses_only_books_pricing_every_leg(repo):
    cfg = cfg_of(repo)
    legs, _ = S.load_scan_legs([prob("e1", 0.8), prob("e2", 0.75)],
                               [price("e1", "bk1", 1.2), price("e2", "bk1", 1.3), price("e1", "bk2", 1.25)], SCAN, NOW, cfg)
    cards, _, _ = S.build_high_p(legs, cfg, CAL)
    d = [c for c in cards if c["k"] == 2][0]
    assert d["n_books_priced"] == 1 and d["best_book"] == "bk1" and d["odds_median"] == pytest.approx(1.2 * 1.3)
    assert d["p_joint"] == pytest.approx(0.6) and d["book"] == "*"


def test_unknown_dependence_same_participant_has_no_joint_p(repo):
    cfg = cfg_of(repo)
    legs, _ = S.load_scan_legs([prob("e1", 0.8, a="Sam", b="Bo"), prob("e2", 0.8, a="Sam", b="Cy")],
                               [price("e1", "bk1", 1.2, a="Sam", b="Bo"), price("e2", "bk1", 1.2, a="Sam", b="Cy")], SCAN, NOW, cfg)
    cards, counts, _ = S.build_high_p(legs, cfg, CAL)
    d = [c for c in cards if c["k"] == 2][0]
    assert d["status"] == "RESEARCH_ONLY_UNVERIFIED" and d["p_joint"] == "" and "SAME_PARTICIPANT" in d["dependence_flags"]
    assert counts["dependence_unverified"][2] == 1


# ---------------------------------------------------------------- deterministic sampling
def test_treble_sampling_is_fixed_reproducible_and_price_independent():
    salt = "cer-2|HIGH_P|k3|2026-09-30"
    assert S.sample_unit("e1:A;e2:B;e3:C", salt) == S.sample_unit("e1:A;e2:B;e3:C", salt)
    assert S.legset_key([("e3", "C"), ("e1", "A"), ("e2", "B")]) == "e1:A;e2:B;e3:C"
    keys = [S.legset_key([(f"e{i}", "x"), (f"e{j}", "y"), (f"e{k}", "z")]) for i, j, k in itertools.combinations(range(40), 3)]
    frac = sum(S.sample_unit(k, salt) < 0.10 for k in keys) / len(keys)
    assert 0.085 < frac < 0.115                                                        # 9,880 keys: ~10%
    assert S.sample_unit("e1:A;e2:B;e3:C", salt) != S.sample_unit("e1:A;e2:B;e3:C", salt + "x")


def test_sampled_trebles_identical_across_reruns_order_and_odds(repo):
    cfg = cfg_of(repo)
    probs = [prob(f"e{i}", 0.70 + i * 0.01) for i in range(12)]
    pr1 = [price(f"e{i}", "bk1", 1.3) for i in range(12)]
    pr2 = [price(f"e{i}", "bk1", 1.1 + i * 0.02) for i in reversed(range(12))]      # different odds, reversed order
    a = S.build_high_p(S.load_scan_legs(probs, pr1, SCAN, NOW, cfg)[0], cfg, CAL)
    b = S.build_high_p(S.load_scan_legs(list(reversed(probs)), pr2, SCAN, NOW, cfg)[0], cfg, CAL)
    ids = lambda r: sorted(c["card_id"] for c in r[0] if c["k"] == 3)                  # noqa: E731
    assert ids(a) == ids(b) and a[1]["enumerated"][3] == 220
    assert a[1]["logged"][3] + a[1]["sampling_excluded"][3] == 220
    assert all(c["sample_weight"] == 10.0 for c in a[0] if c["k"] == 3)
    assert a[1]["logged"][2] == 66 and a[1]["logged"][1] == 12                          # singles + doubles complete


# ---------------------------------------------------------------- end-to-end run, append-only, idempotency
def test_run_logs_this_runs_scan_and_rerun_is_idempotent(repo):
    rec, store = run(repo)
    assert rec["status"] == S.OK and rec["cards_logged"] > 0 and rec["run_id"] == "r1" and rec["commit_sha"] == "abc"
    assert rec["config_sha"] and rec["bsv2_rule_version"] == "bsv2-3" and json.loads(rec["input_shas"])["prices"]
    before = tree(store.root)
    again, _ = run(repo)
    assert again["status"] == "ALREADY_LOGGED" and tree(store.root) == before
    cards = store.read_all("cards.csv")
    assert len({c["card_id"] for c in cards}) == len(cards)
    assert {c["cohort"] for c in cards} == {"HIGH_P", "POS_EV"}
    assert all(c["rule_version"] == "cer-2" and c["record_id"] == rec["record_id"] for c in cards)
    legs = store.read_all("legs.csv")
    assert {l["book"] for l in legs if l["event_id"] == "e1"} == {"*"}                 # HIGH_P legs stored at event level
    assert all(l["book"] != "*" and float(l["ev"]) > 0 for l in legs if l["event_id"] == "e4")


def test_append_only_guard_detects_rewrite(tmp_path):
    st = S.ShadowStore(tmp_path)
    st.append_unique("m/x.csv", ["k", "v"], "k", [{"k": "1", "v": "a"}])
    assert st.append_unique("m/x.csv", ["k", "v"], "k", [{"k": "1", "v": "CHANGED"}]) == 0     # never overwrites
    assert st.read("m/x.csv") == [{"k": "1", "v": "a"}]


# ---------------------------------------------------------------- missing / partial / failed / late scans
def test_no_scan_this_run_is_explicit_not_zero(repo):
    rec, store = run(repo, ws=datetime(2026, 10, 2, 7, 0, tzinfo=timezone.utc))
    assert rec["status"] == S.NO_SCAN and store.read_all("cards.csv") == []
    assert store.read_all("scan_runs.csv")[0]["status"] == S.NO_SCAN


def test_late_scan_is_not_backfilled(repo):
    rec, store = run(repo, now=NOW + timedelta(hours=3))
    assert rec["status"] == S.LATE and store.read_all("cards.csv") == []


def test_missing_input_file_recorded(repo):
    (repo / "tennis_predictions/price_snapshots.csv").unlink()
    rec, store = run(repo)
    assert rec["status"] == S.INPUT_MISSING and store.read_all("scan_runs.csv")[0]["status"] == S.INPUT_MISSING


def test_probabilities_without_same_scan_prices_is_invalid_not_zero(repo):
    write_csv(repo / "tennis_predictions/price_snapshots.csv", PRICE_COLS, [price("e1", "bk1", 1.2, scan="2026-10-01T06:40:00+00:00")])
    rec, store = run(repo)
    assert rec["status"] == S.INPUT_INVALID and store.read_all("cards.csv") == []


def test_prices_without_probabilities_is_invalid(repo):
    write_csv(repo / "tennis_predictions/exchange_probability_snapshots.csv", PROB_COLS,
              [prob("e1", 0.8, scan="2026-10-01T06:40:00+00:00")])
    rec, _ = run(repo)
    assert rec["status"] == S.INPUT_INVALID


def test_genuinely_empty_scan_is_ok_zero(repo):
    write_csv(repo / "tennis_predictions/exchange_probability_snapshots.csv", PROB_COLS, [prob("e1", 0.8, validated="False")])
    rec, _ = run(repo)
    assert rec["status"] == S.OK_ZERO


def test_exception_is_recorded_as_failure_with_no_partial_success(repo):
    bad = {**prob("e1", 0.8), "p_a": "not-a-number"}
    write_csv(repo / "tennis_predictions/exchange_probability_snapshots.csv", PROB_COLS, [bad])
    rec, store = run(repo)
    assert rec["status"] == S.FAILED and "ValueError" in rec["failure_reason"]
    assert store.read_all("cards.csv") == [] and [r["status"] for r in store.read_all("scan_runs.csv")] == [S.FAILED]


def test_disabled_flag_writes_nothing(repo):
    from scripts_loader import load_cli
    cli = load_cli()
    p = repo / "config/card_research_shadow.yaml"
    c = yaml.safe_load(p.read_text())
    c["logging_enabled"] = False
    p.write_text(yaml.safe_dump(c))
    cli.REPO = repo
    assert cli.main(["log", "--config", str(p)]) == 0
    assert not (repo / c["output_dir"]).exists()


# ---------------------------------------------------------------- output-size bounds
def test_row_cap_fails_closed_with_counts(repo):
    rec, store = run(repo, cfg=cfg_of(repo, max_rows_per_scan=3))
    assert rec["status"] == S.CAP_EXCEEDED and store.read_all("cards.csv") == [] and json.loads(rec["counts_json"])["cards_stored"] > 0


def test_pos_ev_card_cap_keeps_singles_and_counts_dropped(repo):
    cfg = cfg_of(repo, pos_ev_max_cards_per_scan=3)
    legs, _ = S.load_scan_legs([prob(f"e{i}", 0.6) for i in range(4)], [price(f"e{i}", "bk1", 1.9) for i in range(4)], SCAN, NOW, cfg)
    cards, counts, _ = S.build_pos_ev(legs, cfg, CAL)
    assert {c["k"] for c in cards} == {1} and counts["dropped_by_card_cap"] == {1: 0, 2: 6, 3: 4}
    assert counts["anomaly"] == "POS_EV_CARD_CAP_EXCEEDED_SINGLES_ONLY"


def test_high_p_event_cap_counts_truncation(repo):
    cfg = cfg_of(repo, high_p_max_events=3)
    legs, _ = S.load_scan_legs([prob(f"e{i}", 0.71 + i / 100) for i in range(5)], [price(f"e{i}", "bk1", 1.2) for i in range(5)],
                               SCAN, NOW, cfg)
    _, counts, _ = S.build_high_p(legs, cfg, CAL)
    assert counts["eligible_events"] == 5 and counts["kept_events"] == 3 and counts["truncated_events"] == 2


def test_worst_case_rows_per_scan_bounded_by_config():
    cfg = cfg_of_default()
    n = cfg.high_p_max_events
    worst_high_p = n + math.comb(n, 2) + math.comb(n, 3)          # upper bound before sampling
    assert n + math.comb(n, 2) + 0.2 * math.comb(n, 3) < cfg.max_rows_per_scan   # expected with a 10% sample, generous margin
    assert worst_high_p > 0 and cfg.max_rows_per_scan <= 3000


# ---------------------------------------------------------------- production isolation / failure containment / no API
def test_store_refuses_paths_outside_research_dir(tmp_path):
    st = S.ShadowStore(tmp_path / "research_out")
    for bad in ("../tennis_predictions/ledger_predictions.csv", "/tmp/x.csv", "../../paper_betting_v2/x.csv"):
        with pytest.raises(PermissionError):
            st.append_unique(bad, ["k"], "k", [{"k": "1"}])


def test_run_changes_only_the_research_directory(repo):
    before = tree(repo)
    rec, store = run(repo)
    after = tree(repo)
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    out = str(Path(cfg_of(repo).output_dir))
    assert changed and all(k.startswith(out + "/") for k in changed)


def test_no_network_during_run(repo, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    rec, _ = run(repo)
    assert rec["status"] == S.OK


def test_research_sources_have_no_api_client_or_production_writer():
    src = "".join(p.read_text() for p in (REPO / "src/prediction_markets_lab/card_engine").glob("*.py"))
    src += (REPO / "scripts/run_card_shadow.py").read_text()
    for forbidden in ("requests", "urllib", "http.client", "THE_ODDS_API_KEY", "odds_api", "paper_betting_v2",
                      "record_selections", "unified_ledger", "append_predictions", "append_settlements"):
        assert forbidden not in src, forbidden


def test_workflow_step_is_last_isolated_and_keyless():
    wf = yaml.safe_load((REPO / ".github/workflows/tennis_prediction_board.yml").read_text())
    steps = wf["jobs"]["tennis"]["steps"]
    names = [s.get("name", "") for s in steps]
    i_shadow = next(i for i, n in enumerate(names) if n.startswith("V2-7 research card shadow"))
    i_commit = names.index("Commit tennis prediction artefacts")
    sh = steps[i_shadow]
    assert i_shadow == len(steps) - 1 and i_shadow > i_commit
    assert sh["continue-on-error"] is True and sh["if"] == "always()" and sh["timeout-minutes"] <= 5
    assert "THE_ODDS_API_KEY" not in json.dumps(sh)
    assert 'git add -- "$OUT"' in sh["run"] and "git add tennis_predictions" not in sh["run"]
    assert "prospective" not in steps[i_commit]["run"] and "card_engine_v2_7" not in steps[i_commit]["run"]
    for s in steps[:i_shadow]:                                           # no production step references the research code
        assert "run_card_shadow" not in json.dumps(s) and "tests_research" not in json.dumps(s)


def test_production_pytest_gate_does_not_collect_research_tests():
    cfg = (REPO / "pyproject.toml").read_text()
    assert 'testpaths = ["tests"]' in cfg and not (REPO / "tests/unit/test_card_engine.py").exists()


# ---------------------------------------------------------------- exposure aggregation / effective sample size
def test_card_correlation_matches_brute_force():
    a = (("e1", "x", 0.6), ("e2", "y", 0.7))
    b = (("e2", "y", 0.7), ("e3", "z", 0.8))
    ps = {"e1": 0.6, "e2": 0.7, "e3": 0.8}
    pa, pb, pab = 0.0, 0.0, 0.0
    for w in itertools.product((0, 1), repeat=3):
        pr = math.prod(ps[e] if wi else 1 - ps[e] for e, wi in zip(("e1", "e2", "e3"), w))
        wa, wb = w[0] and w[1], w[1] and w[2]
        pa, pb, pab = pa + pr * wa, pb + pr * wb, pab + pr * (wa and wb)
    rho = (pab - pa * pb) / math.sqrt(pa * (1 - pa) * pb * (1 - pb))
    assert S.card_correlation(a, b) == pytest.approx(rho)
    assert S.card_correlation(a, (("e1", "OTHER", 0.4),)) < 0                          # opposite side of a shared match


def test_effective_n_identical_vs_disjoint():
    c = (("e1", "x", 0.6),)
    assert S.effective_n([(c, 1.0)] * 5) == pytest.approx(1.0)                          # same leg set at 5 books = 1 observation
    assert S.effective_n([((("e%d" % i, "x", 0.6),), 1.0) for i in range(5)]) == pytest.approx(5.0)


def test_exposure_diagnostics_counts_shared_matches(repo):
    rec, store = run(repo)
    d = json.loads((store.root / "2026-10/scan_diagnostics.jsonl").read_text().splitlines()[0])
    k2 = d["HIGH_P"]["k2"]
    # HIGH_P events: e1 .80, e2 .75, e3 .72, e5 (favourite B) .70 -> 6 doubles; 12 of 15 card pairs share a match
    assert k2["unique_matches"] == 4 and k2["cards_logged"] == 6 and k2["share_of_card_pairs_sharing_a_match"] == 0.8
    assert k2["effective_n_model_implied"] < k2["cards_logged"]
    assert "NOT independent" in d["note"] and d["equal_capital_pos_ev_multis"]["assumptions"]


# ---------------------------------------------------------------- settlement edge cases
def card(legs, cohort="POS_EV", leg_ids="", odds=""):
    return {"card_id": "c" + "".join(l[0] for l in legs) + cohort, "cohort": cohort, "k": len(legs), "leg_ids": leg_ids,
            "odds_indicative": odds, "legs_compact": json.dumps(legs)}


L1 = ["e1", "Ann", "Bea", "2026-10-02T10:00:00+00:00", 0.7]
L2 = ["e2", "Viktória Morvayová", "Cy", "2026-10-02T11:00:00+00:00", 0.7]
PREDS = [{"prediction_id": "p1", "event_id": "e1"}, {"prediction_id": "p2", "event_id": "e2"}]
T = datetime(2026, 10, 3, tzinfo=timezone.utc)


def st(pid, status, winner, score="6-4 6-4"):
    return {"prediction_id": pid, "status": status, "winner": winner, "score": score}


def test_settlement_waits_for_every_leg():
    rows, d = SS.settle_cards([card([L1, L2])], {}, PREDS, [st("p1", "SETTLED_INCORRECT", "Bea")], [], T, 7)
    assert rows == [] and d["pending"] == 1                                             # a lost leg alone does not settle


def test_settlement_accent_folded_names_and_won_lost():
    ok = [st("p1", "SETTLED_CORRECT", "Ann"), st("p2", "SETTLED_CORRECT", "Viktoria Morvayova")]
    rows, _ = SS.settle_cards([card([L1, L2])], {}, PREDS, ok, [], T, 7)
    assert rows[0]["status"] == "WON" and rows[0]["legs_won"] == 2
    lost = [st("p1", "SETTLED_CORRECT", "Ann"), st("p2", "SETTLED_CORRECT", "Cy")]
    assert SS.settle_cards([card([L1, L2])], {}, PREDS, lost, [], T, 7)[0][0]["status"] == "LOST"


def test_unmatched_winner_and_conflicts_never_settle():
    rows, d = SS.settle_cards([card([L1])], {}, PREDS, [st("p1", "SETTLED_CORRECT", "Zed Unknown")], [], T, 7)
    assert rows == [] and d["unmatched"] == 1
    preds = PREDS + [{"prediction_id": "p1b", "event_id": "e1"}]
    conflict = [st("p1", "SETTLED_CORRECT", "Ann"), st("p1b", "SETTLED_INCORRECT", "Bea")]
    rows, d = SS.settle_cards([card([L1])], {}, preds, conflict, [], T, 7)
    assert rows == [] and d["conflict"] == 1
    dup = [st("p1", "SETTLED_CORRECT", "Ann"), st("p1", "SETTLED_CORRECT", "Ann")]     # identical duplicate rows are fine
    assert SS.settle_cards([card([L1])], {}, PREDS, dup, [], T, 7)[0][0]["status"] == "WON"


def test_void_legs_postponement_and_overdue():
    legs_by_id = {"l1": {"event_id": "e1", "odds": "1.5"}, "l2": {"event_id": "e2", "odds": "1.4"}}
    c = card([L1, L2], leg_ids="l1|l2", odds="2.1")
    wv = [st("p1", "SETTLED_CORRECT", "Ann"), st("p2", "VOID", "Cy", "W/O")]
    r = SS.settle_cards([c], legs_by_id, PREDS, wv, [], T, 7)[0][0]
    assert r["status"] == "WON_REDUCED_VOID_LEG" and r["reduced_odds_indicative"] == pytest.approx(1.5)
    assert r["return_per_unit_indicative"] == pytest.approx(0.5) and "VOID_LEG_REDUCTION_BOOK_RULE_UNVERIFIED" in r["flags"]
    lv = [st("p1", "SETTLED_INCORRECT", "Bea"), st("p2", "VOID", "Cy", "W/O")]
    assert SS.settle_cards([c], legs_by_id, PREDS, lv, [], T, 7)[0][0]["status"] == "LOST"
    vv = [st("p1", "VOID", "", "W/O"), st("p2", "VOID", "", "W/O")]
    assert SS.settle_cards([c], legs_by_id, PREDS, vv, [], T, 7)[0][0]["return_per_unit_indicative"] == 0.0
    rows, d = SS.settle_cards([c], legs_by_id, PREDS, [], [], T + timedelta(days=9), 7)   # postponed / no result
    assert rows == [] and d["overdue_unsettled"] == 1


def test_retirement_flagged_and_duplicate_settlement_prevented_and_corrections_supersede():
    ret = [st("p1", "SETTLED_CORRECT", "Ann", "6-3 2-0 RET")]
    rows, _ = SS.settle_cards([card([L1])], {}, PREDS, ret, [], T, 7)
    assert "RETIREMENT_BOOK_RULE_UNVERIFIED" in rows[0]["flags"]
    again, d = SS.settle_cards([card([L1])], {}, PREDS, ret, rows, T, 7)
    assert again == [] and d["settled_new"] == 0                                       # rerun: no duplicate
    corrected = [st("p1", "SETTLED_INCORRECT", "Bea")]                                  # source corrected later (new ledger state)
    fix, d = SS.settle_cards([card([L1])], {}, PREDS, corrected, rows, T, 7)
    assert fix[0]["status"] == "LOST" and fix[0]["supersedes"] == rows[0]["settlement_id"] and d["superseded"] == 1


def test_end_to_end_settle_cli_on_logged_cards(repo):
    rec, store = run(repo)
    cards = store.read_all("cards.csv")
    evs = {r["event_id"] for r in store.read_all("legs.csv")}
    write_csv(repo / "tennis_predictions/ledger_predictions.csv", ["prediction_id", "event_id"],
              [{"prediction_id": f"p{e}", "event_id": e} for e in evs])
    fav = {r["event_id"]: r["selection"] for r in store.read_all("legs.csv")}
    write_csv(repo / "tennis_predictions/ledger_settlements.csv", ["prediction_id", "status", "winner", "score"],
              [st(f"p{e}", "SETTLED_CORRECT", fav[e]) for e in evs])
    from scripts_loader import load_cli
    cli = load_cli()
    cli.REPO = repo
    prod_before = tree(repo / "tennis_predictions")
    assert cli.main(["settle", "--config", str(repo / "config/card_research_shadow.yaml"), "--now", "2026-10-03T00:00:00+00:00"]) == 0
    sett = store.read_all("card_settlements.csv")
    assert len(sett) == len(cards) and all(s["status"] == "WON" for s in sett)
    assert cli.main(["settle", "--config", str(repo / "config/card_research_shadow.yaml"), "--now", "2026-10-03T01:00:00+00:00"]) == 0
    assert len(store.read_all("card_settlements.csv")) == len(cards)                   # idempotent
    assert tree(repo / "tennis_predictions") == prod_before                             # production inputs untouched


def test_attach_legs_fails_closed_when_a_leg_is_missing():
    legs = [{"record_id": "r", "event_id": "e1", "selection": "Ann", "opponent": "Bea", "start": "2026-10-02T10:00:00+00:00", "p": "0.7"}]
    ok, bad = SS.attach_legs([{"record_id": "r", "legset": "e1:Ann", "k": "1"}, {"record_id": "r", "legset": "e1:Ann;e2:Cy", "k": "2"},
                              {"record_id": "OTHER", "legset": "e1:Ann", "k": "1"}], legs)
    assert len(ok) == 1 and bad == 2 and json.loads(ok[0]["legs_compact"])[0][:3] == ["e1", "Ann", "Bea"]
