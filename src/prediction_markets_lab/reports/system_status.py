"""Machine-readable production system-health status (Section 12,
Production Infrastructure Build, 2026-09-20).

The critical distinction this file exists for: "No bets qualified today"
(the engine ran correctly and found nothing worth recommending -- a
valid, expected outcome) versus "The scanner failed" (the engine did NOT
run correctly, and the absence of recommendations means nothing). Without
this file, both look identical from ChatGPT's point of view -- an empty
or missing card.json. status/latest.json exists so ChatGPT can tell them
apart and say so.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class SystemStatus:
    last_scan_at: str
    last_scan_status: str  # "success" | "failure" | "unknown"
    last_scan_candidates: int | None
    last_scan_qualified_count: int | None
    last_settlement_at: str
    last_settlement_status: str  # "success" | "failure" | "unknown"
    last_performance_update_at: str
    engine_version: str
    unsettled_paper_bet_count: int
    warnings: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "last_scan": {
                "at": self.last_scan_at,
                "status": self.last_scan_status,
                "candidates_analysed": self.last_scan_candidates,
                "qualified_count": self.last_scan_qualified_count,
            },
            "last_settlement": {
                "at": self.last_settlement_at,
                "status": self.last_settlement_status,
            },
            "last_performance_update_at": self.last_performance_update_at,
            "engine_version": self.engine_version,
            "unsettled_paper_bet_count": self.unsettled_paper_bet_count,
            "warnings": self.warnings,
        }
