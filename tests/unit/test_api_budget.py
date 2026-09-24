from datetime import datetime, timezone
from pathlib import Path

from prediction_markets_lab.ops.api_budget import check, load_budget, month_spend

REPO = Path(__file__).resolve().parents[2]
B = {"global_reserve_remaining": 75,
     "consumers": {"t": {"monthly_cap": 3, "min_remaining": 150}, "core": {"monthly_cap": 180}}}


def test_repo_budget_respects_limits() -> None:
    b = load_budget(REPO / "config" / "api_budget.json")
    total = sum(c["monthly_cap"] for c in b["consumers"].values())
    assert total <= b["monthly_target_max"]
    assert b["monthly_plan_limit"] - b["monthly_target_max"] >= b["global_reserve_remaining"]
    assert b["consumers"]["tennis_prediction_board"]["monthly_cap"] <= 120
    assert b["consumers"]["nba_prediction_board"]["monthly_cap"] <= 60


def test_month_spend_counts_only_current_month(tmp_path: Path) -> None:
    p = tmp_path / "log.csv"
    p.write_text("timestamp_utc,call,x_requests_used,x_requests_remaining,x_requests_last\n"
                 "2026-08-31T23:00:00+00:00,odds:a,1,1,5\n2026-09-01T00:00:00+00:00,sports_list,1,1,0\n"
                 "2026-09-23T20:00:00+00:00,odds:a,1,1,1\n2026-09-24T20:00:00+00:00,odds:b,1,1,\n")
    assert month_spend(p, datetime(2026, 9, 24, tzinfo=timezone.utc)) == 1
    assert month_spend(tmp_path / "missing.csv", datetime(2026, 9, 24, tzinfo=timezone.utc)) == 0


def test_cap_and_floor() -> None:
    assert check(B, "t", spent=2, remaining=400).allowed
    assert not check(B, "t", spent=3, remaining=400).allowed
    assert not check(B, "t", spent=0, remaining=150).allowed          # optional floor 150
    assert check(B, "core", spent=0, remaining=150).allowed           # core only needs 75
    assert not check(B, "core", spent=0, remaining=75).allowed
