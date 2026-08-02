"""Tests for performance.brier.

STAGE 1 NOTE: performance/brier.py is a documented placeholder (see
docs/ROADMAP.md, Stage 5). There is no Brier score calculation logic
to test yet — this test only confirms the module imports cleanly so
CI does not silently skip it once real logic is added here.
"""

import importlib


def test_brier_module_imports_without_error():
    module = importlib.import_module("prediction_markets_lab.performance.brier")
    assert module is not None
