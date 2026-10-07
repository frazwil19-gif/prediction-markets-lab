import importlib.util
from datetime import datetime, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location("g", Path(__file__).resolve().parents[2] / "scripts/recent_run_guard.py")
G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
NOW = datetime(2026, 10, 10, 13, 0, tzinfo=timezone.utc)
RUNS = [{"id": 1, "conclusion": "success", "run_started_at": "2026-10-10T06:16:00Z"},
        {"id": 2, "conclusion": "failure", "run_started_at": "2026-10-10T12:00:00Z"}]


def test_guard_rules():
    assert G.should_skip(RUNS, NOW, 10, "schedule", "0 7 * * *", [], 99) is True          # dispatched run 6.7 h ago succeeded
    assert G.should_skip(RUNS, NOW, 6, "schedule", "0 7 * * *", [], 99) is False         # outside the window
    assert G.should_skip(RUNS, NOW, 10, "workflow_dispatch", "", [], 99) is False        # dispatch never skipped
    assert G.should_skip(RUNS, NOW, 10, "schedule", "30 22 * * *", ["30 22 * * *"], 99) is False   # exempt slot
    assert G.should_skip(RUNS[1:], NOW, 10, "schedule", "0 7 * * *", [], 99) is False    # failures don't count
