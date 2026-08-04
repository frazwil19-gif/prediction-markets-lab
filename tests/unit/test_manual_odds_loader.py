from pathlib import Path

import pytest

from prediction_markets_lab.ingestion.manual_odds_loader import load_manual_odds_by_market


def write_csv(tmp_path: Path, contents: str) -> Path:
    path = tmp_path / "manual_odds.csv"
    path.write_text(contents)
    return path


def test_load_manual_odds_groups_by_market_and_selection(tmp_path: Path):
    contents = (
        "market_id,selection,bookmaker,decimal_odds\n"
        "M-FB-001,home,Bookmaker A,2.10\n"
        "M-FB-001,home,Bookmaker B,2.05\n"
        "M-FB-001,draw,Bookmaker A,3.40\n"
    )
    path = write_csv(tmp_path, contents)
    result = load_manual_odds_by_market(path)

    assert result["M-FB-001"]["home"] == [2.10, 2.05]
    assert result["M-FB-001"]["draw"] == [3.40]


def test_load_manual_odds_multiple_markets(tmp_path: Path):
    contents = (
        "market_id,selection,bookmaker,decimal_odds\n"
        "M-FB-001,home,Bookmaker A,2.10\n"
        "M-TN-001,player_a,Bookmaker A,1.85\n"
    )
    path = write_csv(tmp_path, contents)
    result = load_manual_odds_by_market(path)
    assert set(result.keys()) == {"M-FB-001", "M-TN-001"}


def test_load_manual_odds_rejects_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_manual_odds_by_market(tmp_path / "missing.csv")


def test_load_manual_odds_rejects_missing_columns(tmp_path: Path):
    contents = "market_id,selection\nM-FB-001,home\n"
    path = write_csv(tmp_path, contents)
    with pytest.raises(ValueError):
        load_manual_odds_by_market(path)


def test_load_manual_odds_rejects_non_numeric_odds(tmp_path: Path):
    contents = (
        "market_id,selection,bookmaker,decimal_odds\n"
        "M-FB-001,home,Bookmaker A,not_a_number\n"
    )
    path = write_csv(tmp_path, contents)
    with pytest.raises(ValueError):
        load_manual_odds_by_market(path)


def test_load_manual_odds_skips_blank_rows(tmp_path: Path):
    contents = (
        "market_id,selection,bookmaker,decimal_odds\n"
        "M-FB-001,home,Bookmaker A,2.10\n"
        ",,,\n"
    )
    path = write_csv(tmp_path, contents)
    result = load_manual_odds_by_market(path)
    assert result["M-FB-001"]["home"] == [2.10]
