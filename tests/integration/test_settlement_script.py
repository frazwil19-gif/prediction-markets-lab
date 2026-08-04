"""End-to-end test of scripts/settle_results.py via subprocess.

Verifies the settlement math (stake, matched odds, commission) and
that the bets/bankroll CSVs are correctly updated, without needing to
restructure the script into an importable library module.
"""

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "settle_results.py"

BET_ROW = {
    "bet_id": "B-0001",
    "market_id": "M-FB-001",
    "bet_timestamp": "2026-08-03T09:00:00+00:00",
    "sport": "football",
    "competition": "Premier League",
    "event": "Arsenal vs Chelsea",
    "market": "pre_match_1x2",
    "selection": "home",
    "venue": "Smarkets",
    "requested_odds": "2.20",
    "matched_odds": "2.20",
    "stake": "0.25",
    "estimated_probability": "0.5",
    "implied_probability": "0.4545",
    "net_ev_at_entry": "0.05",
    "confidence_score": "High",
    "grade": "A",
    "bankroll_before": "10.00",
    "liability": "0.30",
    "result": "pending",
    "gross_profit": "0.0",
    "commission_paid": "0.0",
    "net_profit": "0.0",
    "bankroll_after": "",
    "closing_odds": "",
    "closing_probability": "",
    "clv": "",
    "notes": "",
}


def write_bets_csv(path: Path) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(BET_ROW.keys()))
        writer.writeheader()
        writer.writerow(BET_ROW)


def run_settle(bets_path: Path, bankroll_path: Path, result: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--bets",
            str(bets_path),
            "--bankroll",
            str(bankroll_path),
            "--bet-id",
            "B-0001",
            "--result",
            result,
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def test_settle_win_updates_bets_and_bankroll(tmp_path: Path):
    bets_path = tmp_path / "bets.csv"
    bankroll_path = tmp_path / "bankroll.csv"
    write_bets_csv(bets_path)

    result = run_settle(bets_path, bankroll_path, "win")
    assert result.returncode == 0, result.stderr

    with open(bets_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["result"] == "win"
    # gross profit = stake * (odds - 1) = 0.25 * 1.20 = 0.30
    assert float(rows[0]["gross_profit"]) == pytest_approx(0.30)
    # commission = 2% of gross profit = 0.006
    assert float(rows[0]["commission_paid"]) == pytest_approx(0.006)
    # net profit = 0.30 - 0.006 = 0.294
    assert float(rows[0]["net_profit"]) == pytest_approx(0.294)

    with open(bankroll_path, newline="") as f:
        ledger_rows = list(csv.DictReader(f))
    assert len(ledger_rows) == 1
    assert float(ledger_rows[0]["balance"]) == pytest_approx(10.294)


def test_settle_loss_reduces_bankroll(tmp_path: Path):
    bets_path = tmp_path / "bets.csv"
    bankroll_path = tmp_path / "bankroll.csv"
    write_bets_csv(bets_path)

    result = run_settle(bets_path, bankroll_path, "loss")
    assert result.returncode == 0, result.stderr

    with open(bankroll_path, newline="") as f:
        ledger_rows = list(csv.DictReader(f))
    assert float(ledger_rows[0]["balance"]) == pytest_approx(9.75)  # 10.00 - 0.25 stake


def test_settle_unknown_bet_id_fails_cleanly(tmp_path: Path):
    bets_path = tmp_path / "bets.csv"
    bankroll_path = tmp_path / "bankroll.csv"
    write_bets_csv(bets_path)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--bets",
            str(bets_path),
            "--bankroll",
            str(bankroll_path),
            "--bet-id",
            "DOES-NOT-EXIST",
            "--result",
            "win",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 1
    assert "no bet found" in result.stderr


def pytest_approx(value: float):
    import pytest

    return pytest.approx(value, abs=1e-6)
