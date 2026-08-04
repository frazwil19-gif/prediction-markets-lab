"""End-to-end test of the corrected scripts/generate_daily_shortlist.py.

Proves the fixed pipeline genuinely removes bookmaker margin before
building consensus, by checking the report reflects the lower,
margin-free probability rather than the higher raw implied probability
that the old (buggy) version would have used.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "generate_daily_shortlist.py"


def test_daily_shortlist_uses_margin_free_probability_not_raw_implied(tmp_path: Path):
    odds_csv = tmp_path / "odds.csv"
    odds_csv.write_text(
        "market_id,selection,bookmaker,decimal_odds\n"
        "M-FB-001,home,Bookmaker A,2.10\n"
        "M-FB-001,draw,Bookmaker A,3.40\n"
        "M-FB-001,away,Bookmaker A,3.60\n"
        "M-FB-001,home,Bookmaker B,2.05\n"
        "M-FB-001,draw,Bookmaker B,3.50\n"
        "M-FB-001,away,Bookmaker B,3.75\n"
    )
    exchange_csv = tmp_path / "exchange.csv"
    exchange_csv.write_text(
        "market_id,exchange,selection,decimal_odds,available_size_gbp,commission,notes\n"
        "M-FB-001,Smarkets,home,2.20,150.00,0.02,\n"
    )
    out_dir = tmp_path / "reports"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--odds",
            str(odds_csv),
            "--exchange",
            str(exchange_csv),
            "--outcomes",
            "home",
            "draw",
            "away",
            "--sport",
            "football",
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr

    reports = list(out_dir.glob("*.md"))
    assert len(reports) == 1
    report_text = reports[0].read_text()

    # Raw implied probability for home from Bookmaker A alone would be
    # 1/2.10 = 0.4762 (47.6%), which is higher than the true margin-free
    # figure. If the bug were still present (raw implied probability
    # treated as consensus), net EV against 2.20 odds would show a much
    # stronger positive edge. The corrected, margin-free consensus is
    # lower, so this market must NOT be recommended as a live bet
    # (Grade A/A+) -- it should land as a low-grade watch/paper item or
    # be rejected outright.
    assert "M-FB-001" in report_text
    assert "BET:" not in report_text
    assert "Grade A+: 0" in report_text
    assert "Grade A: 0" in report_text


def test_daily_shortlist_reports_incomplete_bookmaker_rejection(tmp_path: Path):
    odds_csv = tmp_path / "odds.csv"
    odds_csv.write_text(
        "market_id,selection,bookmaker,decimal_odds\n"
        "M-FB-002,home,Bookmaker A,2.10\n"
        "M-FB-002,draw,Bookmaker A,3.40\n"
        "M-FB-002,away,Bookmaker A,3.60\n"
        "M-FB-002,home,Bookmaker B,2.05\n"
        "M-FB-002,draw,Bookmaker B,3.50\n"
        # Bookmaker B is missing "away" -- must be excluded, not silently used.
    )
    exchange_csv = tmp_path / "exchange.csv"
    exchange_csv.write_text(
        "market_id,exchange,selection,decimal_odds,available_size_gbp,commission,notes\n"
        "M-FB-002,Smarkets,home,2.20,150.00,0.02,\n"
    )
    out_dir = tmp_path / "reports"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--odds",
            str(odds_csv),
            "--exchange",
            str(exchange_csv),
            "--outcomes",
            "home",
            "draw",
            "away",
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "excluded from M-FB-002 consensus" in result.stderr
    assert "Bookmaker B" in result.stderr
