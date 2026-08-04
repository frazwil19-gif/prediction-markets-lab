from pathlib import Path

import pytest

from prediction_markets_lab.ingestion.exchange_price_loader import (
    best_price_for_selection,
    load_exchange_prices,
)


def write_csv(tmp_path: Path, contents: str) -> Path:
    path = tmp_path / "exchange_prices.csv"
    path.write_text(contents)
    return path


def test_load_exchange_prices_parses_rows(tmp_path: Path):
    contents = (
        "market_id,exchange,selection,decimal_odds,available_size_gbp,commission,notes\n"
        "M-FB-001,Smarkets,home,2.20,150.00,0.02,\n"
        "M-FB-001,Betfair,home,2.18,500.00,0.05,\n"
    )
    path = write_csv(tmp_path, contents)
    prices = load_exchange_prices(path)
    assert len(prices) == 2
    assert prices[0].exchange == "Smarkets"
    assert prices[0].decimal_odds == pytest.approx(2.20)


def test_load_exchange_prices_rejects_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_exchange_prices(tmp_path / "missing.csv")


def test_load_exchange_prices_rejects_invalid_numeric_value(tmp_path: Path):
    contents = (
        "market_id,exchange,selection,decimal_odds,available_size_gbp,commission,notes\n"
        "M-FB-001,Smarkets,home,not_a_number,150.00,0.02,\n"
    )
    path = write_csv(tmp_path, contents)
    with pytest.raises(ValueError):
        load_exchange_prices(path)


def test_best_price_for_selection_picks_highest_odds_with_size():
    prices = load_exchange_prices_from_string(
        "market_id,exchange,selection,decimal_odds,available_size_gbp,commission,notes\n"
        "M-FB-001,Smarkets,home,2.20,150.00,0.02,\n"
        "M-FB-001,Betfair,home,2.25,0.00,0.05,\n"  # better odds but no size
        "M-FB-001,Betfair,home,2.18,500.00,0.05,\n"
    )
    best = best_price_for_selection(prices, "M-FB-001", "home")
    assert best is not None
    assert best.exchange == "Smarkets"
    assert best.decimal_odds == pytest.approx(2.20)


def test_best_price_for_selection_returns_none_when_no_match():
    prices = load_exchange_prices_from_string(
        "market_id,exchange,selection,decimal_odds,available_size_gbp,commission,notes\n"
        "M-FB-001,Smarkets,home,2.20,150.00,0.02,\n"
    )
    assert best_price_for_selection(prices, "M-FB-002", "away") is None


def load_exchange_prices_from_string(contents: str):
    import tempfile
    from pathlib import Path as P

    with tempfile.TemporaryDirectory() as d:
        path = P(d) / "prices.csv"
        path.write_text(contents)
        return load_exchange_prices(path)
