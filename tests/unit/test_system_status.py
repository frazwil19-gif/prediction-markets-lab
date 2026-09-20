"""Tests for reports.system_status (Production Infrastructure Build, 2026-09-20)."""

from __future__ import annotations

from prediction_markets_lab.reports.system_status import SystemStatus


def test_to_dict_shape():
    status = SystemStatus(
        last_scan_at="2026-09-20T07:00:00",
        last_scan_status="success",
        last_scan_candidates=193,
        last_scan_qualified_count=9,
        last_settlement_at="",
        last_settlement_status="unknown",
        last_performance_update_at="",
        engine_version="daily-engine-v1.1.0-odds-api",
        unsettled_paper_bet_count=9,
    )
    d = status.to_dict()
    assert d["last_scan"]["status"] == "success"
    assert d["last_scan"]["candidates_analysed"] == 193
    assert d["unsettled_paper_bet_count"] == 9
    assert d["last_settlement"]["status"] == "unknown"
    assert d["engine_version"] == "daily-engine-v1.1.0-odds-api"


def test_warnings_default_empty():
    status = SystemStatus(
        last_scan_at="",
        last_scan_status="unknown",
        last_scan_candidates=None,
        last_scan_qualified_count=None,
        last_settlement_at="",
        last_settlement_status="unknown",
        last_performance_update_at="",
        engine_version="v1",
        unsettled_paper_bet_count=0,
    )
    assert status.to_dict()["warnings"] == []
