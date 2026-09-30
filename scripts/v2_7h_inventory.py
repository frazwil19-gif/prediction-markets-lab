"""V2-7H data inventory (counts and coverage only -- no outcome-dependent statistics). Research only."""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
U = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/mnt/user-data/uploads/prediction-markets-lab/data")
OUT = REPO / "research/platform_v2/card_backtest_v2_7h/DATA_INVENTORY.json"


def main() -> int:
    inv: dict = {}
    for tour, f in (("ATP", "data/interim/v2_tennis_market_dataset.csv"), ("WTA", "data/interim/v2_wta_market_dataset.csv")):
        t = pd.read_csv(REPO / f)
        inv[f"tennis_{tour}_betfair_basic"] = {
            "file": f, "rows": len(t), "events": int(t.match_id.nunique()), "years": t.year.value_counts().sort_index().to_dict(),
            "date_range": [t.scheduled_start.min()[:10], t.scheduled_start.max()[:10]],
            "prediction": "frozen engine P = multiplicative de-vig of Betfair LTP at/before T-30 min",
            "outcome": int(t.outcome_a_won.notna().sum()), "odds": "Betfair LTP both runners (same source as P)",
            "timestamp_semantics": "LTP at/before T-30 min of scheduled start; ~1% contaminated when match started early (V2-6D)",
            "executable": "no (LTP is not a back price; no bookmakers)",
            "suitability": {"A_probability": True, "B_indicative_price": False, "C_executable_profitability": False}}
    td = U / "raw/tennis/tennis_data_co_uk"
    for tour in ("atp", "wta"):
        n = {}
        cols = set()
        for y in range(2021, 2026):
            x = pd.read_excel(td / f"tennis_data_{tour}_{y}.xlsx")
            n[y] = len(x)
            cols |= {c for c in x.columns if c.endswith("W") and c[:-1] + "L" in x.columns and c not in ("W",)}
        inv[f"tennis_{tour.upper()}_tennis_data_co_uk"] = {
            "files": f"{td}/tennis_data_{tour}_2021..2025.xlsx (gitignored; hashes in historical_v2_6h/tennis_data_co_uk)",
            "rows_by_year": n, "price_columns": sorted(cols),
            "linkage_to_betfair_rows": "ATP 88.2% / WTA 89.2% unique, 0 ambiguous, winner agreement 99.95% (V2-6D)",
            "timestamp_semantics": "CLOSING ONLY ('most recent before play starts'), no timestamps",
            "known_issues": "corrupt price rows leak outcomes -> validity screen (both > 1.01, overround 0.98-1.20); BFE only ~5% (2025)",
            "executable": "B365/PS closing = named-book closing quote (indicative of close, not decision-time)",
            "suitability": {"A_probability": True, "B_indicative_price": "CLOSING-PRICE DIAGNOSTIC only (P from PS close, price B365 close)",
                            "C_executable_profitability": False}}
    nb = []
    for f in sorted(glob.glob(str(U / "raw/basketball/wippa_nba/nba_*_results_odds.csv"))):
        x = pd.read_csv(f)
        x["season"] = Path(f).stem.split("_")[1]
        nb.append(x)
    n = pd.concat(nb)
    reg = n[(n["round"].astype(str) != "Pre-season") & (n.is_allstar.astype(str) != "True")] if "is_allstar" in n else n[n["round"].astype(str) != "Pre-season"]
    inv["nba_wippa_oddsportal"] = {
        "files": "raw/basketball/wippa_nba/nba_<season>_results_odds.csv", "rows": len(n), "non_preseason_rows": len(reg),
        "seasons": reg.season.value_counts().sort_index().to_dict(), "missing_seasons": ["2019-2020", "2020-2021"],
        "prediction": "frozen engine P = proportional de-vig of the average closing moneyline",
        "odds": "one AVERAGE closing price per side (OddsPortal), no per-book", "timestamp_semantics": "closing, untimestamped",
        "executable": "no", "suitability": {"A_probability": True, "B_indicative_price": False, "C_executable_profitability": False}}
    fb = U / "processed/football"
    b = pd.concat([pd.read_csv(fb / "cycle_001_bookmaker_markets_full.csv"), pd.read_csv(fb / "h_fb2_002_sealed_oos_2025_26_bookmaker_markets.csv")])
    m = pd.concat([pd.read_csv(fb / "cycle_001_matches_full.csv"), pd.read_csv(fb / "h_fb2_002_sealed_oos_2025_26_matches.csv")]).drop_duplicates("match_id")
    inv["football_1x2_football_data_co_uk"] = {
        "files": "processed/football/cycle_001_* + h_fb2_002_sealed_oos_2025_26_*", "matches": int(m.match_id.nunique()),
        "by_season_competition": {f"{s}|{c}": int(v) for (s, c), v in m.groupby(["season", "competition_code"]).size().items()},
        "book_rows_by_snapshot": {f"{t}|{bk}": int(v) for (t, bk), v in b.groupby(["price_timing", "bookmaker"]).size().items()},
        "prediction": "frozen engine P = median across >=3 books of per-book proportional fair probabilities, SAME snapshot",
        "timestamp_semantics": "'opening' = football-data pre-closing collection (Fri for weekend, Tue for midweek); 'closing' = at kick-off; no exact times",
        "executable": "per-book named quotes at each snapshot (UK primary: B365, WH, BW, BF[2024/25, 5% comm]); availability at stake not verified",
        "known_issues": "single-book outlier quotes (V2-6H); 2025/26 has no WH/BF; 2025/26 file was a sealed OOS set already opened by V2-6H",
        "suitability": {"A_probability": True, "B_indicative_price": True,
                        "C_executable_profitability": "closest available: same-snapshot per-book singles; multis INDICATIVE (no acca prices)"}}
    inv["prospective_live_files"] = {
        "tennis_predictions/*, paper_betting_v2/*, V2-7 prospective/": "EXCLUDED from V2-7H (independent prospective evidence streams; rule P)"}
    inv["previous_research_outputs_used_as_reference_only"] = [
        "research/platform_v2/historical_v2_6h/* (V2-6H, V2-6D)", "research/platform_v2/card_engine_v2_7/RESULTS.json (Phase 1 A1/A2/B)"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(inv, indent=1, default=str))
    print(json.dumps({k: {kk: v for kk, v in d.items() if kk in ("rows", "events", "matches", "non_preseason_rows", "rows_by_year")}
                      for k, d in inv.items() if isinstance(d, dict)}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
